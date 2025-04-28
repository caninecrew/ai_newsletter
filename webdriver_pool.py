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


# Pool settings - Adjusted for GitHub Actions Runner (4 vCPU)
_POOL_SIZE = 3  # Keep slightly below vCPU count
_pool = Queue(maxsize=_POOL_SIZE)

# User Agents to rotate
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0", # Example Firefox UA
]

def _create_driver() -> webdriver.Chrome:
    """Creates a new WebDriver instance with specified options for GitHub Actions."""
    attempt = 0
    max_attempts = 3
    while attempt < max_attempts:
        try:
            opts = webdriver.ChromeOptions()
            # --- GitHub Actions Specific Flags ---
            opts.add_argument("--headless=new")      # Modern headless
            opts.add_argument("--disable-dev-shm-usage") # Overcome limited resource problems
            opts.add_argument("--no-sandbox")        # Runner is already sandboxed
            # opts.add_argument("--single-process") # May help on low-resource, test if needed
            opts.page_load_strategy = "eager"       # Don't wait for full page load (ads, trackers)
            # -------------------------------------
            opts.add_argument("--disable-gpu")
            opts.add_argument("--window-size=1920,1080")

            # --- Masking & Performance Flags ---
            user_agent = random.choice(USER_AGENTS)
            opts.add_argument(f"--user-agent={user_agent}")
            opts.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
            opts.add_experimental_option('useAutomationExtension', False)
            opts.add_argument("--disable-blink-features=AutomationControlled")
            opts.add_argument('--log-level=3')
            opts.add_argument("--blink-settings=imagesEnabled=false") # Disable images
            opts.add_argument("--disable-extensions")             # Disable extensions
            # -----------------------------------

            # Service configuration
            try:
                os.environ['WDM_LOG_LEVEL'] = '0' # Suppress WebDriver Manager logs
                # Check if chromedriver is already available in PATH (common in GH Actions)
                chromedriver_path = os.getenv("CHROMEWEBDRIVER") # GH Actions often sets this
                if chromedriver_path and os.path.exists(os.path.join(chromedriver_path, 'chromedriver')):
                     logger.info("Using chromedriver from environment variable CHROMEWEBDRIVER")
                     service = Service(executable_path=os.path.join(chromedriver_path, 'chromedriver'))
                else:
                     logger.info("CHROMEWEBDRIVER not found or invalid, using WebDriverManager to install.")
                     service = Service(ChromeDriverManager().install())

                driver = webdriver.Chrome(service=service, options=opts)
                logger.info("WebDriver instance created successfully.")

                # --- Set Timeouts --- 
                driver.set_page_load_timeout(30) # Increased timeout
                driver.set_script_timeout(30)  # Increased timeout
                # --------------------

                driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                return driver
            except Exception as driver_exc:
                 logger.error(f"Error creating WebDriver service or instance: {driver_exc}")
                 raise

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
