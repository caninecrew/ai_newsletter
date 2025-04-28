import feedparser
import requests
import time
import random
import re
import ssl  # Added import
import certifi # Added import
from datetime import datetime, timezone, timedelta
import concurrent.futures
from bs4 import BeautifulSoup
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from webdriver_pool import get_driver, USER_AGENTS, WebDriverPool # Import USER_AGENTS and WebDriverPool
from dateutil import parser as dateutil_parser, tz as dateutil_tz
import threading
import hashlib
from urllib.parse import urlparse, parse_qs, urlunparse, unquote, urlencode # Added urlencode, parse_qs
from collections import defaultdict # Added import
from difflib import SequenceMatcher # Added import
from google_redirect import resolve_google_redirect_selenium # Import Google redirect resolver

# --- Local Imports ---
from logger_config import setup_logger # Import logger setup
from config import ( # Import config settings and feed lists
    SYSTEM_SETTINGS,
    USER_INTERESTS,
    PRIMARY_NEWS_FEEDS,
    SECONDARY_FEEDS,
    SUPPLEMENTAL_FEEDS,
    PROBLEM_SOURCES # Assuming PROBLEM_SOURCES is defined in config.py
)

# --- Setup ---
logger = setup_logger() # Initialize logger
CENTRAL = dateutil_tz.gettz('America/Chicago') or timezone.utc # Ensure CENTRAL is defined

# --- Metrics Initialization ---
FETCH_METRICS = defaultdict(lambda: 0) # Initialize metrics
FETCH_METRICS['failed_sources'] = []
FETCH_METRICS['empty_sources'] = []
FETCH_METRICS['source_statistics'] = defaultdict(lambda: {'articles': 0, 'fetch_time': 0.0, 'success': 0, 'failures': 0})
FETCH_METRICS['pool_timeouts'] = 0
# --------------------------

# --- Concurrency Control ---
# Set concurrency limit based on WebDriver pool size
CONCURRENCY_LIMIT = WebDriverPool._POOL_SIZE  # Access _POOL_SIZE through the class
selenium_semaphore = threading.Semaphore(CONCURRENCY_LIMIT)
logger.info(f"Selenium concurrency limit set to: {CONCURRENCY_LIMIT}")
# ---------------------------

# Domains to try with Requests first
REQUESTS_FIRST_DOMAINS = [
    "reuters.com",
    "apnews.com",
    "businesswire.com",
    # Add other domains known to work well with requests or block Selenium
]

# --- Global Variables & Sets ---
attempted_urls = set() # Track URLs attempted in this run
failed_urls = set() # Track URLs that failed all fetch attempts
unique_article_urls = set() # Track unique normalized URLs seen across all feeds
source_performance = defaultdict(lambda: {'total_time': 0.0, 'attempts': 0, 'successes': 0}) # Track performance per source
# -----------------------------

# --- Helper Functions ---

def create_secure_session():
    """Creates a requests session with updated TLS settings and certifi."""
    session = requests.Session()
    # Use certifi's CA bundle
    session.verify = certifi.where()
    # Optional: Configure adapters with specific SSL context if needed,
    # but session.verify usually suffices for CA verification.
    # adapter = requests.adapters.HTTPAdapter()
    # session.mount('https://', adapter)
    return session

def configure_feedparser():
    """Configures feedparser to use certifi for SSL verification."""
    # Create an SSL context using certifi's CA bundle
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    ssl_context.check_hostname = True # Ensure hostname checking is enabled
    ssl_context.verify_mode = ssl.CERT_REQUIRED
    # Enforce TLS 1.2 or higher if necessary (usually default context is good)
    # ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2

    # Set feedparser's global handlers to use this context
    # Note: feedparser might not directly expose easy SSL context injection globally.
    # If direct fetching within feedparser fails due to SSL, consider fetching
    # the feed content with 'requests' first, then parsing the string content.
    # For now, rely on system/requests handling unless specific errors arise.
    logger.info("Feedparser configured to use system/requests SSL handling with certifi.")
    # feedparser.RESOLVE_RELATIVE_URIS = False # Example configuration if needed

# Initialize session and configure feedparser
secure_session = create_secure_session()
configure_feedparser()

