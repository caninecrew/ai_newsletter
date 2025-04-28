import feedparser
from newspaper import Article, Config
from newspaper.article import ArticleException
import nltk
import requests
from bs4 import BeautifulSoup
import os
from dotenv import load_dotenv
import openai
import time
from datetime import datetime, timezone, timedelta
from dateutil import tz as dateutil_tz
from typing import Optional, List, Dict
from ai_newsletter.logging_cfg.logger import setup_logger
from ai_newsletter.config.settings import (
    PRIMARY_NEWS_FEEDS, SECONDARY_FEEDS, SUPPLEMENTAL_FEEDS, BACKUP_RSS_FEEDS, 
    SYSTEM_SETTINGS, USER_INTERESTS, EMAIL_SETTINGS
)
import certifi
import ssl
import urllib3

# Set up logger
logger = setup_logger()

# Load environment variables
load_dotenv()

# Configure default timezone using dateutil
CENTRAL = dateutil_tz.gettz("America/Chicago")
DEFAULT_TZ = CENTRAL

# Configure newspaper
config = Config()
config.browser_user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
config.request_timeout = 15
config.fetch_images = False
config.memoize_articles = False

def create_secure_session():
    """Create a requests session with proper SSL configuration"""
    session = requests.Session()
    session.verify = certifi.where()
    
    # Configure modern cipher suites
    adapter = requests.adapters.HTTPAdapter(
        max_retries=3,
        pool_connections=100,
        pool_maxsize=100
    )
    
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

# Create secure session for reuse
secure_session = create_secure_session()

# Set up OpenAI API
openai.api_key = os.environ.get('OPENAI_API_KEY')

def ensure_nltk_resources():
    """Ensure all required NLTK resources are available"""
    required_resources = ['punkt']
    for resource in required_resources:
        try:
            nltk.data.find(f'tokenizers/{resource}')
        except LookupError:
            logger.info(f"Downloading NLTK resource: {resource}")
            try:
                nltk.download(resource, quiet=True)
            except Exception as e:
                logger.error(f"Failed to download NLTK resource {resource}: {e}")
                raise

# Initialize NLTK resources
ensure_nltk_resources()

# --- RSS Feed Configuration ---
RSS_FEEDS = {}
# Include PRIMARY_NEWS_FEEDS
RSS_FEEDS.update(PRIMARY_NEWS_FEEDS)

# Include SECONDARY_FEEDS if enabled
if SYSTEM_SETTINGS.get("use_secondary_feeds", True):
    for category, feeds in SECONDARY_FEEDS.items():
        if category not in RSS_FEEDS:
            RSS_FEEDS[category] = {}
        if isinstance(feeds, dict):
            RSS_FEEDS[category].update(feeds)
        else:
            logger.warning(f"Invalid feed structure in SECONDARY_FEEDS for category '{category}': {feeds}")

# Include SUPPLEMENTAL_FEEDS if enabled
if SYSTEM_SETTINGS.get("use_supplemental_feeds", False):
    for category, feeds in SUPPLEMENTAL_FEEDS.items():
        if category not in RSS_FEEDS:
            RSS_FEEDS[category] = {}
        if isinstance(feeds, dict):
            RSS_FEEDS[category].update(feeds)
        else:
            logger.warning(f"Invalid feed structure in SUPPLEMENTAL_FEEDS for category '{category}': {feeds}")

# Include BACKUP_RSS_FEEDS if primary sources fail
if SYSTEM_SETTINGS.get("use_backup_feeds", True):
    for category, feeds in BACKUP_RSS_FEEDS.items():
        if category not in RSS_FEEDS:
            RSS_FEEDS[category] = {}
        if isinstance(feeds, dict):
            RSS_FEEDS[category].update(feeds)
        else:
            logger.warning(f"Invalid feed structure in BACKUP_RSS_FEEDS for category '{category}': {feeds}")

