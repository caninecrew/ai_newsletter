import logging
import os
import sys
import datetime
from concurrent_log_handler import ConcurrentRotatingFileHandler

# Global metrics for tracking fetch statistics
FETCH_METRICS = {
    'sources_checked': 0,
    'successful_sources': 0,
    'failed_sources': [],
    'empty_sources': [],
    'total_articles': 0,
    'duplicate_articles': 0,
    'processing_time': 0,
    'source_statistics': {}
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
        'source_statistics': {}
    }

def print_metrics_summary():
    """Print a summary of the metrics from the current run."""
    summary = f"\n=== Newsletter Fetch Summary ===\n"
    summary += f"Sources Checked: {FETCH_METRICS['sources_checked']}\n"
    summary += f"Total Articles Fetched: {FETCH_METRICS['total_articles']}\n"
    summary += f"Successful Sources: {FETCH_METRICS['successful_sources']}\n"
    
    if FETCH_METRICS['failed_sources']:
        summary += f"Failed Sources: {len(FETCH_METRICS['failed_sources'])} ({', '.join(FETCH_METRICS['failed_sources'][:5])})"
        if len(FETCH_METRICS['failed_sources']) > 5:
            summary += f" and {len(FETCH_METRICS['failed_sources']) - 5} more"
        summary += "\n"
    else:
        summary += "Failed Sources: 0\n"
    
    if FETCH_METRICS['empty_sources']:
        summary += f"Empty Sources: {len(FETCH_METRICS['empty_sources'])} ({', '.join(FETCH_METRICS['empty_sources'][:5])})"
        if len(FETCH_METRICS['empty_sources']) > 5:
            summary += f" and {len(FETCH_METRICS['empty_sources']) - 5} more"
        summary += "\n"
    
    summary += f"Duplicate Articles Removed: {FETCH_METRICS['duplicate_articles']}\n"
    
    # Format processing time nicely
    minutes = int(FETCH_METRICS['processing_time'] // 60)
    seconds = int(FETCH_METRICS['processing_time'] % 60)
    summary += f"Elapsed Time: {minutes} min {seconds} sec\n"
    
    # Add most successful sources (top 3)
    if FETCH_METRICS['source_statistics']:
        sorted_sources = sorted(
            FETCH_METRICS['source_statistics'].items(), 
            key=lambda x: x[1].get('articles', 0), 
            reverse=True
        )
        top_sources = sorted_sources[:3]
        summary += "\nMost Productive Sources:\n"
        for source, stats in top_sources:
            summary += f"- {source}: {stats.get('articles', 0)} articles\n"
    
    summary += "=========================="
    return summary

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
    today = datetime.datetime.now().strftime('%Y%m%d')
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