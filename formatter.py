# This module contains functions to format news articles for email or display purposes.
from datetime import datetime, timedelta
import re
from difflib import SequenceMatcher

# Define personalization tags with emojis
PERSONALIZATION_TAGS = {
    "Legal": "🔒",
    "Education": "🏫",
    "Healthcare": "🏥",
    "Economy": "📈",
    "Global Affairs": "🧭",
    "Technology": "⚡️",
    "Politics": "🏛️",
    "Science": "🔬",
    "Environment": "🌱",
    "Sports": "⚽",
    "Entertainment": "🎬",
    "Business": "💼",
    "Finance": "💰",
    "Social Issues": "👥"
}

# Define user interests/tags for classification
USER_INTERESTS = [
    "Scouting", "Education", "Policy", "AI", "Technology", "Business", 
    "Civic Affairs", "Tennessee", "Global Missions", "Outdoor", "Backpacking",
    "FOIA", "Transparency", "Government"
]

# Define news section categories
SECTION_TYPES = {
    'global_major': 'Super Major International News',
    'domestic_major': 'Major Domestic Headlines',
    'personal_interest': 'Personalized Interest Stories',
    'fox_exclusive': 'Fox News Exclusive Reporting'
}

def classify_article(article):
    """
    Classify an article into one of the four sections:
    1. Super major international news
    2. Major domestic headlines (across political spectrum)
    3. Personal interest stories based on user tags
    4. Fox News exclusive stories
    
    Args:
        article (dict): Article dictionary with title, content, source, etc.
        
    Returns:
        str: Section classification
    """
    title = article.get('title', '').lower()
    content = article.get('content', '').lower()
    source = article.get('source', '').lower()
    combined_text = f"{title} {content}"
    
    # Get tags for this article
    tags = identify_tags(article)
    
    # Keywords for international major news
    global_keywords = [
        'war', 'conflict', 'pope', 'vatican', 'disaster', 'earthquake', 'tsunami',
        'pandemic', 'global crisis', 'united nations', 'nato', 'international',
        'world', 'global', 'peace', 'treaty', 'catastrophe', 'genocide'
    ]
    
    # Keywords for domestic major news
    domestic_keywords = [
        'president', 'congress', 'senate', 'supreme court', 'election',
        'federal', 'national', 'u.s.', 'united states', 'america', 'american',
        'government shutdown', 'legislation', 'law', 'policy', 'inflation',
        'economy', 'healthcare', 'scandal', 'bill', 'national security'
    ]
    
    # Check for Fox News exclusive
    if 'fox news' in source and not any(outlet in source for outlet in ['cnn', 'msnbc', 'nbc', 'abc', 'cbs', 'npr', 'washington post', 'new york times']):
        return 'fox_exclusive'
    
    # Check for global major news
    if any(keyword in combined_text for keyword in global_keywords):
        return 'global_major'
    
    # Check for domestic major news
    if any(keyword in combined_text for keyword in domestic_keywords):
        return 'domestic_major'
    
    # For personal interest section, only include if it has at least one relevant tag
    # This removes the "default" behavior of putting everything into personal interest
    relevant_tags = [tag for tag in tags if tag in USER_INTERESTS or tag == "General News"]
    
    if relevant_tags and len(relevant_tags) > 0:
        return 'personal_interest'
    
    # If no clear classification based on content, put in appropriate general category
    # based on source and geographic focus
    if 'international' in combined_text or 'world' in combined_text or 'global' in combined_text:
        return 'global_major'
    
    # Default to domestic news if we can't classify otherwise
    return 'domestic_major'

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
        if "fox news" in article.get('source', '').lower():
            matched_tags.append("U.S. News")
        elif any(k in combined_text for k in ["international", "world", "global", "foreign"]):
            matched_tags.append("International")
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
    url = article.get('url', '#')
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
        why_matters = get_why_this_matters(article)
        
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

def format_section_summary(section_type, articles):
    """
    Create a summary for a section based on its contents.
    
    Args:
        section_type (str): Type of section
        articles (list): Articles in this section
        
    Returns:
        str: HTML summary for the section
    """
    if not articles:
        return ""
        
    if section_type == 'global_major':
        return "<p class='section-summary'>Major international events and global developments that may impact world affairs.</p>"
    elif section_type == 'domestic_major':
        return "<p class='section-summary'>Key U.S. headlines appearing across multiple news outlets that could affect you or your community.</p>"
    elif section_type == 'personal_interest':
        interests = set()
        for article in articles:
            interests.update(identify_tags(article))
        interest_text = ", ".join(interests)
        return f"<p class='section-summary'>News stories related to your interests: {interest_text}.</p>"
    elif section_type == 'fox_exclusive':
        return "<p class='section-summary'>Stories reported by Fox News that aren't widely covered by other major outlets.</p>"
    else:
        return ""

