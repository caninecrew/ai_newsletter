"""Direct SMTP test script that bypasses the main email sending logic."""

import os
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr, formatdate
import logging
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_smtp_direct():
    """Test SMTP connection and sending directly."""
    load_dotenv()
    
    # Get settings from environment
    settings = {
        'host': os.getenv('SMTP_SERVER'),
        'port': int(os.getenv('SMTP_PORT', '587')),
        'username': os.getenv('SMTP_EMAIL'),
        'password': os.getenv('SMTP_PASS'),
        'sender': os.getenv('SMTP_EMAIL'),
        'recipient': os.getenv('RECIPIENT_EMAIL')
    }
    
    # Validate settings
    missing = [k for k, v in settings.items() if not v]
    if missing:
        raise ValueError(f"Missing required settings: {', '.join(missing)}")
    
    # Create message
    msg = MIMEMultipart('alternative')
    msg['Subject'] = "SMTP Direct Test"
    msg['From'] = formataddr(("SMTP Test", settings['sender']))
    msg['To'] = settings['recipient']
    msg['Date'] = formatdate(localtime=True)
    
    text = "This is a direct SMTP test."
    msg.attach(MIMEText(text, 'plain', 'utf-8'))
    
    # Create SSL context
    context = ssl.create_default_context()
    
    try:
        # For port 465, use SMTP_SSL
        if settings['port'] == 465:
            logger.info(f"Connecting to {settings['host']}:{settings['port']} using SSL")
            with smtplib.SMTP_SSL(settings['host'], settings['port'], context=context) as server:
                server.set_debuglevel(1)
                
                # Authenticate
                logger.info(f"Authenticating as {settings['username']}")
                server.login(settings['username'], settings['password'])
                
                # Send message
                logger.info(f"Sending test email to {settings['recipient']}")
                server.send_message(msg)
                
                logger.info("Test email sent successfully!")
        
        # For other ports (587, 25), use SMTP with STARTTLS
        else:
            logger.info(f"Connecting to {settings['host']}:{settings['port']} using STARTTLS")
            with smtplib.SMTP(settings['host'], settings['port']) as server:
                server.set_debuglevel(1)
                
                # Start TLS
                logger.info("Starting TLS")
                server.starttls(context=context)
                
                # Authenticate
                logger.info(f"Authenticating as {settings['username']}")
                server.login(settings['username'], settings['password'])
                
                # Send message
                logger.info(f"Sending test email to {settings['recipient']}")
                server.send_message(msg)
                
                logger.info("Test email sent successfully!")
            
    except Exception as e:
        logger.exception("Failed to send test email")
        raise

if __name__ == "__main__":
    test_smtp_direct()