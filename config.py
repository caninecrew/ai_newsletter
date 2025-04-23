# Configuration file for AI Newsletter
# This file contains configurable settings for the newsletter system

# --- News Source Configuration ---
# Set the primary news source to use: "rss" or "gnews"
PRIMARY_NEWS_SOURCE = "rss"

# GNews API Configuration
# Note: API key should be stored in .env file as GNEWS_API_KEY, not here
GNEWS_API_CONFIG = {
    "api_key": "",  # API key should come from .env file, not stored here
    "topic_mapping": {
        "global_major": "world",
        "domestic_major": ["nation", "politics"],
        "technology": "technology",
        "business": "business",
        "entertainment": "entertainment",
        "sports": "sports",
        "science": "science",
        "health": "health"
    },
    "language": "en",  # Language for news articles
    "country": "us",   # Country for domestic news
    "max_results": 10, # Maximum number of results per topic
    "hours": 24       # How many hours back to fetch news
}

# --- RSS Feed Definitions ---
# Format: Category -> Source -> URL
# Removed problematic sources: Fox News, Politico, WKRN, Washington Times

RSS_FEEDS = {
    "Left": {
        "CNN": "http://rss.cnn.com/rss/cnn_topstories.rss",
        "CNN Americas": "http://rss.cnn.com/rss/edition_americas.rss",
        "NYT": "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml",
        "NYT US": "https://rss.nytimes.com/services/xml/rss/nyt/US.xml",
        "NYT Politics": "https://rss.nytimes.com/services/xml/rss/nyt/Politics.xml",
        "MSNBC": "https://www.msnbc.com/feeds/latest",
        "Washington Post National": "http://feeds.washingtonpost.com/rss/national",
        "Washington Post World": "https://feeds.washingtonpost.com/rss/world"
    },
    "Center": {
        "NPR": "https://feeds.npr.org/1001/rss.xml",
        "AP": "https://apnews.com/rss",
        "Reuters": "http://feeds.reuters.com/reuters/domesticNews",
        "PBS Headlines": "https://www.pbs.org/newshour/feeds/rss/headlines",
        "PBS World": "https://www.pbs.org/newshour/feeds/rss/podcasts/world",
        "PBS Politics": "https://www.pbs.org/newshour/feeds/rss/politics",
        "ABC US": "https://abcnews.go.com/abcnews/usheadlines",
        "CBS Top Stories": "https://www.cbsnews.com/latest/rss/main",
        "USA Today": "http://rssfeeds.usatoday.com/UsatodaycomNation-TopStories"
    },
    "Right": {
        "Wall Street Journal": "https://feeds.a.dj.com/rss/RSSWorldNews.xml",
        "National Review": "https://www.nationalreview.com/feed/",
        "The Hill": "https://thehill.com/rss/syndicator/19110",
        "Washington Examiner": "https://www.washingtonexaminer.com/tag/news.xml",
        "Newsmax": "https://www.newsmax.com/rss/Headline/0",
        "The Dispatch": "https://thedispatch.com/feed/",  # Added reliable conservative source
        "The Bulwark": "https://thebulwark.com/feed/"    # Added moderate conservative source
    },
    "International": {
        "BBC": "http://feeds.bbci.co.uk/news/world/rss.xml",
        "Reuters World": "http://feeds.reuters.com/reuters/worldNews",
        "Al Jazeera": "https://www.aljazeera.com/xml/rss/all.xml",
        "France24": "https://www.france24.com/en/rss",
        "DW": "https://rss.dw.com/rdf/rss-en-all",
        "The Guardian World": "https://www.theguardian.com/world/rss", # Added reliable international source
        "BBC US & Canada": "http://feeds.bbci.co.uk/news/world/us_and_canada/rss.xml" # Added BBC's US coverage
    },
    "Tennessee": {
        "Tennessean": "https://rssfeeds.tennessean.com/nashville/home",
        "Tennessee Tribune": "https://tntribune.com/category/community/local/nashville/feed/",
        "News Channel 5 Nashville": "https://www.newschannel5.com/news/local-news/feed",
        "WPLN Nashville Public Radio": "https://wpln.org/feed/" # Added reliable local source
    },
    "Technology": { # Added dedicated Technology category
        "TechCrunch": "https://techcrunch.com/feed/",
        "Wired": "https://www.wired.com/feed/rss",
        "Ars Technica": "http://feeds.arstechnica.com/arstechnica/index",
        "BBC Tech": "http://feeds.bbci.co.uk/news/technology/rss.xml",
        "MIT Technology Review": "https://www.technologyreview.com/feed/"
    },
    "Personalized": {
        "Scouting": "https://blog.scoutingmagazine.org/feed/",
        "Scout Life Magazine": "https://scoutlife.org/feed/",
        "Scouting Newsroom": "https://www.scoutingnewsroom.org/feed/",
        "NPR Education": "https://feeds.npr.org/1013/rss.xml"
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
    "max_articles_per_source": 3,    # Maximum articles from any single source to prevent domination
    "max_articles_total": 15,        # Maximum total articles to include in newsletter
    "show_why_this_matters": True,
    "show_key_takeaways": True,
    "include_table_of_contents": True
}

# --- System Settings ---
# General system configuration options

SYSTEM_SETTINGS = {
    "log_level": "INFO",           # Options: DEBUG, INFO, WARNING, ERROR, CRITICAL
    "article_fetch_timeout": 5,    # Reduced timeout from 10 to 5 seconds for faster processing
    "max_articles_to_process": 50, # Maximum number of articles to process in one run
    "max_retries": 2,              # Maximum number of retries for failed requests
    "session_reuse": True,         # Whether to reuse HTTP/browser sessions between categories
    "skip_empty_feeds": True,      # Whether to skip or flag empty feeds without spamming logs
    "max_parallel_workers": 8,     # Number of parallel workers for concurrent processing
    "max_articles_per_feed": 5,    # Maximum number of articles to fetch per feed
    "report_slow_sources": True    # Whether to report slow sources in logs
}