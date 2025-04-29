from typing import List, Dict, Optional, Set
from datetime import datetime, timedelta
import re
from difflib import SequenceMatcher
import hashlib
import pytz
from dateutil import parser, tz as dateutil_tz
import pandas as pd
from ai_newsletter.logging_cfg.logger import setup_logger, DEFAULT_TZ
from ai_newsletter.config.settings import USER_INTERESTS, PERSONALIZATION_TAGS, EMAIL_SETTINGS
from bs4 import BeautifulSoup

# Set up logger
logger = setup_logger()

# Updated categories based on RSS feed structure
SECTION_CATEGORIES = {
    'US_NEWS': 'U.S. Headlines',
    'WORLD_NEWS': 'World News',
    'POLITICS': 'Politics',
    'TECHNOLOGY': 'Technology',
    'BUSINESS': 'Business & Economy',
    'LEFT_LEANING': 'Left-Leaning Sources',
    'CENTER': 'Center-Aligned Sources',
    'RIGHT_LEANING': 'Right-Leaning Sources',
    'PERSONALIZED': 'Personalized Stories',
    'LOCAL': 'Local News'
}

# Define Central timezone
CENTRAL = dateutil_tz.gettz("America/Chicago")

def categorize_article(article: Dict) -> str:
    """
    Categorize an article based on its source, content, and metadata.
    
    Args:
        article: Article dictionary with title, content, source, etc.
        
    Returns:
        Category key from SECTION_CATEGORIES
    """
    title = article.get('title', '').lower()
    content = article.get('content', '').lower()
    source = article.get('source', '').lower()
    combined_text = f"{title} {content}"
    
    # Extract the category from the source if available (e.g., "CNN (Left)" -> "Left")
    source_category = None
    if '(' in source and ')' in source:
        category_match = re.search(r'\(([^)]+)\)', source)
        if category_match:
            source_category = category_match.group(1)
    
    # First, categorize based on source category from RSS feed structure
    if source_category:
        if source_category.lower() == 'left':
            return 'LEFT_LEANING'
        elif source_category.lower() == 'center':
            return 'CENTER'
        elif source_category.lower() == 'right':
            return 'RIGHT_LEANING'
        elif source_category.lower() == 'international':
            return 'WORLD_NEWS'
        elif source_category.lower() == 'tennessee':
            return 'LOCAL'
        elif source_category.lower() == 'technology':
            return 'TECHNOLOGY'
        elif source_category.lower() == 'personalized':
            return 'PERSONALIZED'
    
    # Next, categorize based on known sources
    if any(s in source.lower() for s in ['cnn', 'msnbc', 'nyt', 'new york times', 'washington post']):
        return 'LEFT_LEANING'
    elif any(s in source.lower() for s in ['fox', 'national review', 'newsmax', 'washington examiner']):
        return 'RIGHT_LEANING'
    elif any(s in source.lower() for s in ['npr', 'reuters', 'ap', 'associated press', 'pbs', 'abc', 'cbs']):
        return 'CENTER'
    elif any(s in source.lower() for s in ['bbc', 'al jazeera', 'france24', 'dw', 'guardian world']):
        return 'WORLD_NEWS'
    elif any(s in source.lower() for s in ['techcrunch', 'wired', 'ars technica', 'technology review']):
        return 'TECHNOLOGY'
    elif any(s in source.lower() for s in ['tennessean', 'nashville', 'tennessee']):
        return 'LOCAL'
    elif any(s in source.lower() for s in ['scouting', 'scout life', 'education']):
        return 'PERSONALIZED'
    
    # Then, categorize based on content keywords
    if any(kw in combined_text for kw in ['international', 'global', 'worldwide', 'foreign', 'abroad']):
        return 'WORLD_NEWS'
    elif any(kw in combined_text for kw in ['president', 'congress', 'senate', 'governor', 'election', 'campaign', 'government']):
        return 'POLITICS'
    elif any(kw in combined_text for kw in ['tech', 'technology', 'software', 'app', 'digital', 'ai', 'artificial intelligence']):
        return 'TECHNOLOGY'
    elif any(kw in combined_text for kw in ['business', 'economy', 'market', 'stock', 'company', 'entrepreneur', 'ceo']):
        return 'BUSINESS'
    
    # Default to U.S. News if nothing else matches
    return 'US_NEWS'

