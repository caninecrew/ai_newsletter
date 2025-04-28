import re
import pytest
from fetch_news import fetch_articles_from_all_feeds
from config import PRIMARY_NEWS_FEEDS, SECONDARY_FEEDS, SUPPLEMENTAL_FEEDS

def test_feed_tuple_order():
    """Ensure all feed definitions have valid URLs as the first element."""
    all_feeds = {**PRIMARY_NEWS_FEEDS, **SECONDARY_FEEDS, **SUPPLEMENTAL_FEEDS}
    url_re = re.compile(r'^https?://')
    for source_name, feed_url in all_feeds.items():
        assert url_re.match(feed_url), f"Feed URL for {source_name} is invalid: {feed_url}"

def test_fetch_always_returns_tuple():
    """Ensure fetch_articles_from_all_feeds always returns a 2-tuple."""
    articles, stats = fetch_articles_from_all_feeds()
    assert isinstance(articles, list), "First element of the return value should be a list."
    assert isinstance(stats, dict), "Second element of the return value should be a dictionary."