def process_article_with_newspaper(url, retries=3, delay=2):
    """
    Process an article URL with Newspaper3k with retry logic
    
    Args:
        url (str): Article URL
        retries (int): Number of retries
        delay (int): Delay between retries in seconds
        
    Returns:
        tuple: (success, article_object or None, error_message or None)
    """
    for attempt in range(retries):
        try:
            article = Article(url, config=config)
            article.download()
            article.parse()
            
            # Only attempt NLP if we have enough content
            if len(article.text) >= 100:
                try:
                    article.nlp()
                except Exception as nlp_error:
                    logger.warning(f"NLP failed but parsing succeeded: {nlp_error}")
                    # Continue with parsed content even if NLP fails
            
            return True, article, None
            
        except ArticleException as e:
            if "Article html is empty" in str(e) and attempt < retries - 1:
                time.sleep(delay * (attempt + 1))
                continue
            return False, None, f"Newspaper error: {str(e)}"
            
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(delay * (attempt + 1))
                continue
            return False, None, f"Unexpected error: {str(e)}"
    
    return False, None, "Max retries exceeded"

def fetch_articles_from_all_feeds(max_articles_per_source=3):
    """Fetch articles from all configured feeds"""
    all_articles = []
    stats = {
        'total_attempts': 0,
        'successful_fetches': 0,
        'failed_fetches': 0,
        'empty_content': 0,
        'errors': {}
    }

    for category, feeds in RSS_FEEDS.items():
        logger.info(f"Fetching articles for category: {category}")
        for source_name, feed_url in feeds.items():
            logger.info(f"From: {source_name}")
            
            try:
                feed = feedparser.parse(feed_url)
                count = 0

                for entry in feed.entries:
                    if count >= max_articles_per_source:
                        break
                        
                    stats['total_attempts'] += 1
                    success = False
                    
                    # Try Newspaper3k first
                    success, article_obj, error = process_article_with_newspaper(entry.link)
                    
                    if success and article_obj:
                        all_articles.append({
                            'title': article_obj.title,
                            'url': article_obj.url,
                            'source': source_name,
                            'category': category,
                            'published': entry.get('published', "Unknown"),
                            'content': article_obj.text,
                            'summary': article_obj.summary if hasattr(article_obj, 'summary') else None,
                            'keywords': article_obj.keywords if hasattr(article_obj, 'keywords') else [],
                            'fetch_method': 'newspaper'
                        })
                        stats['successful_fetches'] += 1
                        count += 1
                        continue
                    
                    # Fallback to requests + BeautifulSoup
                    try:
                        headers = {'User-Agent': config.browser_user_agent}
                        response = secure_session.get(entry.link, headers=headers, timeout=config.request_timeout)
                        response.raise_for_status()
                        
                        soup = BeautifulSoup(response.text, 'html.parser')
                        
                        # Remove unwanted elements
                        for tag in soup.find_all(['script', 'style', 'nav', 'header', 'footer']):
                            tag.decompose()
                        
                        # Try to find article content
                        content = ""
                        article_tags = soup.find_all(['article', 'main', '[role="article"]', '.article-content'])
                        
                        if article_tags:
                            content = article_tags[0].get_text(separator="\n", strip=True)
                        else:
                            # Fallback to paragraphs
                            paragraphs = soup.find_all('p')
                            content = "\n".join(p.get_text().strip() for p in paragraphs 
                                              if len(p.get_text().strip()) > 50)
                        
                        if len(content) >= 100:
                            all_articles.append({
                                'title': entry.get('title', 'No Title'),
                                'url': entry.link,
                                'source': source_name,
                                'category': category,
                                'published': entry.get('published', "Unknown"),
                                'content': content,
                                'fetch_method': 'beautifulsoup'
                            })
                            stats['successful_fetches'] += 1
                            count += 1
                        else:
                            stats['empty_content'] += 1
                            
                    except Exception as e:
                        error_type = type(e).__name__
                        if error_type not in stats['errors']:
                            stats['errors'][error_type] = 0
                        stats['errors'][error_type] += 1
                        stats['failed_fetches'] += 1
                        logger.warning(f"Failed to fetch {entry.link}: {str(e)}")
                        
            except Exception as e:
                logger.error(f"Error processing feed {feed_url}: {str(e)}")
                continue

    # Log statistics
    logger.info("Article fetching statistics:")
    logger.info(f"Total attempts: {stats['total_attempts']}")
    logger.info(f"Successful fetches: {stats['successful_fetches']}")
    logger.info(f"Failed fetches: {stats['failed_fetches']}")
    logger.info(f"Empty content: {stats['empty_content']}")
    if stats['errors']:
        logger.info("Errors by type:")
        for error_type, count in stats['errors'].items():
            logger.info(f"  {error_type}: {count}")

    return all_articles

