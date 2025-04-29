# Configuration file for AI Newsletter
# This file contains configurable settings for the newsletter system

import os
from typing import Dict, Any
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

# --- News Source Configuration ---
# Using Google News RSS feeds as primary source for reliable aggregated content

# --- Feed Configuration Settings ---
# Control which feeds are enabled/disabled
FEED_SETTINGS = {
    "headlines": {
        "top_stories": True,              # Type 1: Top headlines
        "us_news": True,                  # Type 2: Headlines by topic
        "politics": True,
        "technology": True,
        "business": True,
        "world": True,
        "science": False,                 # Disabled by default
        "health": False                   # Disabled by default
    },
    "location": {
        "tennessee": True,               # Type 3: Location headlines
        "nashville": True,
        "knoxville": False,              # Disabled by default
        "memphis": False                 # Disabled by default
    },
    "interests": {
        "scouting": True,                # Type 4: News by search criteria
        "education": True,
        "youth_leadership": True,
        "outdoor": True,
        "kenya": True,
        "nazarene": True
    },
    "aggregators": {
        "yahoo": False,                  # Additional aggregators (disabled by default)
        "msn": False
    }
}

# --- PRIMARY NEWS FEEDS ---
# Primary RSS feed sources using all four types of Google News RSS feeds
PRIMARY_NEWS_FEEDS = {}

# Type 1: Top headlines
if FEED_SETTINGS["headlines"]["top_stories"]:
    PRIMARY_NEWS_FEEDS["Google News Top Stories"] = "https://news.google.com/news/rss"  # More reliable URL format

# Type 2: Headlines by topic
if FEED_SETTINGS["headlines"]["us_news"]:
    PRIMARY_NEWS_FEEDS["Google News US"] = "https://news.google.com/news/rss/headlines/section/topic/NATION"
if FEED_SETTINGS["headlines"]["politics"]:
    PRIMARY_NEWS_FEEDS["Google News Politics"] = "https://news.google.com/news/rss/headlines/section/topic/POLITICS"
if FEED_SETTINGS["headlines"]["technology"]:
    PRIMARY_NEWS_FEEDS["Google News Technology"] = "https://news.google.com/news/rss/headlines/section/topic/TECHNOLOGY"
if FEED_SETTINGS["headlines"]["business"]:
    PRIMARY_NEWS_FEEDS["Google News Business"] = "https://news.google.com/news/rss/headlines/section/topic/BUSINESS"
if FEED_SETTINGS["headlines"]["world"]:
    PRIMARY_NEWS_FEEDS["Google News World"] = "https://news.google.com/news/rss/headlines/section/topic/WORLD"
if FEED_SETTINGS["headlines"]["science"]:
    PRIMARY_NEWS_FEEDS["Google News Science"] = "https://news.google.com/news/rss/headlines/section/topic/SCIENCE"
if FEED_SETTINGS["headlines"]["health"]:
    PRIMARY_NEWS_FEEDS["Google News Health"] = "https://news.google.com/news/rss/headlines/section/topic/HEALTH"

# Type 3: Location headlines
if FEED_SETTINGS["location"]["tennessee"]:
    PRIMARY_NEWS_FEEDS["Google News Tennessee"] = "https://news.google.com/news/rss/search?q=location:Tennessee&hl=en-US&gl=US"
if FEED_SETTINGS["location"]["nashville"]:
    PRIMARY_NEWS_FEEDS["Google News Nashville"] = "https://news.google.com/news/rss/search?q=location:Nashville&hl=en-US&gl=US"
if FEED_SETTINGS["location"]["knoxville"]:
    PRIMARY_NEWS_FEEDS["Google News Knoxville"] = "https://news.google.com/news/rss/search?q=location:Knoxville&hl=en-US&gl=US"
if FEED_SETTINGS["location"]["memphis"]:
    PRIMARY_NEWS_FEEDS["Google News Memphis"] = "https://news.google.com/news/rss/search?q=location:Memphis&hl=en-US&gl=US"

