"""Type definitions for articles and metadata."""
from typing import TypedDict, Optional, Dict, Any
from datetime import datetime

class ArticleSource(TypedDict):
    name: str
    url: Optional[str]
    category: Optional[str]  # Political leaning or type (e.g., LEFT_LEANING, CENTER)
    reliability_score: Optional[float]  # Source reliability score

class ArticleMetadata(TypedDict):
    """Metadata for article date and source tracking."""
    date_extracted: bool  # Whether date was successfully extracted
    date_confidence: float  # Confidence in date extraction (0-1)
    original_date: Optional[str]  # Original date string before parsing
    source_confidence: float  # Confidence in source identification
    extracted_from_url: bool  # Whether source was extracted from URL

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
    metadata: Optional[ArticleMetadata]  # Additional metadata like author, section, etc.
    date_extracted: bool  # Flag indicating if date was successfully extracted
    date_confidence: float  # Confidence score for date extraction (0-1)
    original_date_string: Optional[str]  # Original date string before parsing