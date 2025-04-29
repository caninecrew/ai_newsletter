"""Filters for removing old, irrelevant, or duplicate articles."""
from typing import List, Dict
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from dateutil import parser, tz
from ai_newsletter.core.types import Article
from ai_newsletter.core.constants import NEWS_SOURCE_CATEGORIES
from ai_newsletter.logging_cfg.logger import setup_logger

logger = setup_logger()

# Define Central timezone
CENTRAL = tz.gettz("America/Chicago")

def filter_articles_by_date(articles: List[Article], start_date=None, end_date=None) -> List[Article]:
    """Filter articles based on datetime-aware start and end dates."""
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

    filtered = []
    for article in articles:
        publish_date = article.get('published_at', '')
        if not publish_date:
            continue

        # Parse and normalize date
        try:
            if isinstance(publish_date, str):
                publish_date = parser.parse(publish_date)
            if publish_date.tzinfo is None:
                publish_date = publish_date.replace(tzinfo=tz.UTC).astimezone(CENTRAL)
            elif publish_date.tzinfo != CENTRAL:
                publish_date = publish_date.astimezone(CENTRAL)
        except (ValueError, AttributeError):
            logger.warning(f"Could not parse date: {publish_date}")
            continue

        # Apply date filters
        if start_date and publish_date < start_date:
            continue
        if end_date and publish_date > end_date:
            continue
        filtered.append(article)

    return filtered

def is_duplicate(article1: Article, article2: Article, title_threshold: float = 0.8) -> bool:
    """Detect duplicate articles using title and description similarity."""
    def normalize_text(text: str) -> str:
        if not text:
            return ""
        return " ".join(text.lower().split())
    
    # Compare URLs first
    if article1.get('url') == article2.get('url'):
        return True
    
    # Compare normalized titles
    title1 = normalize_text(article1.get('title', ''))
    title2 = normalize_text(article2.get('title', ''))
    
    if not title1 or not title2:
        return False
        
    if title1 == title2:
        return True
        
    # Check title similarity
    title_similarity = SequenceMatcher(None, title1, title2).ratio()
    if title_similarity > title_threshold:
        # If titles are very similar, check descriptions
        desc1 = normalize_text(article1.get('description', ''))
        desc2 = normalize_text(article2.get('description', ''))
        if desc1 and desc2:
            desc_similarity = SequenceMatcher(None, desc1, desc2).ratio()
            return desc_similarity > 0.6
        return True
    
    return False

def deduplicate_articles(articles: List[Article]) -> List[Article]:
    """Remove duplicate articles, prioritizing preferred sources."""
    if not articles:
        return []

    # Source preference scoring (higher is better)
    source_preference = {
        "Associated Press": 10,
        "Reuters": 9,
        "NPR": 8,
        "PBS": 8,
        "BBC News": 8,
        "The Wall Street Journal": 7,
        "The New York Times": 7,
        "The Washington Post": 7,
        "Bloomberg": 7
    }
    
    # Sort by source preference and date
    sorted_articles = sorted(
        articles,
        key=lambda a: (
            source_preference.get(a.get('source', {}).get('name', ''), 5),
            a.get('published_at', '0')
        ),
        reverse=True
    )
    
    unique_articles = []
    seen_urls = set()
    duplicates_found = 0
    
    for article in sorted_articles:
        url = article.get('url', '')
        
        # Skip if URL already seen
        if url in seen_urls:
            duplicates_found += 1
            continue
            
        # Check for similar articles
        is_duplicate_article = False
        for existing in unique_articles:
            if is_duplicate(article, existing):
                duplicates_found += 1
                is_duplicate_article = True
                break
                
        if not is_duplicate_article:
            if url:
                seen_urls.add(url)
            unique_articles.append(article)
    
    logger.info(f"Removed {duplicates_found} duplicate articles")
    return unique_articles