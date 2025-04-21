import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

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
