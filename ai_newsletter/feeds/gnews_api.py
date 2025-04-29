import os
import time
import logging
import requests
from typing import List, Dict, Optional
from datetime import datetime, timezone
from ..logging_cfg.logger import setup_logger

logger = setup_logger()

class GNewsClient:
    """Client for interacting with the GNews API."""
    
    BASE_URL = "https://gnews.io/api/v4"
    
    def __init__(self):
        self.api_key = os.getenv('GNEWS_API_KEY')
        if not self.api_key:
            raise ValueError("GNEWS_API_KEY environment variable is required")
            
        self.session = requests.Session()
        self.last_request_time = 0
        self.min_request_interval = 1.0  # Minimum time between requests to avoid rate limits
        
    def _wait_for_rate_limit(self):
        """Implements basic rate limiting."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_request_interval:
            time.sleep(self.min_request_interval - time_since_last)
        self.last_request_time = time.time()
        
    def _make_request(self, endpoint: str, params: Dict) -> Dict:
        """Makes a request to the GNews API with rate limiting and error handling."""
        self._wait_for_rate_limit()
        
        params['apikey'] = self.api_key
        url = f"{self.BASE_URL}/{endpoint}"
        
        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:  # Too Many Requests
                logger.warning("Rate limit exceeded, implementing longer delay")
                time.sleep(5)  # Wait longer before retrying
                return self._make_request(endpoint, params)  # Retry once
            elif e.response.status_code == 403:  # Invalid API key
                logger.error("Invalid GNews API key")
                raise ValueError("Invalid GNews API key") from e
            else:
                logger.error(f"HTTP error occurred: {e}")
                raise
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise
            
    def _process_article(self, article: Dict) -> Dict:
        """Processes and normalizes a raw article from the API."""
        try:
            # Convert published date string to datetime
            published_at = article.get('publishedAt')
            if published_at:
                published_dt = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
            else:
                published_dt = None
                
            return {
                'title': article.get('title', '').strip(),
                'description': article.get('description', '').strip(),
                'content': article.get('content', '').strip(),
                'url': article.get('url', ''),
                'image': article.get('image'),
                'published': published_dt,
                'source': article.get('source', {}).get('name', 'Unknown'),
                'source_url': article.get('source', {}).get('url'),
                'fetch_method': 'gnews_api'
            }
            
        except Exception as e:
            logger.error(f"Error processing article: {e}")
            return None
            
    def search_news(
        self,
        query: str,
        language: str = 'en',
        country: Optional[str] = None,
        max_results: int = 10,
        exclude_websites: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        Search for news articles using the GNews API.
        
        Args:
            query: Search query string
            language: Language code (e.g., 'en' for English)
            country: Optional country code (e.g., 'us' for United States)
            max_results: Maximum number of results to return
            exclude_websites: Optional list of websites to exclude from results
            
        Returns:
            List of processed article dictionaries
        """
        params = {
            'q': query,
            'lang': language,
            'max': max_results
        }
        
        if country:
            params['country'] = country
            
        if exclude_websites:
            params['in'] = ','.join(f'site:{site}' for site in exclude_websites)
            
        try:
            data = self._make_request('search', params)
            articles = []
            
            for article in data.get('articles', []):
                processed = self._process_article(article)
                if processed:
                    articles.append(processed)
                    
            return articles
            
        except Exception as e:
            logger.error(f"Error searching news: {e}")
            return []
            
    def get_top_headlines(
        self,
        language: str = 'en',
        country: Optional[str] = None,
        category: Optional[str] = None,
        max_results: int = 10
    ) -> List[Dict]:
        """
        Get top headlines from GNews API.
        
        Args:
            language: Language code (e.g., 'en' for English)
            country: Optional country code (e.g., 'us' for United States)
            category: Optional category (general, world, nation, business, technology, etc.)
            max_results: Maximum number of results to return
            
        Returns:
            List of processed article dictionaries
        """
        params = {
            'lang': language,
            'max': max_results
        }
        
        if country:
            params['country'] = country
            
        if category:
            params['category'] = category
            
        try:
            data = self._make_request('top-headlines', params)
            articles = []
            
            for article in data.get('articles', []):
                processed = self._process_article(article)
                if processed:
                    articles.append(processed)
                    
            return articles
            
        except Exception as e:
            logger.error(f"Error fetching top headlines: {e}")
            return []