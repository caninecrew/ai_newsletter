import feedparser
from newspaper import Article

# You can add more feeds here
RSS_FEEDS = {
    "Scouting": "https://blog.scoutingmagazine.org/feed/",
    "Technology": "http://feeds.bbci.co.uk/news/technology/rss.xml",
    "Education": "https://feeds.npr.org/1013/rss.xml",
    "Kenya News": "https://www.aljazeera.com/xml/rss/all.xml",  # general feed, may need filtering
}

def fetch_articles_from_rss(topic="Technology", max_articles=5):
    if topic not in RSS_FEEDS:
        print(f"[WARN] Topic '{topic}' not found. Defaulting to Technology.")
        topic = "Technology"
    
    feed_url = RSS_FEEDS[topic]
    feed = feedparser.parse(feed_url)

    articles = []
    count = 0

    for entry in feed.entries:
        if count >= max_articles:
            break
        try:
            article = Article(entry.link)
            article.download()
            article.parse()
            articles.append({
                'title': article.title,
                'url': article.url,
                'content': article.text,
                'published': entry.published if 'published' in entry else "Unknown"
            })
            count += 1
        except Exception as e:
            print(f"[ERROR] Failed to process article: {entry.link}\n{e}")

    return articles

# Test the module
if __name__ == "__main__":
    topic = "Scouting"
    articles = fetch_articles_from_rss(topic, max_articles=3)
    for i, article in enumerate(articles, 1):
        print(f"\n--- Article {i} ---")
        print(f"Title: {article['title']}")
        print(f"Published: {article['published']}")
        print(f"URL: {article['url']}")
        print(f"Content Preview:\n{article['content'][:300]}...\n")
