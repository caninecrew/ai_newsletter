"""Article categorization functions."""
from typing import Dict

# Updated categories based on RSS feed structure
SECTION_CATEGORIES = {
    'US_NEWS': 'U.S. Headlines',
    'WORLD_NEWS': 'World News',
    'POLITICS': 'Politics',
    'TECHNOLOGY': 'Technology',
    'BUSINESS': 'Business & Economy',
    'LEFT_LEANING': 'Left-Leaning Sources',
    'CENTER': 'Center-Aligned Sources',
    'RIGHT_LEANING': 'Right-Leaning Sources',
    'PERSONALIZED': 'Personalized Stories',
    'LOCAL': 'Local News'
}

def categorize_article(article: Dict) -> str:
    """
    Categorize an article based on its source and GNews metadata.
    
    Args:
        article: Article dictionary with GNews metadata
        
    Returns:
        Category key from SECTION_CATEGORIES
    """
    title = article.get('title', '').lower()
    description = article.get('description', '').lower()
    source = article.get('source', {})
    source_name = source.get('name', '').lower() if isinstance(source, dict) else str(source).lower()
    combined_text = f"{title} {description}"
    
    # First, categorize based on source name
    if any(s in source_name for s in ['cnn', 'msnbc', 'nyt', 'new york times', 'washington post']):
        return 'LEFT_LEANING'
    elif any(s in source_name for s in ['fox', 'national review', 'newsmax', 'washington examiner']):
        return 'RIGHT_LEANING'
    elif any(s in source_name for s in ['npr', 'reuters', 'ap', 'associated press', 'pbs', 'abc', 'cbs']):
        return 'CENTER'
    elif any(s in source_name for s in ['bbc', 'al jazeera', 'france24', 'dw', 'guardian world']):
        return 'WORLD_NEWS'
    elif any(s in source_name for s in ['techcrunch', 'wired', 'ars technica', 'technology review']):
        return 'TECHNOLOGY'
    elif any(s in source_name for s in ['tennessean', 'nashville', 'tennessee']):
        return 'LOCAL'
    
    # Then, categorize based on content keywords
    if any(kw in combined_text for kw in ['international', 'global', 'worldwide', 'foreign', 'abroad']):
        return 'WORLD_NEWS'
    elif any(kw in combined_text for kw in ['president', 'congress', 'senate', 'governor', 'election', 'campaign', 'government']):
        return 'POLITICS'
    elif any(kw in combined_text for kw in ['tech', 'technology', 'software', 'app', 'digital', 'ai', 'artificial intelligence']):
        return 'TECHNOLOGY'
    elif any(kw in combined_text for kw in ['business', 'economy', 'market', 'stock', 'company', 'entrepreneur', 'ceo']):
        return 'BUSINESS'
    
    # Default to U.S. News if nothing else matches
    return 'US_NEWS'

def get_section_description(section_key: str) -> str:
    """Generate a description for each section."""
    descriptions = {
        'US_NEWS': 'Top domestic news stories from across the United States.',
        'WORLD_NEWS': 'Major international events and global developments.',
        'POLITICS': 'The latest political news, policy updates, and government affairs.',
        'TECHNOLOGY': 'Breaking tech news, digital trends, and innovation.',
        'BUSINESS': 'Business headlines, economic updates, and market news.',
        'LEFT_LEANING': 'News from sources that tend to have a center-left perspective.',
        'CENTER': 'News from sources that aim for balanced, centrist coverage.',
        'RIGHT_LEANING': 'News from sources that tend to have a center-right perspective.',
        'PERSONALIZED': 'Stories selected based on your personal interests and preferences.',
        'LOCAL': 'News from your local area that may directly affect your community.'
    }
    return descriptions.get(section_key, '')