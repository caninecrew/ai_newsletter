import feedparser
from newspaper import Article
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
import time
import requests
from bs4 import BeautifulSoup
from logger_config import setup_logger
from config import RSS_FEEDS, SYSTEM_SETTINGS, PRIMARY_NEWS_SOURCE
from gnews_api import fetch_articles_from_gnews
import datetime
from dateutil import parser as date_parser
from dateutil.parser._parser import ParserError
import pytz
from collections import defaultdict

# Set up logger
logger = setup_logger()

# --- Fetching Logic ---

def try_rss_summary(entry):
    return entry.get('summary', '').strip()

def try_syndicated_version(title):
    search_query = f"{title} site:news.yahoo.com OR site:msn.com"
    url = f"https://www.google.com/search?q={requests.utils.quote(search_query)}"
    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(url, headers=headers)
    if res.ok:
        soup = BeautifulSoup(res.text, "html.parser")
        links = soup.select("a")
        for link in links:
            href = link.get("href", "")
            if "yahoo.com" in href or "msn.com" in href:
                return href
    return None

def try_google_cache(original_url):
    cache_url = f"http://webcache.googleusercontent.com/search?q=cache:{original_url}"
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(cache_url, headers=headers)
        if res.ok:
            soup = BeautifulSoup(res.text, "html.parser")
            paragraphs = soup.find_all("p")
            return "\n".join(p.get_text() for p in paragraphs).strip()
    except Exception as e:
        logger.warning(f"Google cache retrieval failed for {original_url}: {str(e)}")
    return None

def try_archive_dot_org(original_url):
    archive_lookup = f"https://archive.org/wayback/available?url={original_url}"
    try:
        res = requests.get(archive_lookup)
        snapshot = res.json().get("archived_snapshots", {}).get("closest", {}).get("url")
        if snapshot:
            res2 = requests.get(snapshot)
            soup = BeautifulSoup(res2.text, "html.parser")
            paragraphs = soup.find_all("p")
            return "\n".join(p.get_text() for p in paragraphs).strip()
    except Exception as e:
        logger.warning(f"Archive.org retrieval failed for {original_url}: {str(e)}")
    return None

def get_article_fallback_content(entry):
    title = entry.get("title", "")
    url = entry.get("link", "")

    logger.info(f"Attempting fallback for blocked source: {url}")

    # Step 1: RSS Summary
    summary = try_rss_summary(entry)
    if summary:
        logger.debug(f"Successfully retrieved RSS summary for {url}")
        return summary, "summary"

    # Step 2: Syndicated Version
    syndicated_url = try_syndicated_version(title)
    if syndicated_url:
        logger.info(f"Found syndicated version: {syndicated_url}")
        try:
            res = requests.get(syndicated_url, headers={"User-Agent": "Mozilla/5.0"})
            soup = BeautifulSoup(res.text, "html.parser")
            paragraphs = soup.find_all("p")
            return "\n".join(p.get_text() for p in paragraphs).strip(), "syndicated"
        except Exception as e:
            logger.warning(f"Failed to retrieve syndicated content: {str(e)}")

    # Step 3: Google Cache
    logger.debug(f"Trying Google cache for {url}")
    cached_content = try_google_cache(url)
    if cached_content:
        logger.debug(f"Successfully retrieved Google cache for {url}")
        return cached_content, "google-cache"

    # Step 4: Archive.org
    logger.debug(f"Trying Archive.org for {url}")
    archived_content = try_archive_dot_org(url)
    if archived_content:
        logger.debug(f"Successfully retrieved Archive.org content for {url}")
        return archived_content, "wayback"

    # Step 5: Give up
    logger.warning(f"All fallback methods failed for {url}")
    return "Content not accessible due to site restrictions.", "source-limited"

