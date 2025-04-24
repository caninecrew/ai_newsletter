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
        'average_length': 0,
        'articles_with_content': 0,
        'articles_without_content': 0
    }
}

def reset_metrics():
    """Reset metrics for a new run."""
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
            'average_length': 0,
            'articles_with_content': 0,
            'articles_without_content': 0
        }
    }

def categorize_article_age(publish_date: datetime) -> str:
    """Categorize article age for statistics"""
    now = datetime.now()
    if not publish_date:
        return 'unknown'
    
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
    stats.append("\n=== Newsletter Fetch Statistics ===\n")
    
    # Source statistics
    stats.append(f"Sources Processed: {FETCH_METRICS['sources_checked']}")
    stats.append(f"├─ Successful: {FETCH_METRICS['successful_sources']}")
    stats.append(f"├─ Failed: {len(FETCH_METRICS['failed_sources'])}")
    stats.append(f"└─ Empty: {len(FETCH_METRICS['empty_sources'])}")
    
    # Article statistics
    stats.append(f"\nArticles:")
    stats.append(f"├─ Total found: {FETCH_METRICS['total_articles']}")
    stats.append(f"├─ Duplicates removed: {FETCH_METRICS['duplicate_articles']}")
    stats.append(f"├─ With content: {FETCH_METRICS['content_statistics']['articles_with_content']}")
    stats.append(f"└─ Without content: {FETCH_METRICS['content_statistics']['articles_without_content']}")
    
    # Content statistics
    if FETCH_METRICS['content_statistics']['articles_with_content'] > 0:
        avg_length = FETCH_METRICS['content_statistics']['average_length']
        stats.append(f"\nContent Statistics:")
        stats.append(f"├─ Average length: {avg_length:.0f} characters")
        stats.append(f"└─ Total content: {FETCH_METRICS['content_statistics']['total_length']/1000:.1f}K characters")
    
    # Age distribution
    stats.append("\nArticle Age Distribution:")
    age_stats = FETCH_METRICS['article_ages']
    total_aged = sum(age_stats.values())
    if total_aged > 0:
        for age, count in age_stats.items():
            percentage = (count / total_aged) * 100
            stats.append(f"├─ {age.replace('_', ' ').title()}: {count} ({percentage:.1f}%)")
    
    # Performance metrics
    stats.append(f"\nPerformance:")
    stats.append(f"├─ Total processing time: {FETCH_METRICS['processing_time']:.1f}s")
    stats.append(f"├─ Average fetch time: {FETCH_METRICS['average_article_fetch_time']:.2f}s")
    stats.append(f"├─ Browser instances created: {FETCH_METRICS['browser_instances']}")
    stats.append(f"└─ Browser reuse count: {FETCH_METRICS['driver_reuse_count']}")
    
    # Slow sources
    if FETCH_METRICS['slow_sources']:
        stats.append("\nSlow Sources (>5s):")
        for source in FETCH_METRICS['slow_sources'][:5]:  # Show top 5
            stats.append(f"├─ {source['source']}: {source['time']:.1f}s")
    
    # Failed sources
    if FETCH_METRICS['failed_sources']:
        stats.append("\nFailed Sources:")
        for source in FETCH_METRICS['failed_sources'][:5]:  # Show top 5
            stats.append(f"├─ {source}")
    
    return "\n".join(stats)

def setup_logger(name='ai_newsletter', level=None):
    """
    Set up and configure the logger with both console and file handlers.
    
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
    
    # Create a formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
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