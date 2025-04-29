"""Main module for fetching news articles from GNews API."""
import time
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Tuple
from dateutil import parser as dateutil_parser, tz as dateutil_tz
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
    'empty_sources': []
}

CENTRAL = dateutil_tz.gettz('America/Chicago') or timezone.utc

def safe_fetch_news_articles(**kwargs) -> Tuple[List[Dict], Dict]:
    """
    Safely fetch news articles with parameter validation.
    
    Valid parameters:
    - max_articles_per_source (int): Maximum articles to fetch per source
    - language (str): Language code for articles (e.g., 'en')
    - country (str): Country code for articles
    
    Returns:
        tuple: (list of articles, fetch statistics dictionary)
    """
    valid_params = {
        'max_articles_per_source': int,
        'language': str,
        'country': str
    }
    
    filtered_kwargs = {}
    for key, value in kwargs.items():
        if key in valid_params:
            if not isinstance(value, valid_params[key]):
                logger.warning(f"Parameter '{key}' has invalid type. Expected {valid_params[key].__name__}, got {type(value).__name__}")
                continue
            filtered_kwargs[key] = value
        else:
            logger.warning(f"Ignoring unexpected parameter '{key}' in fetch_news_articles call")
    
    try:
        return fetch_articles_from_all_feeds(**filtered_kwargs)
    except Exception as e:
        logger.error(f"Error in safe_fetch_news_articles: {str(e)}", exc_info=True)
        return [], {'error': str(e)}

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

def fetch_from_gnews() -> List[Dict]:
    """
    Fetch articles using the GNews API based on configured settings.
    """
    try:
        gnews_client = GNewsAPI()
        all_articles = []
        
        logger.info("Starting GNews API article fetch process")
        
        # Fetch top headlines for enabled categories
        if isinstance(GNEWS_CONFIG.get('categories'), dict):
            logger.debug(f"Processing {len(GNEWS_CONFIG['categories'])} categories")
            for category, enabled in GNEWS_CONFIG['categories'].items():
                if not enabled:
                    logger.debug(f"Category {category} is disabled, skipping")
                    continue
                    
                try:
                    logger.debug(f"Fetching articles for category: {category}")
                    articles = gnews_client.get_top_headlines(
                        language=GNEWS_CONFIG.get('language', 'en'),
                        country=GNEWS_CONFIG.get('country'),
                        category=category if category != 'general' else None,
                        max_results=GNEWS_CONFIG.get('max_articles_per_query', 10)
                    )
                    
                    if articles:
                        # Add category to each article
                        for article in articles:
                            article['category'] = category
                        all_articles.extend(articles)
                        logger.info(f"Fetched {len(articles)} articles for category: {category}")
                    else:
                        logger.warning(f"No articles found for category: {category}")
                        FETCH_METRICS['empty_sources'].append(f"GNews-{category}")
                        
                except GNewsAPIError as e:
                    logger.error(f"GNews API error fetching {category} headlines: {e}")
                    FETCH_METRICS['failed_sources'].append(f"GNews-{category}")
                    continue
                except Exception as e:
                    logger.error(f"Unexpected error fetching {category} headlines: {e}")
                    FETCH_METRICS['failed_sources'].append(f"GNews-{category}")
                    continue
        else:
            logger.warning("GNEWS_CONFIG categories is not a dictionary, skipping category fetching")
        
        # Fetch articles for configured interest areas
        if isinstance(USER_INTERESTS, dict):
            logger.debug(f"Processing {len(USER_INTERESTS)} interests")
            for interest, enabled in USER_INTERESTS.items():
                if not enabled:
                    logger.debug(f"Interest {interest} is disabled, skipping")
                    continue
                    
                try:
                    logger.debug(f"Fetching articles for interest: {interest}")
                    query = interest.replace('_', ' ')
                    articles = gnews_client.search_news(
                        query=query,
                        language=GNEWS_CONFIG.get('language', 'en'),
                        country=GNEWS_CONFIG.get('country'),
                        max_results=GNEWS_CONFIG.get('max_articles_per_query', 10)
                    )
                    
                    if articles:
                        # Add interest and category to each article
                        for article in articles:
                            article['interest'] = interest
                            article['category'] = 'Interest'
                        all_articles.extend(articles)
                        logger.info(f"Fetched {len(articles)} articles for interest: {interest}")
                    else:
                        logger.warning(f"No articles found for interest: {interest}")
                        FETCH_METRICS['empty_sources'].append(f"GNews-{interest}")
                        
                except GNewsAPIError as e:
                    logger.error(f"GNews API error fetching articles for interest {interest}: {e}")
                    FETCH_METRICS['failed_sources'].append(f"GNews-{interest}")
                    continue
                except Exception as e:
                    logger.error(f"Unexpected error fetching articles for interest {interest}: {e}")
                    FETCH_METRICS['failed_sources'].append(f"GNews-{interest}")
                    continue
        else:
            logger.warning("USER_INTERESTS is not a dictionary, skipping interest-based fetching")

        if not all_articles:
            logger.warning("No articles were fetched from any source")
            return []
            
        # Add age categorization to all articles
        for article in all_articles:
            if article.get('published_at'):
                article['age_category'] = categorize_article_age(article['published_at'])
            else:
                article['age_category'] = 'Unknown'
        
        logger.info(f"Successfully fetched {len(all_articles)} total articles")
        return all_articles
        
    except Exception as e:
        logger.error(f"Error in GNews fetch process: {e}")
        return []

