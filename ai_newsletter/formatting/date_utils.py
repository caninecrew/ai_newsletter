"""Date handling utilities."""
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from dateutil import parser, tz as dateutil_tz
import re
from bs4 import BeautifulSoup
import requests
from ai_newsletter.logging_cfg.logger import setup_logger

logger = setup_logger()

# Define Central timezone
CENTRAL = dateutil_tz.gettz("America/Chicago")

def extract_date_from_metadata(html_content: str) -> Tuple[Optional[str], float]:
    """Extract publication date from HTML metadata tags."""
    if not html_content:
        return None, 0.0
    
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Common metadata patterns
    meta_patterns = [
        ('meta[property="article:published_time"]', 'content', 0.9),
        ('meta[property="og:article:published_time"]', 'content', 0.9),
        ('meta[name="publishedDate"]', 'content', 0.9),
        ('meta[name="date"]', 'content', 0.8),
        ('meta[name="article:published"]', 'content', 0.8),
        ('time[datetime]', 'datetime', 0.8),
        ('time[class*="publish"]', 'datetime', 0.7),
        ('.article-date', 'content', 0.6),
        ('.published-date', 'content', 0.6)
    ]
    
    for selector, attr, confidence in meta_patterns:
        element = soup.select_one(selector)
        if element:
            date_str = element.get(attr)
            if date_str:
                return date_str, confidence
                
    return None, 0.0

def extract_date_from_text(content: str) -> Tuple[Optional[str], float]:
    """Extract date from article text using regex patterns."""
    if not content:
        return None, 0.0
        
    # Common date patterns
    date_patterns = [
        (r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:?\d{2}', 0.9),  # ISO format
        (r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{4}', 0.8),
        (r'\d{1,2} (January|February|March|April|May|June|July|August|September|October|November|December),? \d{4}', 0.8),
        (r'\d{1,2}/\d{1,2}/\d{4}', 0.7),
        (r'\d{4}/\d{2}/\d{2}', 0.7)
    ]
    
    for pattern, confidence in date_patterns:
        match = re.search(pattern, content)
        if match:
            return match.group(), confidence
            
    return None, 0.0

def format_date(article: Dict) -> Tuple[str, bool, float]:
    """Format a date string into a human-readable format with confidence score."""
    date_str = article.get('published_at')
    original_date = date_str
    
    if not date_str:
        # Try to extract date from article content
        if article.get('html_content'):
            date_str, confidence = extract_date_from_metadata(article['html_content'])
            if date_str:
                logger.info(f"Extracted date from metadata: {date_str}")
                return format_extracted_date(date_str), True, confidence
        
        # Try text-based extraction
        content = article.get('description', '') or article.get('title', '')
        date_str, confidence = extract_date_from_text(content)
        if date_str:
            logger.info(f"Extracted date from text: {date_str}")
            return format_extracted_date(date_str), True, confidence
        
        # Use current date as fallback
        logger.warning("No date found, using current date")
        return datetime.now(CENTRAL).strftime("%B %d, %Y"), False, 0.1
    
    try:
        # Parse the original date string
        if isinstance(date_str, datetime):
            parsed_date = date_str
        else:
            parsed_date = parser.parse(date_str)
        
        # Ensure timezone awareness
        if parsed_date.tzinfo is None:
            parsed_date = parsed_date.replace(tzinfo=dateutil_tz.UTC)
        
        # Convert to Central time
        central_date = parsed_date.astimezone(CENTRAL)
        return central_date.strftime("%B %d, %Y"), True, 1.0
        
    except Exception as e:
        logger.warning(f"Date parsing error: {e}")
        return "Date Not Available", False, 0.0

def format_extracted_date(date_str: str) -> str:
    """Format an extracted date string consistently."""
    try:
        parsed_date = parser.parse(date_str)
        if parsed_date.tzinfo is None:
            parsed_date = parsed_date.replace(tzinfo=dateutil_tz.UTC)
        return parsed_date.astimezone(CENTRAL).strftime("%B %d, %Y")
    except:
        return date_str

def filter_articles_by_date(articles: List[Dict], 
                          start_date: Optional[datetime] = None, 
                          end_date: Optional[datetime] = None) -> List[Dict]:
    """Filter articles based on aware start and end dates in CENTRAL timezone."""
    if not start_date and not end_date:
        return articles

    # Ensure filter dates are aware and in CENTRAL
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
        # Format and validate the date
        formatted_date, extracted, confidence = format_date(article)
        
        # Update article with date extraction metadata
        article['date_extracted'] = extracted
        article['date_confidence'] = confidence
        article['original_date_string'] = article.get('published_at')
        article['published_at'] = formatted_date
        
        # Skip articles without valid dates for filtering
        if not extracted or confidence < 0.5:
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
            filtered_articles.append(article)
            
        except Exception as e:
            logger.warning(f"Error filtering article by date: {e}")
            continue

    return filtered_articles