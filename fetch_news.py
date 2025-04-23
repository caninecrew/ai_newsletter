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
import datetime
import dateutil.parser
import pytz
import re
import time
import random
import logging
from logger_config import setup_logger
from urllib.parse import urlparse
from config import RSS_FEEDS, SYSTEM_SETTINGS, PRIMARY_NEWS_SOURCE
from gnews_api import fetch_articles_from_gnews
from collections import defaultdict
import concurrent.futures

# Get the logger
logger = setup_logger()

# Global URL tracking to prevent duplicate attempts
attempted_urls = set()
failed_urls = set()

# Global WebDriver instance for reuse
_driver = None
_driver_creation_time = None
_driver_request_count = 0

# List of problematic sources/domains that should be skipped or handled with extra care
PROBLEMATIC_SOURCES = [
    "nytimes.com/section/politics",  # New York Times Politics section
    "cnnunderscored.com",           # CNN Underscored is often problematic
    "nytimes.com/wirecutter",       # NYT Wirecutter has complex JS and paywalls
    "wsj.com",                      # Wall Street Journal has strong paywall
    "washingtonpost.com/opinions",  # Washington Post opinions section
    "bloomberg.com",                # Bloomberg has strict paywall
    "foxnews.com/opinion",          # Fox News opinions often has issues
]

# Performance tracking and statistics
source_performance = defaultdict(lambda: {'avg_time': 0, 'success_rate': 0, 'attempts': 0})

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

def get_webdriver(force_new=False, max_age_minutes=30, max_requests=50):
    """
    Get or create a WebDriver instance, with intelligent session management.
    
    Args:
        force_new (bool): Force creation of a new WebDriver instance
        max_age_minutes (int): Maximum age of driver in minutes before recreation
        max_requests (int): Maximum number of requests before recreating driver
        
    Returns:
        WebDriver: A Chrome WebDriver instance
    """
    global _driver, _driver_creation_time, _driver_request_count
    
    current_time = time.time()
    
    # Determine if we need a new driver
    create_new = False
    reason = None
    
    if _driver is None:
        create_new = True
        reason = "No driver exists"
    elif force_new:
        create_new = True
        reason = "Force new requested"
    elif _driver_creation_time and (current_time - _driver_creation_time) / 60 > max_age_minutes:
        create_new = True
        reason = f"Driver age exceeded {max_age_minutes} minutes"
    elif _driver_request_count >= max_requests:
        create_new = True
        reason = f"Request count exceeded {max_requests}"
        
    # Close existing driver if needed
    if create_new and _driver is not None:
        try:
            _driver.quit()
        except Exception as e:
            logger.warning(f"Error closing existing WebDriver: {e}")
    
    # Create a new driver if needed
    if create_new:
        logger.debug(f"Creating new WebDriver instance: {reason}")
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-infobars")
        options.add_argument("--mute-audio")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        try:
            _driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
            _driver_creation_time = current_time
            _driver_request_count = 0
            logger.debug("WebDriver created successfully")
        except Exception as e:
            logger.error(f"Failed to create WebDriver: {e}")
            _driver = None
            raise
    
    # Increment request counter if driver exists
    if _driver is not None:
        _driver_request_count += 1
    
    return _driver