def summarize_articles(articles: List[Dict], max_summary_length=150, min_summary_length=50) -> List[Dict]:
    """
    Summarize articles with OpenAI, focusing on the most important ones.
    
    Args:
        articles: List of article dictionaries
        
    Returns:
        List of articles with added summaries
    """
    if not articles:
        return []

    logger.info(f"Starting summarization of {len(articles)} articles")
    
    # Sort articles by importance score and recency
    sorted_articles = sorted(
        articles,
        key=lambda a: (
            a.get('importance_score', 0),  # Primary sort by importance
            a.get('published', datetime.now())  # Secondary sort by date
        ),
        reverse=True
    )

    # Take only top N articles based on EMAIL_SETTINGS
    max_articles = EMAIL_SETTINGS.get('max_articles_total', 15)
    articles_to_process = sorted_articles[:max_articles]
    
    logger.info(f"Selected {len(articles_to_process)} most important articles out of {len(articles)} total")
    
    summarized = []
    summarization_stats = {
        'total': len(articles_to_process),
        'newspaper': 0,
        'openai': 0,
        'truncation': 0,
        'failed': 0
    }
    
    for i, article in enumerate(articles_to_process):
        try:
            title = article.get('title', '')
            content = article.get('content', '')
            
            if not content or len(content.strip()) < 100:
                logger.warning(f"Insufficient content for article: {title}")
                summarization_stats['failed'] += 1
                continue
            
            # Use existing Newspaper3k summary if available
            if article.get('summary') and article.get('fetch_method') == 'newspaper':
                logger.debug(f"Using existing Newspaper summary for: {title}")
                summarization_stats['newspaper'] += 1
                summarized.append(article)
                continue
            
            # Try Newspaper3k summarization first
            if SYSTEM_SETTINGS.get('use_newspaper3k', True):
                try:
                    article_obj = Article('', config=config)
                    article_obj.text = content
                    article_obj.title = title
                    article_obj.nlp()
                    
                    if article_obj.summary and len(article_obj.summary) >= 100:
                        article['summary'] = article_obj.summary
                        article['summary_method'] = 'newspaper'
                        article['keywords'] = article_obj.keywords
                        summarization_stats['newspaper'] += 1
                        summarized.append(article)
                        continue
                        
                except Exception as e:
                    logger.warning(f"Newspaper summarization failed for {title}: {str(e)}")
            
            # Fall back to OpenAI summarization
            summary = summarize_with_openai(content, title)
            if summary:
                article['summary'] = summary
                article['summary_method'] = 'openai'
                summarization_stats['openai'] += 1
                summarized.append(article)
            else:
                # Last resort: truncate long content
                article['summary'] = content[:1000] + "..."
                article['summary_method'] = 'truncation'
                summarization_stats['truncation'] += 1
                summarized.append(article)
            
            # Log progress periodically
            if (i+1) % 5 == 0 or i == len(articles_to_process) - 1:
                logger.info(f"Summarized {i+1}/{len(articles_to_process)} articles")
                
        except Exception as e:
            logger.error(f"Failed to process article {article.get('title', 'Unknown')}: {str(e)}")
            summarization_stats['failed'] += 1
            continue
    
    # Log summarization statistics
    logger.info("\nSummarization Statistics:")
    logger.info(f"Total articles processed: {summarization_stats['total']}")
    logger.info(f"Newspaper3k summaries: {summarization_stats['newspaper']}")
    logger.info(f"OpenAI summaries: {summarization_stats['openai']}")
    logger.info(f"Truncated summaries: {summarization_stats['truncation']}")
    logger.info(f"Failed articles: {summarization_stats['failed']}")
    
    return summarized

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
    if not openai.api_key:
        logger.warning("OpenAI API key not set. Skipping AI summarization.")
        return None
    
    # Prepare the text for summarization
    context = f"Title: {title}\n\nContent: {text}" if title else text
    
    # Truncate if too long for API call
    if len(context) > 15000:
        context = context[:15000] + "..."
    
    # Define the summarization prompt
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
                time.sleep(retry_delay * attempts)  # Exponential backoff
            else:
                logger.error(f"Failed to get OpenAI summary after {max_retries} attempts")
                return None

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
