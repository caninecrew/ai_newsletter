"""Jinja2 template rendering for newsletter."""
from pathlib import Path
from typing import Dict, List, Any
from jinja2 import Environment, FileSystemLoader, select_autoescape
from ai_newsletter.formatting.date_utils import format_date
from ai_newsletter.formatting.tags import get_personalization_tags_html
from ai_newsletter.formatting.components import format_summary_block
from ai_newsletter.formatting.text_utils import get_key_takeaways

def get_template_environment() -> Environment:
    """Create and configure Jinja2 environment."""
    # Get project root directory (parent of ai_newsletter package)
    project_root = Path(__file__).parent.parent.parent
    template_dir = project_root / 'templates'
    
    env = Environment(
        loader=FileSystemLoader(template_dir),
        autoescape=select_autoescape(['html', 'xml'])
    )
    
    # Register custom filters
    env.filters['format_date'] = format_date
    env.filters['render_tags'] = get_personalization_tags_html
    env.filters['format_summary_block'] = format_summary_block
    env.filters['get_takeaways'] = get_key_takeaways
    
    return env

def render_newsletter(
    articles: List[Dict[str, Any]], 
    date: str,
    max_articles: int = 10,
    hosted_url: str = None
) -> str:
    """Render the newsletter template with provided data.
    
    Args:
        articles: List of article dictionaries
        date: Formatted date string for the newsletter
        max_articles: Maximum number of articles to show
        hosted_url: Optional URL to hosted version of newsletter
        
    Returns:
        str: The rendered HTML newsletter
    """
    env = get_template_environment()
    template = env.get_template('newsletter.html')
    
    return template.render(
        articles=articles[:max_articles],
        date=date,
        total_articles=len(articles),
        max_articles=max_articles,
        hosted_url=hosted_url
    )