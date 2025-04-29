"""Type definitions for articles and metadata."""
from typing import TypedDict, Optional, Dict, Any

class ArticleSource(TypedDict):
    name: str
    url: Optional[str]

class Article(TypedDict):
    title: str
    description: str
    url: str
    published_at: str
    source: ArticleSource
    summary: Optional[str]
    summary_method: Optional[str]
    newsletter_category: Optional[str]
    query_matched: Optional[str]
    tags: Optional[list[str]]