"""Tests for fetcher validation logic."""
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
from ai_newsletter.feeds.fetcher import safe_fetch_news_articles
from ai_newsletter.feeds.filters import (
    filter_articles_by_date,
    is_duplicate,
    deduplicate_articles
)

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

    def test_filter_articles_by_date(self):
        """Test article date filtering"""
        now = datetime.now(timezone.utc)
        articles = [
            {
                'title': 'Old Article',
                'published_at': (now - timezone.timedelta(days=2)).isoformat()
            },
            {
                'title': 'Recent Article',
                'published_at': (now - timezone.timedelta(hours=12)).isoformat()
            }
        ]
        
        start_date = now - timezone.timedelta(days=1)
        filtered = filter_articles_by_date(articles, start_date=start_date)
        
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]['title'], 'Recent Article')

    def test_is_duplicate_detection(self):
        """Test duplicate article detection"""
        article1 = {
            'title': 'Breaking News: Major Event',
            'description': 'A major event has occurred.',
            'url': 'https://example.com/1'
        }
        
        article2 = {
            'title': 'BREAKING: Major Event Unfolds',  # Similar but not identical
            'description': 'A significant event has taken place.',
            'url': 'https://example.com/2'
        }
        
        article3 = {
            'title': 'Completely Different News',
            'description': 'Something else happened.',
            'url': 'https://example.com/3'
        }
        
        # Test similar articles
        self.assertTrue(is_duplicate(article1, article2))
        
        # Test different articles
        self.assertFalse(is_duplicate(article1, article3))
        
        # Test exact duplicates
        self.assertTrue(is_duplicate(article1, article1))

    def test_deduplicate_articles(self):
        """Test article deduplication with source preferences"""
        articles = [
            {
                'title': 'Breaking News',
                'url': 'https://ap.com/1',
                'source': {'name': 'Associated Press'},
                'published_at': '2025-04-29T10:00:00Z'
            },
            {
                'title': 'Breaking News Story',  # Similar title
                'url': 'https://reuters.com/1',
                'source': {'name': 'Reuters'},
                'published_at': '2025-04-29T09:00:00Z'
            },
            {
                'title': 'Different Story',
                'url': 'https://example.com/2',
                'source': {'name': 'Other Source'},
                'published_at': '2025-04-29T08:00:00Z'
            }
        ]
        
        deduped = deduplicate_articles(articles)
        
        # Should keep AP version (preferred source) and the different story
        self.assertEqual(len(deduped), 2)
        self.assertEqual(deduped[0]['source']['name'], 'Associated Press')
        self.assertEqual(deduped[1]['title'], 'Different Story')

if __name__ == '__main__':
    unittest.main()