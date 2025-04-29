from ai_newsletter.email.sender import send_email
from ai_newsletter.formatting.formatter import build_empty_newsletter
from unittest.mock import MagicMock, patch
import smtplib
import ssl

def create_mock_smtp():
    """Create a properly configured SMTP mock."""
    mock = MagicMock()
    mock.local_hostname = "localhost"
    mock.ehlo_resp = "250 localhost"
    mock.noop.return_value = (250, b'250 OK')
    mock.login.return_value = None
    mock.starttls.return_value = None
    mock.send_message.return_value = {}
    mock.__enter__.return_value = mock
    mock.__exit__.return_value = None
    return mock

def test_send_empty_newsletter():
    """Test sending an empty newsletter with proper SMTP mocking."""
    html = build_empty_newsletter()
    subject = "Test Email"

    # Create mock instances
    mock_smtp = create_mock_smtp()
    mock_smtp_ssl = create_mock_smtp()
    
    # Mock both SMTP and SMTP_SSL classes
    with patch('smtplib.SMTP', return_value=mock_smtp) as smtp_class, \
         patch('smtplib.SMTP_SSL', return_value=mock_smtp_ssl) as smtp_ssl_class, \
         patch('ssl.create_default_context') as mock_ssl_context:
        
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
        assert smtp_class.called
        assert not smtp_ssl_class.called
        
        # Reset mocks
        smtp_class.reset_mock()
        smtp_ssl_class.reset_mock()
        
        # Test with SMTP_SSL (port 465)
        success = send_email(
            subject=subject, 
            body=html,
            smtp_settings={'host': 'smtp.test.com', 'port': 465, 'username': 'test', 'password': 'test', 'sender': 'test@test.com'}
        )
        assert success is True
        assert smtp_ssl_class.called
        assert not smtp_class.called