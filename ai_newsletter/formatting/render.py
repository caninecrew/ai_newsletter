"""Article rendering and formatting functions."""
from typing import List
from datetime import datetime
from ai_newsletter.core.types import Article
from ai_newsletter.formatting.components import format_summary_block, get_tags_html
from ai_newsletter.formatting.date_utils import format_date
from ai_newsletter.formatting.layout import (
    wrap_with_css, 
    build_header, 
    build_footer, 
    build_empty_newsletter
)
from ai_newsletter.formatting.text_utils import get_key_takeaways
from ai_newsletter.logging_cfg.logger import setup_logger

logger = setup_logger()

def format_article(article: Article, html: bool = False) -> str:
    """Format a single article for the newsletter."""
    title = article.get('title', 'No Title')
    source = article.get('source', {}).get('name', 'Unknown Source')
    date_str = format_date(article.get('published_at', ''))
    description = article.get('description', 'No description available')
    url = article.get('url', '#')
    
    if html:
        # summary_block = format_summary_block(article)
        # tags_block = get_tags_html(article)
        takeaways = get_key_takeaways(article.get('summary', '') or description)
        
        return f"""
        <div class="article">
            <h2 class="article-title"><a href="{url}">{title}</a></h2>
            <p class="article-meta">
                <span class="source">{source}</span> | 
                <span class="date">{date_str}</span>
            </p>
            {takeaways}
            <hr>
        </div>
        """
    
    # Plain text formatting
    text_output = [
        title,
        f"Source: {source}",
        f"Date: {date_str}",
        f"Description: {description}"
    ]
    
    if article.get('summary'):
        text_output.append(f"Summary: {article['summary']}")
    
    text_output.append(f"Link: {url}")
    return "\n".join(text_output)

def build_newsletter(articles: List[Article]) -> str:
    """Build the complete newsletter HTML."""
    if not articles:
        return build_empty_newsletter()
    
    # Format all articles
    articles_html = "\n".join(format_article(article, html=True) for article in articles)
    
    # Combine all sections
    content = f"""
        {build_header()}
        <div class="articles">
            {articles_html}
        </div>
        {build_footer()}
    """
    
    return wrap_with_css(content)