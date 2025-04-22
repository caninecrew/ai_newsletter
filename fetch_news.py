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
from logger_config import setup_logger
from config import RSS_FEEDS, SYSTEM_SETTINGS

# Set up logger
logger = setup_logger()

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
    except Exception as e:
        logger.warning(f"Google cache retrieval failed for {original_url}: {str(e)}")
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
    except Exception as e:
        logger.warning(f"Archive.org retrieval failed for {original_url}: {str(e)}")
    return None

def get_article_fallback_content(entry):
    title = entry.get("title", "")
    url = entry.get("link", "")

    logger.info(f"Attempting fallback for blocked source: {url}")

    # Step 1: RSS Summary
    summary = try_rss_summary(entry)
    if summary:
        logger.debug(f"Successfully retrieved RSS summary for {url}")
        return summary, "summary"

    # Step 2: Syndicated Version
    syndicated_url = try_syndicated_version(title)
    if syndicated_url:
        logger.info(f"Found syndicated version: {syndicated_url}")
        try:
            res = requests.get(syndicated_url, headers={"User-Agent": "Mozilla/5.0"})
            soup = BeautifulSoup(res.text, "html.parser")
            paragraphs = soup.find_all("p")
            return "\n".join(p.get_text() for p in paragraphs).strip(), "syndicated"
        except Exception as e:
            logger.warning(f"Failed to retrieve syndicated content: {str(e)}")

    # Step 3: Google Cache
    logger.debug(f"Trying Google cache for {url}")
    cached_content = try_google_cache(url)
    if cached_content:
        logger.debug(f"Successfully retrieved Google cache for {url}")
        return cached_content, "google-cache"

    # Step 4: Archive.org
    logger.debug(f"Trying Archive.org for {url}")
    archived_content = try_archive_dot_org(url)
    if archived_content:
        logger.debug(f"Successfully retrieved Archive.org content for {url}")
        return archived_content, "wayback"

    # Step 5: Give up
    logger.warning(f"All fallback methods failed for {url}")
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

    driver = None
    try:
        logger.info("Setting up Chrome WebDriver")
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()), 
            options=chrome_options
        )

        for category, feeds in RSS_FEEDS.items():
            logger.info(f"Fetching articles for category: {category}")
            for source_name, feed_url in feeds.items():
                logger.info(f"Processing feed: {source_name}")
                try:
                    feed = feedparser.parse(feed_url)
                    if not feed.entries:
                        logger.warning(f"No entries found in feed: {source_name} ({feed_url})")
                        continue
                        
                    count = 0
                    for entry in feed.entries:
                        if count >= max_articles_per_source:
                            break
                        try:
                            if source_name in ["Fox News", "Washington Times"]:
                                content, method = get_article_fallback_content(entry)
                                logger.debug(f"Used fallback method {method} for {source_name}: {entry.get('link', 'No URL')}")
                            else:
                                article = Article(entry.link)
                                article.download()
                                article.parse()
                                content = article.text
                                method = "full"
                                logger.debug(f"Successfully parsed article from {source_name}: {entry.get('title', 'No Title')}")
                        except Exception as e:
                            logger.warning(f"Newspaper failed for: {entry.get('link', 'No URL')} - Reason: {str(e)}")
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
                except Exception as e:
                    logger.error(f"Error processing feed {source_name}: {str(e)}")

        # Log skipped articles
        if skipped_articles:
            logger.info(f"Skipped {len(skipped_articles)} articles")
            for skipped in skipped_articles:
                logger.debug(f"Skipped URL: {skipped['url']} - Reason: {skipped['reason']}")

    except Exception as e:
        logger.error(f"Error in fetch_articles_from_all_feeds: {str(e)}", exc_info=True)
    finally:
        if driver is not None:  # Check if driver was initialized
            driver.quit()  # Ensure the WebDriver is closed
            logger.debug("WebDriver closed")

    logger.info(f"Article fetching completed. Retrieved {len(all_articles)} articles.")
    return all_articles


# --- Test Execution ---

if __name__ == "__main__":
    logger.info("Running fetch_news.py directly for testing")
    articles = fetch_articles_from_all_feeds()
    for i, article in enumerate(articles, 1):
        logger.info(f"Article {i}: {article['title']} - {article['source']} ({article['category']})")
        logger.debug(f"URL: {article['url']}")
        logger.debug(f"Published: {article['published']}")
        logger.debug(f"Content Preview: {article['content'][:150]}...")
