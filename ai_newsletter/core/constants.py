"""Constants and configuration values."""
from enum import Enum

# Section categories with friendly names
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

# Emoji mappings for article tags
TAG_EMOJIS = {
    "Legal": "🔒",
    "Education": "🏫",
    "Healthcare": "🏥", 
    "Economy": "📈",
    "Global Affairs": "🧭",
    "Technology": "⚡️",
    "Politics": "🏛️",
    "Science": "🔬",
    "Environment": "🌱",
    "Sports": "⚽",
    "Entertainment": "🎬",
    "Business": "💼",
    "Finance": "💰",
    "Social Issues": "👥"
}

# Source categorization
NEWS_SOURCE_CATEGORIES = {
    'LEFT_LEANING': ['cnn', 'msnbc', 'nyt', 'new york times', 'washington post'],
    'RIGHT_LEANING': ['fox', 'national review', 'newsmax', 'washington examiner'],
    'CENTER': ['npr', 'reuters', 'ap', 'associated press', 'pbs', 'abc', 'cbs'],
    'WORLD_NEWS': ['bbc', 'al jazeera', 'france24', 'dw', 'guardian world'],
    'TECHNOLOGY': ['techcrunch', 'wired', 'ars technica', 'technology review'],
    'LOCAL': ['tennessean', 'nashville', 'tennessee']
}

# Article age categories
class AgeCategory(str, Enum):
    BREAKING = 'Breaking'
    TODAY = 'Today'
    YESTERDAY = 'Yesterday'
    THIS_WEEK = 'This Week'
    OLDER = 'Older'

# Interest-to-keyword mapping for article tagging
INTEREST_KEYWORDS = {
    "Technology": ["tech", "technology", "software", "hardware", "digital", "computer", "programming"],
    "AI": ["ai", "artificial intelligence", "machine learning", "neural network", "deep learning", "chatgpt", "llm"],
    "Business": ["business", "company", "corporate", "industry", "market", "economy", "startup"],
    "Policy": ["policy", "regulation", "legislation", "law", "guideline", "rule"],
    "Education": ["education", "school", "teacher", "student", "classroom", "learning", "curriculum"],
    "Healthcare": ["health", "medical", "hospital", "patient", "doctor", "treatment", "medicine"],
    "Environment": ["climate", "environment", "sustainability", "renewable", "green energy", "conservation"],
    "Science": ["science", "research", "study", "discovery", "innovation", "breakthrough"]
}