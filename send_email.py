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
    return context

def send_email(subject, html_content, recipients):
    """
    Send an HTML email with proper SSL/TLS security
    
    Args:
        subject (str): Email subject
        html_content (str): HTML content of the email
        recipients (list): List of recipient email addresses
    """
    # Get email configuration from environment
    smtp_server = os.environ.get('SMTP_SERVER')
    smtp_port = int(os.environ.get('SMTP_PORT', 587))
    smtp_username = os.environ.get('SMTP_USERNAME')
    smtp_password = os.environ.get('SMTP_PASSWORD')
    sender_email = os.environ.get('SENDER_EMAIL')
    sender_name = os.environ.get('SENDER_NAME', 'AI Newsletter')
    
    if not all([smtp_server, smtp_username, smtp_password, sender_email]):
        logger.error("Missing required email configuration in environment variables")
        return False
    
    try:
        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = formataddr((sender_name, sender_email))
        msg['To'] = ', '.join(recipients)
        
        # Attach HTML content
        msg.attach(MIMEText(html_content, 'html'))
        
        # Create secure SSL context
        context = create_secure_smtp_context()
        
        # Create SMTP connection with SSL/TLS
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls(context=context)
            server.login(smtp_username, smtp_password)
            server.send_message(msg)
            
        logger.info(f"Email sent successfully to {len(recipients)} recipients")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send email: {str(e)}")
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
            to_email=email,        # send to self
            from_email=email,
            smtp_server=smtp_server,
            smtp_port=smtp_port,
            login=email,
            password=password,
            use_tls=(smtp_port == 587),  # Use STARTTLS for port 587
            use_ssl=(smtp_port == 465),   # Use SSL for port 465
            is_html=False
        )
        logger.info("✅ Test email sent successfully.")
    except Exception as e:
        logger.error(f"❌ Failed to send test email: {e}", exc_info=True)

if __name__ == "__main__":
    test_send_email()

