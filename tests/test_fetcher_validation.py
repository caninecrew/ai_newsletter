import unittest
from unittest.mock import patch, MagicMock

class TestFetcherValidation(unittest.TestCase):
    def setUp(self):
        self.patcher = patch('ai_newsletter.feeds.fetcher.fetch_news_articles')
        self.mock_fetch = self.patcher.start()
        self.mock_fetch.return_value = ([], {})  # Return empty articles list and stats dict
        
    def tearDown(self):
        self.patcher.stop()

    @patch('ai_newsletter.feeds.fetcher.logger')
    def test_safe_fetch_news_articles_invalid_argument(self, mock_logger):
        """Test that safe_fetch_news_articles correctly filters invalid parameters"""
        from ai_newsletter.feeds.fetcher import safe_fetch_news_articles
        
        # Call with valid and invalid parameters
        safe_fetch_news_articles(max_articles=5, invalid_param="test", another_invalid=123)
        
        # Verify logger warned about invalid parameters
        mock_logger.warning.assert_any_call("Ignoring unexpected parameter 'invalid_param' in fetch_news_articles call")
        mock_logger.warning.assert_any_call("Ignoring unexpected parameter 'another_invalid' in fetch_news_articles call")
        
        # Verify fetch_news_articles was called with only valid parameters
        self.mock_fetch.assert_called_once_with(max_articles=5)

if __name__ == '__main__':
    unittest.main()