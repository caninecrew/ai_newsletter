import feedparser
import requests
import time
import random
import re
import ssl
import certifi
from datetime import datetime, timezone, timedelta
import concurrent.futures
from bs4 import BeautifulSoup
from dateutil import parser as dateutil_parser, tz as dateutil_tz
import threading
import hashlib
from urllib.parse import urlparse, parse_qs, urlunparse, unquote, urlencode
from collections import defaultdict
from difflib import SequenceMatcher
from ai_newsletter.utils.redirects import (
    resolve_google_redirect, 
    extract_article_content, 
    create_session,
    USER_AGENTS
)
from ai_newsletter.logging_cfg.logger import setup_logger
from ai_newsletter.config.settings import (
    SYSTEM_SETTINGS,
    USER_INTERESTS,
    PRIMARY_NEWS_FEEDS,
    SECONDARY_FEEDS,
    SUPPLEMENTAL_FEEDS,
    PROBLEM_SOURCES,
    GNEWS_CONFIG,
    FEED_SETTINGS
)
from ai_newsletter.feeds.gnews_api import GNewsAPI

# --- Setup ---
logger = setup_logger()
CENTRAL = dateutil_tz.gettz('America/Chicago') or timezone.utc

# --- Metrics Initialization ---
FETCH_METRICS = defaultdict(lambda: 0)
FETCH_METRICS['failed_sources'] = []
FETCH_METRICS['empty_sources'] = []
FETCH_METRICS['source_statistics'] = defaultdict(lambda: {'articles': 0, 'fetch_time': 0.0, 'success': 0, 'failures': 0})

# --- Global Variables & Sets ---
attempted_urls = set()
failed_urls = set()
unique_article_urls = set()
source_performance = defaultdict(lambda: {'total_time': 0.0, 'attempts': 0, 'successes': 0})

# Create a shared session for feed fetching
feed_session = create_session()

def fetch_article_content(article, max_retries=2):
    """Fetch article content using HTTP-based methods."""
    url = article['link']
    source_name = article.get('source', 'Unknown Source')

    if url in attempted_urls:
        logger.debug(f"Skipping already attempted URL: {url}")
        return article
    attempted_urls.add(url)
    FETCH_METRICS['content_attempts'] = FETCH_METRICS.get('content_attempts', 0) + 1

    start_time = time.time()
    success = False

    try:
        # Extract content using our new methods
        content_data = extract_article_content(url, timeout=SYSTEM_SETTINGS.get('http_timeout', 15))
        
        if content_data and content_data.get('text'):
            article['content'] = content_data['text']
            article['fetch_method'] = content_data['fetch_method']
            article['authors'] = content_data.get('authors')
            article['meta_description'] = content_data.get('meta_description')
            
            # Update article title if we found a better one
            if content_data['title'] and len(content_data['title']) > len(article.get('title', '')):
                article['title'] = content_data['title']
                
            success = True
            FETCH_METRICS['content_success_requests'] = FETCH_METRICS.get('content_success_requests', 0) + 1
            logger.info(f"Successfully fetched content with {content_data['fetch_method']}: {url}")
        else:
            logger.warning(f"Failed to extract content from {url}")
            failed_urls.add(url)

    except Exception as e:
        logger.error(f"Error fetching content for {url}: {e}")
        failed_urls.add(url)

    # Update stats
    end_time = time.time()
    duration = end_time - start_time
    stats = FETCH_METRICS['source_statistics'][source_name]
    stats['fetch_time'] += duration
    if success:
        stats['success'] += 1
    else:
        stats['failures'] += 1

    # Add age categorization
    if article.get('published'):
        article['age_category'] = categorize_article_age(article['published'])
    else:
        article['age_category'] = 'Unknown'

    return article

