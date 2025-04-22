import feedparser
from newspaper import Article
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
import time
import requests
from bs4 import BeautifulSoup

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


# --- Fetching Logic ---

def try_rss_summary(entry):
    return entry.get('summary', '').strip()

def try_syndicated_version(title):
    search_query = f"{title} site:news.yahoo.com OR site:msn.com"
    url = f"https://www.google.com/search?q={requests.utils.quote(search_query)}"
    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(url, headers=headers)
    if res.ok:
        soup = BeautifulSoup(res.text, "html.parser")
        links = soup.select("a")
        for link in links:
            href = link.get("href", "")
            if "yahoo.com" in href or "msn.com" in href:
                return href
    return None

def try_google_cache(original_url):
    cache_url = f"http://webcache.googleusercontent.com/search?q=cache:{original_url}"
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(cache_url, headers=headers)
        if res.ok:
            soup = BeautifulSoup(res.text, "html.parser")
            paragraphs = soup.find_all("p")
            return "\n".join(p.get_text() for p in paragraphs).strip()
    except:
        pass
    return None

def try_archive_dot_org(original_url):
    archive_lookup = f"https://archive.org/wayback/available?url={original_url}"
    try:
        res = requests.get(archive_lookup)
        snapshot = res.json().get("archived_snapshots", {}).get("closest", {}).get("url")
        if snapshot:
            res2 = requests.get(snapshot)
            soup = BeautifulSoup(res2.text, "html.parser")
            paragraphs = soup.find_all("p")
            return "\n".join(p.get_text() for p in paragraphs).strip()
    except:
        pass
    return None

def get_article_fallback_content(entry):
    title = entry.get("title", "")
    url = entry.get("link", "")

    print(f"[INFO] Attempting fallback for blocked source: {url}")

    # Step 1: RSS Summary
    summary = try_rss_summary(entry)
    if summary:
        return summary, "summary"

    # Step 2: Syndicated Version
    syndicated_url = try_syndicated_version(title)
    if syndicated_url:
        print(f"[INFO] Found syndicated version: {syndicated_url}")
        try:
            res = requests.get(syndicated_url, headers={"User-Agent": "Mozilla/5.0"})
            soup = BeautifulSoup(res.text, "html.parser")
            paragraphs = soup.find_all("p")
            return "\n".join(p.get_text() for p in paragraphs).strip(), "syndicated"
        except:
            pass

    # Step 3: Google Cache
    cached_content = try_google_cache(url)
    if cached_content:
        return cached_content, "google-cache"

    # Step 4: Archive.org
    archived_content = try_archive_dot_org(url)
    if archived_content:
        return archived_content, "wayback"

    # Step 5: Give up
    return "Content not accessible due to site restrictions.", "source-limited"

def fetch_articles_from_all_feeds(max_articles_per_source=3):
    all_articles = []
    skipped_articles = []  # To log skipped articles

    # Configure Selenium WebDriver
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run in headless mode
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run in headless mode (no browser UI)
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), 
        options=chrome_options
)

    try:
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
                        if source_name in ["Fox News", "Washington Times"]:
                            content, method = get_article_fallback_content(entry)
                            print(f"[INFO] Used fallback method: {method}")
                        else:
                            article = Article(entry.link)
                            article.download()
                            article.parse()
                            content = article.text
                            method = "full"
                    except Exception as e:
                        print(f"    [WARN] Newspaper failed for: {entry.link}\n    Reason: {e}")
                        content, method = get_article_fallback_content(entry)

                    all_articles.append({
                        'title': entry.title if 'title' in entry else "No Title",
                        'url': entry.link,
                        'source': source_name,
                        'category': category,
                        'published': entry.published if 'published' in entry else "Unknown",
                        'content': content,
                        'fetch_method': method
                    })
                    count += 1

        # Log skipped articles
        if skipped_articles:
            print("\n[INFO] Skipped Articles:")
            for skipped in skipped_articles:
                print(f"  - URL: {skipped['url']}\n    Reason: {skipped['reason']}")

    finally:
        if driver is not None:  # Check if driver was initialized
            driver.quit()  # Ensure the WebDriver is closed

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
