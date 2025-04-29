import os
from datetime import datetime
import logging
from typing import List, Dict, Optional, Any
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from urllib.parse import urlencode
from dateutil import parser as dateutil_parser

logger = logging.getLogger(__name__)

class GNewsAPIError(Exception):
    """Custom exception for GNews API errors."""
    pass

class GNewsAPI:
    """Client for the GNews API service."""
    
    BASE_URL = "https://gnews.io/api/v4"
    
    def __init__(self):
        self.api_key = os.getenv('GNEWS_API_KEY')
        if not self.api_key:
            raise GNewsAPIError("GNEWS_API_KEY environment variable not set")
            
        # Configure session with retry logic
        self.session = requests.Session()
        retries = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504]
        )
        self.session.mount('https://', HTTPAdapter(max_retries=retries))
    
    def _validate_query(self, query: str) -> str:
        """Validate query string before sending to GNews API."""
        if not query or len(query.strip()) < 3:
            raise ValueError(f"Invalid search term: {query}")
        return query.strip()
    
    def _validate_response(self, data: dict) -> None:
        """Validate GNews API response data."""
        if not isinstance(data, dict):
            raise GNewsAPIError(f"Invalid response format. Expected dict, got {type(data)}")
            
        if 'errors' in data:
            raise GNewsAPIError(f"API returned errors: {data['errors']}")
            
        if 'articles' not in data:
            raise GNewsAPIError("Response missing 'articles' field")
            
        if not isinstance(data['articles'], list):
            raise GNewsAPIError(f"Invalid articles format. Expected list, got {type(data['articles']}")
    
    def _build_url(self, endpoint: str, params: Dict[str, Any]) -> str:
        """Build URL with proper encoding for GNews API."""
        # Log the request URL for debugging (without API key)
        debug_params = params.copy()
        debug_params['apikey'] = 'REDACTED'
        debug_url = f"{self.BASE_URL}/{endpoint}?{urlencode(debug_params)}"
        logger.debug(f"GNews API request URL (redacted): {debug_url}")
        
        # Build and return actual URL with API key
        return f"{self.BASE_URL}/{endpoint}?{urlencode(params)}"

    def search_news(
        self,
        query: str,
        language: str = "en",
        country: Optional[str] = None,
        max_results: int = 10,
        exclude_domains: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for news articles using the GNews API.
        
        Args:
            query: Search query string
            language: Language code (default: "en")
            country: Optional country code
            max_results: Maximum number of results to return
            exclude_domains: List of domains to exclude from results
            
        Returns:
            List of articles as dictionaries
            
        Raises:
            GNewsAPIError: If the API request fails or returns invalid data
        """
        # Validate but don't pre-encode the query
        validated_query = self._validate_query(query)
        
        params = {
            'q': validated_query,  # Let urlencode handle the encoding
            'lang': language,
            'max': min(max_results, 100),  # API limit is 100
            'apikey': self.api_key
        }
        
        if country:
            params['country'] = country
            
        try:
            url = self._build_url('search', params)
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            self._validate_response(data)
            articles = data['articles']
            
            # Filter out excluded domains if specified
            if exclude_domains:
                articles = [
                    article for article in articles
                    if not any(domain in article.get('source', {}).get('url', '')
                             for domain in exclude_domains)
                ]
            
            return self._process_articles(articles[:max_results])
            
        except requests.exceptions.RequestException as e:
            logger.error(f"GNews API request failed: {str(e)}")
            raise GNewsAPIError(f"Failed to fetch news: {str(e)}")
            
    def get_top_headlines(
        self,
        language: str = "en",
        country: Optional[str] = None,
        category: Optional[str] = None,
        max_results: int = 10
    ) -> List[Dict]:
        """
        Fetch top headlines using the GNews API.
        
        Args:
            language: Language code (default: "en")
            country: Optional country code
            category: Optional category (general, world, nation, business, etc.)
            max_results: Maximum number of results to return
            
        Returns:
            List of articles as dictionaries
            
        Raises:
            GNewsAPIError: If the API request fails or returns invalid data
        """
        params = {
            'lang': language,
            'max': min(max_results, 100),
            'apikey': self.api_key
        }
        
        if country:
            params['country'] = country
        if category:
            params['category'] = category
            
        try:
            url = self._build_url('top-headlines', params)
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            self._validate_response(data)
            articles = data['articles']
            return self._process_articles(articles[:max_results])
            
        except requests.exceptions.RequestException as e:
            logger.error(f"GNews API request failed: {str(e)}")
            raise GNewsAPIError(f"Failed to fetch headlines: {str(e)}")
    
    def _process_articles(self, articles: List[Dict]) -> List[Dict]:
        """Process and normalize article data."""
        processed_articles = []
        
        for article in articles:
            if not isinstance(article, dict):
                logger.warning(f"Skipping invalid article format: {type(article)}")
                continue
                
            # Ensure we have a URL field
            url = article.get('url')
            if not url:
                logger.warning("Skipping article without URL")
                continue
                
            try:
                # Pre-validate required fields
                title = article.get('title', '').strip()
                description = article.get('description', '').strip()
                published_at = article.get('publishedAt')
                
                if not title:
                    logger.warning(f"Skipping article with empty title: {url}")
                    continue
                
                # Parse date with more robust method
                parsed_date = self._parse_date(published_at) if published_at else None
                if not parsed_date:
                    logger.warning(f"Article date parsing failed: {url}")
                
                processed_article = {
                    'title': title,
                    'description': description,
                    'url': url,
                    'link': url,  # For compatibility
                    'source': {
                        'name': article.get('source', {}).get('name', '').strip() if isinstance(article.get('source'), dict) else str(article.get('source', '')).strip(),
                        'url': article.get('source', {}).get('url', '').strip() if isinstance(article.get('source'), dict) else ''
                    },
                    'published_at': parsed_date.isoformat() if parsed_date else None
                }
                
                processed_articles.append(processed_article)
                
            except Exception as e:
                logger.warning(f"Error processing article {url}: {str(e)}")
                continue
            
        return processed_articles
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse API date string into datetime object using dateutil."""
        if not date_str:
            return None
            
        try:
            # Use dateutil.parser for more robust date parsing
            return dateutil_parser.parse(date_str)
        except ValueError as e:
            logger.warning(f"Failed to parse date: {date_str} - {str(e)}")
            return None