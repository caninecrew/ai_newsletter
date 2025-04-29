"""Article summarization using OpenAI API."""
from openai import OpenAI
import time
import os
from typing import Optional
from ai_newsletter.logging_cfg.logger import setup_logger
from ai_newsletter.core.types import Article

# Set up logger
logger = setup_logger()

# Initialize OpenAI client with API key
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def summarize_article(article: Article, max_retries: int = 3, retry_delay: int = 1) -> Optional[str]:
    """Generate a summary for a single article using OpenAI's API."""
    title = article.get('title', '').strip()
    description = article.get('description', '').strip()
    
    if not title and not description:
        logger.warning("Article lacks title and description for summarization")
        return None
    
    # Combine available metadata for summary
    text_to_summarize = []
    if title:
        text_to_summarize.append(f"Title: {title}")
    if description:
        text_to_summarize.append(f"Description: {description}")
        
    combined_text = "\n".join(text_to_summarize)
    
    # Try to generate summary
    for attempt in range(max_retries):
        try:
            messages = [
                {"role": "system", "content": "You are a helpful assistant that creates concise news summaries."},
                {"role": "user", "content": "Create a concise 2-3 sentence summary of this news article content. Focus on the key facts and main points:\n\n"}
            ]
            
            if title:
                messages[1]["content"] += f"Title: {title}\n\n"
            messages[1]["content"] += f"Content:\n{combined_text}"
            
            # Using the OpenAI API
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                max_tokens=150,
                temperature=0.5
            )
            
            summary = response.choices[0].message.content.strip()
            if summary:
                return summary
                
        except Exception as e:
            logger.warning(f"OpenAI API error (attempt {attempt + 1}): {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay * (attempt + 1))
            continue
            
    return None