"""Formatting package exports."""
from ai_newsletter.formatting.components import (
    format_summary_block, 
    get_tags_html
)
from ai_newsletter.formatting.layout import (
    wrap_with_css, 
    build_header, 
    build_footer, 
    build_empty_newsletter
)
from ai_newsletter.formatting.render import (
    format_article, 
    build_newsletter
)
from ai_newsletter.formatting.categorization import (
    categorize_article,
    get_section_description,
    SECTION_CATEGORIES
)
from ai_newsletter.formatting.date_utils import (
    format_date,
    filter_articles_by_date
)
from ai_newsletter.formatting.deduplication import (
    deduplicate_articles,
    limit_articles_by_source,
    is_duplicate
)
from ai_newsletter.formatting.tags import (
    identify_tags,
    get_personalization_tags_html
)
from ai_newsletter.formatting.text_utils import (
    strip_html,
    get_key_takeaways
)
from ai_newsletter.formatting.formatter import (
    format_article,
    format_articles
)

__all__ = [
    # Components
    'format_summary_block',
    'get_tags_html',
    
    # Layout
    'wrap_with_css',
    'build_header',
    'build_footer',
    'build_empty_newsletter',
    
    # Render
    'format_article',
    'build_newsletter',
    
    # Categorization
    'categorize_article',
    'get_section_description',
    'SECTION_CATEGORIES',
    
    # Date utils
    'format_date',
    'filter_articles_by_date',
    
    # Deduplication
    'deduplicate_articles',
    'limit_articles_by_source',
    'is_duplicate',
    
    # Tags
    'identify_tags',
    'get_personalization_tags_html',
    
    # Text utils
    'strip_html',
    'get_key_takeaways',
    
    # High-level formatting
    'format_article',
    'format_articles'
]