def fetch_rss_feed(feed_url, source_name, max_articles=5):
    """Fetches and parses an RSS feed, returning a list of article dicts."""
    logger.info(f"Fetching RSS feed: {source_name} ({feed_url})")
    FETCH_METRICS['sources_checked'] += 1
    articles = []
    unique_article_urls_in_feed = set()

    try:
        # Use our shared session to fetch the feed
        headers = {'User-Agent': random.choice(USER_AGENTS)}
        response = feed_session.get(feed_url, timeout=20, headers=headers)
        response.raise_for_status()

        # Check content type
        content_type = response.headers.get('content-type', '').lower()
        if 'xml' not in content_type and 'rss' not in content_type and 'atom' not in content_type:
            logger.warning(f"Unexpected content type '{content_type}' for feed {source_name}.")

        # Parse the feed
        feed = feedparser.parse(response.text)

        if feed.bozo:
            logger.warning(f"Feedparser encountered issues (bozo=1) for {source_name}: {feed.bozo_exception}")
            if not feed.entries:
                FETCH_METRICS['failed_sources'].append(f"{source_name} (Bozo/No Entries)")
                return []

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

            # Handle Google News URLs
            original_link = link
            if "news.google.com" in link:
                extracted = resolve_google_redirect(link)
                if extracted and extracted != link:
                    logger.debug(f"Extracted Google News URL: {link} -> {extracted}")
                    link = extracted
                else:
                    logger.warning(f"Could not extract final URL from Google News link: {link}. Using original.")

            # Check for duplicates
            normalized_link = normalize_url(link)
            if normalized_link in unique_article_urls or normalized_link in unique_article_urls_in_feed:
                logger.debug(f"Skipping duplicate article URL: {link}")
                FETCH_METRICS['duplicate_articles'] = FETCH_METRICS.get('duplicate_articles', 0) + 1
                continue

            unique_article_urls.add(normalized_link)
            unique_article_urls_in_feed.add(normalized_link)

            # Convert published time to Central Time
            published_date = force_central(published, link) if published else None

            # Basic interest check
            relevant = True
            if USER_INTERESTS:
                relevant = any(interest.lower() in title.lower() for interest in USER_INTERESTS)

            if relevant:
                articles.append({
                    'title': title.strip(),
                    'link': link,
                    'original_google_link': original_link if link != original_link else None,
                    'published': published_date,
                    'source': source_name,
                    'feed_url': feed_url,
                    'content': None,
                    'fetch_method': None,
                    'id': hashlib.sha256(link.encode()).hexdigest()[:16]
                })
                count += 1
            else:
                logger.debug(f"Skipping article not matching interests: '{title}' from {source_name}")

        if articles:
            FETCH_METRICS['successful_sources'] += 1
            FETCH_METRICS['total_articles'] += len(articles)
            stats = FETCH_METRICS['source_statistics'][source_name]
            stats['articles'] += len(articles)
            logger.info(f"Successfully fetched {len(articles)} articles from {source_name}")
        elif not feed.bozo:
            FETCH_METRICS['empty_sources'].append(source_name)

    except requests.exceptions.Timeout:
        logger.error(f"Timeout fetching RSS feed: {source_name} ({feed_url})")
        FETCH_METRICS['failed_sources'].append(f"{source_name} (Timeout)")
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching RSS feed {source_name} ({feed_url}): {e}")
        FETCH_METRICS['failed_sources'].append(f"{source_name} (Request Error)")
    except Exception as e:
        logger.error(f"Unexpected error processing feed {source_name} ({feed_url}): {e}", exc_info=True)
        if source_name not in FETCH_METRICS['failed_sources']:
            FETCH_METRICS['failed_sources'].append(f"{source_name} (Parse Error)")

    return articles

def create_secure_session():
    """Creates a requests session with updated TLS settings and certifi."""
    session = requests.Session()
    session.verify = certifi.where()
    return session

def configure_feedparser():
    """Configures feedparser to use certifi for SSL verification."""
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    ssl_context.check_hostname = True
    ssl_context.verify_mode = ssl.CERT_REQUIRED
    logger.info("Feedparser configured to use system/requests SSL handling with certifi.")

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
    if not dt_obj:
        return None
        
    try:
        # Convert time tuple to datetime
        if isinstance(dt_obj, time.struct_time):
            dt_obj = datetime.fromtimestamp(time.mktime(dt_obj))
            
        # Make naive datetime aware (assume UTC)
        if dt_obj.tzinfo is None:
            dt_obj = dt_obj.replace(tzinfo=timezone.utc)
            
        # Convert to Central Time
        central_time = dt_obj.astimezone(CENTRAL)
        return central_time
        
    except Exception as e:
        logger.warning(f"Error converting datetime for {url_for_logging}: {e}")
        return None

