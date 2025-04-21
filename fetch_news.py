import feedparser
from newspaper import Article

# --- RSS Feed Definitions ---

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
    "Right": {
        "Fox News": "http://feeds.foxnews.com/foxnews/latest",
        "Daily Wire": "https://www.dailywire.com/feed",
        "Washington Times": "https://www.washingtontimes.com/rss/headlines/news/politics/"
    },
    "International": {
        "BBC": "http://feeds.bbci.co.uk/news/world/rss.xml",
        "Reuters": "http://feeds.reuters.com/reuters/worldNews",
        "Al Jazeera": "https://www.aljazeera.com/xml/rss/all.xml",
        "France24": "https://www.france24.com/en/rss",
        "DW": "https://rss.dw.com/rdf/rss-en-all"
    },
    "Personalized": {
        "Scouting": "https://blog.scoutingmagazine.org/feed/",
        "NPR Education": "https://feeds.npr.org/1013/rss.xml",
        "BBC Tech": "http://feeds.bbci.co.uk/news/technology/rss.xml"
    }
}


# --- Fetching Logic ---

def fetch_articles_from_all_feeds(max_articles_per_source=3):
    all_articles = []

    for category, feeds in RSS_FEEDS.items():
        print(f"\n[INFO] Fetching articles for category: {category}")
        for source_name, feed_url in feeds.items():
            print(f"  • From: {source_name}")
            feed = feedparser.parse(feed_url)
            count = 0

            for entry in feed.entries:
                if count >= max_articles_per_source:
                    break
                try:
                    article = Article(entry.link)
                    article.download()
                    article.parse()
                    all_articles.append({
                        'title': article.title,
                        'url': article.url,
                        'source': source_name,
                        'category': category,
                        'published': entry.published if 'published' in entry else "Unknown",
                        'content': article.text
                    })
                    count += 1
                except Exception as e:
                    print(f"    [WARN] Skipping article: {entry.link}\n    Reason: {e}")

    return all_articles


# --- Test Execution ---

if __name__ == "__main__":
    articles = fetch_articles_from_all_feeds()
    for i, article in enumerate(articles, 1):
        print(f"\n--- Article {i} ---")
        print(f"Title: {article['title']}")
        print(f"Source: {article['source']} ({article['category']})")
        print(f"URL: {article['url']}")
        print(f"Published: {article['published']}")
        print(f"Content Preview:\n{article['content'][:300]}...\n")
