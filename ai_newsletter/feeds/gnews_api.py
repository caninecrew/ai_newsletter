import os
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging
from ..logging_cfg.logger import setup_logger

logger = setup_logger()

class GNewsClient:
    """Client for interacting with the GNews API."""
    
    BASE_URL = "https://gnews.io/api/v4"
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the GNews API client."""
        self.api_key = api_key or os.environ.get('GNEWS_API_KEY')
        if not self.api_key:
            raise ValueError("GNews API key is required. Set GNEWS_API_KEY environment variable.")
    
    def search_news(self, 
                   query: str, 
                   language: str = "en",
                   country: Optional[str] = None,
                   max_results: int = 10,
                   from_date: Optional[datetime] = None) -> List[Dict]:
        """
        Search for news articles using the GNews API.
        
        Args:
            query: Search query string
            language: Language code (default: "en")
            country: Optional country code
            max_results: Maximum number of results to return (default: 10)
            from_date: Optional start date for articles
            
        Returns:
            List of article dictionaries
        """
        params = {
            'q': query,
            'lang': language,
            'max': max_results,
            'apikey': self.api_key
        }
        
        if country:
            params['country'] = country
            
        if from_date:
            params['from'] = from_date.strftime("%Y-%m-%dT%H:%M:%SZ")
            
        try:
            response = requests.get(f"{self.BASE_URL}/search", params=params)
            response.raise_for_status()
            data = response.json()
            
            articles = []
            for article in data.get('articles', []):
                processed_article = {
                    'title': article.get('title'),
                    'description': article.get('description'),
                    'content': article.get('content'),
                    'link': article.get('url'),
                    'source': article.get('source', {}).get('name'),
                    'published': datetime.strptime(article.get('publishedAt'), "%Y-%m-%dT%H:%M:%SZ"),
                    'fetch_method': 'gnews_api'
                }
                articles.append(processed_article)
            
            return articles
            
        except requests.exceptions.RequestException as e:
            logger.error(f"GNews API request failed: {e}")
            if hasattr(e.response, 'status_code'):
                if e.response.status_code == 429:
                    logger.error("GNews API rate limit exceeded")
                elif e.response.status_code == 401:
                    logger.error("Invalid GNews API key")
            raise
            
    def get_top_headlines(self,
                         language: str = "en",
                         country: Optional[str] = None,
                         category: Optional[str] = None,
                         max_results: int = 10) -> List[Dict]:
        """
        Get top headlines from GNews API.
        
        Args:
            language: Language code (default: "en")
            country: Optional country code
            category: Optional category (business, entertainment, health, science, sports, technology)
            max_results: Maximum number of results to return (default: 10)
            
        Returns:
            List of article dictionaries
        """
        params = {
            'lang': language,
            'max': max_results,
            'apikey': self.api_key
        }
        
        if country:
            params['country'] = country
            
        if category:
            params['category'] = category
            
        try:
            response = requests.get(f"{self.BASE_URL}/top-headlines", params=params)
            response.raise_for_status()
            data = response.json()
            
            articles = []
            for article in data.get('articles', []):
                processed_article = {
                    'title': article.get('title'),
                    'description': article.get('description'),
                    'content': article.get('content'),
                    'link': article.get('url'),
                    'source': article.get('source', {}).get('name'),
                    'published': datetime.strptime(article.get('publishedAt'), "%Y-%m-%dT%H:%M:%SZ"),
                    'fetch_method': 'gnews_api'
                }
                articles.append(processed_article)
            
            return articles
            
        except requests.exceptions.RequestException as e:
            logger.error(f"GNews API request failed: {e}")
            if hasattr(e.response, 'status_code'):
                if e.response.status_code == 429:
                    logger.error("GNews API rate limit exceeded")
                elif e.response.status_code == 401:
                    logger.error("Invalid GNews API key")
            raise