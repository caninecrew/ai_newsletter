from ai_newsletter.email.sender import send_email
from ai_newsletter.formatting.formatter import build_empty_newsletter
from unittest import mock
import smtplib
import ssl

def test_send_empty_newsletter():
    """Test sending an empty newsletter with proper SMTP mocking."""
    html = build_empty_newsletter()
    subject = "Test Email"

    # Mock both the SMTP class and SSL context
    with mock.patch('smtplib.SMTP') as mock_smtp, \
         mock.patch('ssl.create_default_context') as mock_ssl_context:
        
        # Set up mock SMTP instance
        smtp_instance = mock_smtp.return_value
        smtp_instance.__enter__.return_value = smtp_instance  # For context manager
        smtp_instance.__exit__.return_value = None  # For context manager
        
        # Set up method returns
        smtp_instance.starttls.return_value = None
        smtp_instance.login.return_value = None
        smtp_instance.send_message.return_value = {}
        
        # Set up SSL context
        ssl_context = mock_ssl_context.return_value
        ssl_context.verify_mode = ssl.CERT_REQUIRED
        ssl_context.check_hostname = True
        
        # Call the function
        success = send_email(subject=subject, body=html)
        
        # Verify success
        assert success is True
        
        # Verify SMTP interactions
        mock_smtp.assert_called_once()
        smtp_instance.starttls.assert_called_once()
        smtp_instance.login.assert_called_once()
        smtp_instance.send_message.assert_called_once()
        
        # Verify context manager was used
        smtp_instance.__enter__.assert_called_once()
        smtp_instance.__exit__.assert_called_once()