def parse_date(date_str):
    """
    Parse dates with robust error handling for different formats
    and handle timezone awareness issues
    """
    if not date_str or date_str == "Unknown":
        logger.debug("Empty date string received, using current time")
        return datetime.datetime.now(pytz.UTC)
    
    try:
        # Try parsing with dateutil
        parsed_date = date_parser.parse(date_str)
        
        # Make datetime timezone aware if it's naive
        if parsed_date.tzinfo is None:
            parsed_date = parsed_date.replace(tzinfo=pytz.UTC)
            
        return parsed_date
        
    except (ParserError, ValueError) as e:
        logger.warning(f"Date parsing error: {e} for date string: {date_str}")
        # Try various date formats before giving up
        formats_to_try = [
            "%a, %d %b %Y %H:%M:%S %z",  # RFC 2822 format
            "%Y-%m-%dT%H:%M:%S%z",        # ISO 8601 format
            "%Y-%m-%dT%H:%M:%SZ",         # ISO 8601 UTC format
            "%Y-%m-%d %H:%M:%S",          # Simple datetime format
            "%Y-%m-%d",                   # Simple date format
            "%d %b %Y %H:%M:%S",          # Day first format
            "%d %B %Y",                   # Day month year format
            "%B %d, %Y"                   # Month day, year format
        ]
        
        for fmt in formats_to_try:
            try:
                parsed_date = datetime.datetime.strptime(date_str, fmt)
                logger.debug(f"Successfully parsed date using format: {fmt}")
                
                # Make datetime timezone aware if it's naive
                if parsed_date.tzinfo is None:
                    parsed_date = parsed_date.replace(tzinfo=pytz.UTC)
                    
                return parsed_date
            except ValueError:
                pass
        
        # If all else fails, log the issue with the specific date string
        logger.error(f"Failed to parse date with all formats: '{date_str}'")
        return datetime.datetime.now(pytz.UTC)
    except OverflowError as e:
        # Handle extreme dates (year 0001, 9999, etc.)
        logger.error(f"Date overflow error: {e} for date string: '{date_str}'")
        return datetime.datetime.now(pytz.UTC)
    except Exception as e:
        # Catch any other unexpected errors
        logger.error(f"Unexpected date parsing error: {type(e).__name__}: {e} for '{date_str}'")
        return datetime.datetime.now(pytz.UTC)

class WebDriverManager:
    """
    Class to manage Selenium WebDriver instances with proper session reuse
    """
    def __init__(self):
        self._driver = None
        self.initialized = False
        self.max_retries = 3

    def get_driver(self):
        """Get an existing driver or initialize a new one"""
        if self._driver is not None and self.initialized:
            try:
                # Check if driver is still responsive
                self._driver.title
                return self._driver
            except Exception as e:
                logger.warning(f"WebDriver session expired: {e}. Reinitializing...")
                self.close()
        
        # Initialize new driver
        return self.initialize_driver()
            
    def initialize_driver(self):
        """Initialize a new Chrome WebDriver"""
        attempt = 0
        while attempt < self.max_retries:
            try:
                chrome_options = Options()
                chrome_options.add_argument("--headless")
                chrome_options.add_argument("--disable-gpu")
                chrome_options.add_argument("--no-sandbox")
                chrome_options.add_argument("--disable-dev-shm-usage")
                chrome_options.add_argument("--disable-extensions")
                chrome_options.add_argument("--disable-browser-side-navigation")
                chrome_options.add_argument("--disable-features=VizDisplayCompositor")
                chrome_options.add_argument("--disable-software-rasterizer")
                chrome_options.add_argument("--window-size=1920,1080")
                chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36")

                logger.info("Initializing new Chrome WebDriver instance")
                self._driver = webdriver.Chrome(
                    service=Service(ChromeDriverManager().install()),
                    options=chrome_options
                )
                self._driver.set_page_load_timeout(30)  # 30 seconds timeout
                self.initialized = True
                return self._driver
            except Exception as e:
                attempt += 1
                logger.error(f"WebDriver initialization attempt {attempt} failed: {e}")
                time.sleep(2)  # Wait before retrying
                
                if self._driver:
                    try:
                        self._driver.quit()
                    except:
                        pass
                self._driver = None
                
        logger.critical("Failed to initialize WebDriver after multiple attempts")
        raise RuntimeError("WebDriver initialization failed")
                
    def close(self):
        """Close the current driver properly"""
        if self._driver:
            try:
                self._driver.quit()
                logger.debug("WebDriver closed successfully")
            except Exception as e:
                logger.warning(f"Error closing WebDriver: {e}")
            finally:
                self._driver = None
                self.initialized = False
    
    def __del__(self):
        """Ensure driver is closed on garbage collection"""
        self.close()

# Initialize the WebDriver manager as a module-level variable
driver_manager = WebDriverManager()

