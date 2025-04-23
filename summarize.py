import feedparser
from newspaper import Article
from newspaper.article import ArticleException
import nltk
import requests
from bs4 import BeautifulSoup
import os
from dotenv import load_dotenv
import openai
import time
from logger_config import setup_logger
from config import PRIMARY_NEWS_FEEDS, SECONDARY_FEEDS, SUPPLEMENTAL_FEEDS, BACKUP_RSS_FEEDS, SYSTEM_SETTINGS, USER_INTERESTS

# Set up logger
logger = setup_logger()

# Load environment variables
load_dotenv()

# Set up OpenAI API
openai.api_key = os.environ.get('OPENAI_API_KEY')

# Ensure required NLTK resources are available
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    logger.info("Downloading NLTK 'punkt' resource...")
    nltk.download('punkt')

try:
    nltk.data.find('tokenizers/punkt_tab')
except LookupError:
    logger.info("Downloading NLTK 'punkt_tab' resource...")
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
        logger.info(f"Fetching articles for category: {category}")
        for source_name, feed_url in feeds.items():
            logger.info(f"From: {source_name}")
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
                    logger.warning(f"Newspaper failed for: {entry.link}\nReason: {e}")
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
                        logger.error(f"Fallback failed for: {entry.link}\nReason: {fallback_error}")
                        # Use RSS feed's summary as a last resort or provide a link
                        preview_content = entry.summary if 'summary' in entry else f"Read more: {entry.link}"
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
        logger.info("Skipped Articles:")
        for skipped in skipped_articles:
            logger.debug(f"URL: {skipped['url']}\nReason: {skipped['reason']}")

    return all_articles


# --- OpenAI Summarization ---

def summarize_with_openai(text, title=None, max_retries=3, retry_delay=1):
    """
    Summarize text using OpenAI's API as 2-3 bullet points for fast reading.
    Args:
        text (str): The article text to summarize
        title (str): The article title for context
        max_retries (int): Maximum number of retries for API calls
        retry_delay (int): Delay between retries in seconds
    Returns:
        str: Summarized text (bullet points)
    """
    # Check if OpenAI API key is available
    if not openai.api_key:
        logger.warning("OpenAI API key not set. Skipping AI summarization.")
        return None
    
    # Prepare the text for summarization
    context = f"Title: {title}\n\nContent: {text}" if title else text
    # Truncate if too long for API call
    if len(context) > 15000:
        context = context[:15000] + "..."
    
    # Prompt for bullet points
    prompt = (
        "Summarize the following news article as 2-3 concise bullet points for fast reading. "
        "Each bullet should focus on a key fact, event, or takeaway. Do not write paragraphs. "
        "Be factual, neutral, and clear. Only output the bullet points, nothing else."
    )
    
    # Try to get a summary with retries for API errors
    attempts = 0
    while attempts < max_retries:
        try:
            response = openai.chat.completions.create(
                model="gpt-4o-mini",  # Use a suitable model
                messages=[
                    {"role": "system", "content": "You are a professional news editor. Return only 2-3 bullet points summarizing the article's key facts."},
                    {"role": "user", "content": f"{prompt}\n\n{context}"}
                ],
                temperature=0.4,
                max_tokens=300
            )
            summary = response.choices[0].message.content.strip()
            return summary
        except Exception as e:
            attempts += 1
            logger.warning(f"OpenAI API error (attempt {attempts}/{max_retries}): {str(e)}")
            if attempts < max_retries:
                time.sleep(retry_delay)
            else:
                logger.error(f"Failed to get OpenAI summary after {max_retries} attempts")
                return None


# --- Summarization Logic ---

def summarize_articles(articles):
    """
    Summarizes the content of each article in the provided list.
    Uses OpenAI API if available, falls back to traditional methods.

    Args:
        articles (list): List of articles, each represented as a dictionary.

    Returns:
        list: List of articles with an added 'summary' field.
    """
    logger.info(f"Summarizing {len(articles)} articles")
    summarized = []
    
    # Check if OpenAI API key is configured
    use_openai = bool(openai.api_key)
    if use_openai:
        logger.info("Using OpenAI for article summarization")
    else:
        logger.info("OpenAI API key not found - using fallback summarization")
    
    for i, article in enumerate(articles):
        try:
            title = article.get('title', '')
            content = article.get('content', '')
            
            # Skip if no content
            if not content:
                article['summary'] = "No content available to summarize."
                summarized.append(article)
                continue
            
            # Try OpenAI summarization first if API key is available
            if use_openai:
                try:
                    ai_summary = summarize_with_openai(content, title)
                    if ai_summary:
                        article['summary'] = ai_summary
                        article['summary_method'] = 'openai'
                        summarized.append(article)
                        logger.info(f"Used OpenAI to summarize: {title}")
                        
                        # Log progress for every article with OpenAI
                        logger.info(f"Summarized {i+1}/{len(articles)} articles using OpenAI")
                        continue
                except Exception as e:
                    logger.error(f"OpenAI summarization failed for {title}: {str(e)}")
                    # Continue to fallback methods
            
            # Fallback 1: If content is too long, use newspaper's built-in summarization
            if len(content) > 1000:
                try:
                    article_url = article.get('url', '')
                    from newspaper import Article as NewspaperArticle
                    article_obj = NewspaperArticle(article_url)
                    article_obj.download()
                    article_obj.parse()
                    article_obj.nlp()
                    article['summary'] = article_obj.summary
                    article['summary_method'] = 'newspaper'
                except Exception as e:
                    logger.warning(f"Newspaper summarization failed for {title}: {str(e)}")
                    # Truncate long content as a last resort
                    article['summary'] = content[:1000] + "..."
                    article['summary_method'] = 'truncation'
            else:
                # For short articles, just use the content directly
                article['summary'] = content
                article['summary_method'] = 'passthrough'
            
            summarized.append(article)
            
            # Log progress for every 5 articles
            if (i+1) % 5 == 0:
                logger.info(f"Summarized {i+1}/{len(articles)} articles")
                
        except Exception as e:
            logger.error(f"Failed to process article {article.get('title', 'Unknown')}: {str(e)}")
            # Still include the article with a default summary
            article['summary'] = article.get('content', 'Summary not available.')
            article['summary_method'] = 'error'
            summarized.append(article)
    
    logger.info(f"Summary complete. Processed {len(summarized)}/{len(articles)} articles successfully")
    
    # Summarize methods used
    methods = {}
    for article in summarized:
        method = article.get('summary_method', 'unknown')
        methods[method] = methods.get(method, 0) + 1
    
    logger.info("Summarization methods used:")
    for method, count in methods.items():
        logger.info(f"  - {method}: {count} articles")
        
    return summarized


# --- Test Execution ---

if __name__ == "__main__":
    logger.info("Testing summarization functionality")
    articles = fetch_articles_from_all_feeds()
    articles = summarize_articles(articles)
    for i, article in enumerate(articles, 1):
        logger.info(f"\n--- Article {i} ---")
        logger.info(f"Title: {article['title']}")
        logger.info(f"Source: {article['source']} ({article['category']})")
        logger.info(f"URL: {article['url']}")
        logger.info(f"Published: {article['published']}")
        logger.info(f"Method: {article.get('summary_method', 'unknown')}")
        logger.debug(f"Content Preview:\n{article['content'][:300]}...\n")
        logger.info(f"Summary:\n{article['summary']}\n")