def normalize_url(url: str) -> str:
    """Normalizes a URL by removing common tracking parameters and fragments."""
    try:
        # Basic cleanup
        url = url.strip()
        
        # Parse URL
        parsed = urlparse(url)
        
        # Remove tracking parameters
        query_dict = parse_qs(parsed.query, keep_blank_values=True)
        filtered_params = {
            k: v for k, v in query_dict.items()
            if not any(track in k.lower() for track in [
                'utm_', 'ref_', 'source', 'medium', 'campaign',
                'mc_', 'affiliate', 'fbclid', 'gclid', 'msclkid'
            ])
        }
        
        # Reconstruct URL without tracking params and fragment
        clean_url = urlunparse((
            parsed.scheme,
            parsed.netloc.lower(),
            parsed.path,
            parsed.params,
            urlencode(filtered_params, doseq=True),
            None  # Remove fragment
        ))
        
        return clean_url
        
    except Exception as e:
        logger.warning(f"Failed to normalize URL {url}: {e}")
        return url.strip().lower() # Fallback to simple strip and lower

def is_duplicate_article(title, link, existing_articles, similarity_threshold=0.9):
    """Checks for duplicate articles based on URL or title similarity."""
    normalized_link = normalize_url(link)
    
    for article in existing_articles:
        # Check URL first (exact match)
        if normalize_url(article['link']) == normalized_link:
            return True
            
        # Then check title similarity
        if title and article.get('title'):
            similarity = SequenceMatcher(None, title.lower(), article['title'].lower()).ratio()
            if similarity >= similarity_threshold:
                return True
                
    return False

def print_metrics_summary():
    """Generates a string summary of the fetch metrics."""
    summary = []
    summary.append("\nFetch Metrics Summary:")
    summary.append(f"Total Sources Checked: {FETCH_METRICS['sources_checked']}")
    summary.append(f"Successful Sources: {FETCH_METRICS['successful_sources']}")
    summary.append(f"Failed Sources: {len(FETCH_METRICS['failed_sources'])}")
    summary.append(f"Empty Sources: {len(FETCH_METRICS['empty_sources'])}")
    summary.append(f"Total Articles Found: {FETCH_METRICS['total_articles']}")
    summary.append(f"Total Processing Time: {FETCH_METRICS['processing_time']:.2f}s")
    
    if FETCH_METRICS.get('content_attempts'):
        success_rate = (FETCH_METRICS.get('content_success_requests', 0) / 
                       FETCH_METRICS['content_attempts'] * 100)
        summary.append(f"\nContent Fetch Success Rate: {success_rate:.1f}%")
        
    return '\n'.join(summary)

# --- Core Fetching Logic ---

def fetch_news_articles(rss_feeds=None, fetch_content=True, max_articles=10, max_workers=None):
    """
    Main function to fetch news articles using either GNews API or RSS feeds.
    
    Args:
        rss_feeds (dict, optional): Dictionary of RSS feeds to fetch from. If None, uses configured feeds.
        fetch_content (bool): Whether to fetch full article content. Defaults to True.
        max_articles (int): Maximum number of articles to fetch per source. Defaults to 10.
        max_workers (int, optional): Maximum number of parallel workers. If None, uses system settings.
        
    Returns:
        tuple: A tuple containing (list of articles, fetch statistics dictionary)
    """
    logger.info("Starting news fetch process...")
    FETCH_METRICS['start_time'] = time.time()
    
    if rss_feeds is None:
        if GNEWS_CONFIG.get('enabled', True):
            articles = fetch_from_gnews()
            return articles, {
                "total_articles": len(articles),
                "failed_sources": FETCH_METRICS.get("failed_sources", []),
                "empty_sources": FETCH_METRICS.get("empty_sources", []),
                "processing_time": FETCH_METRICS.get("processing_time", 0),
            }
        else:
            return fetch_articles_from_all_feeds(
                fetch_content=fetch_content,
                max_articles_per_source=max_articles
            )
    
    return fetch_articles_from_all_feeds(
        rss_feeds=rss_feeds,
        fetch_content=fetch_content,
        max_articles_per_source=max_articles,
        max_workers=max_workers
    )

