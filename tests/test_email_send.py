from ai_newsletter.email.sender import send_email
from ai_newsletter.formatting.formatter import build_empty_newsletter
from unittest import mock
import smtplib
import ssl

class MockSMTP:
    """Mock SMTP class with all necessary attributes and methods."""
    def __init__(self, *args, **kwargs):
        self.local_hostname = "localhost"
        self.ehlo_resp = "250 localhost"
        
    def __enter__(self):
        return self
        
    def __exit__(self, *args):
        return None
        
    def starttls(self, *args, **kwargs):
        return None
        
    def login(self, *args, **kwargs):
        return None
        
    def send_message(self, *args, **kwargs):
        return {}
        
    def quit(self):
        return None

def test_send_empty_newsletter():
    """Test sending an empty newsletter with proper SMTP mocking."""
    html = build_empty_newsletter()
    subject = "Test Email"

    # Mock both SMTP and SMTP_SSL classes
    with mock.patch('smtplib.SMTP', MockSMTP) as mock_smtp, \
         mock.patch('smtplib.SMTP_SSL', MockSMTP) as mock_smtp_ssl, \
         mock.patch('ssl.create_default_context') as mock_ssl_context:
        
        # Set up SSL context
        ssl_context = mock_ssl_context.return_value
        ssl_context.verify_mode = ssl.CERT_REQUIRED
        ssl_context.check_hostname = True
        
        # Test with regular SMTP (port 587)
        success = send_email(
            subject=subject, 
            body=html, 
            smtp_settings={'host': 'smtp.test.com', 'port': 587, 'username': 'test', 'password': 'test', 'sender': 'test@test.com'}
        )
        assert success is True
        assert mock_smtp.called
        assert not mock_smtp_ssl.called
        
        # Reset mocks
        mock_smtp.reset_mock()
        mock_smtp_ssl.reset_mock()
        
        # Test with SMTP_SSL (port 465)
        success = send_email(
            subject=subject, 
            body=html,
            smtp_settings={'host': 'smtp.test.com', 'port': 465, 'username': 'test', 'password': 'test', 'sender': 'test@test.com'}
        )
        assert success is True
        assert mock_smtp_ssl.called
        assert not mock_smtp.called