def should_skip_source(url: str) -> bool:
    """Checks if the source domain is in the problematic list."""
    try:
        domain = urlparse(url).netloc
        # Check if the domain itself or a parent domain is blocked
        parts = domain.split('.')
        for i in range(len(parts)):
            sub_domain = '.'.join(parts[i:])
            if sub_domain in PROBLEM_SOURCES:
                logger.debug(f"Skipping problematic source based on domain: {domain} (matched {sub_domain})")
                return True
    except Exception as e:
        logger.warning(f"Error parsing URL {url} in should_skip_source: {e}")
    return False

def force_central(dt_obj, url_for_logging=""):
    """Converts aware or naive datetime to Central Time (CT), handling errors."""
    # ... (rest of force_central function - no changes needed based on errors) ...
    pass

def normalize_url(url: str) -> str:
    """Normalizes a URL by removing common tracking parameters and fragments."""
    try:
        url = url.strip()
        parsed = urlparse(url)
        # Common tracking parameters (add more as needed)
        tracking_params = {'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
                           'fbclid', 'gclid', 'mc_cid', 'mc_eid', '_ga', 'ICID', 'ncid', 'ref'}
        # Filter query parameters
        query_params = parse_qs(parsed.query, keep_blank_values=True)
        filtered_params = {k: v for k, v in query_params.items() if k.lower() not in tracking_params}
        # Rebuild query string
        clean_query = urlencode(filtered_params, doseq=True)
        # Reconstruct URL without fragment and with cleaned query
        normalized = urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, clean_query, ''))
        return normalized.lower() # Lowercase for consistency
    except Exception as e:
        logger.warning(f"Failed to normalize URL {url}: {e}")
        return url.strip().lower() # Fallback to simple strip and lower

def is_duplicate_article(title, link, existing_articles, similarity_threshold=0.9):
    """Checks for duplicate articles based on URL or title similarity."""
    normalized_link = normalize_url(link)
    for existing in existing_articles:
        if normalize_url(existing['link']) == normalized_link:
            return True
        # Check title similarity if links differ slightly (e.g., http vs https)
        cached_title = existing.get('title', '')
        if title and cached_title:
             # Use SequenceMatcher for title comparison
            if SequenceMatcher(None, title.lower(), cached_title.lower()).ratio() > similarity_threshold:
                logger.debug(f"Potential duplicate detected based on title similarity ({link} vs {existing['link']})")
                return True # Consider it a duplicate if titles are very similar
    return False

def print_metrics_summary():
    """Generates a string summary of the fetch metrics."""
    summary = ["\n--- Fetch Metrics Summary ---"]
    summary.append(f"Sources Checked: {FETCH_METRICS['sources_checked']}")
    summary.append(f"Successful Sources: {FETCH_METRICS['successful_sources']}")
    summary.append(f"Empty Sources: {len(FETCH_METRICS['empty_sources'])}")
    summary.append(f"Failed Sources: {len(FETCH_METRICS['failed_sources'])}")
    if FETCH_METRICS['failed_sources']:
        summary.append(f"  Failed List: {', '.join(FETCH_METRICS['failed_sources'])}")
    summary.append(f"Total Articles Found (Initial): {FETCH_METRICS['total_articles']}")
    summary.append(f"Duplicate Articles Skipped: {FETCH_METRICS['duplicate_articles']}")
    summary.append(f"Content Fetch Attempts: {FETCH_METRICS.get('content_attempts', 0)}")
    summary.append(f"Content Fetch Success (Requests): {FETCH_METRICS.get('content_success_requests', 0)}")
    summary.append(f"Content Fetch Success (Selenium): {FETCH_METRICS.get('content_success_selenium', 0)}")
    summary.append(f"Content Fetch Failures: {len(failed_urls)}")
    summary.append(f"WebDriver Pool Timeouts: {FETCH_METRICS['pool_timeouts']}")
    summary.append(f"Total Processing Time: {FETCH_METRICS.get('processing_time', 0):.2f} seconds")
    summary.append("---------------------------")
    return "\n".join(summary)

# --- Core Fetching Logic ---