def identify_tags(article: Dict) -> List[str]:
    """
    Identify relevant tags based on article content and user interests.
    More aggressive matching to ensure accuracy.
    
    Args:
        article: Article dictionary
        
    Returns:
        List of matching tags
    """
    title = article.get('title', '').lower()
    content = article.get('content', '').lower()
    combined_text = f"{title} {content}"
    
    matched_tags = []
    
    # Define interest-to-keyword mapping for better matching
    interest_keywords = {
        "Scouting": ["scout", "boy scout", "girl scout", "eagle scout", "cub scout", "scouting"],
        "Education": ["education", "school", "teacher", "student", "classroom", "learning", "curriculum"],
        "Policy": ["policy", "regulation", "legislation", "law", "guideline", "rule"],
        "AI": ["ai", "artificial intelligence", "machine learning", "neural network", "deep learning", "chatgpt", "llm"],
        "Technology": ["tech", "technology", "software", "hardware", "digital", "computer", "programming"],
        "Business": ["business", "company", "corporate", "industry", "market", "economy", "startup"],
        "Civic Affairs": ["civic", "community", "local government", "municipal", "city council"],
        "Tennessee": ["tennessee", "nashville", "memphis", "knoxville", "chattanooga"],
        "Global Missions": ["mission", "missionary", "global mission", "church mission", "outreach"],
        "Outdoor": ["outdoor", "nature", "hiking", "camping", "wildlife", "conservation", "environment"],
        "Backpacking": ["backpack", "hiking", "trail", "trek", "outdoor gear", "wilderness"],
        "FOIA": ["foia", "freedom of information", "public records", "information request"],
        "Transparency": ["transparency", "disclosure", "open government", "accountability"],
        "Government": ["government", "administration", "federal", "state", "local", "official", "agency"]
    }

    # Check each interest against the text with more specific matching
    for interest, keywords in interest_keywords.items():
        for keyword in keywords:
            if keyword in combined_text:
                matched_tags.append(interest)
                break
    
    # Add some default categorization if no specific tags matched
    if not matched_tags:
        source = article.get('source', '').lower()
        if "fox news" in source:
            matched_tags.append("U.S. News")
        elif any(k in combined_text for k in ["international", "world", "global", "foreign"]):
            matched_tags.append("International")
        elif any(k in combined_text for k in ["technology", "tech", "digital", "software"]):
            matched_tags.append("Technology")
        elif any(k in combined_text for k in ["business", "economy", "market", "stock"]):
            matched_tags.append("Business")
        elif any(k in combined_text for k in ["politics", "president", "congress", "election"]):
            matched_tags.append("Politics")
        else:
            matched_tags.append("General News")
            
    return list(set(matched_tags))  # Remove duplicates

def format_date(date_str: str) -> str:
    """Format a date string into a human-readable format"""
    if not date_str:
        return "Unknown Date"
        
    try:
        if isinstance(date_str, datetime):
            parsed_date = date_str
        else:
            # Try parsing with dateutil first
            try:
                parsed_date = parser.parse(date_str)
                if parsed_date.tzinfo is None:
                    parsed_date = parsed_date.replace(tzinfo=DEFAULT_TZ)
            except:
                # Fall back to manual parsing if dateutil fails
                formats = [
                    '%Y-%m-%dT%H:%M:%S%z',  # ISO format with timezone
                    '%Y-%m-%d %H:%M:%S%z',   # Similar but with space
                    '%a, %d %b %Y %H:%M:%S %z',  # RFC format
                    '%Y-%m-%d %H:%M:%S',     # Without timezone
                    '%Y-%m-%d',              # Just date
                ]
                
                for fmt in formats:
                    try:
                        parsed_date = datetime.strptime(date_str, fmt)
                        if parsed_date.tzinfo is None:
                            parsed_date = parsed_date.replace(tzinfo=DEFAULT_TZ)
                        break
                    except ValueError:
                        continue
                else:
                    # If all formats fail, return original
                    return date_str

        # Convert to DEFAULT_TZ for display
        parsed_date = parsed_date.astimezone(DEFAULT_TZ)
        return parsed_date.strftime("%B %d, %Y")
        
    except Exception as e:
        logger.warning(f"Date parsing error: {e}")
        return date_str

def format_article(article: Dict, html: bool = False) -> str:
    """
    Formats a single article into a string for display or email.

    Args:
        article: A dictionary containing article details.
        html: Whether to format as HTML or plain text.

    Returns:
        A formatted string representation of the article.
    """
    title = article.get('title', 'No Title')
    source = article.get('source', 'Unknown Source')
    url = article.get('link', article.get('url', '#'))
    # Use summary instead of content, fall back to content if summary doesn't exist
    content = article.get('summary', article.get('content', 'No Content'))
    published = article.get('published', 'Unknown Date')
    
    # Format the date using our new function
    formatted_date = format_date(published)
    
    # Get article tags based on content
    tags = identify_tags(article)
    
    if html:
        # Generate personalization tags with emojis
        tags_html = get_personalization_tags_html(article)
        
        # Generate key takeaways
        key_takeaways = get_key_takeaways(content)
        
        # Generate "Why This Matters" section
        why_matters = get_why_this_matters(article) if EMAIL_SETTINGS.get("show_why_this_matters", True) else ""
        
        # Create a unique ID for the full summary toggle functionality
        article_id = f"article-{hash(title) & 0xFFFFFFFF}"
        
        return f"""
        <div class="article">
            <h2 class="article-title"><a href="{url}" target="_blank">{title}</a></h2>
            <div class="article-meta">
                <span class="source">{source}</span>
                <span class="published">{formatted_date}</span>
                <div class="tags">{tags_html}</div>
            </div>
            
            {key_takeaways}
            
            <div id="{article_id}-full" class="article-content full-summary" style="display:none;">
                <p>{content}</p>
                {why_matters}
            </div>
            
            <div class="article-actions">
                <a href="javascript:void(0)" onclick="toggleSummary('{article_id}')" class="toggle-link">Read full summary</a>
                <a href="{url}" target="_blank" class="read-source-link">Read original article →</a>
            </div>
        </div>
        """
    else:
        tags_text = ", ".join(tags)
        return f"Title: {title}\nSource: {source}\nTags: {tags_text}\nPublished: {formatted_date}\n\nKey Takeaways:\n- {content.split('.')[0]}.\n\n{content}\n\nRead more: {url}\n\n"

