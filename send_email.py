import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr
import os
from dotenv import load_dotenv
from logger_config import setup_logger
import ssl
import certifi

# Set up logger
logger = setup_logger()

# Load environment variables
load_dotenv()

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
    load_dotenv()

    # Load credentials from .env
    email        = os.getenv("SMTP_EMAIL")
    password     = os.getenv("SMTP_PASS")
    smtp_server  = os.getenv("SMTP_SERVER", "mail.postale.io")  # Updated default host
    smtp_port    = int(os.getenv("SMTP_PORT", "587"))           # Default to STARTTLS port
    sender_name  = os.getenv("SENDER_NAME", "Newsletter Bot")

    # Validate required environment variables
    if not email or not password:
        logger.error("Missing required environment variables: SMTP_EMAIL or SMTP_PASS")
        raise ValueError("Missing required environment variables: SMTP_EMAIL or SMTP_PASS")

    subject = "✅ Test Email"
    body    = f"This is a test email sent from {sender_name} using Postale SMTP."

    try:
        logger.info("Sending test email to validate configuration")
        # Ensure secure connection using STARTTLS
        send_email(
            subject=subject,
            body=body,
            recipients=[email],        # send to self
            smtp_settings={
                'host': smtp_server,
                'port': smtp_port,
                'username': email,
                'password': password,
                'sender': email
            }
        )
        logger.info("✅ Test email sent successfully.")
    except Exception as e:
        logger.error(f"❌ Failed to send test email: {e}", exc_info=True)

if __name__ == "__main__":
    test_send_email()

