"""
AI Newsletter Command Line Interface.

This module provides the core CLI functionality for the AI Newsletter system.
It handles the main workflow of:
1. Article fetching and filtering
2. AI-powered summarization
3. Newsletter formatting
4. Email delivery

The system uses Central Time (America/Chicago) for all date operations.

Example Usage:
    # Generate newsletter for current day
    python -m ai_newsletter

    # Generate newsletter for specific date range
    python -m ai_newsletter --start-date 2025-05-01 --end-date 2025-05-02

Environment Variables:
    GNEWS_API_KEY: API key for GNews
    OPENAI_API_KEY: API key for OpenAI
    SMTP_SERVER: SMTP server hostname
    SMTP_PORT: SMTP server port
    SMTP_USERNAME: SMTP authentication username
    SMTP_PASSWORD: SMTP authentication password
    EMAIL_SENDER: Sender email address
    EMAIL_RECIPIENTS: Comma-separated list of recipient emails

For detailed configuration options, see config/settings.py
For complete documentation, see README.md

MIT License - See LICENSE for details
"""
# Standard library imports
import os
import sys
import argparse
from datetime import datetime, timedelta
import json
import time

# Third-party imports
import click
from dotenv import load_dotenv
from dateutil import tz

# Local imports
from ai_newsletter.feeds import safe_fetch_news_articles
from ai_newsletter.llm import summarize_article
from ai_newsletter.feeds.filters import filter_articles_by_date
from ai_newsletter.formatting import build_newsletter
from ai_newsletter.email.sender import send_email
from ai_newsletter.deploy.url_builder import build_newsletter_url
from ai_newsletter.logging_cfg.logger import setup_logger
from ai_newsletter.config.settings import EMAIL_SETTINGS

# Load environment variables
load_dotenv()

# Set up logger
logger = setup_logger()

# Define Central timezone
CENTRAL = tz.gettz("America/Chicago")

# Global variables for summary statistics
all_articles_global = []  # Tracks total articles processed
failed_articles_global = []  # Tracks failed article processing

def run_health_check():
    """Run health check validation and return status.
    
    Checks:
    1. API connectivity
    2. Required directories
    3. Environment variables
    4. SMTP connection
    """
    try:
        # Check required directories
        for directory in ['logs', 'output']:
            os.makedirs(directory, exist_ok=True)
        
        # Validate environment variables
        required_vars = [
            'GNEWS_API_KEY',
            'OPENAI_API_KEY',
            'SMTP_SERVER',
            'SMTP_PORT',
            'SMTP_USERNAME',
            'SMTP_PASSWORD',
            'EMAIL_SENDER',
            'EMAIL_RECIPIENTS'
        ]
        
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            logger.error(f"Missing environment variables: {', '.join(missing_vars)}")
            sys.exit(1)
            
        # Test API connections
        from ai_newsletter.feeds.gnews_client import test_gnews_connection
        from ai_newsletter.llm.utils import test_openai_connection
        
        test_gnews_connection()
        test_openai_connection()
        
        # Test SMTP connection
        from ai_newsletter.email.sender import test_smtp_connection
        test_smtp_connection()
        
        logger.info("Health check passed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        sys.exit(1)

def parse_feed_args():
    """Parse command line arguments for feed configuration"""
    parser = argparse.ArgumentParser()
    parser.add_argument('--start-date', help='Start date for article filtering (YYYY-MM-DD)')
    parser.add_argument('--end-date', help='End date for article filtering (YYYY-MM-DD)')
    parser.add_argument('--validate-config', action='store_true', help='Validate configuration')
    parser.add_argument('--dry-run', action='store_true', help='Generate without sending')
    parser.add_argument('--debug', action='store_true', help='Enable debug output')
    parser.add_argument('--test-email', action='store_true', help='Test email configuration')
    parser.add_argument('--performance-log', action='store_true', help='Enable performance logging')
    parser.add_argument('--check-storage', action='store_true', help='Check storage status')
    parser.add_argument('--health-check', action='store_true', help='Run health check')
    return parser.parse_args()

def ensure_output_dir():
    """Create output directory if it doesn't exist."""
    os.makedirs('output', exist_ok=True)

def save_newsletter_html(content: str, filename: str = 'newsletter.html'):
    """Save newsletter HTML to output directory.
    
    Args:
        content: HTML content to save
        filename: Name of the output file
    """
    ensure_output_dir()
    output_path = os.path.join('output', filename)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)
    logger.info(f"Newsletter HTML saved to {output_path}")
    return output_path