def limit_articles_by_source(articles: List[Dict], max_per_source: int = 3) -> List[Dict]:
    """
    Limit the number of articles from each source to prevent one source dominating.
    
    Args:
        articles: List of article dictionaries
        max_per_source: Maximum articles allowed per source
        
    Returns:
        Limited list of articles
    """
    if not articles:
        return []
    
    # Group articles by source
    source_groups = {}
    for article in articles:
        source = article.get('source', {})
        # Handle both string and dict source formats from GNews API
        source_name = source.get('name', source) if isinstance(source, dict) else str(source)
        if not source_name:
            source_name = 'Unknown'
            
        if source_name not in source_groups:
            source_groups[source_name] = []
        source_groups[source_name].append(article)
    
    # Sort each group by date (newest first)
    for source_name, group in source_groups.items():
        source_groups[source_name] = sorted(group, key=lambda a: a.get('published_at') or a.get('published', '0'), reverse=True)
    
    # Take only the top N from each source
    limited_articles = []
    for source_name, group in source_groups.items():
        limited_articles.extend(group[:max_per_source])
    
    # Re-sort all articles by date
    limited_articles = sorted(limited_articles, key=lambda a: a.get('published_at') or a.get('published', '0'), reverse=True)
    
    logger.info(f"Limited articles from {len(source_groups)} sources: kept {len(limited_articles)} out of {len(articles)}")
    
    return limited_articles

def format_section_header(category: str) -> tuple[str, str]:
    """
    Create a section header with appropriate emoji based on category
    
    Args:
        category: Category key from SECTION_CATEGORIES
        
    Returns:
        Tuple of (emoji, title)
    """
    if category == 'US_NEWS':
        return '🇺🇸', 'U.S. Headlines'
    elif category == 'WORLD_NEWS':
        return '🌎', 'World News'
    elif category == 'POLITICS':
        return '🏛️', 'Politics'
    elif category == 'TECHNOLOGY':
        return '💻', 'Technology'
    elif category == 'BUSINESS':
        return '📊', 'Business & Economy'
    elif category == 'LEFT_LEANING':
        return '📰', 'Center-Left Sources'
    elif category == 'CENTER':
        return '📰', 'Center Sources'
    elif category == 'RIGHT_LEANING':
        return '📰', 'Center-Right Sources'
    elif category == 'PERSONALIZED':
        return '📌', 'Personalized For You'
    elif category == 'LOCAL':
        return '🏙️', 'Local News'
    else:
        return '📰', 'Other News'

