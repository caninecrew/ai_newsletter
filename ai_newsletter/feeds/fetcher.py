"""Main module for fetching news articles from GNews API."""
import time
import logging
from datetime import datetime, timezone, timedelta
import concurrent.futures
from typing import List, Dict
from dateutil import parser as dateutil_parser, tz as dateutil_tz
from ai_newsletter.utils.redirects import extract_article_content
from ai_newsletter.logging_cfg.logger import setup_logger
from ai_newsletter.config.settings import (
    SYSTEM_SETTINGS,
    USER_INTERESTS,
    GNEWS_CONFIG
)
from ai_newsletter.feeds.gnews_api import GNewsAPI, GNewsAPIError

# Initialize logger
logger = setup_logger()

# --- Metrics Initialization ---
FETCH_METRICS = {
    'start_time': None,
    'processing_time': 0,
    'total_articles': 0,
    'failed_sources': [],
    'source_statistics': {},
    'content_attempts': 0,
    'content_success_requests': 0
}

CENTRAL = dateutil_tz.gettz('America/Chicago') or timezone.utc

def fetch_article_content(article, max_retries=2):
    """Fetch article content using HTTP-based methods."""
    url = article.get('url', article.get('link'))
    if not url:
        logger.warning("Article missing URL/link field, skipping content fetch")
        return article

    source_name = article.get('source', {}).get('name', 'Unknown Source')
    if isinstance(article['source'], str):
        source_name = article['source']

    FETCH_METRICS['content_attempts'] = FETCH_METRICS.get('content_attempts', 0) + 1
    start_time = time.time()
    success = False

    try:
        # Extract content using our methods
        content_data = extract_article_content(url, timeout=SYSTEM_SETTINGS.get('http_timeout', 15))
        
        if content_data and content_data.get('text'):
            article['content'] = content_data['text']
            article['fetch_method'] = content_data['fetch_method']
            article['authors'] = content_data.get('authors')
            article['meta_description'] = content_data.get('meta_description')
            
            # Update article title if we found a better one
            if content_data.get('title') and len(content_data['title']) > len(article.get('title', '')):
                article['title'] = content_data['title']
                
            success = True
            FETCH_METRICS['content_success_requests'] = FETCH_METRICS.get('content_success_requests', 0) + 1
            logger.info(f"Successfully fetched content with {content_data['fetch_method']}: {url}")
        else:
            logger.warning(f"Failed to extract content from {url}")

    except Exception as e:
        logger.error(f"Error fetching content for {url}: {e}")

    # Update stats
    end_time = time.time()
    duration = end_time - start_time
    
    if source_name not in FETCH_METRICS['source_statistics']:
        FETCH_METRICS['source_statistics'][source_name] = {
            'fetch_time': 0,
            'success': 0,
            'failures': 0,
            'articles': 0
        }
    
    stats = FETCH_METRICS['source_statistics'][source_name]
    stats['fetch_time'] += duration
    if success:
        stats['success'] += 1
    else:
        stats['failures'] += 1

    # Add age categorization
    if article.get('published_at'):
        article['age_category'] = categorize_article_age(article['published_at'])
    else:
        article['age_category'] = 'Unknown'

    return article

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
        for interest, enabled in USER_INTERESTS.items():
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
        
        return all_articles
        
    except Exception as e:
        logger.error(f"Error in GNews fetch process: {e}")
        return []

def fetch_articles_from_all_feeds(fetch_content=True, max_articles_per_source=5):
    """
    Main function to fetch all articles using GNews API.
    
    Args:
        fetch_content: Whether to fetch full article content
        max_articles_per_source: Maximum articles to fetch per source
        
    Returns:
        tuple: (list of articles, fetch statistics dictionary)
    """
    logger.info("Starting news fetch process...")
    FETCH_METRICS['start_time'] = time.time()

    all_articles = []
    
    try:
        articles = fetch_from_gnews()
        all_articles.extend(articles)
    except Exception as e:
        logger.error(f"Error fetching from GNews API: {e}")

    # Fetch full content if requested
    if fetch_content and all_articles:
        logger.info(f"Fetching full content for {len(all_articles)} articles...")
        processed_articles = []

        content_max_workers = min(10, len(all_articles))
        logger.info(f"Using {content_max_workers} workers for content fetching")

        with concurrent.futures.ThreadPoolExecutor(max_workers=content_max_workers) as executor:
            future_to_article = {
                executor.submit(fetch_article_content, article): article 
                for article in all_articles
            }
            for future in concurrent.futures.as_completed(future_to_article):
                original_article = future_to_article[future]
                try:
                    processed_article = future.result()
                    processed_articles.append(processed_article)
                except Exception as exc:
                    logger.error(f"Content fetch failed for {original_article.get('url', 'unknown URL')}: {exc}")
                    processed_articles.append(original_article)

        all_articles = processed_articles

    # Update metrics and return
    end_time = time.time()
    processing_time = end_time - FETCH_METRICS['start_time']
    FETCH_METRICS['processing_time'] = processing_time
    FETCH_METRICS['total_articles'] = len(all_articles)

    logger.info(f"Total fetch process completed in {processing_time:.2f} seconds")
    
    fetch_stats = {
        "total_articles": len(all_articles),
        "failed_sources": FETCH_METRICS.get("failed_sources", []),
        "empty_sources": FETCH_METRICS.get("empty_sources", []),
        "processing_time": FETCH_METRICS.get("processing_time", 0),
    }

    return all_articles, fetch_stats

def categorize_article_age(published_date):
    """Categorizes article age relative to now."""
    if not published_date:
        return 'Unknown'
        
    now = datetime.now(timezone.utc)
    age = now - published_date
    
    if age < timedelta(hours=1):
        return 'Breaking'
    elif age < timedelta(hours=6):
        return 'Very Recent'
    elif age < timedelta(hours=12):
        return 'Recent'
    elif age < timedelta(days=1):
        return 'Today'
    elif age < timedelta(days=2):
        return 'Yesterday'
    elif age < timedelta(days=7):
        return 'This Week'
    else:
        return 'Older'

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
        logger.info(f"  Link: {article.get('url', article.get('link'))}")
        logger.info(f"  Source: {article.get('source', {}).get('name', 'Unknown Source')}")
        logger.info(f"  Published: {article.get('published_at')}")
        logger.info(f"  Age Category: {article.get('age_category')}")
        logger.info(f"  Fetch Method: {article.get('fetch_method')}")
        content_preview = (article.get('content') or "")[:100].replace('\n', ' ') + "..." if article.get('content') else "No Content"
        logger.info(f"  Content Preview: {content_preview}")