def fetch_articles_from_all_feeds(max_articles_per_source: int = 5) -> Tuple[List[Dict], Dict]:
    """
    Main function to fetch all articles using GNews API.
    
    Args:
        max_articles_per_source: Maximum articles to fetch per source
        
    Returns:
        tuple: (list of articles, fetch statistics dictionary)
    """
    logger.info("Starting news fetch process...")
    FETCH_METRICS['start_time'] = time.time()

    try:
        all_articles = fetch_from_gnews()
    except Exception as e:
        logger.error(f"Error fetching from GNews API: {e}")
        all_articles = []

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

    # Log sample articles for debugging
    for i, article in enumerate(all_articles[:3]):
        logger.info(f"\nArticle {i+1}:")
        logger.info(f"  Title: {article.get('title')}")
        logger.info(f"  Description: {article.get('description')}")
        logger.info(f"  Link: {article.get('url', article.get('link'))}")
        logger.info(f"  Source: {article.get('source', {}).get('name', 'Unknown Source')}")
        logger.info(f"  Published: {article.get('published_at')}")
        logger.info(f"  Category: {article.get('category', 'Uncategorized')}")
        logger.info(f"  Age Category: {article.get('age_category', 'Unknown')}")

    return all_articles, fetch_stats

# --- Test Execution ---
if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.DEBUG, # Use DEBUG for detailed pool/fetch logs during testing
                        format='%(asctime)s - %(levelname)s - [%(threadName)s] - %(message)s')

    logger.info("--- Starting Standalone Fetch Test ---")

    # Example: Fetch articles with content
    fetched_articles, fetch_stats = fetch_articles_from_all_feeds(max_articles_per_source=2) # Limit articles per feed for test

    logger.info(f"--- Fetch Test Completed ---")
    logger.info(f"Total articles fetched: {len(fetched_articles)}")

    # Print details of a few articles
    for i, article in enumerate(fetched_articles[:3]):
        logger.info(f"\nArticle {i+1}:")
        logger.info(f"  Title: {article.get('title')}")
        logger.info(f"  Link: {article.get('url', article.get('link'))}")
        logger.info(f"  Source: {article.get('source', {}).get('name', 'Unknown Source')}")
        logger.info(f"  Published: {article.get('published_at')}")
        logger.info(f"  Age Category: {article.get('age_category')}")
        logger.info(f"  Category: {article.get('category')}")