def format_articles(articles: List[Dict], html: bool = False) -> str:
    """
    Formats a list of articles into a single string for display or email.
    Organizes articles by category with clear section headings and visual separators.

    Args:
        articles: A list of dictionaries, each containing article details.
        html: Whether to format as HTML or plain text.

    Returns:
        A formatted string representation of all articles.
    """
    if not articles:
        return "No articles to display." if not html else "<p>No articles to display.</p>"
    
    # Define the section order at the start
    section_order = ['US_NEWS', 'POLITICS', 'WORLD_NEWS', 'BUSINESS', 'TECHNOLOGY', 'LOCAL', 'PERSONALIZED', 'LEFT_LEANING', 'CENTER', 'RIGHT_LEANING']
    
    # Limit articles per source to maintain balance
    max_articles_per_source = EMAIL_SETTINGS.get("max_articles_per_source", 3)
    articles = limit_articles_by_source(articles, max_per_source=max_articles_per_source)
    
    if html:
        # Set the time range (24 hours)
        time_range = f"{(datetime.now() - timedelta(hours=24)).strftime('%B %d')} - {datetime.now().strftime('%B %d, %Y')}"
        
        # Categorize articles
        categories = {}
        for article in articles:
            category = categorize_article(article)
            if category not in categories:
                categories[category] = []
            categories[category].append(article)
        
        # Define the section order
        section_order = ['US_NEWS', 'POLITICS', 'WORLD_NEWS', 'BUSINESS', 'TECHNOLOGY', 'LOCAL', 'PERSONALIZED', 'LEFT_LEANING', 'CENTER', 'RIGHT_LEANING']
        
        # Create HTML output with CSS styles
        html_output = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Your Daily News Summary</title>
            <style>
                body {{
                    font-family: Arial, Helvetica, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 800px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    text-align: center;
                    margin-bottom: 20px;
                    border-bottom: 2px solid #f0f0f0;
                    padding-bottom: 20px;
                }}
                .header h1 {{
                    color: #2c3e50;
                    margin-bottom: 10px;
                }}
                .date {{
                    color: #7f8c8d;
                    font-style: italic;
                }}
                .toc {{
                    background-color: #f9f9f9;
                    padding: 15px;
                    border-radius: 8px;
                    margin-bottom: 30px;
                    border-left: 4px solid #3498db;
                }}
                .toc h2 {{
                    margin-top: 0;
                    margin-bottom: 15px;
                    color: #3498db;
                }}
                .toc ul {{
                    padding-left: 20px;
                    margin-bottom: 5px;
                }}
                .toc li {{
                    margin-bottom: 8px;
                }}
                .toc a {{
                    text-decoration: none;
                    color: #2980b9;
                }}
                .toc a:hover {{
                    text-decoration: underline;
                    color: #1abc9c;
                }}
                .section {{
                    margin-bottom: 40px;
                    border-radius: 8px;
                    padding: 20px;
                    background-color: #ffffff;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.05);
                    position: relative;
                    border-top: 4px solid #3498db;
                }}
                .section:before {{
                    content: '';
                    position: absolute;
                    top: -15px;
                    left: 50%;
                    transform: translateX(-50%);
                    width: 30px;
                    height: 30px;
                    background-color: white;
                    border: 4px solid #3498db;
                    border-radius: 50%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    z-index: 2;
                }}
                .section-header {{
                    margin-top: 10px;
                    margin-bottom: 20px;
                    padding-bottom: 15px;
                    border-bottom: 2px solid #e8e8e8;
                    color: #2c3e50;
                    text-align: center;
                    font-size: 24px;
                    font-weight: bold;
                }}
                .section-description {{
                    font-style: italic;
                    color: #7f8c8d;
                    margin-bottom: 20px;
                    text-align: center;
                }}
                .article {{
                    border-bottom: 1px solid #f0f0f0;
                    padding-bottom: 20px;
                    margin-bottom: 20px;
                }}
                .article:last-child {{
                    border-bottom: none;
                    margin-bottom: 0;
                }}
                .article-title {{
                    margin-top: 0;
                    margin-bottom: 10px;
                    color: #2c3e50;
                }}
                .article-title a {{
                    color: #2c3e50;
                    text-decoration: none;
                }}
                .article-title a:hover {{
                    color: #3498db;
                    text-decoration: underline;
                }}
                .article-meta {{
                    font-size: 14px;
                    color: #7f8c8d;
                    margin-bottom: 15px;
                    display: flex;
                    flex-wrap: wrap;
                    justify-content: space-between;
                    align-items: center;
                }}
                .article-content {{
                    margin-bottom: 15px;
                }}
                .read-more {{
                    text-align: right;
                }}
                .read-more a {{
                    color: #3498db;
                    text-decoration: none;
                    font-weight: bold;
                }}
                .read-more a:hover {{
                    text-decoration: underline;
                }}
                .tag {{
                    display: inline-block;
                    background-color: #f8f9fa;
                    border: 1px solid #e9ecef;
                    border-radius: 30px;
                    padding: 2px 10px;
                    margin-right: 5px;
                    margin-bottom: 5px;
                    font-size: 12px;
                    color: #495057;
                }}
                .tags {{
                    margin-top: 8px;
                    display: flex;
                    flex-wrap: wrap;
                }}
                .footer {{
                    margin-top: 40px;
                    text-align: center;
                    font-size: 14px;
                    color: #7f8c8d;
                    border-top: 1px solid #f0f0f0;
                    padding-top: 20px;
                }}
                .key-takeaways {{
                    background-color: #f5f9ff;
                    border-left: 4px solid #3498db;
                    padding: 10px 15px;
                    margin-bottom: 15px;
                    border-radius: 4px;
                }}
                .key-takeaways h4 {{
                    margin-top: 0;
                    margin-bottom: 10px;
                    color: #2c3e50;
                }}
                .takeaway-bullets {{
                    padding-left: 20px;
                    margin-top: 5px;
                    margin-bottom: 10px;
                }}
                .takeaway-bullets li {{
                    margin-bottom: 8px;
                    line-height: 1.5;
                }}
                .full-summary {{
                    border-top: 1px solid #eee;
                    padding-top: 15px;
                }}
                .why-matters {{
                    background-color: #f0fff4;
                    border-left: 4px solid #2ecc71;
                    padding: 10px 15px;
                    margin: 15px 0;
                    border-radius: 4px;
                }}
                .why-matters h4 {{
                    margin-top: 0;
                    margin-bottom: 10px;
                    color: #27ae60;
                }}
                .why-matters p {{
                    margin: 8px 0;
                }}
                .article-actions {{
                    display: flex;
                    justify-content: space-between;
                    border-top: 1px solid #eee;
                    padding-top: 15px;
                    margin-top: 15px;
                }}
                .toggle-link, .read-source-link {{
                    color: #3498db;
                    text-decoration: none;
                    font-size: 14px;
                }}
                .toggle-link:hover, .read-source-link:hover {{
                    text-decoration: underline;
                }}
                .section-divider {{
                    height: 30px;
                    border-top: 1px solid #ddd;
                    margin: 40px 0;
                    text-align: center;
                    position: relative;
                }}
                .section-divider:before {{
                    content: "§";
                    position: absolute;
                    top: -15px;
                    left: 50%;
                    transform: translateX(-50%);
                    background: white;
                    padding: 0 10px;
                    font-size: 20px;
                    color: #aaa;
                }}
                .no-content-notice {{
                    font-style: italic;
                    color: #888;
                }}
            </style>
            <script type="text/javascript">
                function toggleSummary(id) {{
                    var element = document.getElementById(id + "-full");
                    var link = document.getElementById(id + "-toggle");
                    if (element.style.display === "none") {{
                        element.style.display = "block";
                        link.innerHTML = "Hide full summary";
                    }} else {{
                        element.style.display = "none";
                        link.innerHTML = "Read full summary";
                    }}
                }}
            </script>
        </head>
        <body>
            <div class="header">
                <h1>Your Daily News Summary</h1>
                <p class="date">News from {time_range}</p>
            </div>
        
            <div class="toc">
                <h2>📋 In Today's Newsletter</h2>
                <ul>
        """
        
        # Only include sections with articles in TOC
        sections_with_articles = 0
        for section_key in section_order:
            if section_key in categories and categories[section_key]:
                emoji, title = format_section_header(section_key)
                article_count = len(categories[section_key])
                html_output += f'<li><a href="#{section_key}-section">{emoji} {title} ({article_count})</a></li>'
                sections_with_articles += 1
        
        html_output += """
                </ul>
            </div>
        """
        
        # Add each section in the specified order, but only if it has articles
        first_section = True
        for section_key in section_order:
            if section_key in categories and categories[section_key]:
                emoji, title = format_section_header(section_key)
                
                # Add section divider except for the first section
                if not first_section:
                    html_output += '<div class="section-divider"></div>'
                else:
                    first_section = False
                
                html_output += f"""
                <div id="{section_key}-section" class="section">
                    <h2 class="section-header">{emoji} {title}</h2>
                    <p class="section-description">{get_section_description(section_key)}</p>
                """
                
                # Add articles
                for article in categories[section_key]:
                    html_output += format_article(article, html=True)
                
                html_output += "</div>"
        
        # If no sections had articles, show a message
        if sections_with_articles == 0:
            html_output += """
            <div class="section">
        # Add footer
        html_output += """
            <div class="footer">
                <p>This newsletter was automatically generated based on your interests.</p>
                <p>To unsubscribe, please reply with "unsubscribe" in the subject line.</p>
            </div>
        </body>
        </html>
        """
        
        return html_output
    else:
        # Plain text format - simpler implementation
        categorized = {}
        for article in articles:
            category = categorize_article(article)
            if category not in categorized:
                categorized[category] = []
            categorized[category].append(article)
        
        output = "YOUR DAILY NEWS SUMMARY\n\n"
        
        for section_key in section_order:
            if section_key in categorized and categorized[section_key]:
                emoji, title = format_section_header(section_key)
                output += f"====== {emoji} {title} ======\n\n"
                
                for article in categorized[section_key]:
                    output += format_article(article, html=False) + "\n---\n"
                
                output += "\n"
        
        return output

