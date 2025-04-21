import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
import os

def send_email(subject: str, body: str, to_email: str, from_email: str,
               smtp_server: str, smtp_port: int, login: str, password: str,
               use_tls: bool = False, use_ssl: bool = False) -> None:
    """
    Sends an email with the given subject and body to the specified recipient.
    Allows exceptions to bubble up for the caller to handle.
    """
    try:
        if use_ssl:
            # Connect using SSL
            server = smtplib.SMTP_SSL(smtp_server, smtp_port)
        else:
            # Connect without SSL
            server = smtplib.SMTP(smtp_server, smtp_port)
            if use_tls:
                server.starttls()  # Upgrade to secure connection

        # Log in to the SMTP server
        server.login(login, password)

        # Create the email message
        msg = MIMEMultipart()
        msg['From'] = from_email
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        # Send the email
        server.send_message(msg)
        server.quit()
    except Exception as e:
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
        raise ValueError("Missing required environment variables: SMTP_EMAIL or SMTP_PASS")

    subject = "✅ Test Email"
    body    = f"This is a test email sent from {sender_name} using Postale SMTP."

    try:
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
            use_ssl=(smtp_port == 465)   # Use SSL for port 465
        )
        print("✅ Test email sent successfully.")
    except Exception as e:
        print(f"❌ Failed to send test email: {e}")

if __name__ == "__main__":
    test_send_email()

