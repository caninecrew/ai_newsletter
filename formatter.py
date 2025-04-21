# This module contains functions to format news articles for email or display purposes.
from datetime import datetime, timedelta

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
    category = article.get('category', 'Uncategorized')
    url = article.get('url', '#')
    content = article.get('content', 'No Content')
    published = article.get('published', 'Unknown Date')
    
    if html:
        return f"""
        <div class="article">
            <h2 class="article-title"><a href="{url}" target="_blank">{title}</a></h2>
            <div class="article-meta">
                <span class="source">{source}</span>
                <span class="category">{category}</span>
                <span class="published">{published}</span>
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
        return f"Title: {title}\nSource: {source}\nCategory: {category}\nPublished: {published}\n\n{content}\n\nRead more: {url}\n\n"

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
        
        # Group articles by category
        categorized_articles = {}
        for article in articles:
            category = article.get('category', 'Uncategorized')
            if category not in categorized_articles:
                categorized_articles[category] = []
            categorized_articles[category].append(article)
            
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
                .category-section {{
                    margin-bottom: 30px;
                }}
                .category-header {{
                    background-color: #f8f9fa;
                    padding: 10px 15px;
                    border-left: 4px solid #3498db;
                    margin-bottom: 15px;
                }}
                .article {{
                    border-bottom: 1px solid #f0f0f0;
                    padding-bottom: 20px;
                    margin-bottom: 20px;
                }}
                .article:last-child {{
                    border-bottom: none;
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
                    gap: 15px;
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
                .footer {{
                    margin-top: 40px;
                    text-align: center;
                    font-size: 14px;
                    color: #7f8c8d;
                    border-top: 1px solid #f0f0f0;
                    padding-top: 20px;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Daily News Summary</h1>
                <p class="date">News from {yesterday}</p>
            </div>
        """
        
        # Add each category section
        for category, category_articles in categorized_articles.items():
            html_output += f"""
            <div class="category-section">
                <h2 class="category-header">{category}</h2>
            """
            
            for article in category_articles:
                html_output += format_article(article, html=True)
                
            html_output += "</div>"
            
        # Add footer
        html_output += """
            <div class="footer">
                <p>This newsletter was automatically generated for you.</p>
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
    
    Args:
        articles (list): List of article dictionaries
        days (int): Number of days to look back (default: 1 for yesterday)
        
    Returns:
        list: Filtered list of articles
    """
    filtered_articles = []
    target_date = datetime.now() - timedelta(days=days)
    
    for article in articles:
        try:
            # Try different date formats
            published_str = article.get('published', '')
            if not published_str or published_str == 'Unknown Date':
                # Include articles with unknown dates to avoid losing content
                filtered_articles.append(article)
                continue
                
            # Try parsing the date in different formats
            for date_format in ['%a, %d %b %Y %H:%M:%S %z', '%a, %d %b %Y %H:%M:%S %Z', '%Y-%m-%dT%H:%M:%S%z', '%Y-%m-%d %H:%M:%S']:
                try:
                    published_date = datetime.strptime(published_str, date_format)
                    # If we can parse the date, check if it's from target_date
                    if published_date.date() == target_date.date():
                        filtered_articles.append(article)
                    break
                except ValueError:
                    continue
        except:
            # If date parsing fails completely, include the article
            filtered_articles.append(article)
    
    return filtered_articles