def fetch_rss_feed(feed_url, source_name, max_articles=5):
    """Fetches and parses an RSS feed, returning a list of article dicts."""
    logger.info(f"Fetching RSS feed: {source_name} ({feed_url})")
    FETCH_METRICS['sources_checked'] += 1
    articles = []
    unique_article_urls_in_feed = set() # Track URLs within this specific feed

    try:
        # Use requests to fetch, then parse with feedparser for better SSL control
        headers = {'User-Agent': random.choice(USER_AGENTS)}
        response = secure_session.get(feed_url, timeout=20, headers=headers)
        response.raise_for_status()

        # Check content type - feedparser might handle non-XML, but good practice
        content_type = response.headers.get('content-type', '').lower()
        if 'xml' not in content_type and 'rss' not in content_type and 'atom' not in content_type:
             logger.warning(f"Unexpected content type '{content_type}' for feed {source_name}. Attempting parse anyway.")

        # Parse the content
        feed = feedparser.parse(response.content) # Parse bytes content

        if feed.bozo:
            logger.warning(f"Feedparser encountered issues (bozo=1) for {source_name}: {feed.bozo_exception}")
            # Still try to process entries if available
            if not feed.entries:
                 FETCH_METRICS['failed_sources'].append(f"{source_name} (Bozo/No Entries)")
                 return [] # Return empty if parsing truly failed

        if not feed.entries:
            logger.warning(f"No entries found in feed: {source_name}")
            FETCH_METRICS['empty_sources'].append(source_name)
            return []

        count = 0
        for entry in feed.entries:
            if count >= max_articles:
                break

            title = entry.get('title', 'No Title')
            link = entry.get('link')
            published = entry.get('published_parsed') or entry.get('updated_parsed')

            if not link:
                logger.warning(f"Skipping entry with no link in {source_name}: '{title}'")
                continue

            # --- Handle Google News URLs ---
            original_link = link
            if "news.google.com" in link:
                extracted = resolve_google_redirect_selenium(link)
                if extracted:
                    logger.debug(f"Extracted Google News URL: {link} -> {extracted}")
                    link = extracted
                else:
                    logger.warning(f"Could not extract final URL from Google News link: {link}. Using original.")
            # -------------------------------

            # Check if URL already processed globally or within this feed
            normalized_link = normalize_url(link)
            if normalized_link in unique_article_urls or normalized_link in unique_article_urls_in_feed:
                logger.debug(f"Skipping duplicate article URL (already seen): {link}")
                FETCH_METRICS['duplicate_articles'] = FETCH_METRICS.get('duplicate_articles', 0) + 1
                continue
            unique_article_urls.add(normalized_link)
            unique_article_urls_in_feed.add(normalized_link)


            # Convert published time to Central Time
            published_date = force_central(published, link) if published else None

            # Basic interest check (optional, can be done later)
            relevant = True # Default to relevant
            if USER_INTERESTS: # Check only if interests are defined
                relevant = any(interest.lower() in title.lower() for interest in USER_INTERESTS)

            if relevant:
                articles.append({
                    'title': title.strip(),
                    'link': link,
                    'original_google_link': original_link if link != original_link else None,
                    'published': published_date,
                    'source': source_name,
                    'feed_url': feed_url,
                    'content': None, # Content fetched later
                    'fetch_method': None,
                    'id': hashlib.sha256(link.encode()).hexdigest()[:16] # Generate unique ID
                })
                count += 1
            else:
                 logger.debug(f"Skipping article not matching interests: '{title}' from {source_name}")


        if articles:
            FETCH_METRICS['successful_sources'] += 1
            FETCH_METRICS['total_articles'] += len(articles)
            # Update source statistics
            stats = FETCH_METRICS['source_statistics'][source_name]
            stats['articles'] += len(articles)
            logger.info(f"Successfully fetched {len(articles)} articles from {source_name}")
        elif not feed.bozo: # Only mark as empty if not already marked as failed (bozo)
             FETCH_METRICS['empty_sources'].append(source_name)


    except requests.exceptions.Timeout:
        logger.error(f"Timeout fetching RSS feed: {source_name} ({feed_url})")
        FETCH_METRICS['failed_sources'].append(f"{source_name} (Timeout)")
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching RSS feed {source_name} ({feed_url}): {e}")
        FETCH_METRICS['failed_sources'].append(f"{source_name} (Request Error)")
    except Exception as e:
        logger.error(f"Unexpected error processing feed {source_name} ({feed_url}): {e}", exc_info=True)
        if source_name not in FETCH_METRICS['failed_sources']: # Avoid double counting
             FETCH_METRICS['failed_sources'].append(f"{source_name} (Parse Error)")

    return articles

