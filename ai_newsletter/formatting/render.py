"""Article rendering and formatting functions."""
from typing import List, Dict, DefaultDict
from datetime import datetime
from collections import defaultdict
from bs4 import BeautifulSoup
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
    """Format a single article with enhanced metadata display."""
    title = article.get('title', 'No Title')
    url = article.get('url', '#')
    summary = article.get('summary', '')
    
    # Format date and get metadata
    date, metadata = format_date(article)
    
    # Get source information
    source_data = article.get('source', {})
    source_name = source_data.get('name', 'Unknown Source')
    source_category = source_data.get('category', '')
    source_reliability = source_data.get('reliability_score', None)
    
    # Date confidence indicator
    date_indicator = ""
    if not metadata['date_extracted']:
        date_indicator = ' <span class="date-status low">(Estimated)</span>'
    elif metadata['date_confidence'] < 0.7:
        date_indicator = f' <span class="date-status medium">(~{metadata["date_confidence"]:.0%} confident)</span>'
    
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
        
        # Generate article HTML with inline styles for better email client compatibility
        return f"""
        <div class="article" style="padding: 20px 0; border-bottom: 1px solid #e2e8f0;">
            <h3 class="article-title" style="margin: 0 0 8px 0; font-size: 16px; font-weight: 600; color: #1a202c; line-height: 1.4;">{title}</h3>
            <div class="article-meta" style="font-size: 14px; color: #64748b; margin-bottom: 12px;">
                <a href="{url}" class="read-more" style="color: #3b82f6; text-decoration: none; font-weight: 500;">🔗 Read Full Article</a>
            </div>
            <div class="tags" style="margin: 10px 0;">{tags}</div>
            <div class="key-takeaways" style="background-color: #f8f9fa; border-left: 3px solid #3498db; padding: 10px 15px; margin: 15px 0;">
                <h4 style="margin: 0 0 10px 0; color: #2c3e50;">Key Takeaways</h4>
                {bullets_html}
            </div>
        </div>
        """
    
    # Plain text format with structured layout
    text_bullets = "\n".join([f"* {point.strip()}." for point in bullet_points])
    return f"""
{title}
Source: {source_name} | {date}
Link: {url}

Key Takeaways:
{text_bullets}

{summary}
"""

def prettify_html(html: str) -> str:
    """Clean up and prettify HTML code."""
    soup = BeautifulSoup(html, 'html.parser')
    return soup.prettify()

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
        <div class="more-stories" style="text-align: center; padding: 16px; margin-top: 24px; border-top: 1px solid #e2e8f0; color: #64748b; font-size: 14px;">
            <p>...and {total_articles - max_total} more stories. <a href="#" style="color: #3b82f6; text-decoration: none; font-weight: 500;">View full digest →</a></p>
        </div>
        """

    # Assemble digest content with inline styles
    digest_html = f"""
    <div class="digest" style="background-color: #ffffff; border-radius: 8px; padding: 24px; margin-bottom: 24px; box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);">
        <h2 style="margin: 0 0 24px 0; font-size: 20px; font-weight: 600; color: #1a202c; padding-bottom: 16px; border-bottom: 1px solid #e2e8f0;">Today's Key Stories</h2>
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

    # Wrap with CSS and clean up the HTML
    newsletter_html = wrap_with_css(content)
    return prettify_html(newsletter_html)

def save_newsletter_html(newsletter_content: str, output_path: str) -> None:
    """Save the rendered newsletter HTML to a file.
    
    Args:
        newsletter_content: The fully rendered HTML content
        output_path: Path where to save the HTML file
    """
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(newsletter_content)
    logger.info(f"Newsletter HTML saved to {output_path}")
