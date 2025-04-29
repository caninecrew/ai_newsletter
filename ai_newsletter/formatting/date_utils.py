"""Date handling utilities."""
from typing import List, Dict, Optional
from datetime import datetime
from dateutil import parser, tz as dateutil_tz
from ai_newsletter.logging_cfg.logger import setup_logger

logger = setup_logger()

# Define Central timezone
CENTRAL = dateutil_tz.gettz("America/Chicago")

def format_date(date_str: str) -> str:
    """Format a date string into a human-readable format."""
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
                    parsed_date = parsed_date.replace(tzinfo=CENTRAL)
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
                            parsed_date = parsed_date.replace(tzinfo=CENTRAL)
                        break
                    except ValueError:
                        continue
                else:
                    return date_str  # Return original if all formats fail

        # Convert to CENTRAL for display
        parsed_date = parsed_date.astimezone(CENTRAL)
        return parsed_date.strftime("%B %d, %Y")
        
    except Exception as e:
        logger.warning(f"Date parsing error: {e}")
        return date_str

def filter_articles_by_date(articles: List[Dict], 
                          start_date: Optional[datetime] = None, 
                          end_date: Optional[datetime] = None) -> List[Dict]:
    """Filter articles based on aware start and end dates in CENTRAL timezone."""
    filtered_articles = []
    if not start_date and not end_date:
        return articles  # No filtering needed

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
            continue  # Skip articles without a publish date

        # Ensure article date is aware and in CENTRAL for comparison
        if isinstance(publish_date, str):
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