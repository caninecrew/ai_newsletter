"""Tests for fetcher validation logic."""
import unittest
from unittest.mock import patch, MagicMock
from ai_newsletter.feeds.fetcher import safe_fetch_news_articles

class TestFetcherValidation(unittest.TestCase):
    def setUp(self):
        self.patcher = patch('ai_newsletter.feeds.fetcher.fetch_articles_from_all_feeds')
        self.mock_fetch = self.patcher.start()
        self.mock_fetch.return_value = ([], {})  # Return empty articles list and stats dict
        
    def tearDown(self):
        self.patcher.stop()

    @patch('ai_newsletter.feeds.fetcher.logger')
    def test_safe_fetch_news_articles_invalid_argument(self, mock_logger):
        """Test that safe_fetch_news_articles correctly filters invalid parameters"""
        safe_fetch_news_articles(max_articles_per_source=5, invalid_param="test", another_invalid=123)
        
        mock_logger.warning.assert_any_call("Ignoring unexpected parameter 'invalid_param' in fetch_news_articles call")
        mock_logger.warning.assert_any_call("Ignoring unexpected parameter 'another_invalid' in fetch_news_articles call")
        self.mock_fetch.assert_called_once_with(max_articles_per_source=5)

    @patch('ai_newsletter.feeds.fetcher.logger')
    def test_safe_fetch_news_articles_invalid_type(self, mock_logger):
        """Test handling of parameters with invalid types"""
        safe_fetch_news_articles(max_articles_per_source="5", language=123)
        
        mock_logger.warning.assert_any_call("Parameter 'max_articles_per_source' has invalid type. Expected int, got str")
        mock_logger.warning.assert_any_call("Parameter 'language' has invalid type. Expected str, got int")
        self.mock_fetch.assert_called_once_with()

    def test_safe_fetch_news_articles_valid_params(self):
        """Test that valid parameters are passed through correctly"""
        safe_fetch_news_articles(
            max_articles_per_source=5,
            language="en",
            country="us"
        )
        
        self.mock_fetch.assert_called_once_with(
            max_articles_per_source=5,
            language="en",
            country="us"
        )

    def test_safe_fetch_news_articles_error_handling(self):
        """Test error handling when fetch_articles_from_all_feeds raises an exception"""
        self.mock_fetch.side_effect = Exception("Test error")
        
        articles, stats = safe_fetch_news_articles(max_articles_per_source=5)
        
        self.assertEqual(articles, [])
        self.assertEqual(stats, {'error': 'Test error'})

if __name__ == '__main__':
    unittest.main()