"""HTML components for newsletter articles."""
from typing import Dict
from ai_newsletter.core.types import Article
from ai_newsletter.logging_cfg.logger import setup_logger

logger = setup_logger()

def format_summary_block(article: Article) -> str:
    """Format the article summary as an HTML block."""
    summary = article.get('summary', '')
    if not summary:
        return ''
    
    article_id = f"article-{hash(article['url'])}"
    
    return f"""
        <div class="article-summary">
            <div id="{article_id}-summary" class="summary-content">
                {summary}
            </div>
        </div>
    """