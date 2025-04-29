"""Newsletter layout and styling."""
from typing import List
from datetime import datetime, timedelta
from ai_newsletter.core.types import Article

def wrap_with_css(content: str) -> str:
    """Wrap content with HTML head and CSS styles."""
    return f"""
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
            .article {{
                border-bottom: 1px solid #f0f0f0;
                padding-bottom: 25px;
                margin-bottom: 25px;
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
            .article-summary {{
                margin: 15px 0;
                padding: 15px;
                background-color: #f8f9fa;
                border-left: 3px solid #3498db;
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
        {content}
    </body>
    </html>
    """

def build_header() -> str:
    """Generate the newsletter header with date range."""
    now = datetime.now()
    yesterday = now - timedelta(days=1)
    date_range = f"{yesterday.strftime('%B %d')} - {now.strftime('%B %d, %Y')}"
    
    return f"""
    <div class="header">
        <h1>Your Daily News Summary</h1>
        <div class="date">News from {date_range}</div>
    </div>
    """

def build_footer() -> str:
    """Generate the newsletter footer."""
    return """
    <div class="footer">
        <p>This newsletter was automatically curated based on your interests.</p>
        <p>To unsubscribe, please reply with "unsubscribe" in the subject line.</p>
    </div>
    """

def build_empty_newsletter() -> str:
    """Generate a polite 'no new stories' page."""
    return wrap_with_css("""
        <div class="header">
            <h1>No New Stories Today</h1>
        </div>
        <p>We couldn't find any new articles to share with you today. Check back tomorrow for the latest updates!</p>
        """ + build_footer()
    )