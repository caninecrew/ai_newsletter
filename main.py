import os
import sys
import warnings
import argparse
from datetime import datetime, timedelta
from fetch_news import fetch_articles_from_all_feeds
from summarize import summarize_articles
from formatter import format_articles, filter_articles_by_date, deduplicate_articles
from send_email import send_email
from logger_config import setup_logger
from config import EMAIL_SETTINGS, SYSTEM_SETTINGS, FEED_SETTINGS
from dotenv import load_dotenv

# Set up logger
logger = setup_logger()

# Suppress TensorFlow warnings
warnings.filterwarnings('ignore', category=UserWarning, module='tensorflow')
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

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

def send_newsletter(content):
    """Send the newsletter"""
    try:
        if not content:
            logger.error("No content to send")
            return False
            
        # Prepare email parameters
        now = datetime.now()
        yesterday = now - timedelta(days=1)
        subject = f"Newsletter for {yesterday.strftime('%B %d')} - {now.strftime('%B %d')}, {now.year}"
        
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
    """Main entry point"""
    try:
        # Load environment variables
        load_dotenv()
        
        # Parse arguments
        args = parse_feed_args()
        
        # Enable debug logging if requested
        if args.debug:
            import logging
            logger.setLevel(logging.DEBUG)
        
        # Log start of process
        logger.info("Starting newsletter generation process")
        
        # Generate newsletter content
        content = run_newsletter(args)
        
        if not content:
            logger.error("Newsletter generation failed")
            sys.exit(1)
        
        # Send newsletter
        if not send_newsletter(content):
            logger.error("Newsletter sending failed")
            sys.exit(1)
            
        logger.info("Newsletter process completed successfully")
        
    except Exception as e:
        logger.error(f"Critical error in main process: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