def fetch_article_content(article, max_retries=2):
    """Fetches article content, trying Requests first for specific domains."""
    url = article['link']
    source_domain = urlparse(url).netloc
    source_name = article.get('source', 'Unknown Source') # Get source name for stats

    if url in attempted_urls:
        logger.debug(f"Skipping already attempted URL: {url}")
        return article # Avoid re-fetching
    attempted_urls.add(url)
    FETCH_METRICS['content_attempts'] = FETCH_METRICS.get('content_attempts', 0) + 1


    start_time = time.time()
    content = None
    fetch_method = "None"
    success = False

    # --- Requests-First Strategy ---
    if any(domain in source_domain for domain in REQUESTS_FIRST_DOMAINS):
        logger.debug(f"Attempting fetch with Requests for {url}")
        try:
            headers = {"User-Agent": random.choice(USER_AGENTS)}
            response = secure_session.get(url, timeout=15, headers=headers, allow_redirects=True)
            response.raise_for_status()

            if response.status_code == 200 and response.text:
                content_type = response.headers.get('content-type', '').lower()
                if 'html' in content_type:
                    soup = BeautifulSoup(response.text, 'lxml')
                    body = soup.find('body')
                    if body:
                        for script_or_style in body(['script', 'style']):
                            script_or_style.decompose()
                        extracted_text = body.get_text(separator='\n', strip=True)
                        if extracted_text and len(extracted_text) > 100:
                            content = extracted_text
                            article['content'] = content
                            fetch_method = "Requests"
                            success = True
                            FETCH_METRICS['content_success_requests'] = FETCH_METRICS.get('content_success_requests', 0) + 1
                            logger.info(f"Successfully fetched content with Requests: {url}")
                        else:
                            logger.debug(f"Requests fetch succeeded but content extraction failed/short for {url}")
                    else:
                         logger.debug(f"No body tag found in Requests response for {url}")
                else:
                    logger.warning(f"Skipping non-HTML content from Requests for {url} (Content-Type: {content_type})")
            else:
                 logger.warning(f"Requests fetch for {url} returned status {response.status_code}")

        except requests.exceptions.RequestException as e:
            logger.warning(f"Requests fetch failed for {url}: {e}. Falling back to Selenium if needed.")
        except Exception as e:
             logger.error(f"Unexpected error during Requests fetch for {url}: {e}")
    # -------------------------------

    # --- Fallback to Selenium ---
    if content is None and SYSTEM_SETTINGS.get("use_selenium_fetch", True):
        if should_skip_source(url):
            logger.info(f"Skipping Selenium fetch for problematic source: {url}")
        else:
            logger.debug(f"Falling back to Selenium for {url}")
            with selenium_semaphore:
                logger.debug(f"Acquired semaphore for Selenium fetch: {url}")
                try:
                    # Pass FETCH_METRICS to the selenium function if it needs to update specific counters
                    article_result = fetch_article_content_with_selenium(article, max_retries=max_retries)
                    # Check if content was added by the selenium function
                    if article_result.get('content') and not success: # Ensure we don't double count success
                        fetch_method = "Selenium"
                        success = True
                        FETCH_METRICS['content_success_selenium'] = FETCH_METRICS.get('content_success_selenium', 0) + 1
                        article = article_result # Update article with content
                finally:
                     logger.debug(f"Released semaphore for Selenium fetch: {url}")
            if not success: # Check if Selenium also failed
                 logger.warning(f"Selenium fetch also failed to get content for {url}")
                 # failed_urls.add(url) # Add to failed list only after all methods tried

    elif content is None:
         logger.warning(f"Failed to fetch content for {url} (Requests failed/skipped, Selenium disabled/skipped)")
         # failed_urls.add(url) # Add to failed list only after all methods tried

    # --- Update Stats ---
    end_time = time.time()
    duration = end_time - start_time
    stats = FETCH_METRICS['source_statistics'][source_name]
    stats['fetch_time'] += duration
    if success:
        stats['success'] += 1
    else:
        stats['failures'] += 1
        failed_urls.add(url) # Add to failed list if both methods failed

    article['fetch_method'] = fetch_method # Record how content was fetched (or attempted)

    # --- Age Categorization ---
    if article.get('published'):
        article['age_category'] = categorize_article_age(article['published'])
    else:
        article['age_category'] = 'Unknown'
    # ------------------------

    return article