# Type 4: News by search criteria - personalized to user interests
if FEED_SETTINGS["interests"]["scouting"]:
    PRIMARY_NEWS_FEEDS["Google News Scouting"] = "https://news.google.com/news/rss/search?q=%22Boy+Scouts+of+America%22+OR+%22Scout+Troop%22+OR+%22Eagle+Scout%22+OR+%22Cub+Scout%22+OR+%22Scouting+BSA%22+OR+%22Scouts+BSA%22+-NFL+-sports+-basketball+-football+-baseball+-hockey+-draft"
if FEED_SETTINGS["interests"]["education"]:
    PRIMARY_NEWS_FEEDS["Google News Education"] = "https://news.google.com/news/rss/search?q=(education+OR+learning+OR+teaching)+Tennessee"
if FEED_SETTINGS["interests"]["youth_leadership"]:
    PRIMARY_NEWS_FEEDS["Google News Youth Leadership"] = "https://news.google.com/news/rss/search?q=%22youth+leadership%22+OR+%22student+leadership%22"
if FEED_SETTINGS["interests"]["outdoor"]:
    PRIMARY_NEWS_FEEDS["Google News Outdoor/Camping"] = "https://news.google.com/news/rss/search?q=camping+OR+hiking+OR+backpacking+OR+%22outdoor+adventure%22"
if FEED_SETTINGS["interests"]["kenya"]:
    PRIMARY_NEWS_FEEDS["Google News Kenya"] = "https://news.google.com/news/rss/search?q=kenya+missions+OR+%22humanitarian+aid%22"
if FEED_SETTINGS["interests"]["nazarene"]:
    PRIMARY_NEWS_FEEDS["Google News Nazarene"] = "https://news.google.com/news/rss/search?q=Nazarene+OR+%22Church+of+the+Nazarene%22+OR+%22Nazarene+Compassionate+Ministries%22"

# Additional aggregators
if FEED_SETTINGS["aggregators"]["yahoo"]:
    PRIMARY_NEWS_FEEDS["Yahoo News"] = "https://www.yahoo.com/news/rss"  # Updated Yahoo News URL
if FEED_SETTINGS["aggregators"]["msn"]:
    PRIMARY_NEWS_FEEDS["MSN News US"] = "https://rss.msn.com/en-us"  # Updated MSN News URL

# --- SECONDARY NEWS FEEDS ---
# Secondary feeds for local content and specialized interests
SECONDARY_FEEDS = {
    "Personalized": {
        "Scouting": "https://blog.scoutingmagazine.org/feed/",
        "Scout Life Magazine": "https://scoutlife.org/feed/",
        "Scouting Newsroom": "https://www.scoutingnewsroom.org/feed/",
    }
}

