"""Article rendering and formatting functions."""
from typing import List, Dict, DefaultDict
from datetime import datetime
from collections import defaultdict
from ai_newsletter.core.types import Article
from ai_newsletter.config.settings import EMAIL_SETTINGS
from ai_newsletter.formatting.components import format_summary_block
from ai_newsletter.formatting.date_utils import format_date
from ai_newsletter.formatting.layout import (
    wrap_with_css,
    build_header,
    build_footer,
    build_empty_newsletter
)
from ai_newsletter.formatting.text_utils import get_key_takeaways
from ai_newsletter.formatting.categorization import categorize_article
from ai_newsletter.formatting.deduplication import deduplicate_articles
from ai_newsletter.formatting.tags import get_personalization_tags_html
from ai_newsletter.logging_cfg.logger import setup_logger

logger = setup_logger()

def format_article(article: Dict, html: bool = False, max_takeaways: int = 2) -> str:
    """Format a single article with a clean, minimal layout."""
    title = article.get('title', 'No Title')
    source = article.get('source', {}).get('name', 'Unknown Source')
    date = format_date(article.get('published_at', ''))
    url = article.get('url', '#')
    summary = article.get('summary', '')
    
    # Extract bullet points from summary
    bullet_points = []
    if summary:
        sentences = [s.strip() for s in summary.split('.') if len(s.strip()) > 0]
        # Take 1 bullet if first sentence is long, otherwise take up to max_takeaways
        bullet_points = sentences[:1] if len(sentences[0]) > 100 else sentences[:max_takeaways]
    
    if html:
        # Format bullet points if any
        bullets_html = ""
        if bullet_points:
            bullets = "\n".join([f"<li>{point.strip()}.</li>" for point in bullet_points])
            bullets_html = f'<ul class="takeaway-bullets">{bullets}</ul>'
        
        # Add tags with emojis
        tags = get_personalization_tags_html(article)
        
        return f"""
        <div class="article">
            <h3 class="article-title">{title}</h3>
            <div class="article-meta">
                {source} • {date} • <a href="{url}" class="read-more">🔗 Read Full Article</a>
            </div>
            {tags}
            {bullets_html}
        </div>
        """
    
    # Plain text format
    return f"{title}\nSource: {source} | {date}\nLink: {url}"

def build_newsletter(articles: List[Article]) -> str:
    """Build a complete newsletter with clean formatting and no category sections."""
    if not articles:
        return build_empty_newsletter()

    # Limit total articles and deduplicate
    max_total = EMAIL_SETTINGS.get("max_articles_total", 10)
    articles = deduplicate_articles(articles)
    total_articles = len(articles)
    display_articles = articles[:max_total]

    # Build main article section
    articles_html = "\n".join([
        format_article(a, html=True, max_takeaways=2) for a in display_articles
    ])

    # Add a "more articles" link if needed
    more_link = ""
    if total_articles > max_total:
        more_link = f"""
        <div class="more-stories">
            <p>...and {total_articles - max_total} more stories. <a href="#">View full digest →</a></p>
        </div>
        """

    # Assemble digest content
    digest_html = f"""
    <div class="digest">
        <h2>Today's Key Stories</h2>
        {articles_html}
        {more_link}
    </div>
    """

    # Final content layout
    content = f"""
        {build_header()}
        {digest_html}
        {build_footer()}
    """

    return wrap_with_css(content)
