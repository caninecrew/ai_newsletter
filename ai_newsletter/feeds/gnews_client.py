import os
from datetime import datetime, timedelta
import logging
from typing import List, Dict, Optional, Any, Tuple
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from urllib.parse import urlparse
from dateutil import parser as dateutil_parser
import gnews
from ai_newsletter.core.types import Article, ArticleSource, ArticleMetadata

logger = logging.getLogger(__name__)

class GNewsAPIError(Exception):
    """Custom exception for GNews API errors."""
    pass

class GNewsAPI:
    """Interface for fetching news from GNews API."""
    
    def __init__(self, language: str = 'en', country: str = 'US', max_results: int = 10):
        """Initialize GNewsAPI with configuration."""
        self.gnews = gnews.GNews(
            language=language, 
            country=country, 
            max_results=max_results,
            period='1d'  # Default to last 24 hours
        )
        
        # Source reliability scores (0.0-1.0)
        self.source_reliability = {
            'associated press': 0.95,
            'reuters': 0.95,
            'bbc': 0.9,
            'the new york times': 0.85,
            'the washington post': 0.85,
            'the wall street journal': 0.85,
            'bloomberg': 0.85,
            'npr': 0.85,
            'cnn': 0.75,
            'fox news': 0.75,
            'msnbc': 0.75,
            'the guardian': 0.85,
            'the economist': 0.9,
            'techcrunch': 0.8,
            'wired': 0.8,
            'ars technica': 0.85
        }
        
        # Source categories
        self.source_categories = {
            'cnn': 'LEFT_LEANING',
            'msnbc': 'LEFT_LEANING',
            'new york times': 'LEFT_LEANING',
            'washington post': 'LEFT_LEANING',
            'fox news': 'RIGHT_LEANING',
            'national review': 'RIGHT_LEANING',
            'newsmax': 'RIGHT_LEANING',
            'washington examiner': 'RIGHT_LEANING',
            'reuters': 'CENTER',
            'associated press': 'CENTER',
            'bbc': 'CENTER',
            'npr': 'CENTER',
            'wall street journal': 'CENTER'
        }

    def extract_source_metadata(self, source_name: str) -> Tuple[str, float, str]:
        """Extract source name, reliability score, and category."""
        name_lower = source_name.lower()
        
        # Get reliability score
        reliability = 0.7  # Default score for unknown sources
        for known_source, score in self.source_reliability.items():
            if known_source in name_lower:
                reliability = score
                break
        
        # Get category
        category = 'UNCATEGORIZED'
        for known_source, cat in self.source_categories.items():
            if known_source in name_lower:
                category = cat
                break
        
        return source_name, reliability, category

    def process_article(self, article: Dict[str, Any]) -> Article:
        """Process a raw article into standardized format with metadata."""
        # Extract source information
        raw_source = article.get('source', {})
        source_name = raw_source.get('name', 'Unknown Source')
        name, reliability, category = self.extract_source_metadata(source_name)
        
        # Create source object
        source: ArticleSource = {
            'name': name,
            'url': raw_source.get('url'),
            'category': category,
            'reliability_score': reliability
        }
        
        # Create metadata object
        metadata: ArticleMetadata = {
            'date_extracted': True,
            'date_confidence': 1.0,  # GNews dates are reliable
            'original_date': article.get('published_at'),
            'source_confidence': 1.0 if source_name != 'Unknown Source' else 0.5,
            'extracted_from_url': False
        }
        
        # Create standardized article
        processed: Article = {
            'title': article.get('title', 'No Title'),
            'description': article.get('description', ''),
            'url': article.get('url', ''),
            'published_at': article.get('published_at', ''),
            'source': source,
            'summary': None,
            'summary_method': None,
            'newsletter_category': None,
            'query_matched': None,
            'tags': [],
            'metadata': metadata
        }
        
        return processed

    def search_news(self, query: str) -> List[Article]:
        """Search for news articles using a query."""
        try:
            raw_articles = self.gnews.get_news(query)
            return [self.process_article(a) for a in raw_articles]
        except Exception as e:
            logger.error(f"Failed to fetch news: {str(e)}")
            raise GNewsAPIError(f"Failed to fetch news: {str(e)}")

    def get_top_headlines(self) -> List[Article]:
        """Get top headlines."""
        try:
            raw_articles = self.gnews.get_top_news()
            return [self.process_article(a) for a in raw_articles]
        except Exception as e:
            logger.error(f"Failed to fetch top headlines: {str(e)}")
            raise GNewsAPIError(f"Failed to fetch top headlines: {str(e)}")

    def is_major_story(self, article: Article) -> bool:
        """Determine if a story is a major international event."""
        title = article.get('title', '').lower()
        description = article.get('description', '').lower()
        content = f"{title} {description}"
        
        # Major keywords indicating significant stories
        major_keywords = [
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
        
        # Common country names to check for international context
        countries = {
            'united states', 'china', 'russia', 'india', 'japan', 'germany', 
            'united kingdom', 'france', 'italy', 'canada', 'brazil', 'australia', 
            'south korea', 'spain', 'mexico', 'indonesia', 'netherlands', 
            'saudi arabia', 'turkey', 'switzerland'
        }
        
        # Check for major keywords
        if any(keyword.lower() in content for keyword in major_keywords):
            return True
            
        # Check for multiple country mentions
        country_mentions = sum(1 for country in countries if country in content)
        if country_mentions >= 2:
            return True
            
        return False

    def fetch_news(self) -> List[Article]:
        """Fetch news articles combining top headlines with major stories."""
        # Get top headlines
        top_headlines = self.get_top_headlines()
        
        # Get international news
        time_frame = f"when:{int((datetime.now() - timedelta(days=1)).timestamp())}"
        international_news = self.search_news(time_frame)
        
        # Filter for major stories
        major_international = [
            article for article in international_news 
            if self.is_major_story(article)
        ]
        
        # Combine and deduplicate
        seen_urls = set()
        all_articles = []
        
        for article in top_headlines + major_international:
            url = article.get('url')
            if url and url not in seen_urls:
                seen_urls.add(url)
                all_articles.append(article)
        
        # Sort by date
        return sorted(
            all_articles,
            key=lambda x: dateutil_parser.parse(x['published_at']) if x.get('published_at') else datetime.min,
            reverse=True
        )