from fetch_news import fetch_articles_from_all_feeds
from summarize import summarize_articles
from formatter import format_articles, filter_articles_by_date
from send_email import send_email
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta
import sys

# Add debug mode command line flag
DEBUG_MODE = "--debug" in sys.argv
SKIP_DATE_FILTER = "--skip-date-filter" in sys.argv

def run_newsletter():
    # Fetch raw articles
    raw_articles = fetch_articles_from_all_feeds()
    
    if DEBUG_MODE:
        print(f"[DEBUG] Fetched {len(raw_articles)} raw articles")
        # Print titles of first 5 articles
        for i, article in enumerate(raw_articles[:5]):
            print(f"[DEBUG] Article {i+1}: {article.get('title', 'No Title')} - {article.get('source', 'Unknown')}")
    
    # Filter by date (or skip if flag is set)
    if SKIP_DATE_FILTER:
        print("[INFO] Skipping date filtering as requested by command line flag")
        yesterday_articles = raw_articles
    else:
        yesterday_articles = filter_articles_by_date(raw_articles, days=1)
    
    if DEBUG_MODE:
        print(f"[DEBUG] After date filtering: {len(yesterday_articles)} articles")
    
    # Summarize the articles
    summaries = summarize_articles(yesterday_articles)
    
    if DEBUG_MODE:
        print(f"[DEBUG] After summarization: {len(summaries)} articles")
        for i, article in enumerate(summaries[:5]):
            print(f"[DEBUG] Summary {i+1}: {article.get('title', 'No Title')} - {article.get('source', 'Unknown')}")
    
    return summaries

def send_newsletter():
    load_dotenv()

    # Fetch and summarize articles
    articles = run_newsletter()
    
    if not articles or len(articles) == 0:
        print("[ERROR] No articles to include in the newsletter!")
        # If in DEBUG_MODE, try running without the date filter
        global SKIP_DATE_FILTER
        if DEBUG_MODE and not SKIP_DATE_FILTER:
            print("[INFO] Rerunning with date filter disabled...")
            # Declare global before using it
            
            SKIP_DATE_FILTER = True
            articles = run_newsletter()

    if len(articles) <= 1:
        print(f"[WARN] Only {len(articles)} article(s) found for newsletter. This might produce a sparse newsletter.")
        # You might want to set a minimum threshold (e.g., retry fetching or exit)
    
    formatted_html = format_articles(articles, html=True)

    # Get yesterday's date for the subject line
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%A, %B %d, %Y')

    # Load email configuration from environment variables
    recipient_email = os.getenv("RECIPIENT_EMAIL")
    sender_email = os.getenv("SMTP_EMAIL")
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = int(os.getenv("SMTP_PORT"))
    smtp_password = os.getenv("SMTP_PASS")
    sender_name = os.getenv("SENDER_NAME", "Newsletter Bot")

    if not recipient_email or not sender_email or not smtp_password:
        raise ValueError("Missing required email configuration in .env file.")

    # Create a more engaging subject line with yesterday's date
    subject = f"📰 Your AI Newsletter Summary for {yesterday} ({len(articles)} articles)"
    
    if DEBUG_MODE:
        print(f"[DEBUG] About to send email with {len(articles)} articles")
        print("[DEBUG] Email will be sent to:", recipient_email)
        print("[DEBUG] From:", sender_email)
        print("[DEBUG] Subject:", subject)
        # Optional: Save HTML to a file for inspection
        with open("newsletter_debug.html", "w", encoding="utf-8") as f:
            f.write(formatted_html)
        print("[DEBUG] Email content saved to newsletter_debug.html")
    
    # Send HTML email (skip if no articles)
    if articles:
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
        
        print(f"✅ Newsletter for {yesterday} sent successfully to {recipient_email} with {len(articles)} articles")
    else:
        print("❌ No newsletter sent because no articles were found")

if __name__ == "__main__":
    send_newsletter()
