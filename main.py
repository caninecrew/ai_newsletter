from fetch_news import fetch_articles_from_all_feeds
from summarize import summarize_articles
from formatter import format_articles, filter_articles_by_date
from send_email import send_email
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta

def run_newsletter():
    # Fetch and filter articles from the previous day
    raw_articles = fetch_articles_from_all_feeds()
    yesterday_articles = filter_articles_by_date(raw_articles, days=1)
    summaries = summarize_articles(yesterday_articles)
    return summaries

def send_newsletter():
    load_dotenv()

    # Fetch and summarize articles
    articles = run_newsletter()
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
    subject = f"📰 Your AI Newsletter Summary for {yesterday}"
    
    # Send HTML email
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
    
    print(f"✅ Newsletter for {yesterday} sent successfully to {recipient_email}")

if __name__ == "__main__":
    send_newsletter()