def get_section_description(section_key: str) -> str:
    """
    Generate a description for each section
    
    Args:
        section_key: Category key
        
    Returns:
        Section description
    """
    descriptions = {
        'US_NEWS': 'Top domestic news stories from across the United States.',
        'WORLD_NEWS': 'Major international events and global developments.',
        'POLITICS': 'The latest political news, policy updates, and government affairs.',
        'TECHNOLOGY': 'Breaking tech news, digital trends, and innovation.',
        'BUSINESS': 'Business headlines, economic updates, and market news.',
        'LEFT_LEANING': 'News from sources that tend to have a center-left perspective.',
        'CENTER': 'News from sources that aim for balanced, centrist coverage.',
        'RIGHT_LEANING': 'News from sources that tend to have a center-right perspective.',
        'PERSONALIZED': 'Stories selected based on your personal interests and preferences.',
        'LOCAL': 'News from your local area that may directly affect your community.'
    }
    
    return descriptions.get(section_key, '')

def filter_articles_by_date(articles, start_date=None, end_date=None):
    """Filter articles based on aware start and end dates in CENTRAL timezone."""
    filtered_articles = []
    if not start_date and not end_date:
        return articles # No filtering needed

    # Ensure filter dates are aware and in CENTRAL
    if start_date and start_date.tzinfo is None:
        start_date = start_date.replace(tzinfo=CENTRAL)
    elif start_date and start_date.tzinfo != CENTRAL:
        start_date = start_date.astimezone(CENTRAL)

    if end_date and end_date.tzinfo is None:
        end_date = end_date.replace(tzinfo=CENTRAL)
    elif end_date and end_date.tzinfo != CENTRAL:
         end_date = end_date.astimezone(CENTRAL)


    for article in articles:
        publish_date = article.get('published')
        if not publish_date:
            continue # Skip articles without a publish date

        # Ensure article date is aware and in CENTRAL for comparison
        if isinstance(publish_date, str):
             # Should not happen if fetch_news worked correctly
             logger.warning(f"Filtering received string date: {publish_date}. Skipping article.")
             continue
        elif publish_date.tzinfo is None:
             logger.warning(f"Filtering received naive datetime: {publish_date}. Assuming UTC.")
             publish_date = publish_date.replace(tzinfo=dateutil_tz.UTC).astimezone(CENTRAL)
        elif publish_date.tzinfo != CENTRAL:
             publish_date = publish_date.astimezone(CENTRAL)


        # Perform date comparison
        if start_date and publish_date < start_date:
            continue
        if end_date and publish_date > end_date:
            continue
        filtered_articles.append(article)

    return filtered_articles

