from ai_newsletter.email.sender import send_email
from ai_newsletter.formatting.formatter import build_empty_newsletter
from unittest import mock

def test_send_empty_newsletter():
    """Test sending an empty newsletter."""
    html = build_empty_newsletter()
    subject = "Test Email"

    with mock.patch("smtplib.SMTP") as mock_smtp:
        instance = mock_smtp.return_value
        instance.starttls.return_value = None
        instance.login.return_value = None
        instance.send_message.return_value = None
        
        success = send_email(subject=subject, body=html)
        assert success is True
        
        mock_smtp.assert_called_once()
        instance.starttls.assert_called_once()
        instance.login.assert_called_once()
        instance.send_message.assert_called_once()