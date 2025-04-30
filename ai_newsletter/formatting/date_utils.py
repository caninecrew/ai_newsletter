"""Date handling utilities."""
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from dateutil import parser, tz as dateutil_tz
from bs4 import BeautifulSoup
import re
from urllib.parse import urlparse
from ai_newsletter.logging_cfg.logger import setup_logger
from ai_newsletter.core.types import Article, ArticleMetadata

logger = setup_logger()

# Define Central timezone
CENTRAL = dateutil_tz.gettz("America/Chicago")

def extract_date_from_metadata(html_content: str) -> Tuple[Optional[str], float]:
    """Extract publication date from HTML metadata."""
    if not html_content:
        return None, 0.0
    
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Common metadata patterns with confidence scores
    meta_patterns = [
        ('meta[property="article:published_time"]', 'content', 0.9),
        ('meta[property="og:article:published_time"]', 'content', 0.9),
        ('meta[name="publishedDate"]', 'content', 0.9),
        ('meta[name="date"]', 'content', 0.8),
        ('time[datetime]', 'datetime', 0.8),
        ('.article-date', 'datetime', 0.7),
        ('.published-date', 'datetime', 0.7)
    ]
    
    for selector, attr, confidence in meta_patterns:
        element = soup.select_one(selector)
        if element and element.get(attr):
            return element.get(attr), confidence
    
    return None, 0.0

def extract_date_from_text(text: str) -> Tuple[Optional[str], float]:
    """Extract date from text using regex patterns."""
    if not text:
        return None, 0.0
    
    # Common date patterns with confidence scores
    date_patterns = [
        (r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:?\d{2}', 0.9),  # ISO format
        (r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{4}', 0.8),
        (r'\d{1,2} (January|February|March|April|May|June|July|August|September|October|November|December),? \d{4}', 0.8),
        (r'\d{1,2}/\d{1,2}/\d{4}', 0.7),
        (r'\d{4}/\d{2}/\d{2}', 0.7)
    ]
    
    for pattern, confidence in date_patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(), confidence
    
    return None, 0.0

def format_date(article: Article) -> Tuple[str, ArticleMetadata]:
    """Format article date with enhanced metadata tracking."""
    metadata: ArticleMetadata = {
        'date_extracted': False,
        'date_confidence': 0.0,
        'original_date': None,
        'source_confidence': 0.0,
        'extracted_from_url': False
    }
    
    date_str = article.get('published_at')
    metadata['original_date'] = date_str
    
    if not date_str:
        # Try to extract date from content
        if article.get('html_content'):
            date_str, confidence = extract_date_from_metadata(article['html_content'])
            if date_str:
                metadata['date_extracted'] = True
                metadata['date_confidence'] = confidence
                logger.info(f"Extracted date from metadata: {date_str}")
                return format_extracted_date(date_str), metadata
        
        # Try text-based extraction
        content = article.get('description', '') or article.get('title', '')
        date_str, confidence = extract_date_from_text(content)
        if date_str:
            metadata['date_extracted'] = True
            metadata['date_confidence'] = confidence
            logger.info(f"Extracted date from text: {date_str}")
            return format_extracted_date(date_str), metadata
        
        # Use current date as fallback
        logger.warning("No date found, using current date")
        return datetime.now(CENTRAL).strftime("%B %d, %Y"), metadata
    
    try:
        # Parse the provided date
        if isinstance(date_str, datetime):
            parsed_date = date_str
        else:
            parsed_date = parser.parse(date_str)
        
        # Ensure timezone awareness
        if parsed_date.tzinfo is None:
            parsed_date = parsed_date.replace(tzinfo=dateutil_tz.UTC)
        central_date = parsed_date.astimezone(CENTRAL)
        
        metadata['date_extracted'] = True
        metadata['date_confidence'] = 1.0
        return central_date.strftime("%B %d, %Y"), metadata
        
    except Exception as e:
        logger.warning(f"Date parsing error: {e}")
        return "Date Not Available", metadata

def format_extracted_date(date_str: str) -> str:
    """Format extracted date string consistently."""
    try:
        parsed_date = parser.parse(date_str)
        if parsed_date.tzinfo is None:
            parsed_date = parsed_date.replace(tzinfo=dateutil_tz.UTC)
        return parsed_date.astimezone(CENTRAL).strftime("%B %d, %Y")
    except Exception as e:
        logger.warning(f"Error formatting extracted date: {e}")
        return date_str

def filter_articles_by_date(articles: List[Article], 
                          start_date: Optional[datetime] = None, 
                          end_date: Optional[datetime] = None) -> List[Article]:
    """Filter articles based on publication dates."""
    if not start_date and not end_date:
        return articles

    # Ensure filter dates are timezone-aware
    if start_date and start_date.tzinfo is None:
        start_date = start_date.replace(tzinfo=CENTRAL)
    elif start_date and start_date.tzinfo != CENTRAL:
        start_date = start_date.astimezone(CENTRAL)

    if end_date and end_date.tzinfo is None:
        end_date = end_date.replace(tzinfo=CENTRAL)
    elif end_date and end_date.tzinfo != CENTRAL:
        end_date = end_date.astimezone(CENTRAL)

    filtered_articles = []
    for article in articles:
        # Format date and update article metadata
        formatted_date, metadata = format_date(article)
        article['metadata'] = metadata
        
        if metadata['date_confidence'] < 0.5:
            logger.warning(f"Low confidence date for article: {article.get('title')}")
            continue

        try:
            publish_date = parser.parse(formatted_date)
            if publish_date.tzinfo is None:
                publish_date = publish_date.replace(tzinfo=CENTRAL)
            
            # Apply date filters
            if start_date and publish_date < start_date:
                continue
            if end_date and publish_date > end_date:
                continue
            
            article['published_at'] = formatted_date
            filtered_articles.append(article)
            
        except Exception as e:
            logger.warning(f"Error filtering article by date: {e}")
            continue

    return filtered_articles