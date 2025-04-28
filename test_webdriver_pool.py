import pytest
import time
from concurrent.futures import ThreadPoolExecutor
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_pool import initialize_pool, close_pool, get_driver
from urllib.parse import urlparse

def test_basic_pool_functionality():
    """Test basic pool initialization and driver acquisition."""
    initialize_pool(pool_size=2)
    try:
        with get_driver() as driver:
            assert driver is not None
            driver.get("https://example.com")
            assert "Example Domain" in driver.title
    finally:
        close_pool()

def test_concurrent_access():
    """Test concurrent access to the pool without exhaustion."""
    initialize_pool(pool_size=2)
    
    def fetch_page(url):
        domain = urlparse(url).netloc
        try:
            with get_driver(domain=domain) as driver:
                driver.get(url)
                return driver.title
        except (TimeoutException, WebDriverException) as e:
            return f"Error: {str(e)}"
    
    try:
        urls = [
            "https://example.com",
            "https://httpbin.org/html",
            "https://httpstat.us/200"
        ]
        
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(fetch_page, url) for url in urls]
            results = [f.result() for f in futures]
        
        assert any("Example Domain" in result for result in results)
        assert len([r for r in results if "Error" not in r]) >= 2
        
    finally:
        close_pool()

def test_health_checks():
    """Test that unhealthy drivers are replaced."""
    initialize_pool(pool_size=1)
    try:
        # First request - should work
        with get_driver() as driver:
            driver.get("https://example.com")
            assert "Example Domain" in driver.title
        
        # Force the driver to become "unhealthy" by making it timeout
        with pytest.raises(TimeoutException):
            with get_driver() as driver:
                driver.set_page_load_timeout(1)  # Very short timeout
                driver.get("https://httpbin.org/delay/5")
        
        # Next request should get a new, healthy driver
        with get_driver() as driver:
            driver.get("https://example.com")
            assert "Example Domain" in driver.title
            
    finally:
        close_pool()

def test_rate_limiting():
    """Test domain-specific rate limiting."""
    initialize_pool(pool_size=2)
    try:
        domain = "httpbin.org"
        start_time = time.time()
        
        # Make 3 quick requests to the same domain
        results = []
        for _ in range(3):
            with get_driver(domain=domain) as driver:
                driver.get("https://httpbin.org/html")
                results.append(driver.title)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should take at least 4 seconds due to rate limiting (2s between requests)
        assert duration >= 4.0
        assert all(isinstance(r, str) and len(r) > 0 for r in results)
        
    finally:
        close_pool()

if __name__ == "__main__":
    pytest.main([__file__, "-v"])