# This module contains functions to format news articles for email or display purposes.
from datetime import datetime, timedelta
import re
from difflib import SequenceMatcher
from logger_config import setup_logger
from config import USER_INTERESTS, PERSONALIZATION_TAGS, EMAIL_SETTINGS

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

def categorize_article(article):
    """
    Categorize an article based on its source, content, and metadata.
    
    Args:
        article (dict): Article dictionary with title, content, source, etc.
        
    Returns:
        str: Category key from SECTION_CATEGORIES
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

def identify_tags(article):
    """
    Identify relevant tags based on article content and user interests.
    More aggressive matching to ensure accuracy.
    
    Args:
        article (dict): Article dictionary
        
    Returns:
        list: List of matching tags
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
        "Civic Affairs": ["civic", "community", "local government", "municipal", "city council", "town hall"],
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

def format_article(article, html=False):
    """
    Formats a single article into a string for display or email.

    Args:
        article (dict): A dictionary containing article details.
        html (bool): Whether to format as HTML or plain text.

    Returns:
        str: A formatted string representation of the article.
    """
    title = article.get('title', 'No Title')
    source = article.get('source', 'Unknown Source')
    url = article.get('link', article.get('url', '#'))
    # Use summary instead of content, fall back to content if summary doesn't exist
    content = article.get('summary', article.get('content', 'No Content'))
    published = article.get('published', 'Unknown Date')
    
    # Get article tags based on content and format with emojis
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
                <span class="published">{published}</span>
                <div class="tags">{tags_html}</div>
            </div>
            
            {key_takeaways}
            
            <div id="{article_id}-full" class="article-content full-summary" style="display:none;">
                <p>{content}</p>
                {why_matters}
            </div>
            
            <div class="article-actions">
                <a href="javascript:void(0)" onclick="toggleSummary('{article_id}')" class="toggle-link">Toggle full summary</a>
                <a href="{url}" target="_blank" class="read-source-link">Read full article &rarr;</a>
            </div>
        </div>
        """
    else:
        tags_text = ", ".join(tags)
        return f"Title: {title}\nSource: {source}\nTags: {tags_text}\nPublished: {published}\n\nKey Takeaways:\n- {content.split('.')[0]}.\n\n{content}\n\nRead more: {url}\n\n"

def limit_articles_by_source(articles, max_per_source=3):
    """
    Limit the number of articles from each source to prevent one source dominating.
    
    Args:
        articles (list): List of article dictionaries
        max_per_source (int): Maximum articles allowed per source
        
    Returns:
        list: Limited list of articles
    """
    if not articles:
        return []
    
    # Group articles by source
    source_groups = {}
    for article in articles:
        source = article.get('source', 'Unknown')
        if source not in source_groups:
            source_groups[source] = []
        source_groups[source].append(article)
    
    # Sort each group by date (newest first)
    for source, group in source_groups.items():
        source_groups[source] = sorted(group, key=lambda a: a.get('published', '0'), reverse=True)
    
    # Take only the top N from each source
    limited_articles = []
    for source, group in source_groups.items():
        limited_articles.extend(group[:max_per_source])
    
    # Re-sort all articles by date
    limited_articles = sorted(limited_articles, key=lambda a: a.get('published', '0'), reverse=True)
    
    logger.info(f"Limited articles from {len(source_groups)} sources: kept {len(limited_articles)} out of {len(articles)}")
    
    return limited_articles

def format_section_header(category):
    """
    Create a section header with appropriate emoji based on category
    
    Args:
        category (str): Category key from SECTION_CATEGORIES
        
    Returns:
        tuple: (emoji, title)
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