def combine_feed_sources():
    """Combines primary, secondary, and supplemental feeds based on config."""
    combined_feeds = {}
    
    # Add primary feeds (already flat structure)
    combined_feeds.update(PRIMARY_NEWS_FEEDS)
    logger.info(f"Loaded {len(PRIMARY_NEWS_FEEDS)} primary feeds.")

    # Add secondary feeds
    if isinstance(SECONDARY_FEEDS, dict):
        for category, feeds in SECONDARY_FEEDS.items():
            if isinstance(feeds, dict):
                combined_feeds.update(feeds)
            else:
                logger.warning(f"Invalid feed structure in SECONDARY_FEEDS for category '{category}': {feeds}")
        logger.info(f"Loaded {sum(len(feeds) for feeds in SECONDARY_FEEDS.values() if isinstance(feeds, dict))} secondary feeds.")
    else:
        logger.warning("SECONDARY_FEEDS is not a valid dictionary.")

    # Add supplemental feeds only if enabled in config
    if SYSTEM_SETTINGS.get("use_supplemental_feeds", False):
        if isinstance(SUPPLEMENTAL_FEEDS, dict):
            for category, feeds in SUPPLEMENTAL_FEEDS.items():
                if isinstance(feeds, dict):
                    combined_feeds.update(feeds)
                else:
                    logger.warning(f"Invalid feed structure in SUPPLEMENTAL_FEEDS for category '{category}': {feeds}")
            logger.info(f"Loaded {sum(len(feeds) for feeds in SUPPLEMENTAL_FEEDS.values() if isinstance(feeds, dict))} supplemental feeds (enabled).")
        else:
            logger.warning("SUPPLEMENTAL_FEEDS is not a valid dictionary.")
    else:
        logger.info("Supplemental feeds are disabled in config.")

    logger.info(f"Total unique feed sources to process: {len(combined_feeds)}")
    return combined_feeds


_last_cleanup = time.time()
_cleanup_lock = threading.Lock()

def _check_cleanup_needed():
    """Check if periodic cleanup is needed."""
    global _last_cleanup
    cleanup_interval = SYSTEM_SETTINGS.get("cleanup_interval", 300)
    
    with _cleanup_lock:
        current_time = time.time()
        if current_time - _last_cleanup >= cleanup_interval:
            logger.info("Performing periodic cleanup")
            try:
                # Clear caches and reset tracking sets
                unique_article_urls.clear()
                attempted_urls.clear()
                failed_urls.clear()
                
                # Reset performance tracking
                source_performance.clear()
                
                # Reset session
                global feed_session
                feed_session = create_session()
                
            except Exception as e:
                logger.error(f"Error during periodic cleanup: {e}")
            _last_cleanup = current_time

def fetch_articles_from_all_feeds(fetch_content=True, max_articles_per_source=5, rss_feeds=None, max_workers=None):
    """Combines feeds and fetches articles."""
    # Check for cleanup before starting new fetch
    _check_cleanup_needed()
    
    all_feeds = rss_feeds if rss_feeds else combine_feed_sources()
    if not all_feeds:
        logger.warning("No feed sources defined or loaded. Cannot fetch articles.")
        return [], {"error": "No feed sources available"}

    # Get settings from config
    max_workers = max_workers or SYSTEM_SETTINGS.get("max_parallel_workers", 10) # Default based on pool size + buffer
    max_articles = SYSTEM_SETTINGS.get("max_articles_per_feed", max_articles_per_source)

    logger.info(f"Starting article fetch with max_articles_per_feed={max_articles}, max_workers={max_workers}")

    articles = fetch_news_articles(
        rss_feeds=all_feeds,
        fetch_content=fetch_content,
        max_articles_per_feed=max_articles,
        max_workers=max_workers
    )

    # Return articles and fetch statistics
    fetch_stats = {
        "total_articles": len(articles),
        "failed_sources": FETCH_METRICS.get("failed_sources", []),
        "empty_sources": FETCH_METRICS.get("empty_sources", []),
        "processing_time": FETCH_METRICS.get("processing_time", 0),
    }

    return articles, fetch_stats


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

    # Example: Fetch articles with content
    fetched_articles, fetch_stats = fetch_articles_from_all_feeds(fetch_content=True, max_articles_per_source=2) # Limit articles per feed for test

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