def format_articles(articles, html=False):
    """
    Formats a list of articles into a single string for display or email.
    Suppresses sections that don't have any articles.

    Args:
        articles (list): A list of dictionaries, each containing article details.
        html (bool): Whether to format as HTML or plain text.

    Returns:
        str: A formatted string representation of all articles.
    """
    if not articles:
        return "No articles to display." if not html else "<p>No articles to display.</p>"
        
    if html:
        # Get yesterday's date
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%A, %B %d, %Y')
        
        # Classify articles into the four required sections
        sections = {
            'global_major': [],
            'domestic_major': [],
            'personal_interest': [],
            'fox_exclusive': []
        }
        
        for article in articles:
            section = classify_article(article)
            sections[section].append(article)
        
        # Create HTML output with CSS styles
        html_output = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Daily News Summary</title>
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
                    padding: 15px;
                    background-color: #ffffff;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.05);
                }}
                .section-header {{
                    padding: 10px 15px;
                    margin: -15px -15px 15px -15px;
                    border-top-left-radius: 8px;
                    border-top-right-radius: 8px;
                    font-weight: bold;
                }}
                .global-section .section-header {{
                    background-color: #e74c3c;
                    color: white;
                }}
                .domestic-section .section-header {{
                    background-color: #3498db;
                    color: white;
                }}
                .personal-section .section-header {{
                    background-color: #2ecc71;
                    color: white;
                }}
                .fox-section .section-header {{
                    background-color: #f39c12;
                    color: white;
                }}
                .section-summary {{
                    font-style: italic;
                    color: #555;
                    border-bottom: 1px solid #eee;
                    padding-bottom: 10px;
                    margin-bottom: 15px;
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
                }}
                .footer {{
                    margin-top: 40px;
                    text-align: center;
                    font-size: 14px;
                    color: #7f8c8d;
                    border-top: 1px solid #f0f0f0;
                    padding-top: 20px;
                }}
                .no-articles {{
                    font-style: italic;
                    color: #7f8c8d;
                    text-align: center;
                    padding: 20px;
                }}
                .coverage-note {{
                    background-color: #fcf8e3;
                    border: 1px solid #faebcc;
                    color: #8a6d3b;
                    padding: 15px;
                    margin-bottom: 20px;
                    border-radius: 4px;
                }}
                /* New styles for key takeaways, why this matters, and toggle sections */
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
                .read-full {{
                    text-align: center;
                    margin-bottom: 5px;
                    font-size: 14px;
                }}
                .summary-toggle {{
                    color: #3498db;
                    text-decoration: none;
                    cursor: pointer;
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
                <h1>Your Personalized News Summary</h1>
                <p class="date">News from {yesterday}</p>
            </div>
        
            <div class="toc">
                <h2>📋 In Today's Newsletter</h2>
                <ul>
        """
        
        # Only include sections with articles in TOC
        for section_key in section_order:
            section_articles = sections[section_key]
            if section_articles:
                section_title = section_titles[section_key]
                html_output += f'<li><a href="#{section_key}-section">{section_title} ({len(section_articles)})</a></li>'
        
        html_output += """
                </ul>
            </div>
        """
        
        # If we have too few articles, add a note about coverage
        if len(articles) < 3:
            html_output += """
            <div class="coverage-note">
                <p><strong>Note:</strong> Today's news coverage is limited as we're only including articles 
                published exactly on the target date for accuracy. Some sources may not have provided 
                timestamps or published relevant content today.</p>
            </div>
            """
        
        # Add each section in the specified order, but only if it has articles
        section_order = ['global_major', 'domestic_major', 'personal_interest', 'fox_exclusive']
        section_classes = {
            'global_major': 'global-section',
            'domestic_major': 'domestic-section',
            'personal_interest': 'personal-section',
            'fox_exclusive': 'fox-section'
        }
        
        # Updated section titles with icons
        section_titles = {
            'global_major': '🌍 Super Major International News',
            'domestic_major': '🏛️ Major Domestic Headlines',
            'personal_interest': '📌 Personalized Interest Stories',
            'fox_exclusive': '🦊 What Fox News is Reporting'
        }
        
        # Track if any sections were included
        sections_included = False
        
        for section_key in section_order:
            section_articles = sections[section_key]
            
            # Skip sections with no articles
            if not section_articles:
                print(f"[INFO] Skipping empty section: {section_key}")
                continue
                
            # If we get here, we have articles in this section
            sections_included = True
            section_title = section_titles[section_key]  # Use updated titles with icons
            section_class = section_classes[section_key]
            
            html_output += f"""
            <div id="{section_key}-section" class="section {section_class}">
                <h2 class="section-header">{section_title}</h2>
            """
            
            # Add section summary
            html_output += format_section_summary(section_key, section_articles)
            
            # Add articles
            for article in section_articles:
                html_output += format_article(article, html=True)
            
            html_output += "</div>"
        
        # If no sections had articles, show a message
        if not sections_included:
            html_output += """
            <div class="coverage-note">
                <p><strong>No articles available:</strong> We couldn't find any articles meeting your criteria for today's date.
                Please check back tomorrow for fresh news coverage.</p>
            </div>
            """
        
        # Add footer
        html_output += """
            <div class="footer">
                <p>This newsletter was automatically generated for your interests.</p>
                <p>To unsubscribe, please reply with "unsubscribe" in the subject line.</p>
            </div>
        </body>
        </html>
        """
        
        return html_output
    else:
        return "\n---\n".join(format_article(article) for article in articles)

def filter_articles_by_date(articles, days=None, hours=None):
    """
    Filter articles based on publication date with fallback options.
    Supports filtering by either days or hours for more flexibility.
    
    Args:
        articles (list): List of article dictionaries
        days (int, optional): Number of days to look back (default: None)
        hours (int, optional): Number of hours to look back (default: None)
        
    Returns:
        list: Filtered list of articles
    """
    # Set the time window based on either days or hours parameter
    if hours is not None:
        time_window = timedelta(hours=hours)
        window_text = f"{hours} hours"
    elif days is not None:
        time_window = timedelta(days=days)
        window_text = f"{days} days"
    else:
        # Default to 24 hours if neither parameter is provided
        time_window = timedelta(hours=24)
        window_text = "24 hours"
        
    target_date = datetime.now() - time_window
    target_date_str = target_date.strftime('%Y-%m-%d %H:%M')
    today_date = datetime.now()
    
    print(f"[INFO] Filtering for articles from: {target_date_str} onwards (past {window_text})")
    print(f"[INFO] Starting with {len(articles)} articles")
    
    # Filter articles within the time window
    filtered_articles = []
    
    # Date formats to try
    date_formats = [
        '%a, %d %b %Y %H:%M:%S %z',  # RFC 822 format
        '%a, %d %b %Y %H:%M:%S %Z',
        '%Y-%m-%dT%H:%M:%S%z',       # ISO format
        '%Y-%m-%dT%H:%M:%SZ',
        '%Y-%m-%dT%H:%M:%S.%f%z',
        '%Y-%m-%d %H:%M:%S',
        '%a, %d %b %Y %H:%M:%S',
        '%d %b %Y %H:%M:%S',
        '%Y/%m/%d',
        '%m/%d/%Y',
        '%B %d, %Y',
        '%d %B %Y',
        '%A, %B %d, %Y',
        '%A, %d %B %Y'
    ]
    
    for article in articles:
        try:
            # Try different date formats
            published_str = article.get('published', '')
            if not published_str or published_str == 'Unknown Date':
                continue
                
            parsed = False
            for date_format in date_formats:
                try:
                    published_date = datetime.strptime(published_str, date_format)
                    parsed = True
                    
                    # Include article if it's within the time window (newer than target_date)
                    if published_date >= target_date:
                        filtered_articles.append(article)
                        print(f"[INFO] Including article from {published_date}: {article.get('title', 'No Title')}")
                    else:
                        print(f"[INFO] Excluding article from {published_date}: {article.get('title', 'No Title')}")
                    break
                except ValueError:
                    continue
            
            if not parsed:
                print(f"[INFO] Excluding article with unparseable date: {article.get('title', 'No Title')}")
                
        except Exception as e:
            print(f"[INFO] Excluding article due to date parsing error: {article.get('title', 'No Title')}, Error: {e}")
    
    # If we don't have enough articles from time window, include articles with unknown dates
    if len(filtered_articles) < 3:
        print(f"[INFO] Not enough articles from past {window_text}. Including some articles with unknown dates.")
        unknown_date_articles = []
        
        # Add up to 5 articles with unknown dates
        for article in articles:
            published_str = article.get('published', '')
            if not published_str or published_str == 'Unknown Date':
                unknown_date_articles.append(article)
                print(f"[INFO] Including article with unknown date: {article.get('title', 'No Title')}")
                if len(unknown_date_articles) >= 5:
                    break
        
        filtered_articles.extend(unknown_date_articles[:5])  # Add up to 5 unknown date articles
    
    # If we still don't have enough articles, include the most recent ones regardless of date
    if len(filtered_articles) < 3 and len(articles) > 3:
        print(f"[INFO] Still not enough articles. Including recent available articles.")
        
        # Try to sort articles by date if possible
        dated_articles = []
        for article in articles:
            if article in filtered_articles:
                continue  # Skip articles already included
                
            try:
                published_str = article.get('published', '')
                if not published_str or published_str == 'Unknown Date':
                    continue
                    
                for date_format in date_formats:
                    try:
                        published_date = datetime.strptime(published_str, date_format)
                        dated_articles.append((published_date, article))
                        break
                    except ValueError:
                        continue
            except Exception:
                pass
        
        # Sort by date (most recent first) and take what we need
        if dated_articles:
            dated_articles.sort(reverse=True)  # Sort most recent first
            needed = max(0, 5 - len(filtered_articles))  # Get enough to have at least 5 articles
            for _, article in dated_articles[:needed]:
                filtered_articles.append(article)
                print(f"[INFO] Including recent article: {article.get('title', 'No Title')}")
    
    # If we still have no articles, include some without date checking (last resort)
    if not filtered_articles and articles:
        print(f"[WARN] No dated articles found. Including up to 5 articles without date checking.")
        filtered_articles = articles[:5]  # Include up to 5 articles
    
    print(f"[INFO] Final article count: {len(filtered_articles)} articles")
    return filtered_articles

def deduplicate_articles(articles, similarity_threshold=0.7):
    """
    Remove duplicate or highly similar articles from the list.
    
    Args:
        articles (list): List of article dictionaries
        similarity_threshold (float): Threshold for considering two articles as duplicates (0.0-1.0)
        
    Returns:
        list: Deduplicated list of articles
    """
    if not articles:
        return []
        
    # Initialize with the first article
    deduplicated = [articles[0]]
    duplicates_removed = 0
    
    # Helper function to compute text similarity ratio
    def similarity_ratio(text1, text2):
        return SequenceMatcher(None, str(text1).lower(), str(text2).lower()).ratio()
    
    # Process remaining articles
    for article in articles[1:]:
        title = article.get('title', '').lower()
        content_preview = article.get('content', '')[:500].lower()  # Use just beginning of content
        combined = f"{title} {content_preview}"
        
        # Check if this article is similar to any already included article
        is_duplicate = False
        for existing in deduplicated:
            existing_title = existing.get('title', '').lower()
            existing_preview = existing.get('content', '')[:500].lower()
            existing_combined = f"{existing_title} {existing_preview}"
            
            # Calculate similarity between titles and content
            title_similarity = similarity_ratio(title, existing_title)
            combined_similarity = similarity_ratio(combined, existing_combined)
            
            # If either title or content is very similar, consider it a duplicate
            if title_similarity > similarity_threshold or combined_similarity > similarity_threshold:
                is_duplicate = True
                duplicates_removed += 1
                
                # Choose the article with more content if they're similar
                if len(article.get('content', '')) > len(existing.get('content', '')):
                    # Replace the existing article with this one
                    deduplicated.remove(existing)
                    deduplicated.append(article)
                    print(f"[INFO] Replaced duplicate with more detailed version: {article.get('title', 'No Title')}")
                else:
                    print(f"[INFO] Removed duplicate article: {article.get('title', 'No Title')}")
                break
        
        # If not a duplicate, include it
        if not is_duplicate:
            deduplicated.append(article)
    
    print(f"[INFO] Deduplicated {len(articles)} articles to {len(deduplicated)} (removed {duplicates_removed} duplicates)")
    return deduplicated

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
        section = classify_article(article)
        if section == 'global_major':
            matches.append("This international development could have widespread implications for global politics or economics.")
        elif section == 'domestic_major':
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