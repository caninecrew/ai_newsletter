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
    return {
        'smtp_server': os.getenv('SMTP_SERVER'),
        'smtp_port': int(os.getenv('SMTP_PORT', '587')),
        'smtp_user': os.getenv('SMTP_EMAIL'),
        'smtp_pass': os.getenv('SMTP_PASS'),
        'from_email': os.getenv('SMTP_EMAIL'),
        'to_email': os.getenv('RECIPIENT_EMAIL'),
    }

def create_secure_smtp_context():
    """Create a secure SSL context for SMTP"""
    context = ssl.create_default_context(
        purpose=ssl.Purpose.SERVER_AUTH,
        cafile=certifi.where()
    )
    context.verify_mode = ssl.CERT_REQUIRED
    return context

def create_smtp_connection(smtp_settings):
    """Create and configure SMTP connection with retry logic"""
    retry_count = 0
    while retry_count < MAX_RETRIES:
        try:
            context = create_secure_smtp_context()
            server = smtplib.SMTP(
                smtp_settings['smtp_server'],
                smtp_settings['smtp_port'],
                timeout=SMTP_TIMEOUT
            )
            server.starttls(context=context)
            server.login(smtp_settings['smtp_user'], smtp_settings['smtp_pass'])
            return server
        except (socket_error, smtplib.SMTPException) as e:
            retry_count += 1
            if retry_count == MAX_RETRIES:
                raise
            logger.warning(f"SMTP connection attempt {retry_count} failed: {str(e)}")
            time.sleep(RETRY_DELAY)

def add_hosted_link(html_content: str, hosted_url: str) -> str:
    """Add a link to the hosted version at the top of the newsletter.
    
    Args:
        html_content: Original HTML newsletter content
        hosted_url: URL to the hosted version
        
    Returns:
        str: HTML with hosted link added
    """
    hosted_link = f"""
    <div style="text-align: center; padding: 10px; margin: 10px 0; background-color: #f8fafc; border-radius: 8px;">
        <p style="margin: 0; color: #64748b;">
            Having trouble viewing this email? 
            <a href="{hosted_url}" style="color: #3b82f6; text-decoration: none;">View it in your browser →</a>
        </p>
    </div>
    """
    
    # Insert after the header div
    soup = BeautifulSoup(html_content, 'html.parser')
    header = soup.find('div', class_='header')
    if header:
        header.insert_after(BeautifulSoup(hosted_link, 'html.parser'))
        return str(soup)
    return hosted_link + html_content

def send_email(subject: str, body: str, hosted_url: str = None):
    """Send the newsletter email.
    
    Args:
        subject: Email subject line
        body: HTML content of the email
        hosted_url: Optional URL to hosted version of newsletter
    """
    smtp_settings = setup_email_settings()
    
    # Create message
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = formataddr(('AI Newsletter', smtp_settings['from_email']))
    msg['To'] = smtp_settings['to_email']
    msg['Date'] = formatdate(localtime=True)
    
    # Add hosted link if provided
    if hosted_url:
        body = add_hosted_link(body, hosted_url)
    
    # Attach HTML version
    msg.attach(MIMEText(body, 'html'))
    
    # Create plain text version
    plain_text = strip_html(body)
    msg.attach(MIMEText(plain_text, 'plain'))
    
    # Send email with retry logic
    server = None
    try:
        server = create_smtp_connection(smtp_settings)
        server.send_message(msg)
        logger.info("Email sent successfully")
        
    except Exception as e:
        logger.error(f"Failed to send email: {str(e)}")
        raise
        
    finally:
        if server:
            server.quit()

def strip_html(html_content):
    """Convert HTML to plain text."""
    if not html_content:
        return ""
    
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Remove script and style elements
    for script in soup(["script", "style"]):
        script.decompose()
    
    # Get text and clean up
    text = soup.get_text()
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    
    return '\n'.join(chunk for chunk in chunks if chunk)

def test_send_email():
    """Send a test email to verify configuration."""
    subject = "📧 AI Newsletter - Test Email"
    body = """
    <h1>Test Email</h1>
    <p>This is a test email to verify your newsletter configuration.</p>
    <p>If you received this, your email settings are working correctly!</p>
    """
    
    try:
        send_email(subject=subject, body=body)
        logger.info("Test email sent successfully")
        return True
    except Exception as e:
        logger.error(f"Test email failed: {str(e)}")
        return False

# Initialize email settings when module is imported
setup_email_settings()

# Expose these functions as the public API
__all__ = ['send_email', 'test_send_email', 'setup_email_settings']

if __name__ == "__main__":
    test_send_email()

