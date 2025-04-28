import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
from ai_newsletter.feeds.fetcher import (
    fetch_articles_from_all_feeds,
    should_skip_source,
    force_central,
    normalize_url,
    is_duplicate_article
)

class TestFetchNews(unittest.TestCase):
    def setUp(self):
        pass
        
    def test_should_skip_source(self):
        # Test problematic sources
        self.assertTrue(should_skip_source("https://www.wsj.com/article"))
        self.assertTrue(should_skip_source("https://www.bloomberg.com/news"))
        self.assertTrue(should_skip_source("https://www.nytimes.com/story"))
        
        # Test allowed sources
        self.assertFalse(should_skip_source("https://www.reuters.com/article"))
        self.assertFalse(should_skip_source("https://apnews.com/hub/news"))
        self.assertFalse(should_skip_source("https://www.bbc.com/news"))

    def test_force_central(self):
        # Test UTC time conversion
        utc_time = datetime(2025, 4, 28, 12, 0, tzinfo=timezone.utc)
        central_time = force_central(utc_time)
        self.assertEqual(central_time.hour, 7)  # UTC noon -> 7 AM Central
        
        # Test naive datetime handling
        naive_time = datetime(2025, 4, 28, 12, 0)
        central_time = force_central(naive_time)
        self.assertIsNotNone(central_time.tzinfo)

    def test_normalize_url(self):
        # Test tracking parameter removal
        url = "https://www.example.com/article?utm_source=test&utm_medium=email"
        normalized = normalize_url(url)
        self.assertEqual(normalized, "https://www.example.com/article")
        
        # Test fragment removal
        url = "https://www.example.com/article#section1"
        normalized = normalize_url(url)
        self.assertEqual(normalized, "https://www.example.com/article")

    def test_is_duplicate_article(self):
        article1 = {
            'title': 'Test Article',
            'content': 'This is a test article about something.'
        }
        article2 = {
            'title': 'Test Article',  # Same title
            'content': 'This is a different test article.'  # Different content
        }
        self.assertTrue(is_duplicate_article(article1, article2))
        
        article3 = {
            'title': 'Completely Different',
            'content': 'Totally unrelated content.'
        }
        self.assertFalse(is_duplicate_article(article1, article3))

    @patch('ai_newsletter.feeds.fetcher.feedparser.parse')
    def test_fetch_articles(self, mock_parse):
        mock_feed = MagicMock()
        mock_feed.entries = [
            {
                'title': 'Test Article 1',
                'link': 'https://example.com/1',
                'published': 'Mon, 28 Apr 2025 12:00:00 GMT'
            },
            {
                'title': 'Test Article 2',
                'link': 'https://example.com/2',
                'published': 'Mon, 28 Apr 2025 13:00:00 GMT'
            }
        ]
        mock_parse.return_value = mock_feed
        
        articles = fetch_articles_from_all_feeds(max_articles_per_source=2)
        self.assertTrue(len(articles) > 0)
        self.assertTrue(all('title' in article for article in articles))
        self.assertTrue(all('url' in article for article in articles))

if __name__ == '__main__':
    unittest.main()