class UrlTracker:
    """
    Track processed URLs to prevent duplicate processing and minimize repeat requests
    """
    def __init__(self, cache_file=None):
        self.processed_urls = set()
        self.failed_urls = {}
        self.cache_file = cache_file
        
        # Load cache if available
        self._load_cache()
    
    def _load_cache(self):
        """Load previously processed URLs from disk if available"""
        if not self.cache_file:
            return
            
        try:
            import json
            import os
            
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r') as f:
                    data = json.load(f)
                    self.processed_urls = set(data.get('processed_urls', []))
                    self.failed_urls = data.get('failed_urls', {})
                    logger.info(f"Loaded {len(self.processed_urls)} previously processed URLs from cache")
        except Exception as e:
            logger.warning(f"Failed to load URL cache: {e}")
    
    def _save_cache(self):
        """Save processed URLs to disk"""
        if not self.cache_file:
            return
            
        try:
            import json
            with open(self.cache_file, 'w') as f:
                json.dump({
                    'processed_urls': list(self.processed_urls),
                    'failed_urls': self.failed_urls
                }, f)
            logger.debug(f"Saved {len(self.processed_urls)} URLs to cache")
        except Exception as e:
            logger.warning(f"Failed to save URL cache: {e}")
    
    def is_processed(self, url):
        """Check if URL has already been processed"""
        return url in self.processed_urls
    
    def is_failed(self, url):
        """Check if URL previously failed processing"""
        return url in self.failed_urls
    
    def mark_processed(self, url):
        """Mark URL as successfully processed"""
        self.processed_urls.add(url)
        
        # If it was previously failed, remove from failed list
        if url in self.failed_urls:
            del self.failed_urls[url]
        
        # Save periodically (every 20 new URLs)
        if len(self.processed_urls) % 20 == 0:
            self._save_cache()
    
    def mark_failed(self, url, reason):
        """Mark URL as failed with reason"""
        self.failed_urls[url] = {
            'reason': str(reason),
            'timestamp': datetime.datetime.now().isoformat()
        }
    
    def __del__(self):
        """Save cache on object destruction"""
        self._save_cache()

# Initialize URL tracker
url_tracker = UrlTracker(cache_file='url_cache.json')

