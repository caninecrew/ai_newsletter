"""Formatting package exports."""
from ai_newsletter.formatting.components import format_summary_block
from ai_newsletter.formatting.layout import (
    wrap_with_css, 
    build_header, 
    build_footer, 
    build_empty_newsletter
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
    get_tag_html,
    get_personalization_tags_html
)
from ai_newsletter.formatting.text_utils import (
    strip_html,
    get_key_takeaways
)
from ai_newsletter.formatting.render import (
    format_article,
    build_newsletter
)
from ai_newsletter.formatting.template_renderer import (
    render_newsletter,
    get_template_environment
)

__all__ = [
    # Layout components
    'wrap_with_css',
    'build_header',
    'build_footer',
    'build_empty_newsletter',
    
    # Article rendering
    'format_summary_block',
    'format_article',
    'build_newsletter',
    
    # Article processing
    'categorize_article',
    'get_section_description',
    'SECTION_CATEGORIES',
    
    # Date handling
    'format_date',
    'filter_articles_by_date',
    
    # Content processing
    'deduplicate_articles',
    'limit_articles_by_source',
    'is_duplicate',
    'strip_html',
    'get_key_takeaways',
    
    # Tag management
    'identify_tags',
    'get_tag_html',
    'get_personalization_tags_html',
    
    # Template rendering
    'render_newsletter',
    'get_template_environment'
]