def run_newsletter(args=None):
    """Run the newsletter generation process"""
    try:
        start_dt = None
        end_dt = None
        
        if args and args.start_date:
            start_dt = datetime.strptime(args.start_date, "%Y-%m-%d").replace(tzinfo=CENTRAL)
        if args and args.end_date:
            # Parse, add time component to include the whole day, make aware
            end_dt = (datetime.strptime(args.end_date, "%Y-%m-%d") + timedelta(days=1, seconds=-1)).replace(tzinfo=CENTRAL)
            
        generate_newsletter(start_date=start_dt, end_date=end_dt)
        
    except ValueError:
        logger.error("Invalid date format. Please use YYYY-MM-DD.")
        sys.exit(1)
    except Exception as e:
        logger.critical(f"Unhandled exception during newsletter run: {e}", exc_info=True)
        sys.exit(1)

def generate_newsletter(start_date=None, end_date=None):
    """Fetches, summarizes, formats, and sends the newsletter."""
    global all_articles_global, failed_articles_global

    try:
        logger.info("--- Starting Newsletter Generation ---")

        # 1. Fetch articles using safe wrapper
        logger.info("Fetching articles...")
        articles, fetch_stats = safe_fetch_news_articles()
        all_articles_global = articles  # Store for summary

        if not articles:
            logger.warning("No articles fetched. Exiting.")
            return

        # 2. Filter by date if needed
        if start_date or end_date:
            logger.info(f"Filtering articles between {start_date} and {end_date}")
            articles = filter_articles_by_date(articles, start_date, end_date)
            logger.info(f"{len(articles)} articles remain after date filtering.")

        # 3. Summarize articles
        logger.info("Summarizing articles...")
        for article in articles:
            summary = summarize_article(article)
            if summary:
                article['summary'] = summary
                article['summary_method'] = 'openai'
            else:
                article['summary'] = article.get('description', '')
                article['summary_method'] = 'description_fallback'

        # 4. Format newsletter
        logger.info("Formatting newsletter...")
        newsletter_content = build_newsletter(articles)

        # 5. Save HTML output
        if newsletter_content:
            output_path = save_newsletter_html(newsletter_content)
            logger.info(f"Newsletter HTML saved to {output_path}")

            # 6. Send newsletter
            logger.info("Sending newsletter...")
            # Use timezone-aware dates for subject
            now = datetime.now(CENTRAL)
            yesterday = now - timedelta(days=1)
            date_str = now.strftime("%Y-%m-%d")
            subject = f"AI Newsletter: {yesterday.strftime('%B %d')} - {now.strftime('%B %d, %Y')}"
            hosted_url = build_newsletter_url(now)

            send_email(subject=subject, body=newsletter_content, hosted_url=hosted_url)
            logger.info("Newsletter sent successfully")
        else:
            logger.warning("No content generated after formatting. Newsletter not sent.")

        logger.info("--- Newsletter Generation Finished ---")

    except Exception as e:
        logger.critical(f"Unhandled exception during newsletter generation: {e}", exc_info=True)
        failed_articles_global.append({"error": str(e)})

def main():
    """Main entry point for the CLI"""
    start_time = time.time()
    args = parse_feed_args()
    
    try:
        if args.health_check:
            run_health_check()
            return
            
        if args.validate_config:
            if run_health_check():
                logger.info("Configuration is valid")
            return
            
        run_newsletter(args)
        
    finally:
        # Add summary statistics
        end_time = time.time()
        stats = {
            "articles_fetched_initial": len(all_articles_global),
            "articles_failed": len(failed_articles_global),
            "runtime_seconds": round(end_time - start_time, 2),
            "end_time_utc": datetime.utcnow().isoformat() + "Z"
        }
        logger.info(f"SUMMARY: {json.dumps(stats)}")

@click.command()
def cli():
    """Run the newsletter generator."""
    run_newsletter()

if __name__ == "__main__":
    cli()