def fetch_articles_from_rss(max_articles_per_source=3):
    """
    Fetch news articles from RSS feeds as defined in config.py
    with optimized URL tracking and WebDriver management
    """
    all_articles = []
    skipped_articles = []
    
    # Statistics collection
    stats = {
        "total_feeds": 0,
        "empty_feeds": 0,
        "successful_fetches": 0,
        "failed_fetches": 0,
        "skipped_duplicates": 0,
        "previously_failed": 0,
        "articles_by_category": defaultdict(int),
        "articles_by_source": defaultdict(int),
        "articles_by_method": defaultdict(int),
        "error_types": defaultdict(int)
    }

    try:
        for category, feeds in RSS_FEEDS.items():
            logger.info(f"Fetching articles for category: {category}")
            
            # Category statistics
            category_stats = {
                "total_feeds": len(feeds),
                "empty_feeds": 0,
                "articles_fetched": 0,
            }
            
            for source_name, feed_url in feeds.items():
                stats["total_feeds"] += 1
                logger.info(f"Processing feed: {source_name}")
                try:
                    feed = feedparser.parse(feed_url)
                    if not feed.entries:
                        logger.warning(f"No entries found in feed: {source_name} ({feed_url})")
                        stats["empty_feeds"] += 1
                        category_stats["empty_feeds"] += 1
                        continue
                        
                    count = 0
                    for entry in feed.entries:
                        if count >= max_articles_per_source:
                            break
                            
                        # Skip already processed URLs using our tracker
                        url = entry.get('link', '')
                        if not url:
                            logger.debug(f"Skipping entry with no URL from {source_name}")
                            continue
                            
                        # Check if URL was already processed
                        if url_tracker.is_processed(url):
                            logger.debug(f"Skipping previously processed URL: {url}")
                            stats["skipped_duplicates"] += 1
                            continue
                            
                        # Check if URL previously failed (with backoff)
                        if url_tracker.is_failed(url):
                            logger.debug(f"Skipping previously failed URL: {url}")
                            stats["previously_failed"] += 1
                            continue
                            
                        try:
                            content = None
                            method = None
                            
                            # Use newspaper3k to extract article content
                            article = Article(url)
                            article.download()
                            article.parse()
                            content = article.text
                            method = "newspaper"
                            stats["successful_fetches"] += 1
                            stats["articles_by_method"][method] += 1
                            logger.debug(f"Successfully parsed article from {source_name}: {entry.get('title', 'No Title')}")
                            
                            # Mark URL as successfully processed
                            url_tracker.mark_processed(url)
                            
                        except Exception as e:
                            stats["failed_fetches"] += 1
                            error_type = type(e).__name__
                            stats["error_types"][error_type] += 1
                            logger.warning(f"Newspaper failed for: {url} - Error type: {error_type} - Reason: {str(e)}")
                            
                            try:
                                # Use fallback methods
                                content, method = get_article_fallback_content(entry)
                                if content:
                                    stats["articles_by_method"][method] += 1
                                    # Mark URL as successfully processed if we got content via fallback
                                    url_tracker.mark_processed(url)
                                else:
                                    url_tracker.mark_failed(url, f"No content: {str(e)}")
                                    skipped_articles.append({
                                        'url': url,
                                        'reason': f'All methods failed: {str(e)}'
                                    })
                                    continue
                            except Exception as fallback_error:
                                url_tracker.mark_failed(url, f"Fallback failed: {str(fallback_error)}")
                                logger.error(f"All retrieval methods failed for {url}: {str(fallback_error)}")
                                skipped_articles.append({
                                    'url': url,
                                    'reason': f'Fallback methods failed: {str(fallback_error)}'
                                })
                                continue

                        # Get and parse publication date with improved error handling
                        pub_date_str = entry.get('published', 'Unknown')
                        try:
                            parsed_date = parse_date(pub_date_str)
                            pub_date_str = parsed_date.isoformat()
                        except Exception as e:
                            logger.warning(f"Date parsing failed for {url}: {str(e)}")
                            pub_date_str = datetime.datetime.now(pytz.UTC).isoformat()

                        # Only add if we got content
                        if content:
                            all_articles.append({
                                'title': entry.get('title', "No Title"),
                                'url': url,
                                'source': source_name,
                                'category': category,
                                'published': pub_date_str,
                                'content': content,
                                'fetch_method': method,
                                'summary': entry.get('summary', '')  # Include RSS summary as fallback
                            })
                            count += 1
                            stats["articles_by_category"][category] += 1
                            stats["articles_by_source"][source_name] += 1
                            category_stats["articles_fetched"] += 1
                        else:
                            skipped_articles.append({
                                'url': url,
                                'reason': 'No content retrieved'
                            })
                            url_tracker.mark_failed(url, "Empty content")
                            
                except Exception as e:
                    logger.error(f"Error processing feed {source_name}: {str(e)}")
            
            logger.info(f"Category {category}: {category_stats['articles_fetched']} articles fetched, {category_stats['empty_feeds']} empty feeds")

        # Log skipped articles
        if skipped_articles:
            logger.info(f"Skipped {len(skipped_articles)} articles")
            for skipped in skipped_articles[:10]:  # Log only first 10 to avoid excessive logging
                logger.debug(f"Skipped URL: {skipped['url']} - Reason: {skipped['reason']}")
            if len(skipped_articles) > 10:
                logger.debug(f"... and {len(skipped_articles) - 10} more skipped articles")

        # Log comprehensive statistics
        logger.info("=" * 50)
        logger.info("ARTICLE FETCHING STATISTICS")
        logger.info("=" * 50)
        logger.info(f"Total feeds processed: {stats['total_feeds']}")
        logger.info(f"Empty feeds: {stats['empty_feeds']}")
        logger.info(f"Successful fetches: {stats['successful_fetches']}")
        logger.info(f"Failed fetches: {stats['failed_fetches']}")
        logger.info(f"Skipped duplicates: {stats['skipped_duplicates']}")
        logger.info(f"Skipped previously failed: {stats['previously_failed']}")
        logger.info(f"Total articles collected: {len(all_articles)}")
        logger.info("-" * 50)
        logger.info("Articles by fetch method:")
        for method, count in stats["articles_by_method"].items():
            logger.info(f"  {method}: {count}")
        logger.info("-" * 50)
        logger.info("Articles by category:")
        for cat, count in stats["articles_by_category"].items():
            logger.info(f"  {cat}: {count}")
        logger.info("-" * 50)
        logger.info("Top sources:")
        for source, count in sorted(stats["articles_by_source"].items(), key=lambda x: x[1], reverse=True)[:10]:
            logger.info(f"  {source}: {count}")
        logger.info("-" * 50)
        logger.info("Error types:")
        for error_type, count in sorted(stats["error_types"].items(), key=lambda x: x[1], reverse=True):
            logger.info(f"  {error_type}: {count}")
        logger.info("=" * 50)

    except Exception as e:
        logger.error(f"Error in fetch_articles_from_rss: {str(e)}", exc_info=True)

    logger.info(f"RSS article fetching completed. Retrieved {len(all_articles)} articles.")
    return all_articles

def fetch_articles_from_all_feeds(max_articles_per_source=3):
    """
    Main function to fetch articles based on the configured news source
    """
    logger.info(f"Fetching news using configured source: {PRIMARY_NEWS_SOURCE}")
    
    if PRIMARY_NEWS_SOURCE.lower() == "gnews":
        # Use GNews API
        return fetch_articles_from_gnews()
    else:
        # Default to RSS feeds
        return fetch_articles_from_rss(max_articles_per_source)

# --- Test Execution ---

if __name__ == "__main__":
    logger.info("Running fetch_news.py directly for testing")
    articles = fetch_articles_from_all_feeds()
    for i, article in enumerate(articles, 1):
        logger.info(f"Article {i}: {article['title']} - {article['source']} ({article['category']})")
        logger.debug(f"URL: {article['url']}")
        logger.debug(f"Published: {article['published']}")
        logger.debug(f"Content Preview: {article['content'][:150]}...")
