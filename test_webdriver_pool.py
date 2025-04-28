import pytest
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_pool import initialize_pool, close_pool, get_driver
from urllib.parse import urlparse

@pytest.fixture(autouse=True)
def cleanup_after_test():
    """Ensure pool is cleaned up after each test."""
    try:
        yield
    finally:
        close_pool()

def test_basic_pool_functionality():
    """Test basic pool initialization and driver acquisition."""
    initialize_pool(pool_size=2)
    with get_driver(timeout=10) as driver:
        assert driver is not None
        driver.get("https://example.com")
        assert "Example Domain" in driver.title

def test_concurrent_access():
    """Test concurrent access to the pool without exhaustion."""
    initialize_pool(pool_size=2)
    
    def fetch_page(url):
        domain = urlparse(url).netloc
        for attempt in range(2):
            try:
                with get_driver(domain=domain, timeout=10) as driver:
                    driver.get(url)
                    return driver.title
            except (TimeoutException, WebDriverException) as e:
                if attempt == 1:
                    return f"Error: {str(e)}"
                time.sleep(0.5)
    
    urls = ["https://example.com"] * 3
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(fetch_page, url) for url in urls]
        results = []
        for future in as_completed(futures):
            try:
                result = future.result(timeout=15)
                results.append(result)
            except Exception as e:
                results.append(f"Error: {str(e)}")
    
    successful = [r for r in results if "Error" not in r]
    assert len(successful) > 0, f"No successful results: {results}"
    assert any("Example Domain" in r for r in successful)

def test_health_checks():
    """Test that unhealthy drivers are replaced."""
    initialize_pool(pool_size=1)
    
    # First request - should work
    with get_driver(timeout=10) as driver:
        driver.get("https://example.com")
        title = driver.title
        assert "Example Domain" in title
    
    # Force the driver to become "unhealthy"
    with get_driver(timeout=10) as driver:
        driver.quit()
    
    # Next request should get a new, healthy driver
    with get_driver(timeout=10) as driver:
        driver.get("https://example.com")
        assert "Example Domain" in driver.title

def test_rate_limiting():
    """Test domain-specific rate limiting."""
    initialize_pool(pool_size=2)
    domain = "example.com"
    start_time = time.time()
    
    results = []
    for _ in range(2):  # Reduced to 2 requests to speed up test
        with get_driver(domain=domain, timeout=10) as driver:
            driver.get("https://example.com")
            results.append(driver.title)
    
    duration = time.time() - start_time
    min_expected_duration = 2.0  # One rate limit delay
    
    assert duration >= min_expected_duration, f"Rate limiting not enforced. Took {duration}s"
    assert all("Example Domain" in r for r in results), f"Invalid results: {results}"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])