def parse_date(date_str, url=None):
    """
    Parse a date string into a datetime object with improved error handling.
    
    Args:
        date_str (str): The date string to parse
        url (str): Optional URL for debugging purposes
        
    Returns:
        datetime: A datetime object representing the parsed date, or current time if parsing fails
    """
    if not date_str:
        logger.warning(f"Empty date string received{' for ' + url if url else ''}")
        return datetime.datetime.now(pytz.UTC)
    
    original_date_str = date_str
    
    try:
        # Common preprocessing for problematic date formats
        date_str = date_str.strip()
        
        # Handle "X time ago" format
        time_ago_match = re.search(r'(\d+)\s+(minute|hour|day|week|month|year)s?\s+ago', date_str, re.IGNORECASE)
        if time_ago_match:
            value = int(time_ago_match.group(1))
            unit = time_ago_match.group(2).lower()
            
            now = datetime.datetime.now(pytz.UTC)
            if unit == 'minute':
                return now - datetime.timedelta(minutes=value)
            elif unit == 'hour':
                return now - datetime.timedelta(hours=value)
            elif unit == 'day':
                return now - datetime.timedelta(days=value)
            elif unit == 'week':
                return now - datetime.timedelta(weeks=value)
            elif unit == 'month':
                return now - datetime.timedelta(days=value*30)  # Approximation
            elif unit == 'year':
                return now - datetime.timedelta(days=value*365)  # Approximation
        
        # Remove timezone name in parentheses like "(ET)" or "(PST)"
        date_str = re.sub(r'\([A-Z]{2,5}\)', '', date_str)
        
        # Replace common text month representations
        month_mappings = {
            'Jan': 'January', 'Feb': 'February', 'Mar': 'March',
            'Apr': 'April', 'Jun': 'June', 'Jul': 'July',
            'Aug': 'August', 'Sep': 'September', 'Oct': 'October',
            'Nov': 'November', 'Dec': 'December'
        }
        for abbr, full in month_mappings.items():
            date_str = date_str.replace(f' {abbr} ', f' {full} ')
        
        # Try parsing with dateutil
        parsed_date = dateutil.parser.parse(date_str)
        
        # If no timezone info, assume UTC
        if parsed_date.tzinfo is None:
            parsed_date = parsed_date.replace(tzinfo=pytz.UTC)
            
        return parsed_date
        
    except Exception as e:
        logger.warning(f"Failed to parse date '{original_date_str}'{' for ' + url if url else ''}: {e}")
        
        # Try alternate formats
        date_formats = [
            '%Y-%m-%d', '%Y/%m/%d', '%d-%m-%Y', '%d/%m/%Y',
            '%b %d, %Y', '%B %d, %Y', '%d %b %Y', '%d %B %Y',
            '%m-%d-%Y', '%m/%d/%Y'
        ]
        
        for fmt in date_formats:
            try:
                parsed_date = datetime.datetime.strptime(date_str, fmt)
                parsed_date = parsed_date.replace(tzinfo=pytz.UTC)
                logger.debug(f"Successfully parsed date with format {fmt}")
                return parsed_date
            except ValueError:
                continue
        
        # If all parsing attempts fail, return current time
        logger.error(f"Could not parse date '{original_date_str}' in any format{' for ' + url if url else ''}")
        return datetime.datetime.now(pytz.UTC)

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
    
    if feed_url in attempted_urls:
        logger.debug(f"Skipping previously attempted RSS feed: {feed_url}")
        return []
    
    if should_skip_source(feed_url):
        logger.info(f"Skipping problematic source: {source_name} ({feed_url})")
        return []
    
    attempted_urls.add(feed_url)
    
    try:
        start_time = time.time()
        feed = feedparser.parse(feed_url)
        parsing_time = time.time() - start_time
        
        if parsing_time > 5:  # Log slow feeds
            logger.warning(f"Slow RSS feed parsing: {source_name} took {parsing_time:.2f}s")
        
        if feed.get('status') != 200:
            logger.warning(f"Failed to fetch RSS feed {source_name}: Status {feed.get('status', 'unknown')}")
            failed_urls.add(feed_url)
            return []
        
        if not feed.entries:
            logger.warning(f"RSS feed {source_name} returned no entries")
            return []
        
        articles = []
        
        # Process all entries to extract dates first
        entries_with_dates = []
        for entry in feed.entries:
            try:
                # Skip if we don't have essential fields
                if not entry.get('title') or not entry.get('link'):
                    continue
                
                # Skip if URL was previously processed
                if entry.get('link') in attempted_urls:
                    continue
                
                # Parse the published date
                published = entry.get('published', '')
                published_date = parse_date(published, entry.get('link'))
                
                entries_with_dates.append((entry, published_date))
                
            except Exception as e:
                logger.error(f"Error processing RSS entry from {source_name}: {e}")
        
        # Sort entries by date (newest first) and take only the top N
        entries_with_dates.sort(key=lambda x: x[1], reverse=True)
        limited_entries = entries_with_dates[:max_articles]
        
        # Now process the limited entries
        for entry, published_date in limited_entries:
            try:
                title = entry.get('title', '')
                link = entry.get('link', '')
                attempted_urls.add(link)
                
                # Get description/summary if available
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
                    'source': source_name
                })
                
            except Exception as e:
                logger.error(f"Error processing RSS entry data from {source_name}: {e}")
        
        logger.info(f"Successfully fetched {len(articles)} articles from {source_name} (limited from {len(feed.entries)})")
        return articles
        
    except Exception as e:
        logger.error(f"Exception fetching RSS feed {source_name}: {e}")
        failed_urls.add(feed_url)
        return []