# --- SUPPLEMENTAL NEWS FEEDS ---
# Additional sources categorized by political leaning to ensure balanced perspectives
# These will be used when PRIMARY_NEWS_FEEDS don't provide enough coverage
SUPPLEMENTAL_FEEDS = {
    "Left": {
        "CNN": "http://rss.cnn.com/rss/cnn_topstories.rss",
        "CNN Americas": "http://rss.cnn.com/rss/edition_americas.rss",
        "NYT": "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml",
        "NYT US": "https://rss.nytimes.com/services/xml/rss/nyt/US.xml",
        "NYT Politics": "https://rss.nytimes.com/services/xml/rss/nyt/Politics.xml",
        "MSNBC": "https://www.msnbc.com/feeds/latest",
        "Washington Post National": "http://feeds.washingtonpost.com/rss/national",
        "Washington Post World": "https://feeds.washingtonpost.com/rss/world",
        "Huffington Post": "https://www.huffpost.com/section/front-page/feed",
        "Vox": "https://www.vox.com/rss/index.xml"
    },
    "Center": {
        "NPR News": "https://feeds.npr.org/1001/rss.xml",
        "NPR Politics": "https://feeds.npr.org/1014/rss.xml",
        "AP Top News": "https://apnews.com/rss",
        "AP US News": "https://apnews.com/hub/us-news/rss",
        "Reuters US": "http://feeds.reuters.com/reuters/domesticNews",
        "Reuters Top News": "http://feeds.reuters.com/reuters/topNews",
        "PBS Headlines": "https://www.pbs.org/newshour/feeds/rss/headlines",
        "PBS World": "https://www.pbs.org/newshour/feeds/rss/podcasts/world",
        "PBS Politics": "https://www.pbs.org/newshour/feeds/rss/politics",
        "ABC US": "https://abcnews.go.com/abcnews/usheadlines",
        "CBS Top Stories": "https://www.cbsnews.com/latest/rss/main",
        "CBS US News": "https://www.cbsnews.com/latest/rss/us",
        "USA Today Nation": "http://rssfeeds.usatoday.com/UsatodaycomNation-TopStories",
        "USA Today Top Stories": "http://rssfeeds.usatoday.com/usatoday-NewsTopStories",
        "Bloomberg": "https://www.bloomberg.com/feed"
    },
    "Right": {
        "Wall Street Journal": "https://feeds.a.dj.com/rss/RSSWorldNews.xml",
        "National Review": "https://www.nationalreview.com/feed/",
        "The Hill": "https://thehill.com/rss/syndicator/19110",
        "Washington Examiner": "https://www.washingtonexaminer.com/tag/news.xml",
        "Newsmax": "https://www.newsmax.com/rss/Headline/0",
        "The Dispatch": "https://thedispatch.com/feed/",
        "The Bulwark": "https://thebulwark.com/feed/",
        "The Washington Times": "https://www.washingtontimes.com/rss/headlines/news/national/",
        "New York Post": "https://nypost.com/feed/",
        "Daily Wire": "https://www.dailywire.com/feeds/rss.xml"
    },
    "International": {
        "BBC World": "http://feeds.bbci.co.uk/news/world/rss.xml",
        "Reuters World": "http://feeds.reuters.com/reuters/worldNews",
        "Al Jazeera": "https://www.aljazeera.com/xml/rss/all.xml",
        "France24": "https://www.france24.com/en/rss",
        "DW News": "https://rss.dw.com/rdf/rss-en-all",
        "The Guardian World": "https://www.theguardian.com/world/rss",
        "BBC US & Canada": "http://feeds.bbci.co.uk/news/world/us_and_canada/rss.xml",
        "Euronews": "https://www.euronews.com/rss",
        "CBC World": "https://www.cbc.ca/cmlink/rss-world",
        "The Diplomat": "https://thediplomat.com/feed/",
        "Spiegel International": "https://www.spiegel.de/international/index.rss"
    },
    "Technology": {
        "TechCrunch": "https://techcrunch.com/feed/",
        "Wired": "https://www.wired.com/feed/rss",
        "Ars Technica": "http://feeds.arstechnica.com/arstechnica/index",
        "BBC Tech": "http://feeds.bbci.co.uk/news/technology/rss.xml",
        "MIT Technology Review": "https://www.technologyreview.com/feed/",
        "The Verge": "https://www.theverge.com/rss/index.xml",
        "CNET": "https://www.cnet.com/rss/news/",
        "ZDNet": "https://www.zdnet.com/news/rss.xml",
        "Engadget": "https://www.engadget.com/rss.xml",
        "Slashdot": "http://rss.slashdot.org/Slashdot/slashdotMain"
    }
}

# --- BACKUP NEWS FEEDS ---
# Used when primary feeds fail or return no articles
BACKUP_RSS_FEEDS = {
    "Center": {
        "AP Politics": "https://apnews.com/hub/ap-politics/rss",
        "Reuters Politics": "http://feeds.reuters.com/Reuters/PoliticsNews",
        "Axios": "https://api.axios.com/feed/", 
        "NPR All Topics": "https://feeds.npr.org/1001/rss.xml"
    },
    "Tennessee": {
        "Tennessee State Government": "https://www.tn.gov/news.rss",
        "Nashville Business Journal": "https://www.bizjournals.com/nashville/news/feed",
        "WKRN Nashville": "https://www.wkrn.com/feed/"
    },
    "International": {
        "CNN International": "http://rss.cnn.com/rss/edition.rss",
        "Reuters International": "http://feeds.reuters.com/reuters/INtopNews"
    }
}

