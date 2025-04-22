import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
import os
from logger_config import setup_logger

# Set up logger
logger = setup_logger()

def send_email(subject: str, body: str, to_email: str, from_email: str,
               smtp_server: str, smtp_port: int, login: str, password: str,
               use_tls: bool = False, use_ssl: bool = False, 
               is_html: bool = False) -> None:
    """
    Sends an email with the given subject and body to the specified recipient.
    Allows exceptions to bubble up for the caller to handle.
    """
    try:
        logger.info(f"Preparing to send email to {to_email}")
        logger.debug(f"SMTP Server: {smtp_server}:{smtp_port}, TLS: {use_tls}, SSL: {use_ssl}")
        
        if use_ssl:
            # Connect using SSL
            logger.debug("Connecting with SSL")
            server = smtplib.SMTP_SSL(smtp_server, smtp_port)
        else:
            # Connect without SSL
            logger.debug("Connecting without SSL")
            server = smtplib.SMTP(smtp_server, smtp_port)
            if use_tls:
                logger.debug("Starting TLS")
                server.starttls()  # Upgrade to secure connection

        # Log in to the SMTP server
        logger.debug(f"Logging in as {login}")
        server.login(login, password)

        # Create the email message
        msg = MIMEMultipart('alternative')
        msg['From'] = from_email
        msg['To'] = to_email
        msg['Subject'] = subject
        
        logger.debug(f"Email subject: {subject}")

        # Attach plain text and HTML versions if HTML is provided
        if is_html:
            logger.debug("Creating multipart HTML/plain email")
            # Create a plain text version as fallback
            plain_text = body.replace('<br>', '\n').replace('<p>', '').replace('</p>', '\n\n')
            plain_text = ''.join(c for c in plain_text if ord(c) < 128)  # Remove non-ASCII chars
            msg.attach(MIMEText(plain_text, 'plain'))
            msg.attach(MIMEText(body, 'html'))
        else:
            logger.debug("Creating plain text email")
            msg.attach(MIMEText(body, 'plain'))

        # Send the email
        logger.debug("Sending email")
        server.send_message(msg)
        logger.info(f"Email sent successfully to {to_email}")
        server.quit()
        logger.debug("SMTP connection closed")
    except Exception as e:
        logger.error(f"Failed to send email: {e}", exc_info=True)
        raise RuntimeError(f"Failed to send email: {e}")
    
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

