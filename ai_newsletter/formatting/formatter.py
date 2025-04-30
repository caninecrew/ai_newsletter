"""High-level formatting coordination."""
from typing import List, Dict, DefaultDict
from collections import defaultdict
from ai_newsletter.logging_cfg.logger import setup_logger
from ai_newsletter.config.settings import EMAIL_SETTINGS
from ai_newsletter.formatting.categorization import categorize_article
from ai_newsletter.formatting.date_utils import format_date
from ai_newsletter.formatting.deduplication import deduplicate_articles, limit_articles_by_source
from ai_newsletter.formatting.tags import get_personalization_tags_html, identify_tags
from ai_newsletter.formatting.text_utils import strip_html, get_key_takeaways

logger = setup_logger()

def format_article(article: Dict, html: bool = False) -> str:
    """Format a single article for the email newsletter."""
    title = article.get('title', 'No Title')
    source = article.get('source', {}).get('name', 'Unknown Source')
    date = format_date(article.get('published_at', ''))
    url = article.get('url', '#')
    summary = article.get('summary', '')
    
    # Extract 1-2 key takeaways from the summary
    takeaways = []
    if summary:
        sentences = summary.split('. ')
        takeaways = sentences[:2] if len(sentences[0]) < 100 else sentences[:1]
    
    if html:
        # Format tags with emojis
        tags = get_personalization_tags_html(article)
        
        # Create bullet points for takeaways
        takeaways_html = ""
        if takeaways:
            bullet_points = "".join([f"<li>{point.strip()}.</li>" for point in takeaways])
            takeaways_html = f"""
            <ul class="takeaway-bullets">
                {bullet_points}
            </ul>
            """
        
        return f"""
        <div class="article">
            <h3 class="article-title">
                {title}
            </h3>
            <div class="article-meta">
                {source} • {date} • <a href="{url}" class="read-more">🔗 Read More</a>
            </div>
            {tags}
            {takeaways_html}
        </div>
        """
    
    # Plain text formatting
    return f"{title}\nSource: {source} | {date}\n{summary}\nLink: {url}"

def format_articles(articles: List[Dict], html: bool = False) -> str:
    """Format articles into sections with topic grouping."""
    if not articles:
        return "No articles to display." if not html else "<p>No articles to display.</p>"
    
    # Apply article limits and deduplication
    max_total = EMAIL_SETTINGS.get("max_articles_total", 10)
    articles = deduplicate_articles(articles)[:max_total]
    
    # Group articles by category
    categories: DefaultDict[str, list] = defaultdict(list)
    for article in articles:
        category = categorize_article(article)
        categories[category].append(article)
    
    # Format articles by category
    if html:
        sections = []
        # Add trending/highlighted section first if we have enough articles
        if len(articles) > 3:
            sections.append("""
            <div class="section trending">
                <h2>📊 Top Stories</h2>
                <p class="section-intro">Key developments you should know about:</p>
                <ul class="highlights">
                    {}
                </ul>
            </div>
            """.format("".join([f"<li>{art['title']}</li>" for art in articles[:3]])))
        
        # Format each category section
        category_emojis = {
            'WORLD_NEWS': '🌍',
            'US_NEWS': '🗽',
            'POLITICS': '🏛️',
            'TECHNOLOGY': '⚡',
            'BUSINESS': '💼',
            'PERSONALIZED': '📌'
        }
        
        for category, category_articles in categories.items():
            if category_articles:
                emoji = category_emojis.get(category, '📰')
                section_title = f"{emoji} {category.replace('_', ' ').title()}"
                articles_html = "\n".join([format_article(a, html=True) for a in category_articles])
                sections.append(f"""
                <div class="section">
                    <h2>{section_title}</h2>
                    {articles_html}
                </div>
                """)
        
        # Add "more stories" section if we had to cut articles
        if len(articles) > max_total:
            remaining = len(articles) - max_total
            sections.append(f"""
            <div class="more-stories">
                <p>...and {remaining} more stories. <a href="#">View full digest →</a></p>
            </div>
            """)
        
        return "\n".join(sections)
    
    return "\n---\n".join([format_article(a, html=False) for a in articles])