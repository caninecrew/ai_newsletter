"""URL builder for hosted newsletters."""
from datetime import datetime
from typing import Optional

def build_newsletter_url(date: Optional[datetime] = None) -> str:
    """Build the URL for a newsletter on a specific date.
    
    Args:
        date: Optional date to build URL for. Defaults to today.
        
    Returns:
        str: Full URL to the hosted newsletter
    """
    if date is None:
        date = datetime.now()
    
    # Format YYYY-MM-DD
    date_str = date.strftime("%Y-%m-%d")
    return f"https://samuelrumbley.com/newsletters/{date_str}.html"