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
# Organized by political leaning and content focus

RSS_FEEDS = {
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
    "Tennessee": {
        "The Tennessean": "https://rssfeeds.tennessean.com/nashville/home",
        "Tennessee Tribune": "https://tntribune.com/category/community/local/nashville/feed/",
        "News Channel 5 Nashville": "https://www.newschannel5.com/news/local-news/feed",
        "WPLN Nashville Public Radio": "https://wpln.org/feed/",
        "WSMV News": "https://www.wsmv.com/news/tennessee/?format=rss",
        "Knox News": "https://www.knoxnews.com/news/?format=rss",
        "Tennessee Lookout": "https://tennesseelookout.com/feed/",
        "Chattanooga Times Free Press": "https://www.timesfreepress.com/rss/headlines/breakingnews/",
        "Memphis Commercial Appeal": "https://www.commercialappeal.com/news/?format=rss",
        "Johnson City Press": "https://www.johnsoncitypress.com/search/?f=rss"
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
    },
    "Personalized": {
        "Scouting": "https://blog.scoutingmagazine.org/feed/",
        "Scout Life Magazine": "https://scoutlife.org/feed/",
        "Scouting Newsroom": "https://www.scoutingnewsroom.org/feed/",
        "NPR Education": "https://feeds.npr.org/1013/rss.xml",
        "Education Week": "https://www.edweek.org/rss",
        "Chronicle of Higher Education": "https://www.chronicle.com/feed",
        "Outdoor Life": "https://www.outdoorlife.com/rss/all/",
        "Outside Online": "https://www.outsideonline.com/feed/"
    },
    "News Aggregators": {
        "Google News Top Stories": "https://news.google.com/rss",
        "Google News US": "https://news.google.com/rss/topics/CAAqIggKIhxDQkFTRHdvSkwyMHZNRGxqTjNjd0VnSmxiaWdBUAE",
        "Google News World": "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGx1YlY4U0FtVnVHZ0pWVXlnQVAB",
        "Google News Technology": "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGRqTVhZU0FtVnVHZ0pWVXlnQVAB",
        "Yahoo News": "https://news.yahoo.com/rss",
        "MSN News US": "http://rss.msn.com/en-us/news/us",
        "MSN News World": "http://rss.msn.com/en-us/news/world"
    }
}

# --- RSS Feed Backup List ---
# Used when primary feeds fail or return empty results

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