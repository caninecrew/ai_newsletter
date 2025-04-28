import feedparser
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd
from datetime import datetime, timezone, timedelta
import dateutil.parser
import pytz
import re
import time
import random
import logging
import concurrent.futures
from logger_config import setup_logger, FETCH_METRICS, print_metrics_summary
from urllib.parse import urlparse, parse_qs, urlunparse
from config import PRIMARY_NEWS_FEEDS, SECONDARY_FEEDS, SUPPLEMENTAL_FEEDS, BACKUP_RSS_FEEDS, SYSTEM_SETTINGS, USER_INTERESTS
from collections import defaultdict
import certifi
import ssl
import urllib3
import os
import stat
from difflib import SequenceMatcher
import hashlib
from urllib.parse import urlencode
from webdriver_pool import get_driver
from dateutil import parser as dateutil_parser, tz as dateutil_tz

# Get the logger
logger = setup_logger()

# Define the central timezone
CENTRAL = dateutil_tz.gettz("America/Chicago")
# Define DEFAULT_TZ using the same source for compatibility if needed elsewhere, or phase it out.
DEFAULT_TZ = CENTRAL

# Create a secure session for requests
def create_secure_session():
    """
    Create a requests session with proper SSL configuration
    """
    session = requests.Session()
    session.verify = certifi.where()
    
    # Configure modern cipher suites
    ciphers = [
        'ECDHE-ECDSA-AES128-GCM-SHA256',
        'ECDHE-RSA-AES128-GCM-SHA256',
        'ECDHE-ECDSA-AES256-GCM-SHA384',
        'ECDHE-RSA-AES256-GCM-SHA384',
    ]
    
    # Create custom adapter with modern SSL config
    adapter = requests.adapters.HTTPAdapter(
        max_retries=3,
        pool_connections=100,
        pool_maxsize=100
    )
    
    # Mount adapter for both HTTP and HTTPS
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    
    return session

# Configure feedparser SSL context
def configure_feedparser():
    """
    Configure feedparser with secure SSL context
    """
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    ssl_context.verify_mode = ssl.CERT_REQUIRED
    ssl_context.check_hostname = True
    
    # Set minimum TLS version
    ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2
    
    # Update feedparser settings
    feedparser.PREFERRED_XML_PARSERS = ['lxml', 'html.parser']
    feedparser._SOCKET_DEFAULT_KWARGS = {
        'ssl_context': ssl_context,
        'timeout': 10
    }

# Configure SSL at module load
configure_feedparser()

# Create session for reuse
secure_session = create_secure_session()

# Global URL tracking to prevent duplicate attempts
attempted_urls = set()
failed_urls = set()

# Track unique article URLs to prevent duplicates across feeds
unique_article_urls = set()

# List of problematic sources/domains that should be skipped or handled with extra care
PROBLEMATIC_SOURCES = [
    "nytimes.com/section/politics",  # New York Times Politics section
    "cnnunderscored.com",           # CNN Underscored is often problematic
    "nytimes.com/wirecutter",       # NYT Wirecutter has complex JS and paywalls
    "wsj.com",                      # Wall Street Journal has strong paywall
    "washingtonpost.com/opinions",  # Washington Post opinions section
    "bloomberg.com",                # Bloomberg has strict paywall
    "foxnews.com/opinion",          # Fox News opinions often has issues
    "politico.com",                 # Politico - frequently requires login
    "wkrn.com",                     # WKRN - frequently has issues with parsing
    "washingtontimes.com",          # Washington Times - frequently has issues
    "edweek.org",                   # Education Week - SSL issues
    "chronicle.com",                # Chronicle of Higher Education - SSL issues
    "outdoorlife.com",              # Outdoor Life - SSL issues
    "outsideonline.com",            # Outside Online - SSL issues
    "rssfeeds.tennessean.com",      # The Tennessean - SSL issues
    "newschannel5.com",             # News Channel 5 Nashville - SSL issues
    "johnsoncitypress.com"          # Johnson City Press - Rate limiting issues
]

# Performance tracking and statistics
source_performance = defaultdict(lambda: {'avg_time': 0, 'success_rate': 0, 'attempts': 0})

# URL and content deduplication caching
article_cache = {
    'urls': set(),
    'title_hashes': set(),
    'content_hashes': set(),
    'last_cleanup': time.time()
}

def should_skip_source(url):
    """
    Determine if a source should be skipped based on known problematic sources.
    
    Args:
        url (str): The URL to check
        
    Returns:
        bool: True if the source should be skipped, False otherwise
    """
    for problem_source in PROBLEMATIC_SOURCES:
        if problem_source in url:
            logger.info(f"Skipping known problematic source: {url}")
            return True
    return False