def fetch_article_content_with_selenium(article, max_retries=3, base_delay=3):
    """
    Fetch article content using Selenium WebDriver from the pool.
    Includes exponential backoff and domain-aware driver management.
    """
    url = article['link']
    domain = urlparse(url).netloc

    for attempt in range(max_retries):
        try:
            # Use the get_driver context manager with domain awareness
            with get_driver(domain=domain) as driver:
                if attempt > 0:
                    delay = base_delay * (2 ** (attempt - 1)) + random.uniform(0, 1.5)
                    logger.info(f"Retry attempt {attempt + 1}/{max_retries} for {url}, waiting {delay:.1f}s")
                    time.sleep(delay)

                logger.debug(f"Selenium attempt {attempt + 1}: Loading {url}")
                driver.get(url)

                try:
                    # Wait for either article content or body
                    content_selectors = ["article", "main", ".main-content", ".post-content", "#content", "#main", ".entry-content", ".article-body"]
                    for selector in content_selectors:
                        try:
                            element = WebDriverWait(driver, 15).until(
                                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                            )
                            if element.is_displayed() and len(element.text) > 150:
                                content = element.text
                                article['content'] = content
                                logger.info(f"Successfully fetched content with WebDriver (attempt {attempt + 1}): {url}")
                                return article
                        except TimeoutException:
                            continue

                    # Fallback to body if no content selectors worked
                    body = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.TAG_NAME, "body"))
                    )
                    content = body.text
                    
                    if content and len(content) > 150:
                        article['content'] = content
                        logger.info(f"Successfully fetched content from body with WebDriver (attempt {attempt + 1}): {url}")
                        return article
                    else:
                        logger.warning(f"Content too short from body, retrying: {url}")
                        continue

                except TimeoutException as te:
                    if attempt == max_retries - 1:  # Last attempt
                        logger.error(f"All timeouts exhausted for {url}: {te}")
                        break
                    logger.warning(f"Timeout waiting for content on {url} (attempt {attempt + 1})")
                    continue

        except (TimeoutException, WebDriverException) as e:
            if "ERR_TOO_MANY_REQUESTS" in str(e) or "403" in str(e) or "401" in str(e):
                logger.warning(f"Rate limited or blocked by {domain}, falling back to requests: {e}")
                # Try with requests as fallback
                try:
                    headers = {'User-Agent': random.choice(USER_AGENTS)}
                    response = secure_session.get(url, timeout=15, headers=headers, allow_redirects=True)
                    response.raise_for_status()
                    
                    soup = BeautifulSoup(response.text, 'lxml')
                    for element in soup(['script', 'style', 'nav', 'footer', 'header']):
                        element.decompose()
                    
                    content = soup.get_text(separator='\n', strip=True)
                    if content and len(content) > 150:
                        article['content'] = content
                        article['fetch_method'] = 'Requests (fallback)'
                        return article
                except Exception as req_err:
                    logger.error(f"Requests fallback also failed for {url}: {req_err}")
            
            if attempt < max_retries - 1:  # Not the last attempt
                logger.warning(f"WebDriver error (attempt {attempt + 1}) for {url}: {e}")
                continue
            else:
                logger.error(f"All WebDriver attempts failed for {url}: {e}")
                break

    return article  # Return article without content if all attempts fail


