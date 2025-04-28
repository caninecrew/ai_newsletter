from newspaper import Article, ArticleException
from requests_html import HTMLSession
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
import requests
import random
import time
import logging
from ai_newsletter.logging_cfg.logger import setup_logger, FETCH_METRICS
import certifi

# Get the logger
logger = setup_logger()

# User agent rotation
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2.1 Safari/605.1.15'
]

def create_session():
    """Create a requests session with rotating user agents, proper security, and retry settings."""
    session = requests.Session()
    
    # Use certifi's CA bundle for SSL verification
    session.verify = certifi.where()
    
    # Configure retry strategy with exponential backoff
    retry_strategy = requests.adapters.Retry(
        total=3,  # total number of retries
        backoff_factor=0.5,  # wait 0.5s * (2 ** retry) between retries
        status_forcelist=[429, 500, 502, 503, 504],  # retry on these status codes
        allowed_methods=["GET", "HEAD"]  # only retry safe methods
    )
    
    # Configure connection pooling and timeouts
    adapter = requests.adapters.HTTPAdapter(
        max_retries=retry_strategy,
        pool_connections=20,  # number of urllib3 connection pools to cache
        pool_maxsize=20,  # maximum number of connections to save in the pool
        pool_block=False  # don't block when pool is depleted, raise error instead
    )
    
    # Mount adapter for both HTTP and HTTPS
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    # Set secure headers with rotating user agent
    session.headers.update({
        'User-Agent': random.choice(USER_AGENTS),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'cross-site',
        'Sec-Fetch-User': '?1'
    })
    
    return session

def create_html_session():
    """Create a requests-html session with same security settings as regular session."""
    session = HTMLSession()
    
    # Configure the underlying requests.Session with same settings
    base_session = create_session()
    session.headers = base_session.headers
    session.verify = base_session.verify
    
    # Add specific headers for JavaScript-enabled requests
    session.headers.update({
        'Sec-Fetch-Mode': 'no-cors',  # Different for JS requests
    })
    
    return session

def resolve_google_redirect(url, max_retries=2, timeout=10):
    """
    Resolve Google News redirect URLs to their final destination using requests.
    
    Args:
        url (str): The URL to resolve
        max_retries (int): Maximum number of retry attempts
        timeout (int): Request timeout in seconds
        
    Returns:
        str: The resolved URL, or original URL if resolution fails
    """
    if not url or 'news.google.com' not in url:
        return url
    
    session = create_session()
    
    for attempt in range(max_retries):
        try:
            # First try with regular requests
            response = session.get(url, timeout=timeout, allow_redirects=True)
            response.raise_for_status()
            
            # Check if we got redirected away from Google News
            if response.url and response.url != url and 'news.google.com' not in response.url:
                logger.debug(f"Successfully resolved redirect with requests: {url} -> {response.url}")
                return response.url
                
            # If regular requests didn't work, try with requests-html
            if attempt == max_retries - 1:
                try:
                    html_session = HTMLSession()
                    r = html_session.get(url, timeout=timeout)
                    r.html.render(timeout=10, sleep=1)  # Short render timeout
                    
                    # Check for meta refresh redirects
                    for meta in r.html.find('meta[http-equiv="refresh"]'):
                        content = meta.attrs.get('content', '')
                        if 'url=' in content.lower():
                            final_url = content.split('url=', 1)[1].strip('"\'')
                            if final_url and 'news.google.com' not in final_url:
                                logger.debug(f"Resolved redirect via meta refresh: {url} -> {final_url}")
                                return final_url
                    
                    # Check final URL after JavaScript execution
                    if r.url and r.url != url and 'news.google.com' not in r.url:
                        logger.debug(f"Resolved redirect with requests-html: {url} -> {r.url}")
                        return r.url
                        
                except Exception as e:
                    logger.warning(f"requests-html resolution failed: {e}")
                    
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
                
        except Exception as e:
            logger.warning(f"Redirect resolution attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
    
    return url

def extract_article_content(url, timeout=15):
    """
    Extract article content using newspaper3k with fallback to requests-html.
    
    Args:
        url (str): The article URL to process
        timeout (int): Request timeout in seconds
        
    Returns:
        dict: Article data including title, text, and metadata
    """
    try:
        # Try newspaper3k first
        article = Article(url)
        article.download()
        article.parse()
        
        # Basic validation of extracted content
        if article.text and len(article.text.strip()) > 150:
            return {
                'title': article.title,
                'text': article.text,
                'authors': article.authors,
                'publish_date': article.publish_date,
                'top_image': article.top_image,
                'meta_description': article.meta_description,
                'fetch_method': 'newspaper'
            }
    except ArticleException as e:
        logger.warning(f"newspaper3k extraction failed for {url}: {e}")
    except Exception as e:
        logger.warning(f"Unexpected error during newspaper3k extraction: {e}")
    
    # Fallback to requests-html
    try:
        session = HTMLSession()
        r = session.get(url, timeout=timeout)
        
        # Try to find article content
        content = ""
        selectors = [
            'article', 'main', '[role="article"]', '.article-content',
            '.post-content', '.entry-content', '#article-body'
        ]
        
        for selector in selectors:
            elements = r.html.find(selector)
            if elements:
                content = elements[0].text
                if len(content.strip()) > 150:
                    break
        
        # Fallback to p tags if no content found
        if not content:
            paragraphs = r.html.find('p')
            content = '\n'.join(p.text for p in paragraphs if len(p.text.strip()) > 50)
        
        if content and len(content.strip()) > 150:
            return {
                'title': r.html.find('title')[0].text if r.html.find('title') else None,
                'text': content,
                'authors': None,  # Could extract but would need custom selectors
                'publish_date': None,  # Could extract but would need custom parsing
                'meta_description': r.html.find('meta[name="description"]')[0].attrs['content'] 
                                 if r.html.find('meta[name="description"]') else None,
                'fetch_method': 'requests-html'
            }
            
    except Exception as e:
        logger.warning(f"requests-html extraction failed for {url}: {e}")
    
    return None

def cleanup():
    """Clean up resources when done"""
    global _driver
    if _driver is not None:
        try:
            _driver.quit()
        except:
            pass
        _driver = None

