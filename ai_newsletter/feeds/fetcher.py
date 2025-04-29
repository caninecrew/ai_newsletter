"""Main module for fetching news articles from GNews API."""
import time
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Tuple
from dateutil import parser as dateutil_parser, tz as dateutil_tz
from ai_newsletter.logging_cfg.logger import setup_logger
from ai_newsletter.config.settings import (
    SYSTEM_SETTINGS,
    NEWS_CATEGORIES,
    GNEWS_DAILY_LIMIT,
    GNEWS_REQUEST_DELAY
)
from ai_newsletter.feeds.gnews_api import GNewsAPI, GNewsAPIError

# Initialize logger
logger = setup_logger()

# --- Metrics Initialization ---
FETCH_METRICS = {
    'start_time': None,
    'processing_time': 0,
    'total_articles': 0,
    'articles_per_category': {},
    'failed_queries': [],
    'empty_queries': []
}

def fetch_articles_by_category() -> List[Dict]:
    """
    Fetch articles using the GNews API based on configured categories and their queries.
    
    Returns:
        List[Dict]: List of articles with category information
    """
    try:
        gnews_client = GNewsAPI()
        all_articles = []
        requests_made = 0
        
        logger.info("Starting GNews API article fetch process")
        
        # Process each category
        for category, config in NEWS_CATEGORIES.items():
            if not config.get('enabled', True):
                logger.debug(f"Category {category} is disabled, skipping")
                continue
                
            FETCH_METRICS['articles_per_category'][category] = 0
            
            # Process each query in the category
            for query in config.get('queries', []):
                # Check API rate limit
                if requests_made >= GNEWS_DAILY_LIMIT:
                    logger.warning("Daily API limit reached, stopping fetch process")
                    break
                    
                try:
                    logger.debug(f"Fetching articles for category '{category}' with query: {query}")
                    articles = gnews_client.search_news(
                        query=query,
                        language="en",
                        max_results=3  # Limit per query to ensure diverse coverage
                    )
                    requests_made += 1
                    time.sleep(GNEWS_REQUEST_DELAY)  # Respect rate limiting
                    
                    if articles:
                        # Add category information to each article
                        for article in articles:
                            article['newsletter_category'] = category
                            article['query_matched'] = query
                        
                        all_articles.extend(articles)
                        FETCH_METRICS['articles_per_category'][category] += len(articles)
                        logger.info(f"Fetched {len(articles)} articles for {category} - {query}")
                    else:
                        logger.warning(f"No articles found for query: {query} in category: {category}")
                        FETCH_METRICS['empty_queries'].append(f"{category}:{query}")
                        
                except GNewsAPIError as e:
                    logger.error(f"GNews API error for {category} - {query}: {e}")
                    FETCH_METRICS['failed_queries'].append(f"{category}:{query}")
                    continue
                except Exception as e:
                    logger.error(f"Unexpected error for {category} - {query}: {e}")
                    FETCH_METRICS['failed_queries'].append(f"{category}:{query}")
                    continue
                    
            if requests_made >= GNEWS_DAILY_LIMIT:
                break

        if not all_articles:
            logger.warning("No articles were fetched from any category")
            return []
            
        # Add age categorization
        for article in all_articles:
            if article.get('published_at'):
                try:
                    pub_date = datetime.fromisoformat(article['published_at'].replace('Z', '+00:00'))
                    article['age_category'] = categorize_article_age(pub_date)
                except (ValueError, TypeError) as e:
                    logger.warning(f"Error parsing article date: {e}")
                    article['age_category'] = 'Unknown'
            else:
                article['age_category'] = 'Unknown'
                
        logger.info(f"Successfully fetched {len(all_articles)} total articles across {len(FETCH_METRICS['articles_per_category'])} categories")
        return all_articles
        
    except Exception as e:
        logger.error(f"Error in GNews fetch process: {e}")
        return []

def categorize_article_age(published_date: datetime) -> str:
    """Categorizes article age relative to now."""
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