# --- International News Filter Keywords ---
# Used to filter international news by relevance to user interests
INCLUDE_INTERNATIONAL_KEYWORDS = [
    "U.S.", "America", "United States", "USA", "Kenya", "education", "youth", 
    "leadership", "economy", "economic", "conflict", "war", "crisis", "disaster",
    "Nashville", "Tennessee", "Middle Tennessee", "scouting", "scouts", "climate",
    "global warming", "pandemic", "humanitarian", "AI", "artificial intelligence"
]

# --- User Interests/Tags Definition ---
# These tags are used for article classification and personalization
USER_INTERESTS = [
    "Scouting", "Education", "Policy", "AI", "Technology", "Business", 
    "Civic Affairs", "Tennessee", "Global Missions", "Outdoor", "Backpacking",
    "FOIA", "Transparency", "Government"
]

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
    "article_fetch_timeout": 15,           # Timeout in seconds for article fetching
    "max_articles_to_process": 25,         # Maximum number of articles to process in one run
    "max_retries": 2,                      # Maximum number of retries for failed requests
    "session_reuse": True,                 # Whether to reuse HTTP sessions between categories
    "skip_empty_feeds": True,              # Whether to skip or flag empty feeds without spamming logs
    "max_parallel_workers": 5,             # Number of parallel workers for concurrent processing
    "max_primary_articles_per_feed": 2,    # Maximum number of articles to fetch per primary feed
    "max_secondary_articles_per_feed": 1,  # Maximum number of articles to fetch per secondary feed
    "report_slow_sources": True,           # Whether to report slow sources in logs
    "use_newspaper3k": True,               # Whether to use newspaper3k for article extraction
    "cache_articles": True,                # Whether to cache articles to prevent duplicate processing
    "cache_expiry_hours": 24,              # How long to keep articles in cache
    "use_central_timezone": True,          # Whether to convert all dates to Central Time
    "default_timezone": "America/Chicago", # Default timezone for date standardization
    "prioritize_primary_feeds": True,      # Whether to prioritize PRIMARY_NEWS_FEEDS over others
    "use_supplemental_feeds": False,       # Whether to use SUPPLEMENTAL_FEEDS when primary feeds are empty
    "http_request_delay": 1,               # Delay between requests to the same domain in seconds
    "http_timeout": 15,                    # HTTP request timeout in seconds
    "max_redirects": 5,                    # Maximum number of redirects to follow
    "verify_ssl": True,                    # Whether to verify SSL certificates
    "requests_html_timeout": 20,           # Timeout for requests-html rendering in seconds
    "min_content_length": 150              # Minimum length of article content to be considered valid
}

# --- Problematic Sources ---
# News sources that often block automated access or require special handling
PROBLEM_SOURCES = {
    "wsj.com",           # Wall Street Journal (paywall)
    "ft.com",           # Financial Times (paywall)
    "bloomberg.com",    # Bloomberg (paywall)
    "nytimes.com",      # New York Times (paywall)
    "washingtonpost.com", # Washington Post (paywall)
    "economist.com",    # The Economist (paywall)
    "medium.com",       # Medium (requires cookie handling)
    "substack.com",     # Substack (requires JavaScript)
    "forbes.com",       # Forbes (anti-bot measures)
    "theatlantic.com"   # The Atlantic (paywall)
}

def get_settings() -> Dict[str, Any]:
    """Returns all settings as a dictionary."""
    return {
        'system': SYSTEM_SETTINGS,
        'gnews': GNEWS_CONFIG,
        'feeds': FEED_SETTINGS,
        'email': EMAIL_SETTINGS,
    }