import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr, formatdate
import os
from dotenv import load_dotenv
from logger_config import setup_logger
import ssl
import certifi
from config import EMAIL_SETTINGS
import time
from socket import error as socket_error
from datetime import datetime
from dateutil import tz as dateutil_tz

# Set up logger
logger = setup_logger()

# Load environment variables
load_dotenv()

# Constants for retry settings
MAX_RETRIES = 3
RETRY_DELAY = 5
KEEPALIVE_INTERVAL = 60
SMTP_TIMEOUT = 30

# Define Central timezone
CENTRAL = dateutil_tz.gettz("America/Chicago")

def setup_email_settings():
    """Initialize email settings from environment variables"""
    # Get recipient emails from environment
    recipient_str = os.getenv("RECIPIENT_EMAIL", "")
    recipients = [email.strip() for email in recipient_str.split(',') if email.strip()]
    EMAIL_SETTINGS['recipients'] = recipients

    # Set up SMTP settings
    EMAIL_SETTINGS['smtp'].update({
        'host': os.getenv("SMTP_SERVER", ""),
        'port': int(os.getenv("SMTP_PORT", "587")),
        'username': os.getenv("SMTP_EMAIL", ""),
        'password': os.getenv("SMTP_PASS", ""),
        'sender': os.getenv("SMTP_EMAIL", "")
    })

    return bool(recipients and EMAIL_SETTINGS['smtp']['host'] and EMAIL_SETTINGS['smtp']['username'])

def create_secure_smtp_context():
    """Create a secure SSL context for SMTP"""
    context = ssl.create_default_context(cafile=certifi.where())
    context.verify_mode = ssl.CERT_REQUIRED
    context.check_hostname = True
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    return context

def create_smtp_connection(smtp_settings):
    """Create and configure SMTP connection with retry logic"""
    context = create_secure_smtp_context()
    server = smtplib.SMTP(smtp_settings['host'], smtp_settings['port'], timeout=SMTP_TIMEOUT)
    server.starttls(context=context)
    server.login(smtp_settings['username'], smtp_settings['password'])
    return server

def send_newsletter(html_body: str, text_body: str, subject: str) -> bool:
    """Send the newsletter via SMTP."""
    smtp_host = os.getenv("SMTP_SERVER")
    smtp_port = int(os.getenv("SMTP_PORT", 587))
    smtp_user = os.getenv("SMTP_EMAIL")
    smtp_pass = os.getenv("SMTP_PASS")

    if not all([smtp_host, smtp_port, smtp_user, smtp_pass]):
        raise ValueError("SMTP configuration is incomplete. Check environment variables.")

    # Construct the email
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = smtp_user
    msg["To"] = os.getenv("NEWSLETTER_RECIPIENT", "recipient@example.com")

    # Attach text and HTML parts
    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP_SSL(smtp_host, smtp_port) as server:
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, [msg["To"]], msg.as_string())
        return True
    except Exception as e:
        raise RuntimeError(f"Failed to send email: {e}")

def test_send_email():
    """
    Sends a test email to verify the email sending functionality.
    """
    if not setup_email_settings():
        logger.error("Email settings not properly configured")
        return False

    subject = "✅ Test Email"
    body = f"This is a test email sent using the configured SMTP settings."

    try:
        logger.info("Sending test email to validate configuration")
        success = send_newsletter(
            subject=subject,
            html_body=body,
            text_body=body
        )
        if success:
            logger.info("✅ Test email sent successfully.")
        else:
            logger.error("❌ Failed to send test email.")
        return success
    except Exception as e:
        logger.error(f"❌ Failed to send test email: {e}", exc_info=True)
        return False

# Initialize email settings when module is imported
setup_email_settings()

if __name__ == "__main__":
    test_send_email()

