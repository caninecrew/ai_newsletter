import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr
import os
from dotenv import load_dotenv
from logger_config import setup_logger
import ssl
import certifi
from config import EMAIL_SETTINGS

# Set up logger
logger = setup_logger()

# Load environment variables
load_dotenv()

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

def send_email(subject, body, recipients, smtp_settings):
    """Send email with secure SSL configuration"""
    try:
        msg = MIMEMultipart()
        msg['Subject'] = subject
        msg['From'] = smtp_settings['sender']
        msg['To'] = ', '.join(recipients)
        msg.attach(MIMEText(body, 'html'))

        # Create secure SSL context
        context = create_secure_smtp_context()
        
        with smtplib.SMTP(smtp_settings['host'], smtp_settings['port']) as server:
            server.starttls(context=context)
            server.login(smtp_settings['username'], smtp_settings['password'])
            server.send_message(msg)
            
        logger.info(f"Successfully sent email to {len(recipients)} recipients")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return False

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

