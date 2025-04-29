"""Root package exports."""
from ai_newsletter.core.types import Article, ArticleSource
from ai_newsletter.feeds import (
    GNewsAPI,
    fetch_articles_from_all_feeds,
    safe_fetch_news_articles
)
from ai_newsletter.formatting import (
    format_article,
    build_newsletter,
    build_empty_newsletter
)
from ai_newsletter.email.sender import send_email, test_send_email
from ai_newsletter.llm import summarize_article

__all__ = [
    'Article',
    'ArticleSource',
    'GNewsAPI',
    'fetch_articles_from_all_feeds',
    'safe_fetch_news_articles',
    'format_article',
    'build_newsletter',
    'build_empty_newsletter',
    'send_email',
    'test_send_email',
    'summarize_article'
]