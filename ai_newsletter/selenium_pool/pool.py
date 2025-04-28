import atexit
import logging
import os
import threading
import time
from collections import defaultdict
from contextlib import contextmanager
from queue import Queue, Empty
from typing import Optional, Dict
import psutil

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import WebDriverException, TimeoutException

logger = logging.getLogger(__name__)

# Default pool size for the WebDriver pool
_POOL_SIZE = 3

# List of user agents to rotate through for anti-bot detection
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
]

class DriverWrapper:
    def __init__(self, driver: webdriver.Chrome):
        self.driver = driver
        self.last_used = time.time()
        self.total_requests = 0
        self.errors = 0
        self.creation_time = time.time()

    def increment_errors(self):
        self.errors += 1

    def is_healthy(self) -> bool:
        # Check various health indicators
        if self.errors >= 3:
            return False
        
        if time.time() - self.creation_time > 1800:  # 30 minutes max lifetime
            return False

        try:
            # Basic health check
            self.driver.current_url
            handles = self.driver.window_handles
            
            # Memory check (if process still exists)
            if hasattr(self.driver.service.process, 'pid'):
                try:
                    process = psutil.Process(self.driver.service.process.pid)
                    mem_usage = process.memory_percent()
                    if mem_usage > 10.0:  # If using more than 10% of system memory
                        return False
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    return False
            
            return len(handles) > 0
        except Exception:
            return False

class WebDriverPool:
    _instance = None
    _lock = threading.Lock()
    _POOL_SIZE = 3  # Default pool size, accessible as a class variable

    def __init__(self, pool_size: int = 3):
        self.pool_size = pool_size
        WebDriverPool._POOL_SIZE = pool_size  # Update class variable when instance is created
        self.available_drivers: Queue = Queue()
        self.active_drivers: Dict[int, DriverWrapper] = {}
        self.domain_last_access: Dict[str, float] = defaultdict(float)
        self.domain_lock = threading.Lock()
        self.rate_limit_delay = 2.0  # Seconds between requests to same domain
        self._initialize_pool()
        atexit.register(self.cleanup)

    @classmethod
    def get_instance(cls, pool_size: int = 3) -> 'WebDriverPool':
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(pool_size)
        return cls._instance

    def _create_driver(self) -> Optional[DriverWrapper]:
        try:
            chrome_options = Options()
            chrome_options.add_argument('--headless=new')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--disable-software-rasterizer')
            chrome_options.add_argument('--disable-infobars')
            chrome_options.add_argument('--disable-extensions')
            chrome_options.add_argument('--disable-logging')
            chrome_options.add_argument('--single-process')
            chrome_options.add_argument('--ignore-certificate-errors')
            chrome_options.add_argument('--log-level=3')
            chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
            
            # Add random user agent
            import random
            user_agent = random.choice(USER_AGENTS)
            chrome_options.add_argument(f'--user-agent={user_agent}')
            
            # Set resource limits
            chrome_options.add_argument('--memory-pressure-off')
            chrome_options.add_argument('--js-flags="--max-old-space-size=500"')

            service = Service(executable_path=os.getenv('CHROMEWEBDRIVER'), log_output=os.devnull)
            driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # Set reasonable timeouts
            driver.set_page_load_timeout(30)
            driver.set_script_timeout(30)
            
            return DriverWrapper(driver)
        except Exception as e:
            logger.error(f"Failed to create new WebDriver: {e}")
            return None

    def _initialize_pool(self):
        """Initialize the pool with the specified number of drivers."""
        for _ in range(self.pool_size):
            driver = self._create_driver()
            if driver is not None:
                self.available_drivers.put(driver)

    def _enforce_rate_limit(self, domain: Optional[str]):
        """Enforce rate limiting for specific domains."""
        if domain:
            with self.domain_lock:
                last_access = self.domain_last_access[domain]
                current_time = time.time()
                if current_time - last_access < self.rate_limit_delay:
                    sleep_time = self.rate_limit_delay - (current_time - last_access)
                    time.sleep(sleep_time)
                self.domain_last_access[domain] = time.time()

    def get_driver(self, timeout: int = 30, domain: Optional[str] = None) -> Optional[DriverWrapper]:
        """Get a driver from the pool with domain-aware rate limiting."""
        self._enforce_rate_limit(domain)
        
        end_time = time.time() + timeout
        while True:
            try:
                remaining = max(0, end_time - time.time())
                driver = self.available_drivers.get(timeout=remaining)
                
                # Health check and replacement if needed
                if not driver.is_healthy():
                    logger.warning("Unhealthy driver detected, creating replacement")
                    try:
                        driver.driver.quit()
                    except Exception:
                        pass
                    driver = self._create_driver()
                    if driver is None:
                        if time.time() < end_time:
                            continue  # Try again if there's time left
                        raise WebDriverException("Failed to create replacement driver")
                
                driver.last_used = time.time()
                driver.total_requests += 1
                return driver
                
            except Empty:
                if time.time() < end_time:
                    # Try to create a new driver if there's time left
                    driver = self._create_driver()
                    if driver is not None:
                        return driver
                    time.sleep(0.1)  # Short sleep before retry
                    continue
                logger.error("WebDriver pool exhausted")
                raise WebDriverException("WebDriver pool exhausted")
            except Exception as e:
                if time.time() < end_time:
                    time.sleep(0.1)  # Short sleep before retry
                    continue
                raise

    def return_driver(self, driver: DriverWrapper):
        """Return a driver to the pool."""
        try:
            if driver.is_healthy():
                # Clear any previous timeouts
                driver.driver.set_page_load_timeout(30)
                driver.driver.set_script_timeout(30)
                self.available_drivers.put(driver)
            else:
                logger.info("Replacing unhealthy driver")
                try:
                    driver.driver.quit()
                except Exception:
                    pass
                new_driver = self._create_driver()
                if new_driver is not None:
                    self.available_drivers.put(new_driver)
        except Exception as e:
            logger.error(f"Error returning driver to pool: {e}")
            # Create a new driver if return failed
            new_driver = self._create_driver()
            if new_driver is not None:
                self.available_drivers.put(new_driver)

    def cleanup(self):
        """Clean up all drivers in the pool."""
        logger.info("Cleaning up WebDriver pool")
        cleaned = []
        while True:
            try:
                driver = self.available_drivers.get_nowait()
                cleaned.append(driver)
                try:
                    driver.driver.quit()
                except Exception as e:
                    logger.error(f"Error cleaning up driver: {e}")
            except Empty:
                break
        
        # Clear the queue and domain access times
        self.domain_last_access.clear()
        
        # Reinitialize the pool if needed
        if self._instance is not None:
            self._initialize_pool()

# Module-level interface
_pool: Optional[WebDriverPool] = None

def initialize_pool(pool_size: int = 3):
    """Initialize the WebDriver pool with the specified size."""
    global _pool
    _pool = WebDriverPool.get_instance(pool_size)

def close_pool():
    """Close all drivers in the pool."""
    global _pool
    if _pool is not None:
        _pool.cleanup()
        _pool = None

@contextmanager
def get_driver(timeout: int = 30, domain: Optional[str] = None):
    """Context manager for getting and returning a driver from the pool."""
    if _pool is None:
        initialize_pool()
    
    driver = None
    try:
        driver = _pool.get_driver(timeout, domain)
        yield driver.driver
    finally:
        if driver is not None:
            _pool.return_driver(driver)
