"""Tag generation and personalization."""
from typing import List, Dict
from ai_newsletter.config.settings import USER_INTERESTS, PERSONALIZATION_TAGS
from ai_newsletter.logging_cfg.logger import setup_logger

logger = setup_logger()

def identify_tags(article: Dict) -> List[str]:
    """
    Identify relevant tags based on GNews article metadata.
    
    Args:
        article: Article dictionary with GNews metadata
        
    Returns:
        List of matching tags
    """
    title = article.get('title', '').lower()
    description = article.get('description', '').lower()
    combined_text = f"{title} {description}"
    
    matched_tags = []
    
    # Define interest-to-keyword mapping for better matching
    interest_keywords = {
        "Technology": ["tech", "technology", "software", "hardware", "digital", "computer", "programming"],
        "AI": ["ai", "artificial intelligence", "machine learning", "neural network", "deep learning", "chatgpt", "llm"],
        "Business": ["business", "company", "corporate", "industry", "market", "economy", "startup"],
        "Policy": ["policy", "regulation", "legislation", "law", "guideline", "rule"],
        "Education": ["education", "school", "teacher", "student", "classroom", "learning", "curriculum"],
        "Healthcare": ["health", "medical", "hospital", "patient", "doctor", "treatment", "medicine"],
        "Environment": ["climate", "environment", "sustainability", "renewable", "green energy", "conservation"],
        "Science": ["science", "research", "study", "discovery", "innovation", "breakthrough"]
    }

    # Check each interest against the text
    for interest, keywords in interest_keywords.items():
        for keyword in keywords:
            if keyword in combined_text:
                matched_tags.append(interest)
                break
    
    # Add category-based tags if no specific tags matched
    if not matched_tags:
        source_name = article.get('source', {}).get('name', '').lower() if isinstance(article.get('source'), dict) else ''
        if "fox news" in source_name:
            matched_tags.append("U.S. News")
        elif any(k in combined_text for k in ["international", "world", "global", "foreign"]):
            matched_tags.append("International")
        elif any(k in combined_text for k in ["technology", "tech", "digital", "software"]):
            matched_tags.append("Technology")
        elif any(k in combined_text for k in ["business", "economy", "market", "stock"]):
            matched_tags.append("Business")
        elif any(k in combined_text for k in ["politics", "president", "congress", "election"]):
            matched_tags.append("Politics")
        else:
            matched_tags.append("General News")
            
    return list(set(matched_tags))  # Remove duplicates

def get_personalization_tags_html(article: Dict) -> str:
    """
    Generate HTML for personalization tags with emojis.
    Ensures tags are deduplicated and consistently applied.
    
    Args:
        article: The article dictionary
        
    Returns:
        HTML formatted tags with emojis
    """
    raw_tags = identify_tags(article)
    processed_tags = set()  # Use a set to avoid duplicates
    html_tags = []
    
    # Create a mapping of tag categories to prevent duplicates
    tag_categories = {
        "legal": "🔒 Legal",
        "education": "🏫 Education",
        "health": "🏥 Healthcare",
        "economy": "📈 Economy",
        "global": "🧭 Global Affairs", 
        "tech": "⚡️ Technology",
        "politics": "🏛️ Politics",
        "environment": "🌳 Environment",
        "science": "🔬 Science"
    }
    
    # Check which categories this article belongs to
    category_matches = set()
    for tag in raw_tags:
        tag_lower = tag.lower()
        
        # Check for category matches
        if "legal" in tag_lower or "law" in tag_lower or "regulation" in tag_lower:
            category_matches.add("legal")
        elif "education" in tag_lower or "school" in tag_lower or "learning" in tag_lower:
            category_matches.add("education")
        elif "health" in tag_lower or "medical" in tag_lower or "hospital" in tag_lower:
            category_matches.add("health")
        elif "economy" in tag_lower or "market" in tag_lower or "financial" in tag_lower or "business" in tag_lower:
            category_matches.add("economy")
        elif "global" in tag_lower or "international" in tag_lower or "world" in tag_lower:
            category_matches.add("global")
        elif "tech" in tag_lower or "ai" in tag_lower or "software" in tag_lower or "digital" in tag_lower:
            category_matches.add("tech")
        elif "government" in tag_lower or "policy" in tag_lower or "politics" in tag_lower:
            category_matches.add("politics")
        elif "environment" in tag_lower or "climate" in tag_lower or "sustainability" in tag_lower:
            category_matches.add("environment")
        elif "science" in tag_lower or "research" in tag_lower:
            category_matches.add("science")
        else:
            # For unmatched tags, add them directly if they're not already included
            if tag not in processed_tags:
                processed_tags.add(tag)
                if tag in PERSONALIZATION_TAGS:
                    emoji = PERSONALIZATION_TAGS[tag]
                    html_tags.append(f'<span class="tag">{emoji} {tag}</span>')
                else:
                    # Use a generic tag without emoji
                    html_tags.append(f'<span class="tag">{tag}</span>')
    
    # Add all matched category tags
    for category in category_matches:
        html_tags.append(f'<span class="tag">{tag_categories[category]}</span>')
    
    # If no tags were found, add a generic tag based on the article category
    if not html_tags:
        from ai_newsletter.formatting.categorization import categorize_article
        section = categorize_article(article)
        if section == 'WORLD_NEWS':
            html_tags.append('<span class="tag">🧭 Global Affairs</span>')
        elif section == 'US_NEWS':
            html_tags.append('<span class="tag">🏛️ U.S. News</span>')
        elif section == 'TECHNOLOGY':
            html_tags.append('<span class="tag">⚡️ Technology</span>')
        elif section == 'BUSINESS':
            html_tags.append('<span class="tag">📈 Economy</span>')
        elif section == 'POLITICS':
            html_tags.append('<span class="tag">🏛️ Politics</span>')
        else:
            html_tags.append('<span class="tag">📰 News</span>')
    
    return "".join(html_tags)