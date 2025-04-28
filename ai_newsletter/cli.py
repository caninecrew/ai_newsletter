import os
import sys
import warnings
import argparse
from datetime import datetime, timedelta, date
from fetch_news import fetch_articles_from_all_feeds
from summarize import summarize_articles
from formatter import format_articles, filter_articles_by_date, deduplicate_articles, build_html, strip_html, build_empty_newsletter
from send_email import send_email
from logger_config import setup_logger
from config import EMAIL_SETTINGS, SYSTEM_SETTINGS, FEED_SETTINGS
from dotenv import load_dotenv
import json # Import json for summary
import time # Import time for summary

# Import dateutil timezone tools
from dateutil import tz as dateutil_tz
CENTRAL = dateutil_tz.gettz("America/Chicago")

# Load environment variables
load_dotenv()

# Set up logger
logger = setup_logger()

# Suppress TensorFlow warnings
warnings.filterwarnings('ignore', category=UserWarning, module='tensorflow')
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

# --- Global variables for summary ---
all_articles_global = [] # To store articles for summary
failed_articles_global = [] # To store failed articles for summary
selenium_retry_count_global = 0 # To track selenium retries

def parse_feed_args():
    """Parse command line arguments for feed configuration"""
    parser = argparse.ArgumentParser(description='AI Newsletter Generator')
    
    # Debug and filtering options
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    parser.add_argument('--skip-date-filter', action='store_true', help='Skip date filtering of articles')
    
    # Feed category flags
    parser.add_argument('--disable-headlines', action='store_true', help='Disable headline feeds')
    parser.add_argument('--disable-location', action='store_true', help='Disable location feeds')
    parser.add_argument('--disable-interests', action='store_true', help='Disable interest feeds')
    parser.add_argument('--disable-aggregators', action='store_true', help='Disable aggregator feeds')
    
    return parser.parse_args()

def run_newsletter(args):
    """Run the newsletter generation process"""
    try:
        # Fetch articles
        logger.info("Starting article fetch process")
        articles = fetch_articles_from_all_feeds()
        
        if not articles:
            logger.error("No articles fetched")
            return False
            
        logger.info(f"Fetched {len(articles)} articles initially")
        
        # Filter by date unless skipped
        if not args.skip_date_filter:
            # Pass hours=24 instead of cutoff_date
            articles = filter_articles_by_date(articles, hours=24)
            logger.info(f"Date filtering: {len(articles)} articles kept")
        
        # Remove duplicates
        articles = deduplicate_articles(articles)
        logger.info(f"After deduplication: {len(articles)} articles")
        
        if not articles:
            logger.error("No articles remaining after filtering")
            return False
        
        # Summarize articles
        logger.info("Summarizing articles")
        articles = summarize_articles(articles)
        
        # Format newsletter
        logger.info("Formatting newsletter")
        formatted_content = format_articles(articles)
        
        return formatted_content
        
    except Exception as e:
        logger.error(f"Error in newsletter generation: {e}", exc_info=True)
        return False

def generate_newsletter(start_date=None, end_date=None):
    """Fetches, summarizes, formats, and sends the newsletter."""
    global all_articles_global, failed_articles_global, selenium_retry_count_global # Use global vars

    try:
        logger.info("--- Starting Newsletter Generation ---")

        # 1. Fetch articles
        logger.info("Fetching articles...")
        # Assuming fetch_articles_from_all_feeds returns articles and stats
        articles, fetch_stats = fetch_articles_from_all_feeds()
        all_articles_global = articles # Store for summary
        # Extract failed articles and selenium retries from stats if available
        # This requires fetch_news_articles to return detailed stats
        # For now, let's assume fetch_stats might contain relevant info or we track failures separately
        # selenium_retry_count_global = fetch_stats.get('selenium_retries', 0) # Example

        if not articles:
            logger.warning("No articles fetched. Exiting.")
            return

        logger.info(f"Fetched {len(articles)} unique articles initially.")

        # 2. Filter by date (ensure dates are aware)
        if start_date or end_date:
             # Ensure start/end dates are timezone-aware in CENTRAL
             if start_date and start_date.tzinfo is None:
                 start_date = start_date.replace(tzinfo=CENTRAL)
             if end_date and end_date.tzinfo is None:
                 end_date = end_date.replace(tzinfo=CENTRAL)
             logger.info(f"Filtering articles between {start_date} and {end_date}")
             articles = filter_articles_by_date(articles, start_date, end_date)
             logger.info(f"{len(articles)} articles remain after date filtering.")

        # 3. Deduplicate articles (optional, might be redundant if fetch_news handles it)
        # articles = deduplicate_articles(articles)
        # logger.info(f"{len(articles)} articles remain after deduplication.")

        # 4. Summarize articles
        logger.info("Summarizing articles...")
        summarized_articles = summarize_articles(articles)
        # Track failed summaries if needed
        # failed_articles_global.extend([a for a in summarized_articles if not a.get('summary')])

        # 5. Format articles
        logger.info("Formatting articles...")
        newsletter_content = format_articles(summarized_articles)

        # 6. Send newsletter
        if newsletter_content:
            logger.info("Sending newsletter...")
            # Use timezone-aware dates for subject
            now = datetime.now(CENTRAL)
            yesterday = now - timedelta(days=1)
            subject = f"AI Newsletter: {yesterday.strftime('%B %d')} - {now.strftime('%B %d, %Y')}"

            send_newsletter(subject, newsletter_content) # Pass subject here
        else:
            logger.warning("No content generated after formatting. Newsletter not sent.")

        logger.info("--- Newsletter Generation Finished ---")

    except Exception as e:
        logger.critical(f"Unhandled exception during newsletter generation: {e}", exc_info=True)
        # Store exception info if needed for summary
        # failed_articles_global.append({"error": str(e)}) # Example

