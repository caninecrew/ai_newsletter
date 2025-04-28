import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr, formatdate
import os
from dotenv import load_dotenv
from logger_config import setup_logger, DEFAULT_TZ
import ssl
import certifi
from config import EMAIL_SETTINGS
import time
from socket import error as socket_error
from datetime import datetime
import pytz

# Set up logger
logger = setup_logger()

# Load environment variables
load_dotenv()

# Constants for retry settings
MAX_RETRIES = 3
RETRY_DELAY = 5
KEEPALIVE_INTERVAL = 60
SMTP_TIMEOUT = 30

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

def send_email(subject, body, recipients, smtp_settings, retry_count=0):
    """
    Send an email with proper timezone handling for headers.
    
    Args:
        subject: Email subject
        body: Email body (HTML)
        recipients: List of recipient email addresses
        smtp_settings: Dictionary containing SMTP configuration
        retry_count: Current retry attempt number
    
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    server = None
    try:
        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = formataddr(('AI Newsletter', smtp_settings['sender']))
        msg['To'] = ', '.join(recipients)
        
        # Set timezone-aware Date header
        now = datetime.now(DEFAULT_TZ)
        msg['Date'] = formatdate(float(now.timestamp()), localtime=True)
        
        # Add body
        msg.attach(MIMEText(body, 'html'))

        # Create SMTP connection and send
        server = create_smtp_connection(smtp_settings)
        server.send_message(msg)
        
        return True
        
    except (smtplib.SMTPServerDisconnected, socket_error) as e:
        if retry_count < MAX_RETRIES:
            logger.warning(f"SMTP connection lost: {e}. Retrying ({retry_count + 1}/{MAX_RETRIES})")
            time.sleep(RETRY_DELAY * (retry_count + 1))
            return send_email(subject, body, recipients, smtp_settings, retry_count + 1)
        else:
            raise
            
    except smtplib.SMTPException as e:
        if retry_count < MAX_RETRIES:
            logger.warning(f"SMTP error: {e}. Retrying ({retry_count + 1}/{MAX_RETRIES})")
            time.sleep(RETRY_DELAY * (retry_count + 1))
            return send_email(subject, body, recipients, smtp_settings, retry_count + 1)
        else:
            raise
            
    except Exception as e:
        logger.error(f"Failed to send email: {e}", exc_info=True)
        return False
            
    finally:
        if server:
            try:
                server.quit()
            except Exception as e:
                logger.warning(f"Error closing SMTP connection: {e}")

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
            body=body,
            recipients=EMAIL_SETTINGS['recipients'],
            smtp_settings=EMAIL_SETTINGS['smtp']
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

