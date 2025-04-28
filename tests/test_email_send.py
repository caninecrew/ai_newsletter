import send_email
import formatter
from unittest import mock

def test_send_empty_newsletter():
    """Test sending an empty newsletter."""
    html = formatter.build_empty_newsletter()
    text = "No news"
    subject = "Test"

    with mock.patch("smtplib.SMTP_SSL") as mock_smtp:
        assert send_email.send_newsletter(html, text, subject)
        mock_smtp.assert_called_once()