import concurrent.futures
import logging
import time
from typing import List, Dict
from ..config.settings import GNEWS_CONFIG, FEED_SETTINGS, SYSTEM_SETTINGS
from ai_newsletter.feeds.gnews_api import GNewsAPI
from ..logging_cfg.logger import setup_logger

logger = setup_logger()

# Metrics tracking
FETCH_METRICS = {
    'start_time': None,
    'processing_time': 0,
    'total_articles': 0,
    'failed_sources': [],
    'source_statistics': {},
    'content_attempts': 0,
    'content_success_requests': 0
}

import inspect
from functools import wraps

def safe_fetch_news_articles(*args, **kwargs):
    """
    Safe wrapper for fetch_news_articles that filters out unexpected arguments.
    
    Returns:
        Same return type as fetch_news_articles
    """
    sig = inspect.signature(fetch_news_articles)
    valid_params = sig.parameters.keys()
    
    # Filter out invalid kwargs
    filtered_kwargs = {}
    for key, value in kwargs.items():
        if key in valid_params:
            filtered_kwargs[key] = value
        else:
            logger.warning(f"Ignoring unexpected parameter '{key}' in fetch_news_articles call")
    
    return fetch_news_articles(*args, **filtered_kwargs)

def fetch_from_gnews() -> List[Dict]:
    """
    Fetch articles using the GNews API based on configured settings.
    """
    try:
        gnews_client = GNewsAPI()
        all_articles = []
        
        # Fetch top headlines for enabled categories
        for category, enabled in GNEWS_CONFIG['categories'].items():
            if not enabled:
                continue
                
            try:
                articles = gnews_client.get_top_headlines(
                    language=GNEWS_CONFIG.get('language', 'en'),
                    country=GNEWS_CONFIG.get('country'),
                    category=category if category != 'general' else None,
                    max_results=GNEWS_CONFIG.get('max_articles_per_query', 10)
                )
                
                if articles:
                    all_articles.extend(articles)
                    logger.info(f"Fetched {len(articles)} articles for category: {category}")
                    
            except Exception as e:
                logger.error(f"Error fetching {category} headlines: {e}")
                FETCH_METRICS['failed_sources'].append(f"GNews-{category}")
        
        # Fetch articles for configured interest areas
        for interest, enabled in FEED_SETTINGS.get('interests', {}).items():
            if not enabled:
                continue
                
            try:
                query = interest.replace('_', ' ')  # Convert interest name to search query
                articles = gnews_client.search_news(
                    query=query,
                    language=GNEWS_CONFIG.get('language', 'en'),
                    country=GNEWS_CONFIG.get('country'),
                    max_results=GNEWS_CONFIG.get('max_articles_per_query', 10)
                )
                
                if articles:
                    all_articles.extend(articles)
                    logger.info(f"Fetched {len(articles)} articles for interest: {interest}")
                    
            except Exception as e:
                logger.error(f"Error fetching articles for interest {interest}: {e}")
                FETCH_METRICS['failed_sources'].append(f"GNews-{interest}")
        
        # Update metrics
        end_time = time.time()
        FETCH_METRICS['processing_time'] = end_time - FETCH_METRICS['start_time']
        FETCH_METRICS['total_articles'] = len(all_articles)
        
        logger.info(f"Total fetch process completed in {FETCH_METRICS['processing_time']:.2f} seconds")
        logger.info(f"Total articles fetched: {FETCH_METRICS['total_articles']}")
        
        return all_articles
        
    except Exception as e:
        logger.error(f"Error in GNews fetch process: {e}")
        return []

def print_metrics_summary():
    """Print a summary of the fetch metrics."""
    summary = [
        "=== Fetch Metrics Summary ===",
        f"Total Processing Time: {FETCH_METRICS['processing_time']:.2f} seconds",
        f"Total Articles: {FETCH_METRICS['total_articles']}",
        f"Failed Sources: {len(FETCH_METRICS['failed_sources'])}"
    ]
    
    if FETCH_METRICS['failed_sources']:
        summary.append("\nFailed Sources:")
        for source in FETCH_METRICS['failed_sources']:
            summary.append(f"- {source}")
            
    return "\n".join(summary)
