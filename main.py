from fetch_news import fetch_articles_from_all_feeds
from summarize import summarize_articles
from formatter import format_articles, filter_articles_by_date, deduplicate_articles
from send_email import send_email
from logger_config import setup_logger
from dotenv import load_dotenv
import os
import warnings
from datetime import datetime, timedelta
import sys

# Set up logger
logger = setup_logger()

# Suppress TensorFlow warnings about XNNPACK delegate
warnings.filterwarnings('ignore', category=UserWarning, module='tensorflow')
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'  # Suppress TF logs (0=all, 1=INFO, 2=WARNING, 3=ERROR)

# Add debug mode command line flag
DEBUG_MODE = "--debug" in sys.argv
SKIP_DATE_FILTER = "--skip-date-filter" in sys.argv

def run_newsletter():
    # Fetch raw articles
    raw_articles = fetch_articles_from_all_feeds()
    
    if DEBUG_MODE:
        logger.debug(f"Fetched {len(raw_articles)} raw articles")
        # Log titles of first 5 articles
        for i, article in enumerate(raw_articles[:5]):
            logger.debug(f"Article {i+1}: {article.get('title', 'No Title')} - {article.get('source', 'Unknown')}")
    
    # Filter by date - using past 24 hours instead of just yesterday
    if SKIP_DATE_FILTER:
        logger.info("Skipping date filtering as requested by command line flag")
        recent_articles = raw_articles
    else:
        recent_articles = filter_articles_by_date(raw_articles, hours=24)  # Using hours parameter
    
    if DEBUG_MODE:
        logger.debug(f"After date filtering: {len(recent_articles)} articles")
    
    # Deduplicate articles to avoid similar content
    deduplicated_articles = deduplicate_articles(recent_articles)
    
    if DEBUG_MODE:
        logger.debug(f"After deduplication: {len(deduplicated_articles)} articles")
    
    # Summarize the articles
    summaries = summarize_articles(deduplicated_articles)
    
    if DEBUG_MODE:
        logger.debug(f"After summarization: {len(summaries)} articles")
        for i, article in enumerate(summaries[:5]):
            logger.debug(f"Summary {i+1}: {article.get('title', 'No Title')} - {article.get('source', 'Unknown')}")
    
    return summaries

def send_newsletter():
    # Load environment variables from .env file if available
    # This won't fail if the .env file doesn't exist (GitHub Actions)
    load_dotenv(override=True)

    # Fetch, filter, deduplicate, and summarize articles
    articles = run_newsletter()
    
    if not articles or len(articles) == 0:
        logger.error("No articles to include in the newsletter!")
        # If in DEBUG_MODE, try running without the date filter
        global SKIP_DATE_FILTER
        if DEBUG_MODE and not SKIP_DATE_FILTER:
            logger.info("Rerunning with date filter disabled...")
            SKIP_DATE_FILTER = True
            articles = run_newsletter()

    if len(articles) <= 1:
        logger.warning(f"Only {len(articles)} article(s) found for newsletter. This might produce a sparse newsletter.")
    
    formatted_html = format_articles(articles, html=True)

    # Use "Past 24 Hours" instead of yesterday's date
    current_time = datetime.now()
    time_range = f"{(current_time - timedelta(hours=24)).strftime('%B %d, %H:%M')} - {current_time.strftime('%B %d, %H:%M, %Y')}"

    # Load email configuration from environment variables
    recipient_email = os.environ.get("RECIPIENT_EMAIL")
    sender_email = os.environ.get("SMTP_EMAIL")
    smtp_server = os.environ.get("SMTP_SERVER")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_password = os.environ.get("SMTP_PASS")

    if not recipient_email or not sender_email or not smtp_password:
        logger.error("Missing required email configuration in environment variables.")
        raise ValueError("Missing required email configuration in environment variables.")

    # Create a more engaging subject line with the 24-hour time range
    subject = f"📰 Your AI Newsletter Summary: Last 24 Hours ({len(articles)} articles)"
    
    if DEBUG_MODE:
        logger.debug(f"About to send email with {len(articles)} articles")
        logger.debug(f"Time range: {time_range}")
        logger.debug(f"Email will be sent to: {recipient_email}")
        logger.debug(f"From: {sender_email}")
        logger.debug(f"Subject: {subject}")
        # Optional: Save HTML to a file for inspection
        with open("newsletter_debug.html", "w", encoding="utf-8") as f:
            f.write(formatted_html)
        logger.debug("Email content saved to newsletter_debug.html")
    
    # Send HTML email (skip if no articles)
    if articles:
        try:
            send_email(
                subject=subject,
                body=formatted_html,
                to_email=recipient_email,
                from_email=sender_email,
                smtp_server=smtp_server,
                smtp_port=smtp_port,
                login=sender_email,
                password=smtp_password,
                use_tls=(smtp_port == 587),
                use_ssl=(smtp_port == 465),
                is_html=True
            )
            
            logger.info(f"Newsletter for {time_range} sent successfully to {recipient_email} with {len(articles)} articles")
            
            # Log the successful send
            with open("logs.txt", "a") as log_file:
                log_file.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Sent newsletter with {len(articles)} articles to {recipient_email}\n")
        except Exception as e:
            logger.error(f"Failed to send newsletter: {str(e)}")
            # Log the failure to the logs.txt for consistency with existing logging
            with open("logs.txt", "a") as log_file:
                log_file.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Failed to send newsletter: {str(e)}\n")
            raise  # Re-raise the exception for proper error handling upstream
    else:
        logger.error("No newsletter sent because no articles were found")
        
        # Log the failure
        with open("logs.txt", "a") as log_file:
            log_file.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Failed to send newsletter: No articles found\n")

if __name__ == "__main__":
    try:
        logger.info("Starting newsletter generation process")
        send_newsletter()
        logger.info("Newsletter process completed successfully")
    except Exception as e:
        logger.critical(f"Newsletter process failed with error: {str(e)}", exc_info=True)
        sys.exit(1)