def fetch_article_content(article, max_retries=2):
    """
    Fetch the full content of an article using requests and BeautifulSoup.
    If that fails, try using Selenium WebDriver.
    
    Args:
        article (dict): Article dictionary containing link
        max_retries (int): Maximum number of retry attempts
        
    Returns:
        dict: Updated article dictionary with content
    """
    url = article['link']
    
    if url in failed_urls:
        logger.debug(f"Skipping previously failed URL: {url}")
        return article
    
    # Skip problematic sources
    if should_skip_source(url):
        logger.info(f"Skipping problematic content source: {url}")
        return article
        
    # Try with requests/BeautifulSoup first (faster)
    for attempt in range(max_retries):
        try:
            headers = {
                'User-Agent': f'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{random.randint(90, 120)}.0.0.0 Safari/537.36'
            }
            
            # Reduced timeout from 10 to 5 seconds
            response = requests.get(url, headers=headers, timeout=5)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Try to find the article content based on common patterns
            content = ''
            
            # Look for article body in common containers
            content_containers = soup.select('article, .article-body, .article-content, .entry-content, .post-content, main')
            
            if content_containers:
                # Use the first matching container
                container = content_containers[0]
                
                # Remove unwanted elements
                for unwanted in container.select('script, style, nav, header, footer, .ad, .advertisement, .social-share, .related-posts'):
                    unwanted.extract()
                    
                content = container.get_text().strip()
            
            if not content:
                # Try to get all paragraphs as fallback
                paragraphs = soup.select('p')
                content = ' '.join([p.get_text().strip() for p in paragraphs])
            
            # Update the article if we found content
            if content:
                article['content'] = content
                logger.debug(f"Successfully fetched content with requests: {url}")
                return article
            
            # If no content found, try with WebDriver on last attempt
            if attempt == max_retries - 1:
                logger.debug(f"No content found with requests, trying WebDriver: {url}")
                return fetch_article_content_with_selenium(article)
                
        except requests.exceptions.RequestException as e:
            logger.warning(f"Request failed for {url}: {e}")
            if attempt == max_retries - 1:
                logger.debug(f"Request failed after {max_retries} attempts, trying WebDriver")
                return fetch_article_content_with_selenium(article)
            time.sleep(1)  # Brief delay before retry
    
    # If we get here, both methods failed
    failed_urls.add(url)
    return article

