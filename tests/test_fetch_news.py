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
            (now - timezone.timedelta(hours=3), 'Breaking'),
            (now - timezone.timedelta(hours=12), 'Today'),
            (now - timezone.timedelta(hours=30), 'Yesterday'),
            (now - timezone.timedelta(days=4), 'This Week'),
            (now - timezone.timedelta(days=10), 'Older')
        ]
        
        for date, expected in test_cases:
            with self.subTest(date=date):
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
        self.mock_gnews_instance.get_top_headlines.return_value = []
        
        articles, stats = fetch_articles_from_all_feeds(max_articles_per_source=5)
        
        self.assertTrue(len(articles) > 0, "Should return at least one article")
        article = articles[0]
        self.assertEqual(article['title'], mock_articles[0]['title'])
        self.assertEqual(article['description'], mock_articles[0]['description'])
        self.assertEqual(article['url'], mock_articles[0]['url'])
        self.assertEqual(article['source']['name'], mock_articles[0]['source']['name'])
        self.assertIn('newsletter_category', article)

    def test_fetch_top_headlines(self):
        """Test that top headlines are fetched and properly categorized"""
        now = datetime.now(timezone.utc)
        mock_headlines = [
            {
                'title': 'Top Headline 1',
                'description': 'Breaking News 1',
                'url': 'https://example.com/headline1',
                'published_at': now.isoformat(),
                'source': {'name': 'Top News Source'}
            }
        ]
        
        self.mock_gnews_instance.get_top_headlines.return_value = mock_headlines
        self.mock_gnews_instance.search_news.return_value = []  # No category articles
        
        articles, stats = fetch_articles_from_all_feeds(max_articles_per_source=5)
        
        self.assertTrue(len(articles) > 0, "Should return at least one headline")
        headline = articles[0]
        self.assertEqual(headline['title'], mock_headlines[0]['title'])
        self.assertEqual(headline['newsletter_category'], 'TOP_HEADLINES')
        self.assertEqual(headline['query_matched'], 'top_headlines')

    def test_fetch_articles_error_handling(self):
        """Test error handling during article fetching"""
        self.mock_gnews_instance.search_news.side_effect = Exception("API Error")
        self.mock_gnews_instance.get_top_headlines.side_effect = Exception("API Error")
        
        articles, stats = fetch_articles_from_all_feeds(max_articles_per_source=5)
        
        self.assertEqual(len(articles), 0)
        self.assertEqual(stats['total_articles'], 0)
        self.assertTrue(len(stats['failed_queries']) > 0)
        self.assertIn('TOP_HEADLINES:top_headlines', stats['failed_queries'])

    def test_24hour_filtering(self):
        """Test that articles older than 24 hours are filtered out"""
        now = datetime.now(timezone.utc)
        old_date = (now - timezone.timedelta(days=2)).isoformat()
        fresh_date = (now - timezone.timedelta(hours=12)).isoformat()
        
        mock_headlines = [
            {
                'title': 'Old Headline',
                'url': 'https://example.com/old',
                'published_at': old_date,
                'source': {'name': 'News Source'}
            },
            {
                'title': 'Fresh Headline',
                'url': 'https://example.com/fresh',
                'published_at': fresh_date,
                'source': {'name': 'News Source'}
            }
        ]
        
        self.mock_gnews_instance.get_top_headlines.return_value = mock_headlines
        self.mock_gnews_instance.search_news.return_value = []
        
        articles, stats = fetch_articles_from_all_feeds()
        
        self.assertEqual(len(articles), 1, "Should only include the fresh article")
        self.assertEqual(articles[0]['title'], 'Fresh Headline')

if __name__ == '__main__':
    unittest.main()