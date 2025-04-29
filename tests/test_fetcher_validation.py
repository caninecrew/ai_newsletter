import unittest
from unittest.mock import patch, MagicMock
from ai_newsletter.feeds.fetcher import safe_fetch_news_articles, fetch_news_articles

class TestFetcherValidation(unittest.TestCase):
    
    def setUp(self):
        # Ensure we have a fresh mock for each test
        self.patcher1 = patch('ai_newsletter.feeds.fetcher.fetch_news_articles')
        self.patcher2 = patch('ai_newsletter.feeds.fetcher.logger')
        self.mock_fetch = self.patcher1.start()
        self.mock_logger = self.patcher2.start()
        
        # Set up return value
        self.mock_fetch.return_value = ([], {})  # Return empty articles list and stats dict
        
    def tearDown(self):
        self.patcher1.stop()
        self.patcher2.stop()

    def test_safe_fetch_news_articles_invalid_argument(self):
        """Test that safe_fetch_news_articles correctly filters invalid parameters"""
        # Call with valid and invalid parameters
        safe_fetch_news_articles(max_articles=5, invalid_param="test", another_invalid=123)
        
        # Verify logger warned about invalid parameters
        self.mock_logger.warning.assert_any_call("Ignoring unexpected parameter 'invalid_param' in fetch_news_articles call")
        self.mock_logger.warning.assert_any_call("Ignoring unexpected parameter 'another_invalid' in fetch_news_articles call")
        
        # Verify fetch_news_articles was called with only valid parameters
        self.mock_fetch.assert_called_once_with(max_articles=5)

if __name__ == '__main__':
    unittest.main()