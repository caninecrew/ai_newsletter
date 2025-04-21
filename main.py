from fetch_news import fetch_articles_from_all_feeds
from summarize import summarize_articles
from formatter import format_articles
from send_email import send_email
from dotenv import load_dotenv
import os

def run_newsletter():
    raw_articles = fetch_articles_from_all_feeds()
    summaries = summarize_articles(raw_articles)
    return summaries

def send_newsletter():
    load_dotenv()

    # Fetch and summarize articles
    articles = run_newsletter()
    formatted_content = format_articles(articles)

    # Load email configuration from environment variables
    recipient_email = os.getenv("RECIPIENT_EMAIL")
    sender_email = os.getenv("SMTP_EMAIL")
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = int(os.getenv("SMTP_PORT"))
    smtp_password = os.getenv("SMTP_PASS")
    sender_name = os.getenv("SENDER_NAME", "Newsletter Bot")

    if not recipient_email or not sender_email or not smtp_password:
        raise ValueError("Missing required email configuration in .env file.")

    subject = "📰 Your Daily Newsletter"
    body = f"Hello,\n\nHere are today's top articles:\n\n{formatted_content}\n\nBest regards,\n{sender_name}"

    # Send the email
    send_email(
        subject=subject,
        body=body,
        to_email=recipient_email,
        from_email=sender_email,
        smtp_server=smtp_server,
        smtp_port=smtp_port,
        login=sender_email,
        password=smtp_password,
        use_tls=(smtp_port == 587),
        use_ssl=(smtp_port == 465)
    )

if __name__ == "__main__":
    send_newsletter()