def force_central(dt_str: str, url: str = None) -> datetime:
    """
    Parse a date string into a timezone-aware datetime object in Central Time.
    Falls back to current Central Time if parsing fails.

    Args:
        dt_str (str): The date string to parse.
        url (str): Optional URL for logging context.

    Returns:
        datetime: A timezone-aware datetime object in Central Time.
    """
    if not dt_str:
        logger.warning(f"Empty date string received{' for ' + url if url else ''}. Using current time.")
        return datetime.now(tz=CENTRAL)

    original_date_str = dt_str
    try:
        # Handle "X time ago" format first
        time_ago_match = re.search(r'(\d+)\s+(minute|hour|day|week|month|year)s?\s+ago', dt_str, re.IGNORECASE)
        if time_ago_match:
            value = int(time_ago_match.group(1))
            unit = time_ago_match.group(2).lower()
            now = datetime.now(tz=CENTRAL)
            if unit == 'minute': return now - timedelta(minutes=value)
            if unit == 'hour':   return now - timedelta(hours=value)
            if unit == 'day':    return now - timedelta(days=value)
            if unit == 'week':   return now - timedelta(weeks=value)
            if unit == 'month':  return now - timedelta(days=value*30) # Approximation
            if unit == 'year':   return now - timedelta(days=value*365) # Approximation

        # Use dateutil.parser which handles many formats and timezones
        dt = dateutil_parser.parse(dt_str)

        # If naive, assume it's Central Time already (or UTC, depending on source convention)
        # Let's assume UTC if naive, then convert to Central.
        if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
             # logger.debug(f"Parsed naive datetime '{original_date_str}' for {url}. Assuming UTC.")
             dt = dt.replace(tzinfo=dateutil_tz.UTC) # Make it aware, assuming UTC

        # Convert to Central Time
        return dt.astimezone(CENTRAL)

    except Exception as e:
        logger.warning(f"Failed to parse date '{original_date_str}'{' for ' + url if url else ''}: {e}. Using current time.")
        # Mark article as date_inferred=True later if needed
        return datetime.now(tz=CENTRAL)

