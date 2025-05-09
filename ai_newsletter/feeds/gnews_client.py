import os
from datetime import datetime, timedelta
import logging
from typing import List, Dict, Optional, Any
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from urllib.parse import urlencode
from dateutil import parser as dateutil_parser
import gnews

logger = logging.getLogger(__name__)

class GNewsAPIError(Exception):
    """Custom exception for GNews API errors."""
    pass

class GNewsAPI:
    """Interface for fetching news from GNews API."""
    
    def __init__(self, language: str = 'en', country: str = 'US', max_results: int = 10):
        """Initialize GNewsAPI with configuration.
        
        Args:
            language: Language for news articles
            country: Country for news articles
            max_results: Maximum number of results to return
        """
        self.gnews = gnews.GNews(
            language=language, 
            country=country, 
            max_results=max_results,
            period='1d'  # Default to last 24 hours
        )
        self.major_keywords = [
            'global crisis',
            'world summit',
            'international conflict',
            'global economy',
            'climate change',
            'pandemic',
            'worldwide',
            'international agreement',
            'global market',
            'United Nations',
            'NATO',
            'WHO',
            'global impact'
        ]

    def search_news(self, query: str) -> List[Dict[str, Any]]:
        """Search for news articles using a query."""
        try:
            return self.gnews.get_news(query)
        except Exception as e:
            logger.error(f"Failed to fetch news: {str(e)}")
            raise GNewsAPIError(f"Failed to fetch news: {str(e)}")

    def get_top_headlines(self) -> List[Dict[str, Any]]:
        """Get top headlines."""
        try:
            return self.gnews.get_top_news()
        except Exception as e:
            logger.error(f"Failed to fetch top headlines: {str(e)}")
            raise GNewsAPIError(f"Failed to fetch top headlines: {str(e)}")

    def is_major_story(self, article: Dict[str, Any]) -> bool:
        """Determine if a story is a major international event."""
        title = article.get('title', '').lower()
        description = article.get('description', '').lower()
        content = f"{title} {description}"
        
        # Check if contains major keywords
        if any(keyword.lower() in content for keyword in self.major_keywords):
            return True
            
        # Check if multiple countries are mentioned (indicates international scope)
        from country_list import countries_for_language
        countries = dict(countries_for_language('en')).values()
        country_mentions = sum(1 for country in countries if country.lower() in content)
        if country_mentions >= 2:
            return True
            
        return False

    def fetch_news(self) -> List[Dict[str, Any]]:
        """Fetch news articles, combining top headlines with major international stories."""
        # Get top headlines using the correct method
        top_headlines = self.get_top_headlines()
        
        # Get international news from the past 24 hours
        time_frame = f"when:{int((datetime.now() - timedelta(days=1)).timestamp())}"
        international_news = self.search_news(time_frame)
        
        # Filter international news for major stories only
        major_international = [
            article for article in international_news 
            if self.is_major_story(article)
        ]
        
        # Combine and deduplicate articles
        all_articles = []
        seen_urls = set()
        
        for article in top_headlines + major_international:
            url = article.get('url')
            if url and url not in seen_urls:
                seen_urls.add(url)
                all_articles.append(article)
        
        # Sort by publication date
        all_articles.sort(
            key=lambda x: dateutil_parser.parse(x.get('published_at', '')),
            reverse=True
        )
        
        return all_articles[:self.gnews.max_results]

def test_gnews_connection() -> bool:
    """Test GNews API connectivity.
    
    Returns:
        bool: True if connection successful, False otherwise
        
    Raises:
        Exception: If connection test fails
    """
    api_key = os.getenv('GNEWS_API_KEY')
    if not api_key:
        raise Exception("GNews API key not found")
        
    try:
        # Test with minimal query to validate API key
        response = requests.get(
            'https://gnews.io/api/v4/search',
            params={
                'q': 'test',
                'max': 1,
                'apikey': api_key
            },
            timeout=10
        )
        response.raise_for_status()
        
        # Verify response structure
        data = response.json()
        if 'articles' not in data:
            raise Exception("Invalid API response structure")
            
        return True
        
    except requests.exceptions.RequestException as e:
        raise Exception(f"GNews API connection failed: {str(e)}")