def fetch_news_articles(rss_feeds, fetch_content=True, max_articles_per_feed=5, max_workers=None):
    """Fetches articles from RSS feeds and optionally their content in parallel."""
    start_time = time.time()
    all_articles = []
    unique_article_urls.clear() # Reset global set for this run
    attempted_urls.clear() # Reset attempted URLs for this run
    failed_urls.clear() # Reset failed URLs for this run

    # Reset metrics for this run (keep structure, reset values)
    global FETCH_METRICS
    FETCH_METRICS = defaultdict(lambda: 0)
    FETCH_METRICS['failed_sources'] = []
    FETCH_METRICS['empty_sources'] = []
    FETCH_METRICS['source_statistics'] = defaultdict(lambda: {'articles': 0, 'fetch_time': 0.0, 'success': 0, 'failures': 0})
    FETCH_METRICS['pool_timeouts'] = 0


    # Deduplicate feed URLs (using url as key, keep first source_name)
    unique_feeds = {url: name for name, url in reversed(rss_feeds.items())}
    logger.info(f"Processing {len(unique_feeds)} unique feed URLs from {len(rss_feeds)} initial sources.")

    # Adjust max_workers based on CONCURRENCY_LIMIT if not specified
    if max_workers is None:
        # Set slightly higher than semaphore limit to keep queue full, but not excessively so
        max_workers = CONCURRENCY_LIMIT + 2 # For feed fetching (I/O bound)
        logger.info(f"Adjusting max_workers for Feed Fetching ThreadPoolExecutor to {max_workers}")

    # Process feeds in parallel (fetching RSS is usually I/O bound)
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix='FeedFetcher') as executor:
        future_to_feed = {executor.submit(fetch_rss_feed, url, name, max_articles_per_feed): name for name, url in unique_feeds.items()}
        for future in concurrent.futures.as_completed(future_to_feed):
            source_name = future_to_feed[future]
            try:
                articles_from_feed = future.result()
                if articles_from_feed:
                    # Filter duplicates based on global list before adding
                    new_articles = [a for a in articles_from_feed if not is_duplicate_article(a['title'], a['link'], all_articles)]
                    all_articles.extend(new_articles)
                    # Update duplicate count based on filtering
                    duplicates_filtered = len(articles_from_feed) - len(new_articles)
                    if duplicates_filtered > 0:
                         FETCH_METRICS['duplicate_articles'] += duplicates_filtered
                         logger.debug(f"Filtered {duplicates_filtered} duplicates from {source_name} after fetch.")

            except Exception as exc:
                logger.error(f"Feed fetch task for {source_name} generated an exception: {exc}", exc_info=True)
                if source_name not in FETCH_METRICS['failed_sources']: # Ensure it's marked as failed
                    FETCH_METRICS['failed_sources'].append(f"{source_name} (Task Error)")


    logger.info(f"Found {len(all_articles)} unique articles from feeds.")

    # Fetch full content if requested
    if fetch_content and all_articles:
        logger.info(f"Fetching full content for {len(all_articles)} articles...")
        processed_articles = []
        # Adjust workers for content fetching - limited by selenium_semaphore anyway
        content_max_workers = CONCURRENCY_LIMIT + 4 # Allow more threads to wait on semaphore/IO
        logger.info(f"Adjusting max_workers for Content Fetching ThreadPoolExecutor to {content_max_workers}")

        with concurrent.futures.ThreadPoolExecutor(max_workers=content_max_workers, thread_name_prefix='ContentFetcher') as executor:
            future_to_article = {executor.submit(fetch_article_content, article): article for article in all_articles}
            for future in concurrent.futures.as_completed(future_to_article):
                original_article = future_to_article[future]
                try:
                    processed_article = future.result()
                    processed_articles.append(processed_article)
                except Exception as exc:
                    logger.error(f"Content fetch task for {original_article.get('link')} generated an exception: {exc}", exc_info=True)
                    processed_articles.append(original_article) # Keep original article even if content fetch failed

        all_articles = processed_articles
        logger.info(f"Finished content fetching. {FETCH_METRICS.get('content_success_requests', 0)} via Requests, {FETCH_METRICS.get('content_success_selenium', 0)} via Selenium.")

    elif not all_articles:
         logger.info("No articles found from feeds, skipping content fetch.")


    end_time = time.time()
    processing_time = end_time - start_time
    FETCH_METRICS['processing_time'] = processing_time

    # --- Final Stats Calculation (Example) ---
    # Calculate overall success rate, average times etc. from FETCH_METRICS['source_statistics'] if needed
    # stats = {
    #     'total_articles_final': len([a for a in all_articles if a.get('content')]),
    #     'metrics': dict(FETCH_METRICS) # Convert defaultdicts for easier serialization if needed
    # }
    # -----------------------------------------

    logger.info(f"Total fetch process completed in {processing_time:.2f} seconds.")
    logger.info(print_metrics_summary()) # Print summary at the end

    # Return only the list of articles (stats are logged)
    return all_articles # Return the final list


