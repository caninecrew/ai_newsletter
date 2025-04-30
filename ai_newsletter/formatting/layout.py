"""Newsletter layout and styling."""
from typing import List
from datetime import datetime, timedelta
from ai_newsletter.core.types import Article

def wrap_with_css(content: str) -> str:
    """Wrap content with HTML head and CSS styles."""
    return f"""
    <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
    <html xmlns="http://www.w3.org/1999/xhtml">
    <head>
        <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
        <title>Your Daily News Summary</title>
        <style type="text/css">
            /* Base styles */
            body {{
                margin: 0;
                padding: 0;
                min-width: 100%;
                font-family: -apple-system, BlinkMacSystemFont, Arial, sans-serif;
                line-height: 1.5;
                color: #1a202c;
                background-color: #f8fafc;
                -webkit-font-smoothing: antialiased;
            }}

            /* Email container */
            .email-wrapper {{
                width: 100%;
                margin: 0;
                padding: 20px;
                background-color: #f8fafc;
            }}
            
            .email-content {{
                max-width: 600px;
                margin: 0 auto;
            }}

            /* Header styles */
            .header {{
                text-align: center;
                padding: 24px;
                background-color: #ffffff;
                border-radius: 8px;
                margin-bottom: 24px;
                box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
            }}

            .header h1 {{
                margin: 0;
                font-size: 24px;
                font-weight: 600;
                color: #1a202c;
            }}

            .date {{
                margin-top: 8px;
                color: #64748b;
                font-size: 14px;
            }}

            /* Digest content */
            .digest {{
                background-color: #ffffff;
                border-radius: 8px;
                padding: 24px;
                margin-bottom: 24px;
                box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
            }}

            .digest h2 {{
                margin: 0 0 24px 0;
                font-size: 20px;
                font-weight: 600;
                color: #1a202c;
                padding-bottom: 16px;
                border-bottom: 1px solid #e2e8f0;
            }}

            /* Article styling */
            .article {{
                padding: 20px 0;
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
                line-height: 1.4;
            }}

            .article-meta {{
                font-size: 14px;
                color: #64748b;
                margin-bottom: 12px;
            }}

            .read-more {{
                color: #3b82f6;
                text-decoration: none;
                font-weight: 500;
            }}

            /* Tags styling */
            .tag {{
                display: inline-block;
                padding: 2px 8px;
                margin: 0 4px 4px 0;
                border-radius: 12px;
                background-color: #f1f5f9;
                color: #475569;
                font-size: 12px;
            }}

            /* Bullet points */
            .takeaway-bullets {{
                margin: 12px 0 0 0;
                padding-left: 20px;
                list-style-type: disc;
                color: #475569;
            }}

            .takeaway-bullets li {{
                margin-bottom: 8px;
                font-size: 14px;
                line-height: 1.5;
            }}

            .takeaway-bullets li:last-child {{
                margin-bottom: 0;
            }}

            /* More stories section */
            .more-stories {{
                text-align: center;
                padding: 16px;
                margin-top: 24px;
                border-top: 1px solid #e2e8f0;
                color: #64748b;
                font-size: 14px;
            }}

            .more-stories a {{
                color: #3b82f6;
                text-decoration: none;
                font-weight: 500;
            }}

            /* Footer */
            .footer {{
                text-align: center;
                padding: 24px;
                color: #64748b;
                font-size: 14px;
                background-color: #ffffff;
                border-radius: 8px;
                box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
            }}

            .footer a {{
                color: #3b82f6;
                text-decoration: none;
            }}

            /* Metadata confidence indicators */
            .date-status {{
                display: inline-block;
                padding: 2px 6px;
                border-radius: 4px;
                font-size: 12px;
            }}
            
            .date-status.low {{
                background-color: #fee2e2;
                color: #991b1b;
            }}
            
            .date-status.medium {{
                background-color: #fef3c7;
                color: #92400e;
            }}
            
            .date-status.high {{
                background-color: #dcfce7;
                color: #166534;
            }}
            
            .reliability {{
                display: inline-block;
                padding: 2px 6px;
                border-radius: 4px;
                font-size: 12px;
            }}
            
            .reliability.low {{
                background-color: #fee2e2;
                color: #991b1b;
            }}
            
            .reliability.medium {{
                background-color: #fef3c7;
                color: #92400e;
            }}
            
            .reliability.high {{
                background-color: #dcfce7;
                color: #166534;
            }}
            
            .source-category {{
                color: #64748b;
                font-style: italic;
            }}
            
            /* Mobile optimizations */
            @media screen and (max-width: 600px) {{
                .email-wrapper {{
                    padding: 12px;
                }}

                .header, .digest, .footer {{
                    padding: 16px;
                    margin-bottom: 16px;
                }}

                .article {{
                    padding: 16px 0;
                }}

                .article-title {{
                    font-size: 15px;
                }}

                .article-meta, .takeaway-bullets li {{
                    font-size: 13px;
                }}
                
                .date-status, .reliability {{
                    display: inline;
                    padding: 1px 4px;
                    font-size: 11px;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="email-wrapper">
            <div class="email-content">
                {content}
            </div>
        </div>
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
        <h1>🗞️ Daily News Digest</h1>
        <div class="date">{date_range}</div>
    </div>
    """

def build_footer() -> str:
    """Generate the newsletter footer."""
    return """
    <div class="footer">
        <p>This digest was automatically curated for you</p>
        <p>
            <a href="#customize">Customize Topics</a> • 
            <a href="#unsubscribe">Unsubscribe</a>
        </p>
    </div>
    """

def build_empty_newsletter() -> str:
    """Generate a polite 'no new stories' page."""
    return wrap_with_css(f"""
        {build_header()}
        <div class="digest">
            <h2>No New Stories Today</h2>
            <p>We couldn't find any new articles matching your interests today. Check back tomorrow!</p>
        </div>
        {build_footer()}
    """)