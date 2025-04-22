import requests
from datetime import datetime, timedelta
from logger_config import setup_logger
import os
from dotenv import load_dotenv
from config import GNEWS_API_CONFIG, USER_INTERESTS

# Set up logger
logger = setup_logger()

# Load environment variables
load_dotenv()

def fetch_articles_from_gnews():
    """
    Fetch news articles from GNews API based on configured topics and user interests.
    
    Returns:
        list: A list of article dictionaries with standardized format for processing
    """
    all_articles = []
    api_key = GNEWS_API_CONFIG["api_key"]

    # Check if API key is available
    if not api_key:
        api_key = os.environ.get("GNEWS_API_KEY")
        
    if not api_key:
        logger.error("GNews API key not found. Please set it in config.py or as GNEWS_API_KEY in environment variables.")
        return []
    
    # Calculate the time window for articles
    hours = GNEWS_API_CONFIG.get("hours", 24)
    from_date = (datetime.now() - timedelta(hours=hours)).strftime('%Y-%m-%dT%H:%M:%S') + 'Z'
    
    # Set up base parameters
    base_params = {
        "apikey": api_key,
        "lang": GNEWS_API_CONFIG.get("language", "en"),
        "country": GNEWS_API_CONFIG.get("country", "us"),
        "from": from_date,
        "sortby": "publishedAt",
        "max": GNEWS_API_CONFIG.get("max_results", 10)
    }
    
    # Fetch by topic categories
    topic_mapping = GNEWS_API_CONFIG.get("topic_mapping", {})
    logger.info(f"Fetching articles from GNews API using {len(topic_mapping)} topic categories")
    
    for section, topics in topic_mapping.items():
        if not isinstance(topics, list):
            topics = [topics]  # Convert to list if it's a single string
            
        for topic in topics:
            logger.info(f"Fetching articles for section '{section}', topic '{topic}'")
            try:
                # Create topic-specific parameters
                params = base_params.copy()
                params["topic"] = topic
                
                # Make API request
                response = requests.get("https://gnews.io/api/v4/top-headlines", params=params)
                response.raise_for_status()
                data = response.json()
                
                # Process articles
                if "articles" in data:
                    articles_count = len(data["articles"])
                    logger.info(f"Retrieved {articles_count} articles for topic '{topic}'")
                    
                    for article in data["articles"]:
                        # Create standardized article object
                        all_articles.append({
                            'title': article.get("title", "No Title"),
                            'url': article.get("url", ""),
                            'source': article.get("source", {}).get("name", "GNews"),
                            'category': section,
                            'published': article.get("publishedAt", ""),
                            'content': article.get("content", article.get("description", "")),
                            'fetch_method': "gnews_api"
                        })
                else:
                    logger.warning(f"No 'articles' field in GNews API response for topic '{topic}'")
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"Error fetching {topic} articles from GNews API: {str(e)}")
    
    # Fetch articles based on user interests
    logger.info(f"Fetching articles based on {len(USER_INTERESTS)} user interests")
    
    for interest in USER_INTERESTS:
        try:
            # Create interest-specific parameters
            params = base_params.copy()
            params["q"] = interest
            params.pop("topic", None)  # Remove topic parameter for keyword search
            
            # Make API request
            response = requests.get("https://gnews.io/api/v4/search", params=params)
            response.raise_for_status()
            data = response.json()
            
            # Process articles
            if "articles" in data:
                articles_count = len(data["articles"])
                logger.info(f"Retrieved {articles_count} articles for interest '{interest}'")
                
                for article in data["articles"]:
                    # Create standardized article object
                    all_articles.append({
                        'title': article.get("title", "No Title"),
                        'url': article.get("url", ""),
                        'source': article.get("source", {}).get("name", "GNews"),
                        'category': "personal_interest",
                        'published': article.get("publishedAt", ""),
                        'content': article.get("content", article.get("description", "")),
                        'fetch_method': "gnews_api",
                        'interest_match': interest
                    })
            else:
                logger.warning(f"No 'articles' field in GNews API response for interest '{interest}'")
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching articles for interest '{interest}' from GNews API: {str(e)}")
    
    # Log completion
    logger.info(f"GNews API fetching completed. Retrieved {len(all_articles)} total articles")
    return all_articles

# For testing the module independently
if __name__ == "__main__":
    articles = fetch_articles_from_gnews()
    logger.info(f"Retrieved {len(articles)} articles from GNews API")
    for i, article in enumerate(articles[:5]):
        logger.info(f"Article {i+1}: {article['title']} - {article['source']} ({article['category']})")