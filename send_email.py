import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_email(subject: str, body: str, to_email: str, from_email: str,
               smtp_server: str, smtp_port: int, login: str, password: str) -> None:
    """
    Sends an email with the given subject and body to the specified recipient.
    Allows exceptions to bubble up for the caller to handle.
    """
    # Create the email message
    msg = MIMEMultipart()
    msg['From'] = from_email
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    # Connect and send
    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(login, password)
        server.send_message(msg)
