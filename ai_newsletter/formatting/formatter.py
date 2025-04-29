"""High-level formatting coordination."""
from typing import List, Dict
from ai_newsletter.logging_cfg.logger import setup_logger
from ai_newsletter.config.settings import EMAIL_SETTINGS
from ai_newsletter.formatting.categorization import categorize_article
from ai_newsletter.formatting.date_utils import format_date, filter_articles_by_date
from ai_newsletter.formatting.deduplication import deduplicate_articles, limit_articles_by_source
from ai_newsletter.formatting.tags import get_personalization_tags_html, identify_tags
from ai_newsletter.formatting.text_utils import strip_html, get_key_takeaways

logger = setup_logger()

def format_article(article: Dict, html: bool = False) -> str:
    """Format a single article for the email newsletter."""
    title = article.get('title', 'No Title')
    source = article.get('source', {}).get('name', 'Unknown Source')
    date = format_date(article.get('published_at', ''))
    description = article.get('description', 'No description available')
    url = article.get('url', '#')
    summary = article.get('summary', '')
    tags = get_personalization_tags_html(article)
    
    # Handle HTML formatting
    if html:
        summary_html = f'<p class="article-summary">{summary}</p>' if summary else ''
        takeaways = get_key_takeaways(summary or description)
        return f"""
        <div class="article">
            <h2><a href="{url}">{title}</a></h2>
            <p class="meta">
                <span class="source">{source}</span> | 
                <span class="date">{date}</span>
            </p>
            {tags}
            <p class="description">{description}</p>
            {summary_html}
            {takeaways}
            <hr>
        </div>
        """
    
    # Plain text formatting
    text_output = f"""
{title}
Source: {source}
Date: {date}
{description}"""

    if summary:
        text_output += f"\nSummary: {summary}"
        
    text_output += f"\nLink: {url}"
    return text_output

def format_articles(articles: List[Dict], html: bool = False) -> str:
    """Format a list of articles into a single string."""
    if not articles:
        return "No articles to display." if not html else "<p>No articles to display.</p>"
    
    # Limit articles per source to maintain balance
    max_articles_per_source = EMAIL_SETTINGS.get("max_articles_per_source", 3)
    articles = limit_articles_by_source(articles, max_per_source=max_articles_per_source)
    articles = deduplicate_articles(articles)
    
    # Format all articles
    formatted_articles = []
    for article in articles:
        formatted_articles.append(format_article(article, html=html))
    
    if html:
        return "\n".join(formatted_articles)
    else:
        return "\n---\n".join(formatted_articles)