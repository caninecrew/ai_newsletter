from dotenv import load_dotenv
import os
from send_email import send_email

def test_send_email():
    """
    Sends a test email to verify the email sending functionality.
    """
    load_dotenv()

    # Load credentials from .env
    email        = os.getenv("SMTP_EMAIL")
    password     = os.getenv("SMTP_PASS")
    smtp_server  = os.getenv("SMTP_SERVER", "smtp.postale.io")
    smtp_port    = int(os.getenv("SMTP_PORT", "587"))
    sender_name  = os.getenv("SENDER_NAME", "Newsletter Bot")

    # Validate required environment variables
    if not email or not password:
        raise ValueError("Missing required environment variables: SMTP_EMAIL or SMTP_PASS")

    subject = "✅ Test Email"
    body    = f"This is a test email sent from {sender_name} using Postale SMTP."

    try:
        send_email(
            subject=subject,
            body=body,
            to_email=email,        # send to self
            from_email=email,
            smtp_server=smtp_server,
            smtp_port=smtp_port,
            login=email,
            password=password
        )
        print("✅ Test email sent successfully.")
    except Exception as e:
        print(f"❌ Failed to send test email: {e}")

if __name__ == "__main__":
    test_send_email()
