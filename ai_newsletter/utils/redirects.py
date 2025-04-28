from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException
import time
import random
from ai_newsletter.logging_cfg.logger import setup_logger, FETCH_METRICS  # Fix import path

# Get the logger
logger = setup_logger()

# Global WebDriver instance for reuse
_driver = None
_driver_creation_time = None
_driver_request_count = 0

def get_webdriver(force_new=False, max_age_minutes=30, max_requests=50):
    """
    Get or create a WebDriver instance with anti-detection measures
    
    Args:
        force_new (bool): Force creation of a new instance
        max_age_minutes (int): Maximum age of driver instance in minutes
        max_requests (int): Maximum requests before recycling driver
    """
    global _driver, _driver_creation_time, _driver_request_count
    
    current_time = time.time()
    create_new = (
        _driver is None or
        force_new or
        (_driver_creation_time and (current_time - _driver_creation_time) / 60 > max_age_minutes) or
        (_driver_request_count >= max_requests)
    )
    
    if create_new:
        if _driver is not None:
            try:
                _driver.quit()
            except Exception as e:
                logger.warning(f"Error closing existing WebDriver: {e}")
        
        # Configure ChromeOptions with anti-detection measures
        options = Options()
        
        # Random user agent
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2.1 Safari/605.1.15'
        ]
        user_agent = random.choice(user_agents)
        options.add_argument(f'--user-agent={user_agent}')
        
        # Basic configuration
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--ignore-certificate-errors")
        
        # Anti-detection measures
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Additional anti-bot measures
        options.add_argument("--disable-infobars")
        options.add_argument("--disable-browser-side-navigation")
        
        # Performance optimizations
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-extensions")
        
        # Random window size to appear more natural
        window_sizes = [(1920, 1080), (1366, 768), (1536, 864), (1440, 900)]
        width, height = random.choice(window_sizes)
        options.add_argument(f"--window-size={width},{height}")
        
        try:
            _driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
            
            # Additional anti-detection JavaScript
            _driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                "userAgent": user_agent,
                "platform": "Windows",
                "acceptLanguage": "en-US,en;q=0.9"
            })
            
            # Execute stealth JS
            _driver.execute_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """)
            
            _driver_creation_time = current_time
            _driver_request_count = 0
            FETCH_METRICS['browser_instances'] += 1
            logger.debug("Created new WebDriver instance")
            
        except Exception as e:
            logger.error(f"Failed to create WebDriver: {e}")
            return None
    
    if _driver is not None:
        _driver_request_count += 1
        FETCH_METRICS['driver_reuse_count'] += 1
    
    return _driver

def resolve_google_redirect_selenium(url, max_retries=2):
    """
    Resolve Google News redirect URLs to their final destination
    
    Args:
        url (str): The URL to resolve
        max_retries (int): Maximum number of retry attempts
        
    Returns:
        str: The resolved URL, or original URL if resolution fails
    """
    if not url or 'news.google.com' not in url:
        return url
    
    for attempt in range(max_retries):
        try:
            # Get a WebDriver instance
            driver = get_webdriver()
            if not driver:
                logger.error("Failed to create WebDriver for redirect resolution")
                return url
            
            try:
                # Set shorter timeout for redirects
                driver.set_page_load_timeout(10)
                
                # Load the page
                driver.get(url)
                
                # Wait for redirect with dynamic timeout
                timeout = random.uniform(1.5, 3)
                try:
                    # Wait for URL to change or page to stabilize
                    WebDriverWait(driver, timeout).until(
                        lambda d: d.current_url != url or
                        d.execute_script("return document.readyState") == "complete"
                    )
                    # Small additional wait for any final redirects
                    time.sleep(0.5)
                except TimeoutException:
                    pass  # URL might not change if there's no redirect
                
                final_url = driver.current_url
                
                # Only return if we got a different, valid URL
                if final_url and final_url != url and not 'news.google.com' in final_url:
                    logger.debug(f"Successfully resolved redirect: {url} -> {final_url}")
                    return final_url
                    
            finally:
                # Don't quit the driver, it will be reused
                pass
                
        except Exception as e:
            logger.warning(f"Redirect resolution attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
    
    return url

def cleanup():
    """Clean up resources when done"""
    global _driver
    if _driver is not None:
        try:
            _driver.quit()
        except:
            pass
        _driver = None

