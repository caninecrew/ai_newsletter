"""Main module for fetching news articles from GNews API."""
import time
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Tuple, Any
from dateutil import parser as dateutil_parser, tz as dateutil_tz
from ai_newsletter.logging_cfg.logger import setup_logger
from ai_newsletter.config.settings import (
    SYSTEM_SETTINGS,
    NEWS_CATEGORIES,
    GNEWS_DAILY_LIMIT,
    GNEWS_REQUEST_DELAY
)
from ai_newsletter.feeds.gnews_client import GNewsAPI, GNewsAPIError

# Initialize logger
logger = setup_logger()

# --- Metrics Initialization ---
FETCH_METRICS = {
    'start_time': None,
    'processing_time': 0,
    'total_articles': 0,
    'articles_per_category': {},
    'failed_queries': [],
    'empty_queries': [],
    'filtered_old_articles': 0  # New metric to track filtered articles
}

def safe_fetch_news_articles(**kwargs) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Safe wrapper around fetch_articles_from_all_feeds with parameter validation.
    
    Args:
        **kwargs: Keyword arguments to pass to fetch_articles_from_all_feeds
        
    Returns:
        tuple: (list of articles, fetch statistics dictionary)
    """
    # Parameter validation
    valid_params = {
        'max_articles_per_source': int,
        'language': str,
        'country': str
    }

    # Filter and validate parameters
    filtered_kwargs = {}
    for key, value in kwargs.items():
        if key in valid_params:
            expected_type = valid_params[key]
            if not isinstance(value, expected_type):
                logger.warning(f"Parameter '{key}' has invalid type. Expected {expected_type.__name__}, got {type(value).__name__}")
                continue
            filtered_kwargs[key] = value
        else:
            logger.warning(f"Ignoring unexpected parameter '{key}' in fetch_news_articles call")

    try:
        return fetch_articles_from_all_feeds(**filtered_kwargs)
    except Exception as e:
        logger.error(f"Error in safe_fetch_news_articles: {str(e)}")
        return [], {"error": str(e)}

def categorize_article_age(published_date: datetime) -> str:
    """
    Categorizes article age relative to now.
    
    Args:
        published_date: The article's publication date (timezone-aware)
        
    Returns:
        str: Age category ('Breaking', 'Today', 'Yesterday', 'This Week', or 'Older')
    """
    if not published_date.tzinfo:
        published_date = published_date.replace(tzinfo=timezone.utc)
        
    now = datetime.now(timezone.utc)
    age = now - published_date
    
    if age < timedelta(hours=6):
        return 'Breaking'
    elif age < timedelta(hours=24):
        return 'Today'
    elif age < timedelta(days=2):
        return 'Yesterday'
    elif age < timedelta(days=7):
        return 'This Week'
    else:
        return 'Older'

def is_major_international_story(article: Dict[str, Any]) -> bool:
    """
    Determine if an article represents a major international story.
    
    Criteria:
    - Contains keywords indicating global significance
    - Not focused on local crime or minor incidents
    - Has international impact
    """
    title = article.get('title', '').lower()
    description = article.get('description', '').lower()
    content = f"{title} {description}"
    
    # Keywords indicating major international stories
    major_keywords = [
        'global', 'worldwide', 'international', 'crisis', 'summit', 
        'pandemic', 'climate', 'war', 'peace', 'treaty', 'united nations',
        'world health', 'global economy', 'international trade',
        'humanitarian', 'nuclear', 'diplomatic', 'g20', 'g7', 'nato',
        'security council', 'economic crisis', 'global market'
    ]
    
    # Keywords indicating local/minor stories to filter out
    local_keywords = [
        'local police', 'arrested', 'minor incident', 'local council',
        'neighborhood', 'city council', 'municipal', 'local resident',
        'small business', 'traffic accident', 'petty crime'
    ]
    
    # Check if any major keywords are present
    has_major_keywords = any(keyword in content for keyword in major_keywords)
    
    # Check if any local keywords are present
    has_local_keywords = any(keyword in content for keyword in local_keywords)
    
    return has_major_keywords and not has_local_keywords

def fetch_articles_by_category() -> List[Dict[str, Any]]:
    """Fetch articles for each news category."""
    articles = []
    gnews = GNewsAPI()
    
    # First, get top headlines
    try:
        top_headlines = gnews.get_top_headlines()
        for article in top_headlines:
            article['newsletter_category'] = 'TOP_HEADLINES'
            article['query_matched'] = 'top_headlines'
        articles.extend(top_headlines)
        time.sleep(GNEWS_REQUEST_DELAY)  # Respect API rate limits
    except Exception as e:
        logger.error(f"Error fetching top headlines: {e}")
        FETCH_METRICS['failed_queries'].append('TOP_HEADLINES:top_headlines')

    # Then fetch category-specific articles
    for category in NEWS_CATEGORIES:
        try:
            query = f"({category}) AND (global OR international OR worldwide)"
            category_articles = gnews.search_news(query)
            
            # Filter for major international stories
            filtered_articles = [
                article for article in category_articles
                if is_major_international_story(article)
            ]
            
            # Add metadata
            for article in filtered_articles:
                article['newsletter_category'] = category.upper()
                article['query_matched'] = query
            
            articles.extend(filtered_articles)
            
            # Update metrics
            FETCH_METRICS['articles_per_category'][category] = len(filtered_articles)
            
            if not filtered_articles:
                FETCH_METRICS['empty_queries'].append(f"{category}:{query}")
            
            time.sleep(GNEWS_REQUEST_DELAY)
            
        except Exception as e:
            logger.error(f"Error fetching {category} news: {e}")
            FETCH_METRICS['failed_queries'].append(f"{category}:{query}")

    # Remove duplicates based on URL
    unique_articles = {article['url']: article for article in articles}.values()
    
    # Sort by date (most recent first)
    sorted_articles = sorted(
        unique_articles,
        key=lambda x: dateutil_parser.parse(x['published_at']) if x.get('published_at') else datetime.min.replace(tzinfo=timezone.utc),
        reverse=True
    )
    
    return list(sorted_articles)

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
        articles = fetch_articles_by_category()
    except Exception as e:
        logger.error(f"Error fetching articles: {e}")
        articles = []

    # Update metrics and return
    end_time = time.time()
    processing_time = end_time - FETCH_METRICS['start_time']
    FETCH_METRICS['processing_time'] = processing_time
    FETCH_METRICS['total_articles'] = len(articles)

    logger.info(f"Total fetch process completed in {processing_time:.2f} seconds")
    
    fetch_stats = {
        "total_articles": len(articles),
        "processing_time": processing_time,
        "articles_per_category": FETCH_METRICS['articles_per_category'],
        "failed_queries": FETCH_METRICS['failed_queries'],
        "empty_queries": FETCH_METRICS['empty_queries']
    }
    
    return articles, fetch_stats

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
