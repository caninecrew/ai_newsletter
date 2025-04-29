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
        self.gnews = gnews.GNews(language=language, country=country, max_results=max_results)
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
        
    def is_major_story(self, article: Dict[str, Any]) -> bool:
        """
        Determine if a story is a major international event.
        """
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
        """
        Fetch news articles, combining top headlines with major international stories.
        """
        # Get top headlines
        top_headlines = self.gnews.get_top_news()
        
        # Get international news from the past 24 hours
        time_frame = f"when:{int((datetime.now() - timedelta(days=1)).timestamp())}"
        international_news = self.gnews.get_news(time_frame)
        
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