"""Feed module exports."""
from ai_newsletter.feeds.fetcher import (
    fetch_articles_from_all_feeds,
    safe_fetch_news_articles
)
from ai_newsletter.feeds.gnews_api import GNewsAPI, GNewsAPIError

__all__ = [
    'fetch_articles_from_all_feeds',
    'safe_fetch_news_articles',
    'GNewsAPI',
    'GNewsAPIError'
]