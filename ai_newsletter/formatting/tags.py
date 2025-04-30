"""Tag generation and personalization."""
from typing import List, Dict, Set
from ai_newsletter.config.settings import USER_INTERESTS, PERSONALIZATION_TAGS
from ai_newsletter.core.constants import TAG_EMOJIS
from ai_newsletter.logging_cfg.logger import setup_logger

logger = setup_logger()

def identify_tags(article: Dict) -> List[str]:
    """Identify relevant tags based on article content."""
    title = article.get('title', '').lower()
    description = article.get('description', '').lower()
    combined_text = f"{title} {description}"
    
    # Define interest-to-keyword mapping for better matching
    interest_keywords = {
        "Legal": ["legal", "law", "regulation", "compliance", "legislation"],
        "Education": ["education", "school", "learning", "student", "teacher", "university"],
        "Healthcare": ["health", "medical", "hospital", "patient", "doctor", "treatment"],
        "Economy": ["economy", "market", "financial", "business", "trade", "stock"],
        "Global": ["international", "global", "world", "foreign", "diplomatic"],
        "Technology": ["tech", "ai", "software", "digital", "computer", "startup"],
        "Politics": ["politics", "government", "policy", "election", "congress"],
        "Environment": ["climate", "environment", "sustainability", "renewable", "green"],
        "Science": ["science", "research", "study", "discovery", "innovation"]
    }
    
    matched_tags = set()
    
    # Match tags based on keywords
    for interest, keywords in interest_keywords.items():
        if any(k in combined_text for k in keywords):
            matched_tags.add(interest)
    
    # Add any explicit tags from the article
    if article.get('tags'):
        matched_tags.update(t.title() for t in article['tags'])
    
    return list(matched_tags)

def get_tag_html(tag: str, emoji: str = None) -> str:
    """Generate HTML for a single tag."""
    if emoji is None:
        emoji = TAG_EMOJIS.get(tag, '📌')
    return f'<span class="tag">{emoji} {tag}</span>'

def get_personalization_tags_html(article: Dict) -> str:
    """Generate HTML for all article tags with emojis."""
    raw_tags = identify_tags(article)
    processed_tags: Set[str] = set()
    html_tags = []
    
    # Add identified tags first
    for tag in raw_tags:
        if tag not in processed_tags:
            processed_tags.add(tag)
            # Use predefined emoji if available, otherwise use category mapping
            emoji = PERSONALIZATION_TAGS.get(tag)
            html_tags.append(get_tag_html(tag, emoji))
    
    # If no tags were found, add a tag based on article category
    if not html_tags:
        from ai_newsletter.formatting.categorization import categorize_article
        section = categorize_article(article)
        category_emojis = {
            'WORLD_NEWS': '🌍',
            'US_NEWS': '🗽',
            'POLITICS': '🏛️',
            'TECHNOLOGY': '⚡',
            'BUSINESS': '💼',
            'PERSONALIZED': '📌'
        }
        emoji = category_emojis.get(section, '📰')
        tag = section.replace('_', ' ').title()
        html_tags.append(get_tag_html(tag, emoji))
    
    return "".join(html_tags)