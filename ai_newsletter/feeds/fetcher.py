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

def fetch_articles_by_category() -> List[Dict]:
    """
    Fetch articles using the GNews API based on configured categories and their queries.
    Also fetches top headlines.
    
    Returns:
        List[Dict]: List of articles with category information
    """
    try:
        gnews_client = GNewsAPI()
        all_articles = []
        requests_made = 0
        
        logger.info("Starting GNews API article fetch process")
        
        # Calculate cutoff time for article age filtering
        cutoff_time = datetime.now(timezone.utc) - timedelta(days=1)
        logger.info(f"Filtering articles newer than {cutoff_time.isoformat()}")
        
        # First fetch top headlines
        try:
            logger.info("Fetching top headlines...")
            top_headlines = gnews_client.get_top_headlines(
                language="en",
                max_results=5  # Limit top headlines to avoid overwhelming other categories
            )
            requests_made += 1
            time.sleep(GNEWS_REQUEST_DELAY)
            
            if top_headlines:
                fresh_headlines = []
                for article in top_headlines:
                    try:
                        pub_date = dateutil_parser.parse(article['published_at'])
                        if pub_date.tzinfo is None:
                            pub_date = pub_date.replace(tzinfo=timezone.utc)
                        
                        if pub_date >= cutoff_time:
                            article['newsletter_category'] = 'TOP_HEADLINES'
                            article['query_matched'] = 'top_headlines'
                            article['age_category'] = categorize_article_age(pub_date)
                            fresh_headlines.append(article)
                        else:
                            FETCH_METRICS['filtered_old_articles'] += 1
                    except (ValueError, TypeError, KeyError) as e:
                        logger.warning(f"Error parsing headline date: {e}")
                        continue
                
                if fresh_headlines:
                    all_articles.extend(fresh_headlines)
                    FETCH_METRICS['articles_per_category']['TOP_HEADLINES'] = len(fresh_headlines)
                    logger.info(f"Fetched {len(fresh_headlines)} fresh top headlines")
                else:
                    logger.warning("No fresh top headlines found")
                    FETCH_METRICS['empty_queries'].append("TOP_HEADLINES:top_headlines")
            else:
                logger.warning("No top headlines returned from API")
                FETCH_METRICS['empty_queries'].append("TOP_HEADLINES:top_headlines")
                
        except GNewsAPIError as e:
            logger.error(f"GNews API error fetching top headlines: {e}")
            FETCH_METRICS['failed_queries'].append("TOP_HEADLINES:top_headlines")
        except Exception as e:
            logger.error(f"Unexpected error fetching top headlines: {e}")
            FETCH_METRICS['failed_queries'].append("TOP_HEADLINES:top_headlines")
        
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
                        # Filter articles by age and add category information
                        fresh_articles = []
                        for article in articles:
                            # Parse the published_at date
                            try:
                                pub_date = dateutil_parser.parse(article['published_at'])
                                if pub_date.tzinfo is None:
                                    pub_date = pub_date.replace(tzinfo=timezone.utc)
                                
                                # Only include articles newer than cutoff time
                                if pub_date >= cutoff_time:
                                    article['newsletter_category'] = category
                                    article['query_matched'] = query
                                    article['age_category'] = categorize_article_age(pub_date)
                                    fresh_articles.append(article)
                                else:
                                    FETCH_METRICS['filtered_old_articles'] += 1
                            except (ValueError, TypeError, KeyError) as e:
                                logger.warning(f"Error parsing article date: {e}")
                                continue
                        
                        if fresh_articles:
                            all_articles.extend(fresh_articles)
                            FETCH_METRICS['articles_per_category'][category] += len(fresh_articles)
                            logger.info(f"Fetched {len(fresh_articles)} fresh articles for {category} - {query}")
                        else:
                            logger.warning(f"No fresh articles found for query: {query} in category: {category}")
                            FETCH_METRICS['empty_queries'].append(f"{category}:{query}")
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
            logger.warning("No articles were fetched from any category or top headlines")
            return []

        # Log filtering metrics
        logger.info(f"Filtered out {FETCH_METRICS['filtered_old_articles']} articles older than 24 hours")
        logger.info(f"Successfully fetched {len(all_articles)} fresh articles (including top headlines) across {len(FETCH_METRICS['articles_per_category'])} categories")
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
