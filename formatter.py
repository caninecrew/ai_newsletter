# This module contains functions to format news articles for email or display purposes.
from datetime import datetime, timedelta
import re

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
    
    # Check for personal interests
    for interest in USER_INTERESTS:
        if interest.lower() in combined_text:
            return 'personal_interest'
    
    # Default to personal interest if no clear classification
    return 'personal_interest'

def identify_tags(article):
    """
    Identify relevant tags based on article content and user interests.
    
    Args:
        article (dict): Article dictionary
        
    Returns:
        list: List of matching tags
    """
    title = article.get('title', '').lower()
    content = article.get('content', '').lower()
    combined_text = f"{title} {content}"
    
    matched_tags = []
    for interest in USER_INTERESTS:
        if interest.lower() in combined_text:
            matched_tags.append(interest)
    
    # Add some default categorization if no specific tags matched
    if not matched_tags:
        if "fox news" in article.get('source', '').lower():
            matched_tags.append("U.S. News")
        else:
            matched_tags.append("General News")
            
    return matched_tags

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
    content = article.get('content', 'No Content')
    published = article.get('published', 'Unknown Date')
    
    # Get article tags based on content
    tags = identify_tags(article)
    tags_html = "".join([f'<span class="tag">{tag}</span>' for tag in tags])
    
    if html:
        return f"""
        <div class="article">
            <h2 class="article-title"><a href="{url}" target="_blank">{title}</a></h2>
            <div class="article-meta">
                <span class="source">{source}</span>
                <span class="published">{published}</span>
                <div class="tags">{tags_html}</div>
            </div>
            <div class="article-content">
                <p>{content}</p>
            </div>
            <div class="read-more">
                <a href="{url}" target="_blank">Read full article &rarr;</a>
            </div>
        </div>
        """
    else:
        tags_text = ", ".join(tags)
        return f"Title: {title}\nSource: {source}\nTags: {tags_text}\nPublished: {published}\n\n{content}\n\nRead more: {url}\n\n"

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
                    margin-bottom: 30px;
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
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Your Personalized News Summary</h1>
                <p class="date">News from {yesterday}</p>
            </div>
        """
        
        # Add each section in the specified order
        section_order = ['global_major', 'domestic_major', 'personal_interest', 'fox_exclusive']
        section_classes = {
            'global_major': 'global-section',
            'domestic_major': 'domestic-section',
            'personal_interest': 'personal-section',
            'fox_exclusive': 'fox-section'
        }
        
        for section_key in section_order:
            section_articles = sections[section_key]
            section_title = SECTION_TYPES[section_key]
            section_class = section_classes[section_key]
            
            html_output += f"""
            <div class="section {section_class}">
                <h2 class="section-header">{section_title}</h2>
            """
            
            if not section_articles:
                html_output += """
                <div class="no-articles">
                    <p>No articles in this category today.</p>
                </div>
                """
            else:
                # Add section summary
                html_output += format_section_summary(section_key, section_articles)
                
                # Add articles
                for article in section_articles:
                    html_output += format_article(article, html=True)
            
            html_output += "</div>"
            
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

def filter_articles_by_date(articles, days=1):
    """
    Filter articles to only include those from the specified number of days back.
    Now with more flexible date parsing and optional fallback to include more content.
    
    Args:
        articles (list): List of article dictionaries
        days (int): Number of days to look back (default: 1 for yesterday)
        
    Returns:
        list: Filtered list of articles
    """
    filtered_articles = []
    target_date = datetime.now() - timedelta(days=days)
    print(f"[INFO] Filtering for articles from: {target_date.strftime('%Y-%m-%d')}")
    print(f"[INFO] Starting with {len(articles)} articles")
    
    # First pass with strict filtering
    for article in articles:
        try:
            # Try different date formats
            published_str = article.get('published', '')
            if not published_str or published_str == 'Unknown Date':
                # Include articles with unknown dates to avoid losing content
                filtered_articles.append(article)
                print(f"[INFO] Including article with unknown date: {article.get('title', 'No Title')}")
                continue
                
            # Try parsing the date in different formats
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
            
            parsed = False
            for date_format in date_formats:
                try:
                    published_date = datetime.strptime(published_str, date_format)
                    parsed = True
                    # If we can parse the date, check if it's from target_date
                    # Allow a window of ±1 day to account for timezone differences
                    delta = abs((published_date.date() - target_date.date()).days)
                    if delta <= 1:  # Relax the constraint to include more articles
                        filtered_articles.append(article)
                        print(f"[INFO] Including article from {published_date.date()}: {article.get('title', 'No Title')}")
                    break
                except ValueError:
                    continue
            
            # If we couldn't parse the date with any format, include the article anyway
            if not parsed:
                filtered_articles.append(article)
                print(f"[INFO] Including article with unparseable date: {article.get('title', 'No Title')}")
                
        except Exception as e:
            # If date parsing fails completely, include the article
            filtered_articles.append(article)
            print(f"[INFO] Including article due to date parsing error: {article.get('title', 'No Title')}, Error: {e}")
    
    # If we end up with too few articles, be less strict
    if len(filtered_articles) < 5 and len(articles) > 5:
        print(f"[WARN] Only {len(filtered_articles)} articles passed date filtering. Including more recent articles.")
        # Sort by published date if possible and take most recent
        try:
            # This is a simplistic approach - just include more articles
            return articles[:min(10, len(articles))]
        except:
            # If sorting fails, just return what we have plus a few more
            return filtered_articles + articles[:min(5, len(articles))]
    
    print(f"[INFO] Filtered to {len(filtered_articles)} articles")
    return filtered_articles