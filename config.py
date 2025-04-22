# Configuration file for AI Newsletter
# This file contains configurable settings for the newsletter system

# --- RSS Feed Definitions ---
# Format: Category -> Source -> URL

RSS_FEEDS = {
    "Left": {
        "CNN": "http://rss.cnn.com/rss/cnn_topstories.rss",
        "NYT": "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml",
        "MSNBC": "https://www.msnbc.com/feeds/latest"
    },
    "Center": {
        "NPR": "https://feeds.npr.org/1001/rss.xml",
        "AP": "https://apnews.com/rss",
        "Reuters": "http://feeds.reuters.com/reuters/domesticNews"
    },
    "Right": { # limited Right sources that provide RSS feeds for this purpose, therefore only a few work with this system
        "Washington Times": "https://www.washingtontimes.com/rss/headlines/news/politics/"
    },
    "International": {
        "BBC": "http://feeds.bbci.co.uk/news/world/rss.xml",
        "Reuters": "http://feeds.reuters.com/reuters/worldNews",
        "Al Jazeera": "https://www.aljazeera.com/xml/rss/all.xml",
        "France24": "https://www.france24.com/en/rss",
        "DW": "https://rss.dw.com/rdf/rss-en-all"
    },
    "Tennessee": {
        "WKRN News 2 Nashville": "https://wkrn.com/feed",
        "Tennessee Tribune": "https://tntribune.com/category/community/local/nashville/feed/",
        "Tennessee Star": "https://tennesseestar.com/feed/"
    },
    "Personalized": {
        "Scouting": "https://blog.scoutingmagazine.org/feed/",
        "NPR Education": "https://feeds.npr.org/1013/rss.xml",
        "BBC Tech": "http://feeds.bbci.co.uk/news/technology/rss.xml"
    }
}

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
# Control the appearance and structure of the newsletter

EMAIL_SETTINGS = {
    "max_articles_per_category": 3,
    "show_why_this_matters": True,
    "show_key_takeaways": True,
    "include_table_of_contents": True
}

# --- System Settings ---
# General system configuration options

SYSTEM_SETTINGS = {
    "log_level": "INFO",  # Options: DEBUG, INFO, WARNING, ERROR, CRITICAL
    "article_fetch_timeout": 10,  # Timeout in seconds for fetching articles
    "max_articles_to_process": 50  # Maximum number of articles to process in one run
}