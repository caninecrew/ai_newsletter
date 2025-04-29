from ai_newsletter.email.sender import send_email
from ai_newsletter.formatting.formatter import build_empty_newsletter
from unittest import mock

def test_send_empty_newsletter():
    """Test sending an empty newsletter."""
    html = build_empty_newsletter()
    text = "No news"
    subject = "Test"

    with mock.patch("smtplib.SMTP_SSL") as mock_smtp:
        assert send_email(html, text, subject)
        mock_smtp.assert_called_once()