def send_newsletter(subject, content):
    """Send the newsletter"""
    try:
        if not content:
            logger.error("No content to send")
            return False
            
        # Prepare email parameters with proper timezone awareness
        now = datetime.now(CENTRAL)
        yesterday = now - timedelta(days=1)
        
        # Send email
        logger.info(f"Preparing to send email to {EMAIL_SETTINGS['recipients']}")
        success = send_email(
            subject=subject,
            body=content,
            recipients=EMAIL_SETTINGS['recipients'],
            smtp_settings=EMAIL_SETTINGS['smtp']
        )
        
        if success:
            logger.info(f"Newsletter sent successfully to {len(EMAIL_SETTINGS['recipients'])} recipients")
            return True
        else:
            logger.error("Failed to send newsletter")
            return False
            
    except Exception as e:
        logger.error(f"Error sending newsletter: {e}", exc_info=True)
        return False

def main():
    start_time = time.time() # Record start time for summary

    parser = argparse.ArgumentParser(description="Generate and send AI Newsletter.")
    parser.add_argument("--start_date", help="Start date for filtering articles (YYYY-MM-DD)")
    parser.add_argument("--end_date", help="End date for filtering articles (YYYY-MM-DD)")
    args = parser.parse_args()

    start_dt = None
    end_dt = None
    try:
        if (args.start_date):
            # Parse and make timezone-aware in CENTRAL
            start_dt = datetime.strptime(args.start_date, "%Y-%m-%d").replace(tzinfo=CENTRAL)
        if (args.end_date):
            # Parse, add time component to include the whole day, make aware
            end_dt = (datetime.strptime(args.end_date, "%Y-%m-%d") + timedelta(days=1, seconds=-1)).replace(tzinfo=CENTRAL)
    except ValueError:
        logger.error("Invalid date format. Please use YYYY-MM-DD.")
        sys.exit(1)

    try: # Wrap the core logic
        generate_newsletter(start_date=start_dt, end_date=end_dt)
    finally: # Add the summary logging block
        end_time = time.time()
        stats = {
            "articles_fetched_initial": len(all_articles_global), # Use global var
            # Add more stats as they become available, e.g., after filtering/summarizing
            "articles_failed_summary": len(failed_articles_global), # Use global var
            "selenium_retries": selenium_retry_count_global, # Use global var
            "runtime_seconds": round(end_time - start_time, 2),
            "end_time_utc": datetime.utcnow().isoformat() + "Z"
        }
        # Use json.dumps for structured logging
        logger.info(f"SUMMARY: {json.dumps(stats)}")

if __name__ == "__main__":
    start_time = time.time() # Record start time for summary

    parser = argparse.ArgumentParser(description="Generate and send AI Newsletter.")
    parser.add_argument("--start_date", help="Start date for filtering articles (YYYY-MM-DD)")
    parser.add_argument("--end_date", help="End date for filtering articles (YYYY-MM-DD)")
    args = parser.parse_args()

    start_dt = None
    end_dt = None
    try:
        if (args.start_date):
            # Parse and make timezone-aware in CENTRAL
            start_dt = datetime.strptime(args.start_date, "%Y-%m-%d").replace(tzinfo=CENTRAL)
        if (args.end_date):
            # Parse, add time component to include the whole day, make aware
            end_dt = (datetime.strptime(args.end_date, "%Y-%m-%d") + timedelta(days=1, seconds=-1)).replace(tzinfo=CENTRAL)
    except ValueError:
        logger.error("Invalid date format. Please use YYYY-MM-DD.")
        sys.exit(1)

    try: # Wrap the core logic
        generate_newsletter(start_date=start_dt, end_date=end_dt)
    finally: # Add the summary logging block
        end_time = time.time()
        stats = {
            "articles_fetched_initial": len(all_articles_global), # Use global var
            # Add more stats as they become available, e.g., after filtering/summarizing
            "articles_failed_summary": len(failed_articles_global), # Use global var
            "selenium_retries": selenium_retry_count_global, # Use global var
            "runtime_seconds": round(end_time - start_time, 2),
            "end_time_utc": datetime.utcnow().isoformat() + "Z"
        }
        # Use json.dumps for structured logging
        logger.info(f"SUMMARY: {json.dumps(stats)}")

    # Summarize articles
    articles = summarize_articles(all_articles_global)

    # Always send a newsletter
    if articles:
        html = build_html(articles)
        text = strip_html(html)
        subject = f"AI Newsletter – {len(articles)} stories – {date.today():%b %d}"
    else:
        html = build_empty_newsletter()
        text = "No new articles were available today."
        subject = f"AI Newsletter – No new stories – {date.today():%b %d}"

    send_email.send_newsletter(html, text, subject)
