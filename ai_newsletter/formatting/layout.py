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
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Your Daily News Summary</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
                line-height: 1.6;
                color: #2c3e50;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
                background-color: #f8fafc;
            }}
            
            .header {{
                text-align: center;
                margin-bottom: 30px;
                padding: 20px;
                background: white;
                border-radius: 8px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            }}
            
            .header h1 {{
                margin: 0;
                color: #1a202c;
                font-size: 24px;
            }}
            
            .date {{
                color: #64748b;
                font-size: 14px;
                margin-top: 8px;
            }}
            
            .section {{
                background: white;
                border-radius: 8px;
                padding: 24px;
                margin-bottom: 24px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            }}
            
            .section h2 {{
                margin-top: 0;
                margin-bottom: 16px;
                font-size: 20px;
                color: #1a202c;
                display: flex;
                align-items: center;
                gap: 8px;
            }}

            .trending {{
                border-left: 4px solid #3b82f6;
            }}
            
            .highlights {{
                list-style: none;
                padding: 0;
                margin: 16px 0;
            }}
            
            .highlights li {{
                padding: 8px 0;
                border-bottom: 1px solid #e2e8f0;
            }}
            
            .highlights li:last-child {{
                border-bottom: none;
            }}
            
            .article {{
                padding: 16px 0;
                border-bottom: 1px solid #e2e8f0;
            }}
            
            .article:last-child {{
                border-bottom: none;
                padding-bottom: 0;
            }}
            
            .article-title {{
                margin: 0 0 8px 0;
                font-size: 16px;
                font-weight: 600;
                color: #1a202c;
            }}
            
            .article-meta {{
                font-size: 14px;
                color: #64748b;
                margin-bottom: 12px;
            }}
            
            .read-more {{
                color: #3b82f6;
                text-decoration: none;
            }}
            
            .read-more:hover {{
                text-decoration: underline;
            }}
            
            .tag {{
                display: inline-block;
                padding: 2px 8px;
                margin: 0 4px 4px 0;
                border-radius: 16px;
                background-color: #f1f5f9;
                color: #475569;
                font-size: 12px;
            }}
            
            .takeaway-bullets {{
                margin: 12px 0;
                padding-left: 24px;
                color: #475569;
                font-size: 14px;
            }}
            
            .takeaway-bullets li {{
                margin-bottom: 8px;
            }}
            
            .takeaway-bullets li:last-child {{
                margin-bottom: 0;
            }}
            
            .more-stories {{
                text-align: center;
                padding: 16px;
                background: white;
                border-radius: 8px;
                margin-top: 24px;
                color: #64748b;
            }}
            
            .more-stories a {{
                color: #3b82f6;
                text-decoration: none;
            }}
            
            .footer {{
                text-align: center;
                margin-top: 40px;
                padding-top: 20px;
                border-top: 1px solid #e2e8f0;
                color: #64748b;
                font-size: 14px;
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
        <h1>Daily News Digest</h1>
        <div class="date">{date_range}</div>
    </div>
    """

def build_footer() -> str:
    """Generate the newsletter footer."""
    return """
    <div class="footer">
        <p>This digest was automatically curated for you.</p>
        <p>To customize your topics or unsubscribe, click <a href="#preferences">here</a>.</p>
    </div>
    """

def build_empty_newsletter() -> str:
    """Generate a polite 'no new stories' page."""
    return wrap_with_css(f"""
        {build_header()}
        <div class="section">
            <h2>No New Stories Today</h2>
            <p>We couldn't find any new articles matching your interests today. Check back tomorrow!</p>
        </div>
        {build_footer()}
    """)