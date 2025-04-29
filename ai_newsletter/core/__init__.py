"""Core package exports."""
from ai_newsletter.core.types import Article, ArticleSource
from ai_newsletter.core.constants import (
    SECTION_CATEGORIES,
    TAG_EMOJIS,
    NEWS_SOURCE_CATEGORIES,
    AgeCategory,
    INTEREST_KEYWORDS
)

__all__ = [
    'Article',
    'ArticleSource',
    'SECTION_CATEGORIES',
    'TAG_EMOJIS',
    'NEWS_SOURCE_CATEGORIES',
    'AgeCategory',
    'INTEREST_KEYWORDS'
]