def is_duplicate(article1: Dict, article2: Dict, title_threshold: float = 0.8, content_threshold: float = 0.6) -> bool:
    """
    Advanced duplicate detection using both title and content similarity
    with weighted comparison for better accuracy.
    
    Args:
        article1: First article dictionary to compare
        article2: Second article dictionary to compare
        title_threshold: Similarity threshold for titles (0.0-1.0)
        content_threshold: Similarity threshold for content (0.0-1.0)
        
    Returns:
        True if articles are likely duplicates, False otherwise
    """
    # Clean and normalize text for comparison
    def normalize_text(text):
        if not text:
            return ""
        # Convert to lowercase, remove extra spaces
        return re.sub(r'\s+', ' ', text.lower().strip())
    
    # Extract and normalize title and content
    title1 = normalize_text(article1.get('title', ''))
    title2 = normalize_text(article2.get('title', ''))
    
    # If either title is empty, we can't reliably compare
    if not title1 or not title2:
        return False
    
    # Short-circuit: exact title match is definitely duplicate
    if title1 == title2:
        return True
    
    # Calculate title similarity
    title_similarity = SequenceMatcher(None, title1, title2).ratio()
    
    # If titles are very similar, consider it a duplicate immediately
    if title_similarity > title_threshold:
        return True
    
    # If titles are somewhat similar, check content as well
    if title_similarity > title_threshold * 0.75:
        # Get content snippets (first part of content is usually most distinctive)
        content1 = normalize_text(article1.get('content', ''))[:500]
        content2 = normalize_text(article2.get('content', ''))[:500]
        
        # If no content available, rely only on title comparison
        if not content1 or not content2:
            return title_similarity > title_threshold * 0.9
        
        # Check content similarity
        content_similarity = SequenceMatcher(None, content1, content2).ratio()
        
        # Weight title and content for final decision
        combined_similarity = (title_similarity * 0.7) + (content_similarity * 0.3)
        return combined_similarity > (title_threshold * 0.8)
    
    return False

def deduplicate_articles(articles: List[Dict]) -> List[Dict]:
    """
    Remove duplicate articles from the list with improved algorithm.
    Prioritizes keeping articles from preferred sources when duplicates are found.
    Also ensures no duplicate URLs are included.
    
    Args:
        articles: List of article dictionaries
        
    Returns:
        Deduplicated list of articles
    """
    if not articles:
        return []
    
    # Define source preferences (higher is better)
    source_preference = {
        "Associated Press": 10,
        "Reuters": 9,
        "NPR": 8,
        "PBS": 8,
        "BBC News": 8,
        "The Wall Street Journal": 7,
        "The New York Times": 7,
        "The Washington Post": 7,
        "Bloomberg": 7,
        "CNS News": 6,
        "National Review": 6
    }
    
    # Default preference for unlisted sources
    default_preference = 5
    
    # Sort articles by published date (newest first) and source preference
    sorted_articles = sorted(
        articles, 
        key=lambda a: (
            source_preference.get(a.get('source', ''), default_preference),
            a.get('published', '0')  # Default to '0' if no date
        ),
        reverse=True
    )
    
    unique_articles = []
    duplicate_count = 0
    duplicate_groups = []
    seen_urls = set()  # Track URLs we've already seen
    
    # Track duplicate groups for reporting
    current_duplicates = []
    
    for article in sorted_articles:
        is_dup = False
        url = article.get('url', article.get('link', ''))
        
        # Check if this URL has been seen before (exact URL match)
        if url and url in seen_urls:
            is_dup = True
            duplicate_count += 1
            current_duplicates.append(article.get('title', 'No title'))
            logger.debug(f"Duplicate URL found: {url}")
            continue
        
        # Check for content similarity with existing articles
        for existing in unique_articles:
            if is_duplicate(article, existing):
                is_dup = True
                duplicate_count += 1
                current_duplicates.append(article.get('title', 'No title'))
                break
        
        if not is_dup:
            # If we were tracking duplicates, finish the group
            if current_duplicates:
                duplicate_groups.append(current_duplicates)
                current_duplicates = []
            
            # Add to seen URLs and unique articles
            if url:
                seen_urls.add(url)
            unique_articles.append(article)
    
    # Add the last group if it exists
    if current_duplicates:
        duplicate_groups.append(current_duplicates)
    
    # Log deduplication results
    logger.info(f"Deduplication removed {duplicate_count} duplicate articles")
    logger.info(f"Original count: {len(articles)}, Deduplicated count: {len(unique_articles)}")
    
    # Log duplicate groups (limited to first 5 for brevity)
    if duplicate_groups:
        logger.debug(f"Found {len(duplicate_groups)} duplicate groups:")
        for i, group in enumerate(duplicate_groups[:5], 1):
            logger.debug(f"Group {i}: {', '.join(group)}")
        if len(duplicate_groups) > 5:
            logger.debug(f"... and {len(duplicate_groups) - 5} more groups")
    
    return unique_articles

