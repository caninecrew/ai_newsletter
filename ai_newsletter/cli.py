import os
import sys
import argparse
from datetime import datetime, timedelta, date
from ai_newsletter.feeds.fetcher import safe_fetch_news_articles
from ai_newsletter.utils.summarize import summarize_articles
from ai_newsletter.formatting.formatter import (
    format_articles, 
    filter_articles_by_date, 
    deduplicate_articles,
    build_html,
    strip_html,
    build_empty_newsletter
)
from ai_newsletter.email.sender import send_email
from ai_newsletter.logging_cfg.logger import setup_logger
from ai_newsletter.config.settings import EMAIL_SETTINGS, SYSTEM_SETTINGS
from dotenv import load_dotenv
import json
import time

# Import dateutil timezone tools
from dateutil import tz as dateutil_tz
CENTRAL = dateutil_tz.gettz("America/Chicago")

# Load environment variables
load_dotenv()

# Set up logger
logger = setup_logger()

# --- Global variables for summary ---
all_articles_global = [] # To store articles for summary
failed_articles_global = [] # To store failed articles for summary

def parse_feed_args():
    """Parse command line arguments for feed configuration"""
    parser = argparse.ArgumentParser(description="Generate and send AI Newsletter.")
    parser.add_argument("--start_date", help="Start date for filtering articles (YYYY-MM-DD)")
    parser.add_argument("--end_date", help="End date for filtering articles (YYYY-MM-DD)")
    return parser.parse_args()

def run_newsletter(args):
    """Run the newsletter generation process"""
    try:
        start_dt = None
        end_dt = None
        
        if args.start_date:
            start_dt = datetime.strptime(args.start_date, "%Y-%m-%d").replace(tzinfo=CENTRAL)
        if args.end_date:
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
        articles = summarize_articles(articles)

        # 4. Format newsletter
        logger.info("Formatting newsletter...")
        newsletter_content = build_html(articles)

        # 5. Send newsletter
        if newsletter_content:
            logger.info("Sending newsletter...")
            # Use timezone-aware dates for subject
            now = datetime.now(CENTRAL)
            yesterday = now - timedelta(days=1)
            subject = f"AI Newsletter: {yesterday.strftime('%B %d')} - {now.strftime('%B %d, %Y')}"

            send_email(subject=subject, content=newsletter_content)
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

# Define cli as the main entry point for the module
cli = main

if __name__ == "__main__":
    cli()
