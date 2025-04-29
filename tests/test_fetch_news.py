"""Tests for news fetching functionality."""
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
from ai_newsletter.feeds.fetcher import (
    fetch_articles_from_all_feeds,
    categorize_article_age
)

class TestFetchNews(unittest.TestCase):
    def setUp(self):
        self.gnews_patcher = patch('ai_newsletter.feeds.fetcher.GNewsAPI')
        self.mock_gnews = self.gnews_patcher.start()
        self.mock_gnews_instance = self.mock_gnews.return_value

    def tearDown(self):
        self.gnews_patcher.stop()

    def test_categorize_article_age(self):
        """Test article age categorization"""
        now = datetime.now(timezone.utc)
        
        test_cases = [
            (now.timestamp(), 'Breaking'),
            ((now.timestamp() - 3600 * 4), 'Very Recent'),
            ((now.timestamp() - 3600 * 8), 'Recent'),
            ((now.timestamp() - 3600 * 20), 'Today'),
            ((now.timestamp() - 3600 * 30), 'Yesterday'),
            ((now.timestamp() - 3600 * 24 * 4), 'This Week'),
            ((now.timestamp() - 3600 * 24 * 10), 'Older'),
            (None, 'Unknown')
        ]
        
        for timestamp, expected in test_cases:
            with self.subTest(timestamp=timestamp):
                if timestamp:
                    date = datetime.fromtimestamp(timestamp, tz=timezone.utc)
                else:
                    date = None
                self.assertEqual(categorize_article_age(date), expected)

    def test_fetch_articles_metadata_handling(self):
        """Test that article metadata from GNews API is properly handled"""
        mock_articles = [
            {
                'title': 'Test Article 1',
                'description': 'Test Description 1',
                'url': 'https://example.com/1',
                'published_at': datetime.now(timezone.utc).isoformat(),
                'source': {'name': 'Test Source 1'}
            }
        ]
        
        self.mock_gnews_instance.search_news.return_value = mock_articles
        
        articles, stats = fetch_articles_from_all_feeds(max_articles_per_source=5)
        
        self.assertTrue(len(articles) > 0, "Should return at least one article")
        article = articles[0]
        self.assertEqual(article['title'], mock_articles[0]['title'])
        self.assertEqual(article['description'], mock_articles[0]['description'])
        self.assertEqual(article['url'], mock_articles[0]['url'])
        self.assertEqual(article['source']['name'], mock_articles[0]['source']['name'])
        self.assertIn('age_category', article)
        self.assertIn('newsletter_category', article)

    def test_fetch_articles_error_handling(self):
        """Test error handling during article fetching"""
        self.mock_gnews_instance.search_news.side_effect = Exception("API Error")
        
        articles, stats = fetch_articles_from_all_feeds(max_articles_per_source=5)
        
        self.assertEqual(len(articles), 0)
        self.assertEqual(stats['total_articles'], 0)
        self.assertTrue(len(stats['failed_queries']) > 0)

if __name__ == '__main__':
    unittest.main()