def fetch_article_content_with_selenium(article):
    """
    Fetch article content using Selenium WebDriver for JavaScript-heavy sites.
    
    Args:
        article (dict): Article dictionary containing link
        
    Returns:
        dict: Updated article dictionary with content
    """
    url = article['link']
    
    # Skip if this is a known problematic source
    if should_skip_source(url):
        logger.info(f"Skipping selenium fetch for problematic source: {url}")
        return article
    
    try:
        # Get the driver (which handles session reuse)
        driver = get_webdriver()
        
        # Load the page
        driver.get(url)
        
        # Reduced wait time from 10 to 5 seconds
        try:
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
        except TimeoutException:
            logger.warning(f"Selenium timeout waiting for page to load: {url}")
            failed_urls.add(url)
            return article
        
        # Reduced JS render waiting time from 2 to 1 second
        time.sleep(1)
        
        # Try to find article content
        content = ''
        
        # Try to find article container
        for selector in ['article', '.article-body', '.article-content', '.entry-content', '.post-content', 'main']:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    content = elements[0].text
                    break
            except Exception:
                pass
        
        # Fallback to paragraphs if no container found
        if not content:
            try:
                paragraphs = driver.find_elements(By.TAG_NAME, 'p')
                content = ' '.join([p.text for p in paragraphs])
            except Exception as e:
                logger.warning(f"Failed to get paragraphs with Selenium: {e}")
        
        # Update article if content found
        if content:
            article['content'] = content
            logger.debug(f"Successfully fetched content with WebDriver: {url}")
        else:
            logger.warning(f"No content found with WebDriver: {url}")
            failed_urls.add(url)
            
    except (WebDriverException, TimeoutException) as e:
        logger.error(f"WebDriver exception for {url}: {e}")
        failed_urls.add(url)
    except Exception as e:
        logger.error(f"Unexpected error fetching with WebDriver for {url}: {e}")
        failed_urls.add(url)
    
    return article

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
    global attempted_urls, failed_urls
    attempted_urls = set()
    failed_urls = set()
    
    all_articles = []
    stats = {
        'total_sources': len(rss_feeds),
        'successful_sources': 0,
        'failed_sources': 0,
        'total_articles_found': 0,
        'articles_with_content': 0,
        'failed_content_fetches': 0,
        'sources': {},
        'domain_stats': {},
        'processing_time': 0,
        'slow_sources': []
    }
    
    start_time = time.time()
    
    # Process feeds in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Create a mapping of futures to source names for tracking
        future_to_source = {
            executor.submit(fetch_rss_feed, feed_url, source_name, max_articles_per_feed): source_name
            for source_name, feed_url in rss_feeds.items()
            if not should_skip_source(feed_url)
        }
        
        # Process completed futures as they come in
        for future in concurrent.futures.as_completed(future_to_source):
            source_name = future_to_source[future]
            feed_url = next((url for name, url in rss_feeds.items() if name == source_name), None)
            
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
    stats['processing_time'] = time.time() - start_time
    
    # Log a summary of statistics
    logger.info(f"News fetching completed in {stats['processing_time']:.2f} seconds")
    logger.info(f"Sources: {stats['successful_sources']}/{stats['total_sources']} successful")
    logger.info(f"Articles: {stats['total_articles_found']} found, {stats.get('articles_with_content', 0)} with content")
    logger.info(f"Failed content fetches: {stats.get('failed_content_fetches', 0)}")
    
    # Clean up WebDriver if it was created
    if _driver is not None:
        try:
            _driver.quit()
            logger.debug("WebDriver closed successfully")
        except Exception as e:
            logger.warning(f"Error closing WebDriver: {e}")
    
    return all_articles, stats

def fetch_articles_from_all_feeds(max_articles_per_source=3):
    """
    Main function to fetch articles based on the configured news source
    
    Args:
        max_articles_per_source (int): Maximum number of articles to fetch per source
        
    Returns:
        list: List of article dictionaries
    """
    logger.info(f"Fetching news using configured source: {PRIMARY_NEWS_SOURCE}")
    
    if PRIMARY_NEWS_SOURCE.lower() == "gnews":
        # Use GNews API
        return fetch_articles_from_gnews()
    else:
        # Default to RSS feeds
        # Convert nested RSS_FEEDS structure to flat dictionary for fetch_news_articles
        flat_feeds = {}
        
        for category, sources in RSS_FEEDS.items():
            try:
                # If sources is a dictionary, iterate through its items
                if isinstance(sources, dict):
                    for source_name, feed_url in sources.items():
                        # Create a key combining category and source name
                        flat_key = f"{source_name} ({category})"
                        flat_feeds[flat_key] = feed_url
                # If sources is a string (direct URL), use category as source name
                elif isinstance(sources, str):
                    flat_feeds[category] = sources
                else:
                    logger.error(f"Unexpected format for category {category}: {type(sources)}")
            except Exception as e:
                logger.error(f"Error processing source {category}: {e}")
        
        # Now call fetch_news_articles with the flattened dictionary
        result = fetch_news_articles(flat_feeds)
        
        # Handle return values - fetch_news_articles returns a tuple (articles, stats)
        if isinstance(result, tuple) and len(result) > 0:
            return result[0]  # Return just the articles list
        else:
            return result  # Return whatever we got

# --- Test Execution ---

if __name__ == "__main__":
    logger.info("Running fetch_news.py directly for testing")
    articles, stats = fetch_articles_from_all_feeds()
    for i, article in enumerate(articles, 1):
        logger.info(f"Article {i}: {article['title']} - {article['source']} ({article['category']})")
        logger.debug(f"URL: {article['url']}")
        logger.debug(f"Published: {article['published']}")
        logger.debug(f"Content Preview: {article['content'][:150]}...")