def get_key_takeaways(content: str) -> str:
    """
    Extract key takeaways from the article content in a TL;DR style.
    This uses a simple extraction approach based on the first few sentences.
    Includes fallback handling for empty content.
    
    Args:
        content: The article content or summary
        
    Returns:
        HTML formatted key takeaways
    """
    if not content or content.strip() == "No content available to summarize." or content.strip() == "Summary not available.":
        # Fallback to a "No content available" message
        return """
        <div class="key-takeaways">
            <h4>🔑 Key Takeaways:</h4>
            <p class="no-content-notice">This article couldn't be summarized. Please refer to the original source for details.</p>
        </div>
        """
    
    # Split content into sentences
    sentences = re.split(r'(?<=[.!?])\s+', content)
    
    # Get first 2-3 sentences for key takeaways, depending on length
    num_sentences = min(3, len(sentences))
    if len(sentences[0]) > 100:  # If first sentence is very long
        num_sentences = min(2, len(sentences))
    
    takeaways = sentences[:num_sentences]
    
    # Format as bullet points
    if takeaways:
        bullet_points = "".join([f"<li>{sentence.strip()}</li>" for sentence in takeaways])
        
        return f"""
        <div class="key-takeaways">
            <h4>🔑 Key Takeaways:</h4>
            <ul class="takeaway-bullets">
                {bullet_points}
            </ul>
        </div>
        """
    else:
        # Fallback if no sentences were extracted
        return """
        <div class="key-takeaways">
            <h4>🔑 Key Takeaways:</h4>
            <p class="no-content-notice">Key points not available. Please check the original article.</p>
        </div>
        """

def get_why_this_matters(article: Dict) -> str:
    """
    Generate a "Why This Matters" section for the article based on its content and tags.
    
    Args:
        article: The article dictionary with content, tags, etc.
        
    Returns:
        HTML formatted explanation of why this article matters
    """
    title = article.get('title', '').lower()
    content = article.get('content', '').lower()
    tags = identify_tags(article)
    combined_text = f"{title} {content}"
    
    # Map impact explanations to keywords
    impact_map = {
        "economy": "This could impact markets, businesses, and potentially your financial outlook.",
        "election": "This may influence upcoming elections and political landscape shifts.",
        "climate": "This highlights ongoing environmental challenges that affect global sustainability.",
        "health": "This development could affect public health policies or medical practices.",
        "technology": "This represents a shift in technology that might change how we interact with digital tools.",
        "policy": "This policy change may have direct effects on regulations or governance.",
        "law": "This legal development could set precedents affecting rights and responsibilities.",
        "education": "This could impact educational institutions, students, or learning approaches.",
        "global": "This international development may have broader geopolitical implications.",
        "local": "This local issue might directly affect your community or region."
    }
    
    # Check for matches in the text
    matches = []
    for keyword, explanation in impact_map.items():
        if keyword in combined_text:
            matches.append(explanation)
    
    # Add tag-based explanations
    tag_impact = {
        "Legal": "This legal development may set precedents that influence future cases or regulations.",
        "Education": "This could impact students, educators, or learning institutions in your community.",
        "Healthcare": "This health-related news could affect medical practices or patient care standards.",
        "Economy": "This economic trend may influence markets, jobs, or your personal finances.",
        "Global Affairs": "This international development could reshape diplomatic relations or global trade.",
        "Technology": "This tech advancement might change how people interact with devices or services.",
        "Politics": "This political shift could impact governance or upcoming electoral outcomes.",
        "Environment": "This environmental news may affect sustainability efforts or climate policies."
    }
    
    for tag in tags:
        if tag in tag_impact:
            matches.append(tag_impact[tag])
    
    # If we don't have matches, provide generic explanation based on section
    if not matches:
        section = categorize_article(article)
        if section == 'WORLD_NEWS':
            matches.append("This international development could have widespread implications for global politics or economics.")
        elif section == 'US_NEWS':
            matches.append("This domestic issue may affect national policies or public opinion.")
        else:
            matches.append("This story relates to topics you've shown interest in and may have relevance to your professional or personal life.")
    
    # Take up to 2 unique explanations
    unique_matches = list(set(matches))[:2]
    explanation_html = "".join([f"<p>{explanation}</p>" for explanation in unique_matches])
    
    return f"""
    <div class="why-matters">
        <h4>💡 Why This Matters:</h4>
        {explanation_html}
    </div>
    """

