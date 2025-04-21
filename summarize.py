import feedparser
from newspaper import Article
from newspaper.article import ArticleException
import nltk
import requests
from bs4 import BeautifulSoup

# Ensure required NLTK resources are available
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    print("[INFO] Downloading NLTK 'punkt' resource...")
    nltk.download('punkt')

try:
    nltk.data.find('tokenizers/punkt_tab')
except LookupError:
    print("[INFO] Downloading NLTK 'punkt_tab' resource...")
    nltk.download('punkt_tab')

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
    skipped_articles = []  # To log skipped articles

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
                    print(f"    [WARN] Newspaper failed for: {entry.link}\n    Reason: {e}")
                    # Fallback to requests + BeautifulSoup
                    try:
                        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
                        response = requests.get(entry.link, headers=headers, timeout=10)
                        response.raise_for_status()
                        soup = BeautifulSoup(response.text, 'html.parser')
                        content = soup.get_text(separator="\n").strip()
                        all_articles.append({
                            'title': entry.title if 'title' in entry else "No Title",
                            'url': entry.link,
                            'source': source_name,
                            'category': category,
                            'published': entry.published if 'published' in entry else "Unknown",
                            'content': content[:10000]  # Limit content length
                        })
                        count += 1
                    except Exception as fallback_error:
                        print(f"    [ERROR] Fallback failed for: {entry.link}\n    Reason: {fallback_error}")
                        # Use RSS feed's summary as a last resort
                        preview_content = entry.summary if 'summary' in entry else "No preview available."
                        all_articles.append({
                            'title': entry.title if 'title' in entry else "No Title",
                            'url': entry.link,
                            'source': source_name,
                            'category': category,
                            'published': entry.published if 'published' in entry else "Unknown",
                            'content': preview_content
                        })
                        count += 1

    # Log skipped articles
    if skipped_articles:
        print("\n[INFO] Skipped Articles:")
        for skipped in skipped_articles:
            print(f"  - URL: {skipped['url']}\n    Reason: {skipped['reason']}")

    return all_articles


# --- Summarization Logic ---

def summarize_articles(articles):
    """
    Summarizes the content of each article in the provided list.

    Args:
        articles (list): List of articles, each represented as a dictionary.

    Returns:
        list: List of articles with an added 'summary' field.
    """
    for article in articles:
        try:
            # Use the newspaper library's built-in summarization
            article_obj = Article(article['url'])
            article_obj.download()
            article_obj.parse()
            article_obj.nlp()
            article['summary'] = article_obj.summary
        except ArticleException as e:
            print(f"[WARN] Could not summarize article: {article['url']}\nReason: {e}")
            article['summary'] = "Summary not available."

    return articles


# --- Test Execution ---

if __name__ == "__main__":
    articles = fetch_articles_from_all_feeds()
    articles = summarize_articles(articles)
    for i, article in enumerate(articles, 1):
        print(f"\n--- Article {i} ---")
        print(f"Title: {article['title']}")
        print(f"Source: {article['source']} ({article['category']})")
        print(f"URL: {article['url']}")
        print(f"Published: {article['published']}")
        print(f"Content Preview:\n{article['content'][:300]}...\n")
        print(f"Summary:\n{article['summary']}\n")
