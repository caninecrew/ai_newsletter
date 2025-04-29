# Configuration file for AI Newsletter
# This file contains configurable settings for the newsletter system

import os
from typing import Dict, Any, List, Optional
from datetime import timedelta

# System-wide settings
SYSTEM_SETTINGS = {
    'max_concurrent_requests': 5,
    'request_timeout': 30,
    'max_retries': 3,
    'retry_delay': 1,
}

# GNews API Configuration
GNEWS_CONFIG = {
    'enabled': True,  # Set to False to fall back to RSS feeds
    'language': 'en',
    'country': 'us',  # Optional, can be None
    'max_articles_per_query': 10,
    'categories': {
        'general': True,
        'world': True,
        'nation': True,
        'business': True,
        'technology': True,
        'science': False,
        'sports': False,
        'health': True,
        'entertainment': False
    },
    'excluded_domains': [],  # List of domains to exclude from results
}

# GNews API Settings
GNEWS_API_KEY = os.getenv('GNEWS_API_KEY')
GNEWS_DEFAULT_LANGUAGE = "en"
GNEWS_DEFAULT_MAX_RESULTS = 10
GNEWS_EXCLUDED_DOMAINS: List[str] = []

# Updated News Categories and Search Queries
NEWS_CATEGORIES = {
    "major_domestic": {
        "enabled": True,
        "queries": [
            "US national news",
            "US government politics",
            "US education k-12 higher education"
        ]
    },
    "critical_international": {
        "enabled": True,
        "queries": [
            "Kenya East Africa news",
            "world war crisis election",
            "religious freedom global missions"
        ]
    },
    "business_technology": {
        "enabled": True,
        "queries": [
            "nonprofit education business",
            "AI technology cybersecurity",
            "government civic technology"
        ]
    },
    "faith_religion": {
        "enabled": True,
        "queries": [
            "Protestant Nazarene church",
            "religious liberty",
            "Christian missions ministry"
        ]
    },
    "scouting_youth": {
        "enabled": True,
        "queries": [
            "Boy Scouts America Scouting",
            "NYLT NAYLE youth leadership",
            "outdoor youth programs camps"
        ]
    },
    "education_news": {
        "enabled": True,
        "queries": [
            "Tennessee education policy k-12",
            "teacher shortage certification",
            "Tennessee Tech university education"
        ]
    },
    "public_records": {
        "enabled": True,
        "queries": [
            "FOIA open government transparency",
            "public agency lawsuit investigation"
        ]
    },
    "local_regional": {
        "enabled": True,
        "queries": [
            "Tennessee Middle Wilson Putnam County news",
            "Cookeville Mt Juliet Wilson County"
        ]
    },
    "outdoor_adventure": {
        "enabled": True,
        "queries": [
            "hiking backpacking trails",
            "national parks updates",
            "outdoor safety equipment"
        ]
    },
    "ethics_leadership": {
        "enabled": True,
        "queries": [
            "leadership development trends",
            "business government ethics",
            "nonprofit volunteer leadership"
        ]
    }
}

# Rate Limiting
GNEWS_DAILY_LIMIT = 100  # Free tier limit
GNEWS_REQUEST_DELAY = 1  # seconds between requests

# Feed settings (retained for compatibility/fallback)
FEED_SETTINGS = {
    'interests': {
        'artificial_intelligence': True,
        'machine_learning': True,
        'cloud_computing': True,
        'cybersecurity': True,
        'software_development': True,
    },
    'update_interval': 3600,  # How often to check for new articles (in seconds)
    'max_articles_per_feed': 10,
    'min_article_length': 100,  # Minimum content length to consider
}

# Email settings
EMAIL_SETTINGS = {
    'smtp_server': os.getenv('SMTP_SERVER', 'smtp.gmail.com'),
    'smtp_port': int(os.getenv('SMTP_PORT', '587')),
    'sender_email': os.getenv('SENDER_EMAIL'),
    'smtp_username': os.getenv('SMTP_USERNAME'),
    'smtp_password': os.getenv('SMTP_PASSWORD'),
}

# Email Settings
EMAIL_SENDER = os.getenv('EMAIL_SENDER')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')
EMAIL_RECIPIENTS = os.getenv('EMAIL_RECIPIENTS', '').split(',')
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))

# Logging
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# --- International News Filter Keywords ---
# Used to filter international news by relevance to user interests
INCLUDE_INTERNATIONAL_KEYWORDS = [
    "U.S.", "America", "United States", "USA", "Kenya", "education", "youth", 
    "leadership", "economy", "economic", "conflict", "war", "crisis", "disaster",
    "Nashville", "Tennessee", "Middle Tennessee", "scouting", "scouts", "climate",
    "global warming", "pandemic", "humanitarian", "AI", "artificial intelligence"
]

# --- User Interests for News Search ---
USER_INTERESTS = {
    'artificial_intelligence': True,
    'machine_learning': True,
    'cloud_computing': True,
    'cybersecurity': True,
    'software_development': True
}

# --- Personalization Tags with Emojis ---
# Used for visual tagging of articles in the newsletter
PERSONALIZATION_TAGS = {
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

# --- Email Formatting Settings ---
EMAIL_SETTINGS = {
    "max_articles_per_category": 4,         # Maximum articles for each category 
    "max_articles_per_source": 2,           # Maximum articles from any single source to prevent domination
    "max_articles_total": 15,               # Maximum total articles to include in newsletter
    "max_left_leaning": 4,                  # Maximum articles from left-leaning sources
    "max_center": 4,                        # Maximum articles from center sources
    "max_right_leaning": 4,                 # Maximum articles from right-leaning sources
    "max_international": 3,                 # Maximum international articles (must match keywords)
    "show_why_this_matters": True,
    "show_key_takeaways": True,
    "include_table_of_contents": True,
    "include_source_statistics": True,      # Include statistics about source distribution in email
    "recipients": [],                       # Will be populated from environment variables
    "smtp": {
        "host": "",                        # Will be populated from SMTP_SERVER env var
        "port": 587,                       # Will be populated from SMTP_PORT env var
        "username": "",                    # Will be populated from SMTP_EMAIL env var
        "password": "",                    # Will be populated from SMTP_PASS env var
        "sender": ""                       # Will be populated from SMTP_EMAIL env var
    }
}

# --- System Settings ---
# General system configuration options
SYSTEM_SETTINGS = {
    "log_level": "INFO",                   # Options: DEBUG, INFO, WARNING, ERROR, CRITICAL
    "max_articles_to_process": 25,         # Maximum number of articles to process in one run
    "max_retries": 2,                      # Maximum number of retries for failed API requests
    "use_central_timezone": True,          # Whether to convert all dates to Central Time
    "default_timezone": "America/Chicago", # Default timezone for date standardization
    "cache_articles": True,                # Whether to cache articles to prevent duplicate processing
    "cache_expiry_hours": 24              # How long to keep articles in cache
}

def get_settings() -> Dict[str, Any]:
    """Returns all settings as a dictionary."""
    return {
        'system': SYSTEM_SETTINGS,
        'gnews': GNEWS_CONFIG,
        'feeds': FEED_SETTINGS,
        'email': EMAIL_SETTINGS,
    }