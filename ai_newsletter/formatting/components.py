"""HTML components for newsletter articles."""
from typing import Dict
import re
from ai_newsletter.core.types import Article
from ai_newsletter.core.constants import TAG_EMOJIS
from ai_newsletter.logging_cfg.logger import setup_logger

logger = setup_logger()

def format_summary_block(article: Article) -> str:
    """Format the article summary as an HTML block with expand/collapse."""
    summary = article.get('summary', '')
    if not summary:
        return ''
    
    article_id = f"article-{hash(article['url'])}"
    
    return f"""
        <div class="article-summary">
            <div id="{article_id}-summary" class="summary-content">
                {summary}
            </div>
            <div class="article-actions">
                <a href="{article['url']}" class="read-source-link" target="_blank">Read Full Article →</a>
            </div>
        </div>
    """

def get_tags_html(article: Article) -> str:
    """Generate HTML for article tags with appropriate emojis."""
    if not article.get('tags'):
        return ''
        
    html_tags = []
    processed_tags = set()
    
    for tag in article['tags']:
        if tag not in processed_tags:
            processed_tags.add(tag)
            emoji = TAG_EMOJIS.get(tag, '📌')  # Default to 📌 if no emoji found
            html_tags.append(f'<span class="tag">{emoji} {tag}</span>')
    
    return f"""
        <div class="tags">
            {''.join(html_tags)}
        </div>
    """ if html_tags else ''