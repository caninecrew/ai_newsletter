import logging
import os
import sys
from concurrent_log_handler import ConcurrentRotatingFileHandler
from datetime import datetime, timedelta
from typing import Dict, List, Any
import pytz

# Define default timezone constant
DEFAULT_TZ = pytz.timezone('America/Chicago')  # From SYSTEM_SETTINGS['default_timezone']

# Expand metrics tracking
FETCH_METRICS = {
    'sources_checked': 0,
    'successful_sources': 0,
    'failed_sources': [],
    'empty_sources': [],
    'total_articles': 0,
    'duplicate_articles': 0,
    'processing_time': 0,
    'source_statistics': {},
    'driver_reuse_count': 0,
    'browser_instances': 0,
    'average_article_fetch_time': 0,
    'failed_fetches': [],
    'slow_sources': [],
    'article_ages': {
        'last_hour': 0,
        'today': 0,
        'yesterday': 0,
        'this_week': 0,
        'older': 0
    },
    'content_statistics': {
        'total_length': 0,
        'average_length': 0
    },
    'error_counts': {
        'parse_errors': 0,
        'fetch_errors': 0,
        'timeout_errors': 0
    }
}

def update_metrics(metric_name: str, value: Any) -> None:
    """Update the metrics dictionary with a new value."""
    if isinstance(value, (int, float)):
        if metric_name not in FETCH_METRICS:
            FETCH_METRICS[metric_name] = 0
        FETCH_METRICS[metric_name] += value
    elif isinstance(value, (list, set)):
        if metric_name not in FETCH_METRICS:
            FETCH_METRICS[metric_name] = []
        FETCH_METRICS[metric_name].extend(value)
    elif isinstance(value, dict):
        if metric_name not in FETCH_METRICS:
            FETCH_METRICS[metric_name] = {}
        FETCH_METRICS[metric_name].update(value)
    else:
        FETCH_METRICS[metric_name] = value

def get_metrics() -> Dict:
    """Get the current metrics."""
    return FETCH_METRICS

def reset_metrics() -> None:
    """Reset all metrics to their default values."""
    global FETCH_METRICS
    FETCH_METRICS = {
        'sources_checked': 0,
        'successful_sources': 0,
        'failed_sources': [],
        'empty_sources': [],
        'total_articles': 0,
        'duplicate_articles': 0,
        'processing_time': 0,
        'source_statistics': {},
        'driver_reuse_count': 0,
        'browser_instances': 0,
        'average_article_fetch_time': 0,
        'failed_fetches': [],
        'slow_sources': [],
        'article_ages': {
            'last_hour': 0,
            'today': 0,
            'yesterday': 0,
            'this_week': 0,
            'older': 0
        },
        'content_statistics': {
            'total_length': 0,
            'average_length': 0
        },
        'error_counts': {
            'parse_errors': 0,
            'fetch_errors': 0,
            'timeout_errors': 0
        }
    }

def categorize_article_age(publish_date: datetime) -> str:
    """Categorize article age for statistics"""
    now = datetime.now(DEFAULT_TZ)
    if not publish_date:
        return 'unknown'
    
    # Ensure publish_date is timezone-aware
    if publish_date.tzinfo is None:
        publish_date = publish_date.replace(tzinfo=pytz.UTC)
    publish_date = publish_date.astimezone(DEFAULT_TZ)
    
    delta = now - publish_date
    
    if delta < timedelta(hours=1):
        return 'last_hour'
    elif delta < timedelta(days=1):
        return 'today'
    elif delta < timedelta(days=2):
        return 'yesterday'
    elif delta < timedelta(days=7):
        return 'this_week'
    else:
        return 'older'

def print_metrics_summary() -> str:
    """Print a detailed summary of the metrics from the current run."""
    stats = []
    
    # Add core metrics
    stats.append("📊 Newsletter Generation Summary:")
    stats.append(f"├─ Sources checked: {FETCH_METRICS['sources_checked']}")
    stats.append(f"├─ Successful sources: {FETCH_METRICS['successful_sources']}")
    stats.append(f"├─ Total articles processed: {FETCH_METRICS['total_articles']}")
    stats.append(f"├─ Processing time: {FETCH_METRICS['processing_time']:.2f}s")
    
    # Add error statistics if any
    if FETCH_METRICS['failed_sources']:
        stats.append(f"\n❌ Failed Sources ({len(FETCH_METRICS['failed_sources'])}):")
        for source in FETCH_METRICS['failed_sources'][:5]:  # Show top 5
            stats.append(f"├─ {source}")
    
    return "\n".join(stats)

def setup_logger(name='ai_newsletter', level=None):
    """
    Set up and configure the logger with both console and file handlers.
    Ensures consistent timezone handling across the application.
    
    Args:
        name (str): Logger name
        level (str): Log level (DEBUG, INFO, WARNING, ERROR)
        
    Returns:
        logging.Logger: Configured logger instance
    """
    # Create logs directory if it doesn't exist
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    # Create a logger
    logger = logging.getLogger(name)
    
    # Avoid duplicate handlers if logger was already set up
    if logger.handlers:
        return logger
    
    # Set log level - default to INFO if not specified
    if level is None:
        level = logging.INFO
    elif isinstance(level, str):
        level = getattr(logging, level.upper(), logging.INFO)
    
    logger.setLevel(level)
    
    # Create a formatter with timezone-aware timestamps
    class TimeZoneFormatter(logging.Formatter):
        def converter(self, timestamp):
            # Convert timestamp to datetime and ensure it's timezone-aware
            dt = datetime.fromtimestamp(timestamp, pytz.UTC)
            return dt.astimezone(DEFAULT_TZ)
            
        def formatTime(self, record, datefmt=None):
            dt = self.converter(record.created)
            if datefmt:
                return dt.strftime(datefmt)
            return dt.strftime('%Y-%m-%d %H:%M:%S,%f')[:-3]
    
    formatter = TimeZoneFormatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Create and add console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Create and add file handler with rotation
    today = datetime.now(DEFAULT_TZ).strftime('%Y%m%d')
    log_filename = f'logs/newsletter_{today}.log'
    
    # Use ConcurrentRotatingFileHandler to handle concurrent writes
    file_handler = ConcurrentRotatingFileHandler(
        log_filename, 
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Reset metrics for a new run
    reset_metrics()
    
    return logger