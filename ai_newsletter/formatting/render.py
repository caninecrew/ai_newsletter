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

def format_article(article: Dict, html: bool = False) -> str:
    """Format a single article for the email newsletter with concise layout."""
    title = article.get('title', 'No Title')
    source = article.get('source', {}).get('name', 'Unknown Source')
    date = format_date(article.get('published_at', ''))
    url = article.get('url', '#')
    summary = article.get('summary', '')
    category = categorize_article(article)
    
    # Extract 1-2 key bullet points from summary
    bullet_points = []
    if summary:
        # Split into sentences and clean them
        sentences = [s.strip() for s in summary.split('.') if len(s.strip()) > 0]
        # Take 1 bullet if first sentence is long, otherwise take 2
        bullet_points = sentences[:1] if len(sentences[0]) > 100 else sentences[:2]
    
    if html:
        # Get category emoji
        category_emojis = {
            'WORLD_NEWS': '🌍',
            'US_NEWS': '🗽',
            'POLITICS': '🏛️',
            'TECHNOLOGY': '⚡',
            'BUSINESS': '💼',
            'PERSONALIZED': '📌'
        }
        category_emoji = category_emojis.get(category, '📰')
        
        # Format bullet points if any
        bullets_html = ""
        if bullet_points:
            bullets = "".join([f"<li>{point.strip()}.</li>" for point in bullet_points])
            bullets_html = f'<ul class="takeaway-bullets">{bullets}</ul>'
        
        # Add tags with emojis
        tags = get_personalization_tags_html(article)
        
        return f"""
        <div class="article">
            <h3 class="article-title">
                {category_emoji} {title}
            </h3>
            <div class="article-meta">
                {source} • {date} • <a href="{url}" class="read-more">🔗 Read More</a>
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
    extra_count = total_articles - max_total
    more_link = ""
    if extra_count > 0:
        more_link = f'<p><a href="{EMAIL_SETTINGS.get("full_digest_url", "#")}">…and {extra_count} more articles</a></p>'

    # Assemble digest content
    digest_html = f"""
    <div class="digest">
        <h2>🗞️ Daily News Summary</h2>
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
