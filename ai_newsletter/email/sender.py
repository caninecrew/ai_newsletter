import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr, formatdate
import os
from dotenv import load_dotenv
from ai_newsletter.logging_cfg.logger import setup_logger
import ssl
import certifi
from ai_newsletter.config.settings import EMAIL_SETTINGS
import time
from socket import error as socket_error
from datetime import datetime
from dateutil import tz as dateutil_tz
from bs4 import BeautifulSoup

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

def send_email(subject: str, body: str, recipients: list = None, smtp_settings: dict = None) -> bool:
    """Send an email via SMTP with retry logic and secure connection.
    
    Args:
        subject: Email subject line
        body: Email body content (HTML)
        recipients: List of recipient email addresses. If not provided, uses settings
        smtp_settings: SMTP settings dict. If not provided, uses settings
        
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    # Use settings from config if not provided
    if recipients is None:
        recipients = EMAIL_SETTINGS['recipients']
    if smtp_settings is None:
        smtp_settings = EMAIL_SETTINGS['smtp']
    
    if not recipients or not all(smtp_settings.values()):
        logger.error("Missing required email settings")
        return False

    # Prepare the email
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = formataddr(("AI Newsletter", smtp_settings['sender']))
    msg['Date'] = formatdate(localtime=True)
    
    # Add body - both text and HTML versions
    text_part = MIMEText(strip_html(body), 'plain', 'utf-8')
    html_part = MIMEText(body, 'html', 'utf-8')
    msg.attach(text_part)
    msg.attach(html_part)

    # Add recipients
    msg['To'] = ', '.join(recipients)

    # Try to send email with retries
    for attempt in range(MAX_RETRIES):
        try:
            with create_smtp_connection(smtp_settings) as server:
                server.send_message(msg)
                logger.info(f"Email sent successfully to {len(recipients)} recipients")
                return True
                
        except (smtplib.SMTPException, socket_error) as e:
            logger.error(f"SMTP error on attempt {attempt + 1}: {str(e)}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))
            else:
                logger.error(f"Failed to send email after {MAX_RETRIES} attempts")
                return False
                
        except Exception as e:
            logger.error(f"Unexpected error sending email: {str(e)}")
            return False

def strip_html(html_content):
    """Convert HTML to plain text.
    
    Args:
        html_content: HTML string to convert
        
    Returns:
        str: Plain text version of the HTML content
    """
    if not html_content:
        return ""
        
    # Parse HTML with BeautifulSoup
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Remove script and style elements
    for script in soup(["script", "style"]):
        script.decompose()
        
    # Get text
    text = soup.get_text()
    
    # Break into lines and remove leading/trailing space
    lines = (line.strip() for line in text.splitlines())
    
    # Break multi-headlines into a line each
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    
    # Drop blank lines and join
    return '\n'.join(chunk for chunk in chunks if chunk)

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
        success = send_email(
            subject=subject,
            body=body
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

# Expose these functions as the public API
__all__ = ['send_email', 'test_send_email', 'setup_email_settings']

if __name__ == "__main__":
    test_send_email()