def format_articles(articles, html=False):
    """
    Formats a list of articles into a single string for display or email.
    Organizes articles by category with clear section headings.

    Args:
        articles (list): A list of dictionaries, each containing article details.
        html (bool): Whether to format as HTML or plain text.

    Returns:
        str: A formatted string representation of all articles.
    """
    if not articles:
        return "No articles to display." if not html else "<p>No articles to display.</p>"
    
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
                }}
                .section-header {{
                    margin-top: 0;
                    margin-bottom: 20px;
                    padding-bottom: 10px;
                    border-bottom: 2px solid #e8e8e8;
                    color: #2c3e50;
                }}
                .section-description {{
                    font-style: italic;
                    color: #7f8c8d;
                    margin-bottom: 20px;
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
            </style>
            <script type="text/javascript">
                function toggleSummary(id) {{
                    var element = document.getElementById(id + "-full");
                    if (element.style.display === "none") {{
                        element.style.display = "block";
                    }} else {{
                        element.style.display = "none";
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
        for section_key in section_order:
            if section_key in categories and categories[section_key]:
                emoji, title = format_section_header(section_key)
                
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
                <p><strong>No articles available:</strong> We couldn't find any articles meeting your criteria for today's date.
                Please check back tomorrow for fresh news coverage.</p>
            </div>
            """
        
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
                _, title = format_section_header(section_key)
                output += f"==== {title} ====\n\n"
                
                for article in categorized[section_key]:
                    output += format_article(article, html=False) + "\n---\n"
                
                output += "\n"
        
        return output

def get_section_description(section_key):
    """
    Generate a description for each section
    
    Args:
        section_key (str): Category key
        
    Returns:
        str: Section description
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

def filter_articles_by_date(articles, days=1, hours=None):
    """
    Filter articles based on publication date
    
    Args:
        articles: List of article dictionaries
        days: Number of days back to include (default=1)
        hours: Number of hours back to include (overrides days if provided)
        
    Returns:
        List of filtered articles
    """
    # Calculate cutoff time
    if hours is not None:
        cutoff_time = datetime.now() - timedelta(hours=hours)
    else:
        cutoff_time = datetime.now() - timedelta(days=days)
    
    filtered = []
    skipped_count = 0
    parsing_errors = 0
    
    # First ensure we're working with flat list of articles
    flat_articles = []
    for item in articles:
        # Handle case where an article might be a list itself (nested structure)
        if isinstance(item, list):
            flat_articles.extend(item)
        else:
            flat_articles.append(item)
    
    for article in flat_articles:
        # Skip if article is not a dictionary
        if not isinstance(article, dict):
            logger.warning(f"Skipping non-dictionary article: {type(article)}")
            skipped_count += 1
            continue
            
        try:
            # Handle various date formats
            date_str = article.get('published', '')
            
            # Skip articles with no date
            if not date_str:
                logger.debug(f"Skipping article with no date: {article.get('title', 'No title')}")
                skipped_count += 1
                continue
                
            # Try different parsing strategies
            parsed_date = None
            try:
                # Common format in feedparser: Tue, 23 Apr 2025 14:23:45 +0000
                parsed_date = datetime.strptime(date_str, "%a, %d %b %Y %H:%M:%S %z")
            except ValueError:
                try:
                    # ISO format: 2025-04-23T14:23:45Z or 2025-04-23T14:23:45+00:00
                    if 'T' in date_str:
                        if date_str.endswith('Z'):
                            parsed_date = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%SZ")
                        elif '+' in date_str or '-' in date_str[10:]:  # Has timezone
                            try:
                                parsed_date = datetime.fromisoformat(date_str)
                            except:
                                parsed_date = datetime.strptime(date_str[:19], "%Y-%m-%dT%H:%M:%S")
                        else:
                            parsed_date = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S")
                    else:
                        # Basic format: 2025-04-23 14:23:45
                        parsed_date = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    try:
                        # Another common format: Wed, 23 Apr 2025 14:23:45 GMT
                        parsed_date = datetime.strptime(date_str, "%a, %d %b %Y %H:%M:%S %Z")
                    except ValueError:
                        try:
                            # Try format with abbreviated month: 23 Apr 2025 14:23:45
                            parsed_date = datetime.strptime(date_str, "%d %b %Y %H:%M:%S")
                        except ValueError:
                            try:
                                # Last attempt - try to handle any format with dateutil
                                from dateutil import parser
                                parsed_date = parser.parse(date_str)
                            except:
                                # If all parsing attempts fail
                                logger.warning(f"Could not parse date: {date_str} for article: {article.get('title', 'No title')}")
                                # Include recent articles with unparseable dates rather than discarding them
                                filtered.append(article)
                                parsing_errors += 1
                                continue
            
            # Handle timezone-aware vs naive datetime comparison
            if hasattr(parsed_date, 'tzinfo') and parsed_date.tzinfo is not None:
                # If the parsed date is timezone-aware but cutoff_time is not
                if cutoff_time.tzinfo is None:
                    # Convert parsed_date to naive by removing timezone info
                    parsed_date = parsed_date.replace(tzinfo=None)
            
            # Compare dates and add to filtered list if recent enough
            if parsed_date >= cutoff_time:
                filtered.append(article)
            else:
                logger.debug(f"Article too old: {article.get('title', 'No title')} - {parsed_date}")
                skipped_count += 1
                
        except Exception as e:
            logger.warning(f"Date filtering error for article '{article.get('title', 'No title') if isinstance(article, dict) else str(article)}': {str(e)}")
            # Include articles with date errors rather than silently dropping them
            if isinstance(article, dict):
                filtered.append(article)
                parsing_errors += 1
    
    logger.info(f"Date filtering: {len(filtered)} articles kept, {skipped_count} skipped, {parsing_errors} with parsing errors")
    return filtered

def is_duplicate(article1, article2, title_threshold=0.8, content_threshold=0.6):
    """
    Advanced duplicate detection using both title and content similarity
    with weighted comparison for better accuracy.
    
    Args:
        article1, article2: Article dictionaries to compare
        title_threshold: Similarity threshold for titles (0.0-1.0)
        content_threshold: Similarity threshold for content (0.0-1.0)
        
    Returns:
        bool: True if articles are likely duplicates, False otherwise
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

def deduplicate_articles(articles):
    """
    Remove duplicate articles from the list with improved algorithm.
    Prioritizes keeping articles from preferred sources when duplicates are found.
    
    Args:
        articles (list): List of article dictionaries
        
    Returns:
        list: Deduplicated list of articles
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
    
    # Track duplicate groups for reporting
    current_duplicates = []
    
    for article in sorted_articles:
        is_dup = False
        
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

def get_key_takeaways(content):
    """
    Extract key takeaways from the article content in a TL;DR style.
    This uses a simple extraction approach based on the first few sentences.
    
    Args:
        content (str): The article content or summary
        
    Returns:
        str: HTML formatted key takeaways
    """
    if not content:
        return ""
    
    # Split content into sentences
    sentences = re.split(r'(?<=[.!?])\s+', content)
    
    # Get first 2-3 sentences for key takeaways, depending on length
    num_sentences = min(3, len(sentences))
    if len(sentences[0]) > 100:  # If first sentence is very long
        num_sentences = min(2, len(sentences))
    
    takeaways = sentences[:num_sentences]
    
    # Format as bullet points
    bullet_points = "".join([f"<li>{sentence.strip()}</li>" for sentence in takeaways])
    
    return f"""
    <div class="key-takeaways">
        <h4>🔑 Key Takeaways:</h4>
        <ul class="takeaway-bullets">
            {bullet_points}
        </ul>
        <p class="read-full"><a href="#full-summary" class="summary-toggle">Read Full Summary ▼</a></p>
    </div>
    """

def get_why_this_matters(article):
    """
    Generate a "Why This Matters" section for the article based on its content and tags.
    
    Args:
        article (dict): The article dictionary with content, tags, etc.
        
    Returns:
        str: HTML formatted explanation of why this article matters
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

def get_personalization_tags_html(article):
    """
    Generate HTML for personalization tags with emojis.
    
    Args:
        article (dict): The article dictionary
        
    Returns:
        str: HTML formatted tags with emojis
    """
    tags = identify_tags(article)
    html_tags = []
    
    # Map common tags to the personalization tags with emojis
    for tag in tags:
        # Direct matches
        if tag in PERSONALIZATION_TAGS:
            emoji = PERSONALIZATION_TAGS[tag]
            html_tags.append(f'<span class="tag">{emoji} {tag}</span>')
        # Related matches
        elif "Legal" in tag or "law" in tag.lower() or "regulation" in tag.lower():
            html_tags.append(f'<span class="tag">🔒 Legal</span>')
        elif "Education" in tag or "school" in tag.lower() or "learning" in tag.lower():
            html_tags.append(f'<span class="tag">🏫 Education</span>')
        elif "Health" in tag or "medical" in tag.lower() or "hospital" in tag.lower():
            html_tags.append(f'<span class="tag">🏥 Healthcare</span>')
        elif "Economy" in tag or "market" in tag.lower() or "financial" in tag.lower():
            html_tags.append(f'<span class="tag">📈 Economy</span>')
        elif "Global" in tag or "international" in tag.lower() or "world" in tag.lower():
            html_tags.append(f'<span class="tag">🧭 Global Affairs</span>')
        elif "Tech" in tag or "software" in tag.lower() or "digital" in tag.lower():
            html_tags.append(f'<span class="tag">⚡️ Technology</span>')
        elif "Government" in tag or "policy" in tag.lower() or "politics" in tag.lower():
            html_tags.append(f'<span class="tag">🏛️ Politics</span>')
        else:
            # Generic tag without emoji
            html_tags.append(f'<span class="tag">{tag}</span>')
    
    return "".join(html_tags)