def get_personalization_tags_html(article: Dict) -> str:
    """
    Generate HTML for personalization tags with emojis.
    Ensures tags are deduplicated and consistently applied.
    
    Args:
        article: The article dictionary
        
    Returns:
        HTML formatted tags with emojis
    """
    raw_tags = identify_tags(article)
    processed_tags = set()  # Use a set to avoid duplicates
    html_tags = []
    
    # Create a mapping of tag categories to prevent duplicates like "AI🏛 Politics"
    tag_categories = {
        "legal": "🔒 Legal",
        "education": "🏫 Education",
        "health": "🏥 Healthcare",
        "economy": "📈 Economy",
        "global": "🧭 Global Affairs", 
        "tech": "⚡️ Technology",
        "politics": "🏛️ Politics",
        "environment": "🌳 Environment",
        "science": "🔬 Science"
    }
    
    # Check which categories this article belongs to
    category_matches = set()
    
    for tag in raw_tags:
        tag_lower = tag.lower()
        
        # Check for category matches
        if "legal" in tag_lower or "law" in tag_lower or "regulation" in tag_lower:
            category_matches.add("legal")
        elif "education" in tag_lower or "school" in tag_lower or "learning" in tag_lower:
            category_matches.add("education")
        elif "health" in tag_lower or "medical" in tag_lower or "hospital" in tag_lower:
            category_matches.add("health")
        elif "economy" in tag_lower or "market" in tag_lower or "financial" in tag_lower or "business" in tag_lower:
            category_matches.add("economy")
        elif "global" in tag_lower or "international" in tag_lower or "world" in tag_lower:
            category_matches.add("global")
        elif "tech" in tag_lower or "ai" in tag_lower or "software" in tag_lower or "digital" in tag_lower:
            category_matches.add("tech")
        elif "government" in tag_lower or "policy" in tag_lower or "politics" in tag_lower:
            category_matches.add("politics")
        elif "environment" in tag_lower or "climate" in tag_lower or "sustainability" in tag_lower:
            category_matches.add("environment")
        elif "science" in tag_lower or "research" in tag_lower:
            category_matches.add("science")
        else:
            # For unmatched tags, add them directly if they're not already included
            if tag not in processed_tags:
                processed_tags.add(tag)
                if tag in PERSONALIZATION_TAGS:
                    emoji = PERSONALIZATION_TAGS[tag]
                    html_tags.append(f'<span class="tag">{emoji} {tag}</span>')
                else:
                    # Use a generic tag without emoji
                    html_tags.append(f'<span class="tag">{tag}</span>')
    
    # Add all matched category tags
    for category in category_matches:
        html_tags.append(f'<span class="tag">{tag_categories[category]}</span>')
    
    # If no tags were found, add a generic tag based on the article category
    if not html_tags:
        section = categorize_article(article)
        if section == 'WORLD_NEWS':
            html_tags.append('<span class="tag">🧭 Global Affairs</span>')
        elif section == 'US_NEWS':
            html_tags.append('<span class="tag">🏛️ U.S. News</span>')
        elif section == 'TECHNOLOGY':
            html_tags.append('<span class="tag">⚡️ Technology</span>')
        elif section == 'BUSINESS':
            html_tags.append('<span class="tag">📈 Economy</span>')
        elif section == 'POLITICS':
            html_tags.append('<span class="tag">🏛️ Politics</span>')
        else:
            html_tags.append('<span class="tag">📰 News</span>')
    
    return "".join(html_tags)

def build_empty_newsletter() -> str:
    """Generate a polite 'no new stories' HTML page."""
    return """
    <html>
    <head>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            h1 { color: #333; }
            p { color: #555; }
        </style>
    </head>
    <body>
        <h1>No New Stories Today</h1>
        <p>We couldn't find any new articles to share with you today. Check back tomorrow for the latest updates!</p>
    </body>
    </html>
    """

def build_html(articles: List[Dict]) -> str:
    """
    Build the HTML content for the newsletter from a list of articles.

    Args:
        articles: A list of dictionaries, each containing article details.

    Returns:
        A string containing the HTML content of the newsletter.
    """
    if not articles:
        return build_empty_newsletter()

    # Use the format_articles function to generate the HTML content
    return format_articles(articles, html=True)

def strip_html(html: str) -> str:
    """Convert HTML to plain text by removing HTML tags while preserving structure.
    
    Args:
        html: HTML content to convert
        
    Returns:
        Plain text version of the HTML content
    """
    if not html:
        return ""
        
    # Parse HTML with BeautifulSoup
    soup = BeautifulSoup(html, 'html.parser')
    
    # Remove script and style elements
    for script in soup(["script", "style"]):
        script.decompose()
    
    # Get text while preserving some structure
    lines = []
    for element in soup.descendants:
        # Skip NavigableString inside certain tags
        if element.parent and element.parent.name in ['style', 'script']:
            continue
            
        if element.name == 'p':
            lines.append("\n")
        elif element.name == 'br':
            lines.append("\n")
        elif element.name == 'h1':
            lines.append("\n" + "="*40 + "\n")
        elif element.name == 'h2':
            lines.append("\n" + "-"*30 + "\n")
        elif element.name == 'li':
            lines.append("\n* ")
        elif element.name == 'a' and element.string:
            lines.append(f"{element.string} ({element.get('href', '')})")
        elif element.string and element.string.strip():
            lines.append(element.string.strip())
            
    # Join lines and fix spacing
    text = ' '.join(lines)
    
    # Fix multiple newlines and spaces
    text = re.sub(r'\n\s*\n', '\n\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    
    return text.strip()