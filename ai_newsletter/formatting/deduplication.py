"""Article deduplication utilities."""
from typing import List, Dict
import re
from difflib import SequenceMatcher
from ai_newsletter.logging_cfg.logger import setup_logger

logger = setup_logger()

def is_duplicate(article1: Dict, article2: Dict, title_threshold: float = 0.8) -> bool:
    """
    Detect duplicate articles using GNews metadata.
    
    Args:
        article1: First article dictionary to compare
        article2: Second article dictionary to compare
        title_threshold: Similarity threshold for titles (0.0-1.0)
        
    Returns:
        True if articles are likely duplicates, False otherwise
    """
    def normalize_text(text):
        if not text:
            return ""
        return re.sub(r'\s+', ' ', text.lower().strip())
    
    title1 = normalize_text(article1.get('title', ''))
    title2 = normalize_text(article2.get('title', ''))
    desc1 = normalize_text(article1.get('description', ''))
    desc2 = normalize_text(article2.get('description', ''))
    
    # If either title is empty, we can't reliably compare
    if not title1 or not title2:
        return False
    
    # Short-circuit: exact title match is definitely duplicate
    if title1 == title2:
        return True
    
    # Calculate title similarity
    title_similarity = SequenceMatcher(None, title1, title2).ratio()
    
    # If titles are very similar, check description if available
    if title_similarity > title_threshold:
        if desc1 and desc2:
            desc_similarity = SequenceMatcher(None, desc1, desc2).ratio()
            return desc_similarity > 0.6
        return True
    
    return False

def limit_articles_by_source(articles: List[Dict], max_per_source: int = 3) -> List[Dict]:
    """
    Limit the number of articles from each source to prevent one source dominating.
    
    Args:
        articles: List of article dictionaries
        max_per_source: Maximum articles allowed per source
        
    Returns:
        Limited list of articles
    """
    if not articles:
        return []
    
    # Group articles by source
    source_groups = {}
    for article in articles:
        source = article.get('source', {})
        source_name = source.get('name', source) if isinstance(source, dict) else str(source)
        if not source_name:
            source_name = 'Unknown'
            
        if source_name not in source_groups:
            source_groups[source_name] = []
        source_groups[source_name].append(article)
    
    # Sort each group by date (newest first)
    for source_name, group in source_groups.items():
        source_groups[source_name] = sorted(
            group, 
            key=lambda a: a.get('published_at') or a.get('published', '0'), 
            reverse=True
        )
    
    # Take only the top N from each source
    limited_articles = []
    for source_name, group in source_groups.items():
        limited_articles.extend(group[:max_per_source])
    
    # Re-sort all articles by date
    limited_articles = sorted(
        limited_articles, 
        key=lambda a: a.get('published_at') or a.get('published', '0'), 
        reverse=True
    )
    
    logger.info(f"Limited articles from {len(source_groups)} sources: kept {len(limited_articles)} out of {len(articles)}")
    
    return limited_articles

def deduplicate_articles(articles: List[Dict]) -> List[Dict]:
    """
    Remove duplicate articles from the list with improved algorithm.
    Prioritizes keeping articles from preferred sources when duplicates are found.
    
    Args:
        articles: List of article dictionaries
        
    Returns:
        Deduplicated list of articles
    """
    if not articles:
        return []
    
    # Define source preferences (higher is better)
    source_preference = {
        "Associated Press": 10,
        "Reuters": 9,
        "NPR": 8,
        "PBS": 8,
        "BBC News": 8,
        "The Wall Street Journal": 7,
        "The New York Times": 7,
        "The Washington Post": 7,
        "Bloomberg": 7,
        "CNS News": 6,
        "National Review": 6
    }
    
    # Default preference for unlisted sources
    default_preference = 5
    
    # Sort articles by published date (newest first) and source preference
    sorted_articles = sorted(
        articles, 
        key=lambda a: (
            source_preference.get(a.get('source', ''), default_preference),
            a.get('published', '0')  # Default to '0' if no date
        ),
        reverse=True
    )
    
    unique_articles = []
    duplicate_count = 0
    duplicate_groups = []
    seen_urls = set()
    
    # Track duplicate groups for reporting
    current_duplicates = []
    
    for article in sorted_articles:
        is_dup = False
        url = article.get('url', article.get('link', ''))
        
        # Check if this URL has been seen before
        if url and url in seen_urls:
            is_dup = True
            duplicate_count += 1
            current_duplicates.append(article.get('title', 'No title'))
            logger.debug(f"Duplicate URL found: {url}")
            continue
        
        # Check for content similarity with existing articles
        for existing in unique_articles:
            if is_duplicate(article, existing):
                is_dup = True
                duplicate_count += 1
                current_duplicates.append(article.get('title', 'No title'))
                break
        
        if not is_dup:
            # If we were tracking duplicates, finish the group
            if current_duplicates:
                duplicate_groups.append(current_duplicates)
                current_duplicates = []
            
            # Add to seen URLs and unique articles
            if url:
                seen_urls.add(url)
            unique_articles.append(article)
    
    # Add the last group if it exists
    if current_duplicates:
        duplicate_groups.append(current_duplicates)
    
    # Log deduplication results
    logger.info(f"Deduplication removed {duplicate_count} duplicate articles")
    logger.info(f"Original count: {len(articles)}, Deduplicated count: {len(unique_articles)}")
    
    # Log duplicate groups (limited to first 5 for brevity)
    if duplicate_groups:
        logger.debug(f"Found {len(duplicate_groups)} duplicate groups:")
        for i, group in enumerate(duplicate_groups[:5], 1):
            logger.debug(f"Group {i}: {', '.join(group)}")
        if len(duplicate_groups) > 5:
            logger.debug(f"... and {len(duplicate_groups) - 5} more groups")
    
    return unique_articles