def fetch_rss_feed(feed_url, source_name, max_articles=5):
    """
    Fetch and parse an RSS feed with early limiting of articles.
    
    Args:
        feed_url (str): URL of the RSS feed
        source_name (str): Name of the source for logging
        max_articles (int): Maximum number of articles to fetch per feed
        
    Returns:
        list: List of article dictionaries
    """
    logger.info(f"Fetching RSS feed: {source_name} ({feed_url})")
    
    # Update metrics
    FETCH_METRICS['sources_checked'] += 1
    
    if feed_url in attempted_urls:
        logger.debug(f"Skipping previously attempted RSS feed: {feed_url}")
        return []
    
    if should_skip_source(feed_url):
        logger.info(f"Skipping problematic source: {source_name} ({feed_url})")
        FETCH_METRICS['failed_sources'].append(source_name)
        return []
    
    attempted_urls.add(feed_url)
    
    try:
        # Create a session with proper SSL verification
        session = secure_session
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/rss+xml, application/xml, text/xml, application/atom+xml, */*'
        }
        
        start_time = time.time()
        response = session.get(feed_url, headers=headers, allow_redirects=True, timeout=10)
        response.raise_for_status()
        
        # Parse the feed content with proper SSL context
        feed = feedparser.parse(response.content, response_headers=response.headers)
        parsing_time = time.time() - start_time
        
        if parsing_time > 5:
            logger.warning(f"Slow RSS feed parsing: {source_name} took {parsing_time:.2f}s")
        
        if not feed.entries and feed.get('status') not in [200, 301, 302]:
            logger.warning(f"Failed to fetch RSS feed {source_name}: Status {feed.get('status', 'unknown')}")
            failed_urls.add(feed_url)
            FETCH_METRICS['failed_sources'].append(source_name)
            return []
        
        if not feed.entries:
            logger.warning(f"RSS feed {source_name} returned no entries")
            FETCH_METRICS['empty_sources'].append(source_name)
            return []
        
        # Score and filter entries before processing
        scored_entries = []
        for entry in feed.entries:
            try:
                # Skip if missing essential fields
                if not entry.get('title') or not entry.get('link'):
                    continue
                    
                # Skip if URL was previously processed
                if entry.get('link') in unique_article_urls:
                    FETCH_METRICS['duplicate_articles'] += 1
                    continue
                
                # Parse the published date
                published = entry.get('published', '')
                published_date = force_central(published, entry.get('link'))
                article_inferred_date = (published == '') # Mark if date was inferred
                
                # Calculate article importance score
                score = 0
                title = entry.get('title', '').lower()
                description = entry.get('description', '').lower()
                
                # Boost score for articles matching user interests
                for interest in USER_INTERESTS:
                    if interest.lower() in title or interest.lower() in description:
                        score += 2
                
                # Boost score for breaking news indicators
                breaking_terms = ['breaking', 'urgent', 'just in', 'developing']
                if any(term in title.lower() for term in breaking_terms):
                    score += 3
                
                # Boost score for important keywords
                important_terms = ['announcement', 'official', 'update', 'report', 'investigation']
                if any(term in title.lower() for term in important_terms):
                    score += 1
                
                # Add entry with its score
                scored_entries.append((entry, published_date, score))
                
            except Exception as e:
                logger.error(f"Error processing RSS entry from {source_name}: {e}")
        
        # Sort by score (primary) and date (secondary)
        scored_entries.sort(key=lambda x: (x[2], x[1]), reverse=True)
        
        # Take only the top N highest-scoring entries
        limited_entries = scored_entries[:max_articles]
        
        articles = []
        for entry, published_date, _ in limited_entries:
            try:
                title = entry.get('title', '')
                link = entry.get('link', '')
                
                # Mark URL as processed
                attempted_urls.add(link)
                unique_article_urls.add(link)
                
                # Get description/summary
                description = entry.get('description', entry.get('summary', ''))
                if description:
                    soup = BeautifulSoup(description, 'html.parser')
                    description = soup.get_text()
                
                # Get content if available
                content = ''
                if 'content' in entry:
                    content_items = entry.content
                    if isinstance(content_items, list) and content_items:
                        content = content_items[0].get('value', '')
                        if content:
                            soup = BeautifulSoup(content, 'html.parser')
                            content = soup.get_text()
                
                articles.append({
                    'title': title,
                    'link': link,
                    'published': published_date,
                    'description': description,
                    'content': content,
                    'source': source_name,
                    'importance_score': _,  # Include the score for later use
                    'date_inferred': article_inferred_date  # Add flag
                })
                
            except Exception as e:
                logger.error(f"Error processing RSS entry data from {source_name}: {e}")
        
        # Update metrics
        if articles:
            FETCH_METRICS['successful_sources'] += 1
            FETCH_METRICS['total_articles'] += len(articles)
            
            if source_name not in FETCH_METRICS['source_statistics']:
                FETCH_METRICS['source_statistics'][source_name] = {
                    'articles': len(articles),
                    'success_rate': 100.0
                }
            else:
                FETCH_METRICS['source_statistics'][source_name]['articles'] += len(articles)
        else:
            FETCH_METRICS['empty_sources'].append(source_name)
        
        logger.info(f"Successfully fetched {len(articles)} articles from {source_name} (limited from {len(feed.entries)})")
        return articles
        
    except Exception as e:
        logger.error(f"Exception fetching RSS feed {source_name}: {e}")
        failed_urls.add(feed_url)
        FETCH_METRICS['failed_sources'].append(source_name)
        return []

def get_random_user_agent():
    """Return a random modern user agent"""
    chrome_versions = [110, 111, 112, 113, 114, 115, 116, 117, 118, 119, 120]
    return f'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{random.choice(chrome_versions)}.0.0.0 Safari/537.36'

def create_google_news_session():
    """Create a session specifically configured for Google News"""
    session = create_secure_session()
    session.headers.update({
        'User-Agent': get_random_user_agent(),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Referer': 'https://news.google.com/',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'same-origin',
        'Cache-Control': 'max-age=0'
    })
    return session

def resolve_redirect_url(url, max_retries=2, base_delay=1):
    """
    Resolve the final URL after any redirects, with specific handling for Google News redirects.
    
    Args:
        url (str): The URL to resolve
        max_retries (int): Maximum number of retry attempts
        base_delay (int): Base delay between retries in seconds
        
    Returns:
        str: The final URL after redirects, or original URL if resolution fails
    """
    if not url or not isinstance(url, str):
        return url
        
    # Skip if not a redirect URL
    if 'news.google.com' not in url and '/articles/' not in url:
        return url
    
    for attempt in range(max_retries):
        try:
            # Get a WebDriver instance from the pool
            with get_driver() as driver:
                if not driver:
                    logger.error("Failed to get WebDriver from pool for redirect resolution")
                    return url # Or raise an error?

                # Set shorter timeout for redirects
                driver.set_page_load_timeout(10)

                # Load the page
                driver.get(url)

                # Wait for redirect with dynamic timeout
                timeout = random.uniform(1.5, 3)
                try:
                    WebDriverWait(driver, timeout).until(
                        lambda d: d.current_url != url or
                        d.execute_script("return document.readyState") == "complete"
                    )
                    time.sleep(0.5)
                except TimeoutException:
                    pass

                final_url = driver.current_url

                # Only return if we got a different, valid URL
                if final_url and final_url != url and 'news.google.com' not in final_url:
                    logger.debug(f"Successfully resolved redirect: {url} -> {final_url}")
                    return final_url
                else:
                    # If URL didn't change or still google, maybe log and continue loop?
                    logger.debug(f"Redirect resolution attempt {attempt+1} did not yield final URL: current={final_url}")

        except Exception as e:
            logger.warning(f"Redirect resolution failed (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                time.sleep(base_delay * (2 ** attempt))
            else:
                 logger.error(f"All redirect resolution attempts failed for {url}")

    logger.warning(f"Could not resolve redirect for {url}, returning original.")
    return url

def fetch_google_news_article(article, max_retries=3):
    """Special handling for Google News articles with retries"""
    url = article['link']
    
    # Resolve any Google News redirects first
    resolved_url = resolve_redirect_url(url)
    if resolved_url != url:
        article['original_link'] = url
        article['link'] = resolved_url
        url = resolved_url
    
    session = create_google_news_session()
    
    for attempt in range(max_retries):
        try:
            # Rotate user agent on each retry
            session.headers['User-Agent'] = get_random_user_agent()
            
            # Add delay between retries
            if attempt > 0:
                time.sleep(2 ** attempt)  # Exponential backoff
            
            response = session.get(url, timeout=15)  # Increased timeout
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Try multiple content extraction strategies
            content = ''
            
            # Strategy 1: Look for article content
            selectors = [
                'article', '[role="article"]', '.article-body',
                '.article-content', '.entry-content', '.post-content',
                'main', '[role="main"]', '#content', '.content'
            ]
            
            for selector in selectors:
                elements = soup.select(selector)
                if elements:
                    # Get the largest content block
                    content = max([e.get_text(strip=True) for e in elements], key=len)
                    if len(content) > 150:  # Content threshold
                        break
            
            # Strategy 2: If no content found, try paragraphs
            if not content or len(content) < 150:
                paragraphs = soup.select('p')
                content = ' '.join([
                    p.get_text(strip=True) for p in paragraphs
                    if len(p.get_text(strip=True)) > 50  # Skip short paragraphs
                ])
            
            # Update article if content found
            if content and len(content) > 150:
                article['content'] = content
                logger.info(f"Successfully fetched Google News content: {url}")
                return article
                
            # If no content found and this is the last retry, try Selenium
            if attempt == max_retries - 1:
                logger.debug(f"No content found with requests, trying Selenium")
                return fetch_article_content_with_selenium(article)
                
        except Exception as e:
            logger.warning(f"Attempt {attempt + 1}/{max_retries} failed for {url}: {e}")
            if attempt == max_retries - 1:
                logger.debug("All retries failed, trying Selenium as fallback")
                return fetch_article_content_with_selenium(article)
            
    return article

def fetch_article_content(article, max_retries=2):
    """Fetch article content with special handling for Google News"""
    url = article['link']
    start_time = time.time()
    
    try:
        # Check if this is a Google News article and resolve redirect if needed
        if 'news.google.com' in url or article.get('source', '').startswith('Google News'):
            resolved_url = resolve_redirect_url(url)
            if resolved_url != url:
                article['original_link'] = url
                article['link'] = resolved_url
                url = resolved_url
            return fetch_google_news_article(article)
        
        # Rest of the existing function for non-Google News articles
        if url in failed_urls:
            logger.debug(f"Skipping previously failed URL: {url}")
            FETCH_METRICS['failed_fetches'].append({'url': url, 'reason': 'previous_failure'})
            return article
        
        # Skip problematic sources
        if should_skip_source(url):
            logger.info(f"Skipping problematic content source: {url}")
            FETCH_METRICS['failed_fetches'].append({'url': url, 'reason': 'problematic_source'})
            return article
        
        # Use a session for better connection reuse
        session = secure_session
        retries = requests.adapters.Retry(
            total=max_retries,
            backoff_factor=0.5,
            status_forcelist=[408, 429, 500, 502, 503, 504],
            allowed_methods=["GET"]
        )
        session.mount('http://', requests.adapters.HTTPAdapter(max_retries=retries))
        session.mount('https://', requests.adapters.HTTPAdapter(max_retries=retries))
        
        content_found = False
        for attempt in range(max_retries):
            try:
                headers = {
                    'User-Agent': get_random_user_agent(),
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                    'Cache-Control': 'max-age=0'
                }
                
                response = session.get(url, headers=headers, timeout=5)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Try to find the article content based on common patterns
                content = ''
                
                # Look for article body in common containers
                content_containers = soup.select('article, [role="article"], .article-body, .article-content, .entry-content, .post-content, main, .content-area, .story-content')
                
                if content_containers:
                    container = content_containers[0]
                    for unwanted in container.select('script, style, nav, header, footer, .ad, .advertisement, .social-share, .related-posts, .newsletter-signup, .paywall, aside'):
                        unwanted.extract()
                    content = container.get_text().strip()
                
                if not content:
                    paragraphs = soup.select('p')
                    content = ' '.join([p.get_text().strip() for p in paragraphs if len(p.get_text().strip()) > 50])
                
                # Clean up the content
                content = re.sub(r'\s+', ' ', content)
                content = re.sub(r'\n\s*\n', '\n\n', content)
                
                # Update the article and metrics if we found content
                if content and len(content) > 150:
                    article['content'] = content
                    content_found = True
                    
                    # Update content statistics
                    FETCH_METRICS['content_statistics']['articles_with_content'] += 1
                    FETCH_METRICS['content_statistics']['total_length'] += len(content)
                    articles_with_content = FETCH_METRICS['content_statistics']['articles_with_content']
                    total_length = FETCH_METRICS['content_statistics']['total_length']
                    FETCH_METRICS['content_statistics']['average_length'] = total_length / articles_with_content
                    
                    # Update age statistics if we have a published date
                    if 'published' in article:
                        # Ensure publish date is timezone aware before categorizing
                        publish_date = article['published']
                        if isinstance(publish_date, str): # If it's still a string, parse it
                            publish_date = force_central(publish_date, article.get('link'))
                        elif publish_date.tzinfo is None: # If it's naive datetime
                             publish_date = publish_date.replace(tzinfo=dateutil_tz.UTC).astimezone(CENTRAL)
                        elif publish_date.tzinfo != CENTRAL: # If it's aware but not Central
                             publish_date = publish_date.astimezone(CENTRAL)

                        age_category = categorize_article_age(publish_date) # Pass aware datetime
                        FETCH_METRICS['article_ages'][age_category] = FETCH_METRICS['article_ages'].get(age_category, 0) + 1
                    
                    logger.debug(f"Successfully fetched content with requests: {url}")
                    break
                
                # If no content found and this is the last retry, try WebDriver
                if attempt == max_retries - 1 and not content_found:
                    logger.debug(f"No content found with requests, trying WebDriver: {url}")
                    FETCH_METRICS['driver_reuse_count'] += 1
                    return fetch_article_content_with_selenium(article)
                    
            except requests.exceptions.RequestException as e:
                logger.warning(f"Request failed for {url}: {e}")
                if attempt == max_retries - 1:
                    logger.debug(f"Request failed after {max_retries} attempts, trying WebDriver")
                    FETCH_METRICS['driver_reuse_count'] += 1
                    return fetch_article_content_with_selenium(article)
                
        if not content_found:
            FETCH_METRICS['content_statistics']['articles_without_content'] += 1
            FETCH_METRICS['failed_fetches'].append({'url': url, 'reason': 'no_content'})
            failed_urls.add(url)
        
        # Update performance metrics
        fetch_time = time.time() - start_time
        FETCH_METRICS['average_article_fetch_time'] = (
            FETCH_METRICS['average_article_fetch_time'] * FETCH_METRICS['total_articles'] + fetch_time
        ) / (FETCH_METRICS['total_articles'] + 1)
        
        if fetch_time > 5:
            FETCH_METRICS['slow_sources'].append({
                'source': article.get('source', 'Unknown'),
                'url': url,
                'time': fetch_time
            })
        
        return article
        
    except Exception as e:
        logger.error(f"Error fetching content for {url}: {e}")
        FETCH_METRICS['failed_fetches'].append({
            'url': url,
            'reason': str(e),
            'type': type(e).__name__
        })
        failed_urls.add(url)
        return article

def fetch_article_content_with_selenium(article, max_retries=3, base_delay=2):
    """
    Fetch article content using Selenium WebDriver from the pool.
    Includes enhanced retry logic, anti-detection measures, and tab-based retries.
    """
    url = article['link']
    original_window = None

    if should_skip_source(url):
        logger.info(f"Skipping selenium fetch for problematic source: {url}")
        return article

    for attempt in range(max_retries):
        driver = None # Ensure driver is reset for logging scope
        try:
            with get_driver() as driver: # Get driver from pool
                if attempt > 0:
                    delay = base_delay * (2 ** attempt) + random.uniform(0, 2)
                    logger.info(f"Retry attempt {attempt + 1}/{max_retries} for {url}, waiting {delay:.1f}s")
                    time.sleep(delay)

                    # --- Retry in a new tab ---
                    logger.info(f"Opening URL in new tab for retry: {url}")
                    original_window = driver.current_window_handle
                    driver.execute_script("window.open(arguments[0], '_blank');", url)
                    new_window = [win for win in driver.window_handles if win != original_window][-1]
                    driver.switch_to.window(new_window)
                    # --------------------------
                else:
                    # First attempt, load in the current tab (or initial tab)
                    time.sleep(random.uniform(0.5, 2)) # Random delay before load
                    driver.set_page_load_timeout(15)
                    driver.get(url)
                    original_window = driver.current_window_handle # Store for potential closing later

                # Random scroll behavior
                total_height = int(driver.execute_script("return document.body.scrollHeight"))
                for scroll in range(0, total_height, random.randint(500, 1000)):
                    driver.execute_script(f"window.scrollTo(0, {scroll});")
                    time.sleep(random.uniform(0.1, 0.3))

                # Wait for content
                content_selectors = [
                    "article", 
                    "[role='article']", 
                    ".article-body", 
                    ".article-content",
                    ".entry-content",
                    ".post-content",
                    "main",
                    "#content",
                    ".content"
                ]
                
                content = ''
                for selector in content_selectors:
                    try:
                        # Wait for element with random timeout (5-10s)
                        timeout = random.uniform(5, 10)
                        element = WebDriverWait(driver, timeout).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                        )
                        if element:
                            content = element.text
                            if len(content) > 150:
                                break
                    except TimeoutException:
                        continue
                
                # If no content found with selectors, try paragraphs
                if not content or len(content) < 150:
                    try:
                        paragraphs = driver.find_elements(By.CSS_SELECTOR, 'article p, [role="article"] p, .article-body p, .article-content p')
                        if not paragraphs:
                            paragraphs = driver.find_elements(By.TAG_NAME, 'p')
                        
                        # Filter and join paragraphs
                        content = ' '.join([
                            p.text for p in paragraphs
                            if len(p.text.strip()) > 50
                            and not any(skip in p.text.lower() for skip in ['advertisement', 'subscribe', 'newsletter'])
                        ])
                    except Exception as e:
                        logger.warning(f"Failed to get paragraphs: {e}")
                
                # Clean up the content
                if content:
                    # Remove unwanted elements and normalize whitespace
                    content = re.sub(r'\s+', ' ', content).strip()
                    content = re.sub(r'\n\s*\n', '\n\n', content)
                    
                    # Remove common unwanted text
                    unwanted = ['Advertisement', 'Subscribe', 'Sign up', 'Newsletter']
                    for text in unwanted:
                        content = re.sub(f'(?i){text}.*?\n', '', content)
                    
                    if len(content) > 150:
                        article['content'] = content
                        logger.info(f"Successfully fetched content with WebDriver (attempt {attempt + 1}): {url}")

                        # Close the new tab if it was opened for a retry
                        if attempt > 0 and driver.current_window_handle != original_window:
                             try:
                                 driver.close()
                                 driver.switch_to.window(original_window)
                                 logger.debug(f"Closed retry tab for {url}")
                             except Exception as tab_close_exc:
                                 logger.warning(f"Could not close retry tab for {url}: {tab_close_exc}")
                        return article # Success

                # If loop finishes without finding content
                logger.warning(f"No content found with WebDriver (attempt {attempt + 1}): {url}")
                # Close the tab if it was the last attempt and failed
                if attempt == max_retries - 1 and driver and driver.current_window_handle != original_window:
                     try:
                         driver.close()
                         driver.switch_to.window(original_window)
                     except Exception as tab_close_exc:
                         logger.warning(f"Could not close final failed tab for {url}: {tab_close_exc}")


        except WebDriverException as e:
            logger.error(f"WebDriver exception (attempt {attempt + 1}) for {url}: {e}")
            # Close the potentially broken tab
            if driver and driver.current_window_handle != original_window:
                 try:
                     driver.close()
                     driver.switch_to.window(original_window)
                 except Exception: pass # Ignore errors closing a potentially dead tab
            # Let the pool handle the driver health check upon release
            if attempt == max_retries - 1:
                failed_urls.add(url)
        except Exception as e:
            logger.error(f"Unexpected error (attempt {attempt + 1}) fetching {url} with Selenium: {e}")
             # Close the potentially broken tab
            if driver and driver.current_window_handle != original_window:
                 try:
                     driver.close()
                     driver.switch_to.window(original_window)
                 except Exception: pass
            if attempt == max_retries - 1:
                failed_urls.add(url)
        # The 'finally' block in the 'with get_driver()' context manager handles returning the driver to the pool

    # If all retries fail
    logger.error(f"All Selenium attempts failed for {url}")
    return article # Return article without content

def normalize_url(url):
    """Normalize a URL by removing common tracking parameters and fragments"""
    try:
        # Remove common tracking parameters
        ignore_params = {
            'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
            'source', 'ref', 'referrer', 'mc_cid', 'mc_eid', 'fbclid', 'gclid',
            '_ga', '_gl', '_hsenc', '_hsmi', 'yclid', 'mkt_tok'
        }
        
        parsed = urlparse(url)
        if not parsed.query:
            return url
            
        params = parse_qs(parsed.query)
        filtered_params = {k: v for k, v in params.items() if k.lower() not in ignore_params}
        
        # Rebuild URL without ignored parameters
        clean_query = urlencode(filtered_params, doseq=True)
        return urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            clean_query,
            ''  # Remove fragment
        ))
    except:
        return url

def is_duplicate_article(article, similarity_threshold=0.85):
    """
    Check if an article is a duplicate based on URL and content similarity
    
    Args:
        article (dict): Article to check
        similarity_threshold (float): Threshold for content similarity (0-1)
        
    Returns:
        bool: True if article is likely a duplicate
    """
    url = article.get('link', '')
    title = article.get('title', '').lower()
    content = article.get('content', '').lower()
    
    if not url or (not title and not content):
        return False
        
    # Check cache age and clean if needed (24 hour retention)
    current_time = time.time()
    if current_time - article_cache['last_cleanup'] > 86400:  # 24 hours
        article_cache['urls'].clear()
        article_cache['title_hashes'].clear()
        article_cache['content_hashes'].clear()
        article_cache['last_cleanup'] = current_time
    
    # Check normalized URL
    normalized_url = normalize_url(url)
    if normalized_url in article_cache['urls']:
        return True
        
    # Generate hashes for quick comparison
    title_hash = None
    if title:
        title_hash = hashlib.md5(title.encode()).hexdigest()
        if title_hash in article_cache['title_hashes']:
            # If title matches, do a more detailed comparison
            for cached_title in article_cache['title_hashes']:
                if SequenceMatcher(None, title, cached_title).ratio() > similarity_threshold:
                    return True
    
    content_hash = None
    if content:
        content_hash = hashlib.md5(content.encode()).hexdigest()
        if content_hash in article_cache['content_hashes']:
            return True
    
    # Not a duplicate - add to cache
    article_cache['urls'].add(normalized_url)
    if title_hash:
        article_cache['title_hashes'].add(title_hash)
    if content_hash:
        article_cache['content_hashes'].add(content_hash)
    
    return False

def fetch_news_articles(rss_feeds, fetch_content=True, max_articles_per_feed=5, max_workers=8):
    """
    Fetch news articles from multiple RSS feeds with improved statistics
    and tracking features. Uses parallel processing for improved speed.
    
    Args:
        rss_feeds (dict): Dictionary mapping source names to RSS feed URLs
        fetch_content (bool): Whether to fetch full article content
        max_articles_per_feed (int): Maximum articles to fetch per feed
        max_workers (int): Maximum number of parallel workers
        
    Returns:
        tuple: (List of article dictionaries, Statistics dictionary)
    """
    # Reset tracking for this session
    global attempted_urls, failed_urls, unique_article_urls
    attempted_urls = set()
    failed_urls = set()
    unique_article_urls = set()
    
    all_articles = []
    stats = {
        'total_sources': len(rss_feeds),
        'successful_sources': 0,
        'failed_sources': 0,
        'total_articles_found': 0,
        'articles_with_content': 0,
        'failed_content_fetches': 0,
        'duplicate_articles': 0,
        'sources': {},
        'domain_stats': {},
        'processing_time': 0,
        'slow_sources': []
    }
    
    start_time = time.time()
    
    # --- Bonus: Deduplicate feed URLs before fetching ---
    logger.info(f"Deduplicating {len(rss_feeds)} provided feed URLs...")
    unique_feed_urls = {}
    seen_urls = set()
    duplicates_found = 0
    for source_name, feed_url in rss_feeds.items():
        normalized = normalize_url(feed_url) # Normalize for better matching
        if normalized not in seen_urls:
            unique_feed_urls[source_name] = feed_url
            seen_urls.add(normalized)
        else:
            logger.debug(f"Skipping duplicate feed URL: {source_name} ({feed_url})")
            duplicates_found += 1
    logger.info(f"Found {duplicates_found} duplicate feed URLs. Processing {len(unique_feed_urls)} unique feeds.")
    # Use unique_feed_urls instead of rss_feeds below
    # ----------------------------------------------------

    # Process feeds in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Create a mapping of futures to source names for tracking
        future_to_source = {
            executor.submit(fetch_rss_feed, feed_url, source_name, max_articles_per_feed): source_name
            for source_name, feed_url in unique_feed_urls.items()
            if not should_skip_source(feed_url)
        }
        
        # Process completed futures as they come in
        for future in concurrent.futures.as_completed(future_to_source):
            source_name = future_to_source[future]
            feed_url = next((url for name, url in unique_feed_urls.items() if name == source_name), None)
            
            try:
                source_start_time = time.time()
                articles = future.result()
                source_time = time.time() - source_start_time
                
                # Track slow sources
                if source_time > 5:
                    stats['slow_sources'].append({
                        'source': source_name,
                        'time': source_time,
                        'url': feed_url
                    })
                
                if articles:
                    stats['successful_sources'] += 1
                    stats['sources'][source_name] = len(articles)
                    stats['total_articles_found'] += len(articles)
                    
                    # Track domain statistics
                    domain = urlparse(feed_url).netloc if feed_url else "unknown"
                    if domain not in stats['domain_stats']:
                        stats['domain_stats'][domain] = {
                            'articles': 0,
                            'success_rate': 0,
                            'avg_content_length': 0
                        }
                    stats['domain_stats'][domain]['articles'] += len(articles)
                    
                    all_articles.extend(articles)
                else:
                    stats['failed_sources'] += 1
                    stats['sources'][source_name] = 0
                    
            except Exception as e:
                logger.error(f"Error processing source {source_name}: {e}")
                stats['failed_sources'] += 1
                stats['sources'][source_name] = 0
                
                # Update metrics for exceptions
                if source_name not in FETCH_METRICS['failed_sources']:
                    FETCH_METRICS['failed_sources'].append(source_name)
    
    # After fetching articles, before content fetching:
    logger.info("Checking for duplicate articles...")
    unique_articles = []
    for article in all_articles:
        if not is_duplicate_article(article):
            unique_articles.append(article)
        else:
            stats['duplicate_articles'] += 1
            logger.debug(f"Duplicate article removed: {article.get('title', 'Unknown')}")
    
    all_articles = unique_articles
    logger.info(f"Removed {stats['duplicate_articles']} duplicate articles, {len(all_articles)} unique articles remain")
    
    # Fetch full content in parallel if requested
    if fetch_content and all_articles:
        logger.info(f"Fetching content for {len(all_articles)} articles in parallel")
        
        content_stats = {
            'total': len(all_articles),
            'success': 0,
            'failed': 0,
            'avg_length': 0,
            'slow_articles': []
        }
        
        total_content_length = 0
        
        # Process article content in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Create a mapping of futures to articles
            future_to_article = {
                executor.submit(fetch_article_content, article): article
                for article in all_articles
                if not should_skip_source(article.get('link', ''))
            }
            
            for i, future in enumerate(concurrent.futures.as_completed(future_to_article)):
                article = future_to_article[future]
                
                try:
                    # Log progress periodically
                    if (i + 1) % 10 == 0 or i == 0 or i == len(future_to_article) - 1:
                        logger.info(f"Fetching content: {i+1}/{len(future_to_article)} articles")
                    
                    content_start = time.time()
                    updated_article = future.result()
                    content_time = time.time() - content_start
                    
                    # Track slow article fetches
                    if content_time > 3:
                        content_stats['slow_articles'].append({
                            'title': updated_article.get('title', 'Unknown'),
                            'url': updated_article.get('link', 'Unknown'),
                            'time': content_time,
                            'source': updated_article.get('source', 'Unknown')
                        })
                    
                    # Update the original article with content
                    article.update({k: v for k, v in updated_article.items() if v})
                    
                    # Track stats
                    if article.get('content'):
                        content_stats['success'] += 1
                        content_length = len(article['content'])
                        total_content_length += content_length
                        
                        # Update domain stats
                        domain = urlparse(article['link']).netloc
                        if domain not in stats['domain_stats']:
                            stats['domain_stats'][domain] = {
                                'articles': 1,
                                'success_rate': 100.0,
                                'avg_content_length': content_length
                            }
                        else:
                            domain_stats = stats['domain_stats'][domain]
                            domain_stats['articles'] = domain_stats.get('articles', 0) + 1
                            
                            # Update running average of content length
                            current_total = domain_stats.get('avg_content_length', 0) * (domain_stats['articles'] - 1)
                            domain_stats['avg_content_length'] = (current_total + content_length) / domain_stats['articles']
                    else:
                        content_stats['failed'] += 1
                        
                        # Update domain failure stats
                        domain = urlparse(article['link']).netloc
                        if domain in stats['domain_stats']:
                            stats['domain_stats'][domain]['articles'] = stats['domain_stats'][domain].get('articles', 0) + 1
                    
                except Exception as e:
                    logger.error(f"Error fetching content for article {article.get('title', 'Unknown')}: {e}")
                    content_stats['failed'] += 1
        
        # Calculate averages and update stats
        if content_stats['success'] > 0:
            content_stats['avg_length'] = total_content_length / content_stats['success']
        
        # Update overall stats
        stats['articles_with_content'] = content_stats['success']
        stats['failed_content_fetches'] = content_stats['failed']
        stats['avg_content_length'] = content_stats['avg_length']
        stats['slow_article_fetches'] = content_stats['slow_articles']
        
        # Calculate success rates for domains
        for domain, domain_stat in stats['domain_stats'].items():
            domain_stat['success_rate'] = (domain_stat.get('avg_content_length', 0) > 0) * 100.0
            
        # Log slow sources and articles for future optimization
        if stats.get('slow_sources'):
            logger.warning(f"Slow sources detected ({len(stats['slow_sources'])})")
            for src in stats['slow_sources'][:5]:  # Log top 5 slowest
                logger.warning(f"Slow source: {src['source']} - {src['time']:.2f}s")
                
        if content_stats.get('slow_articles'):
            logger.warning(f"Slow article fetches detected ({len(content_stats['slow_articles'])})")
            for art in content_stats['slow_articles'][:5]:  # Log top 5 slowest
                logger.warning(f"Slow article: {art['title']} from {art['source']} - {art['time']:.2f}s")
    
    # Calculate processing time
    processing_time = time.time() - start_time
    stats['processing_time'] = processing_time
    
    # Update global metrics
    FETCH_METRICS['processing_time'] = processing_time
    
    # Log a summary of statistics
    logger.info(f"News fetching completed in {stats['processing_time']:.2f} seconds")
    logger.info(f"Sources: {stats['successful_sources']}/{stats['total_sources']} successful")
    logger.info(f"Articles: {stats['total_articles_found']} found, {stats.get('articles_with_content', 0)} with content")
    logger.info(f"Failed content fetches: {stats.get('failed_content_fetches', 0)}")
    
    # Print a comprehensive summary of the run
    logger.info(print_metrics_summary())
    
    return all_articles, stats

def combine_feed_sources():
    """Combine all feed sources based on system settings."""
    combined_feeds = {}
    
    # Always include PRIMARY_NEWS_FEEDS
    combined_feeds.update(PRIMARY_NEWS_FEEDS)
    
    # Include SECONDARY_FEEDS
    for category, feeds in SECONDARY_FEEDS.items():
        combined_feeds.update(feeds)
    
    # Include SUPPLEMENTAL_FEEDS if enabled
    if SYSTEM_SETTINGS.get("use_supplemental_feeds", False):
        for category, feeds in SUPPLEMENTAL_FEEDS.items():
            combined_feeds.update(feeds)
            
    return combined_feeds

def fetch_articles_from_all_feeds(max_articles_per_source=5):
    """
    Main function to fetch articles from all configured feed sources
    
    Args:
        max_articles_per_source (int): Maximum number of articles to fetch per source
        
    Returns:
        list: List of article dictionaries
    """
    # Get combined feeds based on configuration
    combined_feeds = combine_feed_sources()
    logger.info(f"Fetching news from {len(combined_feeds)} total configured feeds")
    
    # Convert feeds to flat dictionary for fetch_news_articles
    flat_feeds = {}
    
    for source_name, feed_url in combined_feeds.items():
        try:
            # Skip known problematic sources early
            if should_skip_source(feed_url):
                logger.info(f"Skipping problematic source: {source_name} ({feed_url})")
                continue
                
            flat_feeds[source_name] = feed_url
        except Exception as e:
            logger.error(f"Error processing source {source_name}: {e}")
    
    logger.info(f"Fetching content from {len(flat_feeds)} feeds (after filtering problematic sources)")
    
    # Now call fetch_news_articles with the flattened dictionary
    # Use improved parameters: limit articles per feed, use parallel processing
    max_workers = SYSTEM_SETTINGS.get("max_parallel_workers", 8)
    max_articles = SYSTEM_SETTINGS.get("max_articles_per_feed", max_articles_per_source)
    
    result = fetch_news_articles(
        flat_feeds, 
        fetch_content=True,
        max_articles_per_feed=max_articles,
        max_workers=max_workers
    )
    
    # Handle return values - fetch_news_articles returns a tuple (articles, stats)
    if isinstance(result, tuple) and len(result) > 0:
        articles, stats = result
        logger.info(f"Fetch completed in {stats.get('processing_time', 0):.2f} seconds")
        
        # Log efficiency statistics
        if stats.get('slow_sources'):
            logger.warning(f"{len(stats['slow_sources'])} slow sources detected")
        
        if stats.get('slow_article_fetches'):
            slow_count = len(stats.get('slow_article_fetches', []))
            if (slow_count > 0):
                logger.warning(f"{slow_count} slow article fetches detected")
                domains = set(item['url'].split('/')[2] for item in stats.get('slow_article_fetches', [])
                              if 'url' in item and '/' in item['url'])
                logger.warning(f"Slow domains: {', '.join(domains)}")
        
        return articles
    else:
        return result  # Return whatever we got

def fetch_feed_with_redirects(feed_url):
    """Fetch RSS feed with proper redirect handling"""
    try:
        session = create_secure_session()
        response = session.get(feed_url, allow_redirects=True)
        response.raise_for_status()
        
        # Parse feed content
        feed = feedparser.parse(response.content)
        if not feed.entries:
            logger.warning(f"RSS feed {feed_url} returned no entries")
            return None
            
        return feed
    except Exception as e:
        logger.error(f"Failed to fetch RSS feed {feed_url}: {e}")
        return None

def categorize_article_age(publish_date: datetime) -> str:
    """Categorize article age based on a timezone-aware datetime."""
    now = datetime.now(CENTRAL) # Use CENTRAL timezone
    if not publish_date or not isinstance(publish_date, datetime):
        return 'unknown'

    # Ensure publish_date is aware and in CENTRAL timezone
    if publish_date.tzinfo is None:
        # This case should ideally not happen if force_central is used everywhere
        logger.warning("Categorizing age for a naive datetime. Assuming UTC.")
        publish_date = publish_date.replace(tzinfo=dateutil_tz.UTC).astimezone(CENTRAL)
    elif publish_date.tzinfo != CENTRAL:
         publish_date = publish_date.astimezone(CENTRAL)

    delta = now - publish_date

    if delta < timedelta(hours=1): return 'last_hour'
    if delta < timedelta(days=1): return 'today'
    if delta < timedelta(days=2): return 'yesterday'
    if delta < timedelta(days=7): return 'this_week'
    return 'older'

# --- Test Execution ---

if __name__ == "__main__":
    logger.info("Running fetch_news.py directly for testing")
    articles, stats = fetch_articles_from_all_feeds()
    for i, article in enumerate(articles, 1):
        logger.info(f"Article {i}: {article['title']} - {article['source']} ({article['category']})")
        logger.debug(f"URL: {article['url']}")
        logger.debug(f"Published: {article['published'].strftime('%Y-%m-%d %H:%M:%S %Z') if article.get('published') else 'N/A'}")
        logger.debug(f"Content Preview: {article['content'][:150]}...")
