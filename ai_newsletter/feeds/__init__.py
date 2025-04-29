"""Feed package exports."""
from ai_newsletter.feeds.gnews_client import GNewsAPI, GNewsAPIError
from ai_newsletter.feeds.fetcher import fetch_articles_from_all_feeds, safe_fetch_news_articles
from ai_newsletter.feeds.filters import (
    filter_articles_by_date,
    deduplicate_articles,
    is_duplicate
)

__all__ = [
    'GNewsAPI',
    'GNewsAPIError',
    'fetch_articles_from_all_feeds',
    'safe_fetch_news_articles',
    'filter_articles_by_date',
    'deduplicate_articles',
    'is_duplicate'
]