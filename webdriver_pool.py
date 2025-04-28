# webdriver_pool.py
import logging
from queue import Queue, Empty, Full
from contextlib import contextmanager
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import random
import time
import os

# Configure logger for the pool
# Use the main logger setup from logger_config
# Assuming logger_config.py sets up a root logger or a specific one we can get
try:
    from logger_config import setup_logger
    logger = setup_logger('webdriver_pool') # Get a logger specific to this module
except ImportError:
    # Fallback basic logging if logger_config is not available initially
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger('webdriver_pool')


# Pool settings
_POOL_SIZE = 4  # Adjust based on memory/CPU resources
_pool = Queue(maxsize=_POOL_SIZE)

# User Agents to rotate
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0", # Example Firefox UA
]

def _create_driver() -> webdriver.Chrome:
    """Creates a new WebDriver instance with specified options."""
    attempt = 0
    max_attempts = 3
    while attempt < max_attempts:
        try:
            opts = webdriver.ChromeOptions()
            opts.add_argument("--headless=new")
            opts.add_argument("--no-sandbox")
            opts.add_argument("--disable-dev-shm-usage")
            opts.add_argument("--disable-gpu") # Often needed for headless mode
            opts.add_argument("--window-size=1920,1080") # Set a common window size

            # Masking options
            user_agent = random.choice(USER_AGENTS)
            opts.add_argument(f"--user-agent={user_agent}")
            opts.add_experimental_option("excludeSwitches", ["enable-automation"])
            opts.add_experimental_option('useAutomationExtension', False)
            opts.add_argument("--disable-blink-features=AutomationControlled") # More robust way to disable automation detection

            # Suppress console logs from Chrome/WebDriver
            opts.add_experimental_option('excludeSwitches', ['enable-logging'])
            opts.add_argument('--log-level=3') # Suppress logs further

            # Service configuration (optional, WebDriverManager usually handles this)
            try:
                # Ensure WebDriver Manager logs are suppressed or managed if needed
                # Example: Redirect stderr temporarily if it's too noisy
                # Note: This might require more complex handling depending on the environment
                os.environ['WDM_LOG_LEVEL'] = '0' # Suppress WebDriver Manager logs

                service = Service(ChromeDriverManager().install())
                driver = webdriver.Chrome(service=service, options=opts)
                logger.info("WebDriver instance created successfully.")
                # Optional: Execute script to further hide automation state
                driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                return driver
            except Exception as driver_exc:
                 logger.error(f"Error creating WebDriver service or instance: {driver_exc}")
                 raise # Re-raise after logging

        except Exception as e:
            attempt += 1
            logger.error(f"Attempt {attempt}/{max_attempts} failed to create WebDriver: {e}")
            if attempt >= max_attempts:
                logger.critical("Max attempts reached. Failed to create WebDriver.")
                raise  # Re-raise the last exception
            time.sleep(2 * attempt) # Exponential backoff

# --- Pool Management ---
def _initialize_pool():
    """Fills the pool with WebDriver instances."""
    logger.info(f"Initializing WebDriver pool with size {_POOL_SIZE}...")
    drivers_added = 0
    for _ in range(_POOL_SIZE):
        try:
            driver = _create_driver()
            if driver:
                _pool.put(driver)
                drivers_added += 1
        except Exception as e:
            logger.error(f"Failed to add driver to pool during initialization: {e}")
            # If initialization fails critically for one driver, maybe stop? Or log and continue?
            # For now, log and continue trying to fill the pool.
    logger.info(f"WebDriver pool initialized with {drivers_added} instances.")

@contextmanager
def get_driver():
    """Provides a WebDriver instance from the pool."""
    driver = None
    try:
        driver = _pool.get(timeout=60) # Wait up to 60 seconds for a driver
        logger.debug(f"Acquired driver. Pool size: {_pool.qsize()}")
        yield driver
    except Empty:
        logger.error("Timeout waiting for available WebDriver instance from the pool.")
        # Decide how to handle pool exhaustion. Raising an error might be best.
        raise TimeoutError("WebDriver pool exhausted or initialization failed.")
    except Exception as e:
        logger.error(f"Error getting driver from pool: {e}")
        # If the driver instance itself caused an error upon retrieval, discard it
        if driver:
            _discard_driver(driver)
            driver = None # Ensure it's not put back
        raise # Re-raise the exception
    finally:
        if driver:
            try:
                # Basic health check: Check if browser is still running
                _ = driver.window_handles # Accessing this property checks if the browser is still responsive
                _pool.put(driver)
                logger.debug(f"Returned driver to pool. Pool size: {_pool.qsize()}")
            except Exception as e:
                logger.warning(f"WebDriver instance seems unhealthy, discarding: {e}")
                _discard_driver(driver)


def _discard_driver(driver):
    """Safely quits a driver and attempts to replace it in the pool."""
    try:
        driver.quit()
        logger.info("Quit unhealthy WebDriver instance.")
    except Exception as e:
        logger.error(f"Error quitting WebDriver instance: {e}")
    finally:
        # Try to replenish the pool asynchronously or in a separate thread/process
        # to avoid blocking the main flow. For simplicity here, doing it synchronously.
        try:
            logger.info("Attempting to replenish WebDriver pool...")
            new_driver = _create_driver()
            if new_driver:
                _pool.put(new_driver, block=False) # Add without blocking if pool is full
                logger.info("Replenished pool with a new WebDriver instance.")
        except Full:
             logger.warning("Pool is full, cannot replenish discarded driver immediately.")
        except Exception as e:
            logger.error(f"Failed to replenish WebDriver pool: {e}")


def shutdown_pool():
    """Shuts down all WebDriver instances in the pool."""
    logger.info("Shutting down WebDriver pool...")
    drained_drivers = 0
    while not _pool.empty():
        try:
            driver = _pool.get_nowait()
            driver.quit()
            drained_drivers += 1
        except Empty:
            break # Pool is empty
        except Exception as e:
            logger.error(f"Error quitting driver during shutdown: {e}")
            # Continue draining even if one driver fails to quit
    logger.info(f"WebDriver pool shut down. {drained_drivers} instances quit.")

# Initialize the pool when the module is imported
_initialize_pool()

# Optional: Register shutdown function to be called on exit
import atexit
atexit.register(shutdown_pool)
