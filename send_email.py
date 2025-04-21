import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_email(subject, body, to_email, from_email, smtp_server, smtp_port, login, password):
    """
    Sends an email with the given subject and body to the specified recipient.

    Args:
        subject (str): The subject of the email.
        body (str): The body content of the email.
        to_email (str): The recipient's email address.
        from_email (str): The sender's email address.
        smtp_server (str): The SMTP server address.
        smtp_port (int): The SMTP server port.
        login (str): The login username for the SMTP server.
        password (str): The password for the SMTP server.

    Returns:
        None
    """
    try:
        # Create the email message
        msg = MIMEMultipart()
        msg['From'] = from_email
        msg['To'] = to_email
        msg['Subject'] = subject

        # Attach the email body
        msg.attach(MIMEText(body, 'plain'))

        # Connect to the SMTP server and send the email
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()  # Upgrade the connection to secure
            server.login(login, password)
            server.send_message(msg)

        print(f"Email sent successfully to {to_email}")

    except Exception as e:
        print(f"Failed to send email: {e}")