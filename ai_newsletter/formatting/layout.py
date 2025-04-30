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
    </head>
    <body style="margin: 0; padding: 0; min-width: 100%; font-family: -apple-system, BlinkMacSystemFont, Arial, sans-serif; line-height: 1.5; color: #1a202c; background-color: #f8fafc; -webkit-font-smoothing: antialiased;">
        <div class="email-wrapper" style="width: 100%; margin: 0; padding: 20px; background-color: #f8fafc;">
            <div class="email-content" style="max-width: 600px; margin: 0 auto;">
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
    <div class="header" style="text-align: center; padding: 24px; background-color: #ffffff; border-radius: 8px; margin-bottom: 24px; box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);">
        <h1 style="margin: 0; font-size: 24px; font-weight: 600; color: #1a202c;">🗞️ Daily News Digest</h1>
        <div class="date" style="margin-top: 8px; color: #64748b; font-size: 14px;">{date_range}</div>
    </div>
    """

def build_footer() -> str:
    """Generate the newsletter footer."""
    return """
    <div class="footer" style="text-align: center; padding: 24px; color: #64748b; font-size: 14px; background-color: #ffffff; border-radius: 8px; box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);">
        <p style="margin: 0 0 8px 0;">This digest was automatically curated for you</p>
        <p style="margin: 0;">
            <a href="#customize" style="color: #3b82f6; text-decoration: none;">Customize Topics</a> • 
            <a href="#unsubscribe" style="color: #3b82f6; text-decoration: none;">Unsubscribe</a>
        </p>
    </div>
    """

def build_empty_newsletter() -> str:
    """Generate a polite 'no new stories' page."""
    return wrap_with_css(f"""
        {build_header()}
        <div class="digest" style="background-color: #ffffff; border-radius: 8px; padding: 24px; margin-bottom: 24px; box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);">
            <h2 style="margin: 0 0 16px 0; font-size: 20px; font-weight: 600; color: #1a202c;">No New Stories Today</h2>
            <p style="margin: 0; color: #64748b;">We couldn't find any new articles matching your interests today. Check back tomorrow!</p>
        </div>
        {build_footer()}
    """)