def combine_feed_sources():
    """Combines primary, secondary, and supplemental feeds based on config."""
    combined_feeds = {}
    combined_feeds.update(PRIMARY_NEWS_FEEDS)
    logger.info(f"Loaded {len(PRIMARY_NEWS_FEEDS)} primary feeds.")

    # Add secondary feeds (always included if defined)
    if SECONDARY_FEEDS:
        count = 0
        for category, feeds in SECONDARY_FEEDS.items():
            combined_feeds.update(feeds)
            count += len(feeds)
        logger.info(f"Loaded {count} secondary feeds.")
    else:
        logger.info("No secondary feeds defined.")


    # Add supplemental feeds only if enabled in config
    if SYSTEM_SETTINGS.get("use_supplemental_feeds", False):
        if SUPPLEMENTAL_FEEDS:
            count = 0
            for category, feeds in SUPPLEMENTAL_FEEDS.items():
                combined_feeds.update(feeds)
                count += len(feeds)
            logger.info(f"Loaded {count} supplemental feeds (enabled).")
        else:
             logger.info("Supplemental feeds enabled, but none defined.")
    else:
        logger.info("Supplemental feeds are disabled in config.")

    logger.info(f"Total unique feed sources to process: {len(combined_feeds)}")
    return combined_feeds


def fetch_articles_from_all_feeds(fetch_content=True, max_articles_per_source=5):
    """Combines feeds and fetches articles."""
    all_feeds = combine_feed_sources()
    if not all_feeds:
        logger.warning("No feed sources defined or loaded. Cannot fetch articles.")
        return []

    # Get settings from config
    max_workers = SYSTEM_SETTINGS.get("max_parallel_workers", CONCURRENCY_LIMIT + 2) # Default based on pool size + buffer
    max_articles = SYSTEM_SETTINGS.get("max_articles_per_feed", max_articles_per_source)

    logger.info(f"Starting article fetch with max_articles_per_feed={max_articles}, max_workers={max_workers}")

    articles = fetch_news_articles(
        rss_feeds=all_feeds,
        fetch_content=fetch_content,
        max_articles_per_feed=max_articles,
        max_workers=max_workers
    )
    return articles


def categorize_article_age(published_date):
    """Categorizes article age relative to now (in Central Time)."""
    if not published_date or not isinstance(published_date, datetime):
        return 'Unknown'

    # Ensure the published date is timezone-aware (assume Central if naive, though force_central should handle this)
    if published_date.tzinfo is None:
        published_date = published_date.replace(tzinfo=CENTRAL)
    else:
        published_date = published_date.astimezone(CENTRAL)

    now_ct = datetime.now(CENTRAL)
    age = now_ct - published_date

    if age < timedelta(hours=6):
        return 'Very Recent (<6h)'
    elif age < timedelta(hours=12):
        return 'Recent (6-12h)'
    elif age < timedelta(days=1):
        return 'Today (<24h)'
    elif age < timedelta(days=2):
        return 'Yesterday (24-48h)'
    else:
        return f'{age.days} days ago'


# --- Test Execution ---
if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.DEBUG, # Use DEBUG for detailed pool/fetch logs during testing
                        format='%(asctime)s - %(levelname)s - [%(threadName)s] - %(message)s')

    logger.info("--- Starting Standalone Fetch Test ---")

    # Ensure pool is initialized for standalone test
    from webdriver_pool import initialize_pool, close_pool
    initialize_pool()

    # Example: Fetch articles with content
    fetched_articles = fetch_articles_from_all_feeds(fetch_content=True, max_articles_per_source=2) # Limit articles per feed for test

    logger.info(f"--- Fetch Test Completed ---")
    logger.info(f"Total articles fetched with content: {len([a for a in fetched_articles if a.get('content')])}")
    logger.info(f"Total articles fetched (including without content): {len(fetched_articles)}")

    # Print details of a few articles
    for i, article in enumerate(fetched_articles[:3]):
        logger.info(f"\nArticle {i+1}:")
        logger.info(f"  Title: {article.get('title')}")
        logger.info(f"  Link: {article.get('link')}")
        logger.info(f"  Source: {article.get('source')}")
        logger.info(f"  Published: {article.get('published')}")
        logger.info(f"  Age Category: {article.get('age_category')}")
        logger.info(f"  Fetch Method: {article.get('fetch_method')}")
        content_preview = (article.get('content') or "")[:100].replace('\n', ' ') + "..." if article.get('content') else "No Content"
        logger.info(f"  Content Preview: {content_preview}")


    # Close the pool when done
    close_pool()
    logger.info("--- WebDriver Pool Closed ---")
