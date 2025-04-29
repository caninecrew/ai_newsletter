"""Module for article summarization using metadata from GNews API."""
import openai
import time
import os
from dotenv import load_dotenv
from typing import List, Dict
from ai_newsletter.logging_cfg.logger import setup_logger

# Set up logger
logger = setup_logger()

# Load environment variables
load_dotenv()

def summarize_articles(articles: List[Dict], max_summary_length=150, min_summary_length=50) -> List[Dict]:
    """
    Create summaries for articles using their metadata from GNews API.
    
    Args:
        articles: List of article dictionaries with title, description and content fields
        max_summary_length: Maximum length of generated summaries
        min_summary_length: Minimum length of generated summaries
        
    Returns:
        List of articles with added summaries
    """
    summarized = []
    summarization_stats = {
        'total': 0,
        'success': 0,
        'failed': 0,
        'skipped': 0
    }

    for article in articles:
        summarization_stats['total'] += 1
        
        # Skip if article already has a summary
        if article.get('summary'):
            summarization_stats['skipped'] += 1
            summarized.append(article)
            continue

        # Combine available metadata for summarization
        title = article.get('title', '').strip()
        description = article.get('description', '').strip()
        content = article.get('content', '').strip()
        
        # Skip if we don't have enough content to summarize
        if not title and not description and not content:
            logger.warning("Article has no content to summarize")
            summarization_stats['failed'] += 1
            continue
            
        try:
            # Combine available text for the summary
            text_to_summarize = []
            if title:
                text_to_summarize.append(f"Title: {title}")
            if description:
                text_to_summarize.append(f"Description: {description}")
            if content:
                text_to_summarize.append(f"Content: {content}")
                
            combined_text = "\n".join(text_to_summarize)
            
            # Generate summary using OpenAI
            summary = summarize_with_openai(combined_text, title)
            if summary:
                article['summary'] = summary
                article['summary_method'] = 'openai'
                summarization_stats['success'] += 1
            else:
                logger.warning(f"Failed to generate summary for: {title}")
                summarization_stats['failed'] += 1
                
        except Exception as e:
            logger.error(f"Error summarizing article: {str(e)}")
            summarization_stats['failed'] += 1
            continue
            
        summarized.append(article)

    # Log summarization statistics
    logger.info("\nSummarization Statistics:")
    logger.info(f"Total articles: {summarization_stats['total']}")
    logger.info(f"Successfully summarized: {summarization_stats['success']}")
    logger.info(f"Failed to summarize: {summarization_stats['failed']}")
    logger.info(f"Skipped (had summary): {summarization_stats['skipped']}")

    return summarized

def summarize_with_openai(text: str, title: str = None, max_retries: int = 3, retry_delay: int = 1) -> str:
    """
    Generate a summary using OpenAI's API.
    
    Args:
        text: Text to summarize
        title: Optional article title for context
        max_retries: Maximum number of retry attempts
        retry_delay: Delay between retries in seconds
        
    Returns:
        Generated summary or None if failed
    """
    for attempt in range(max_retries):
        try:
            messages = [
                {"role": "system", "content": "You are a helpful assistant that creates concise news summaries."},
                {"role": "user", "content": "Create a concise 2-3 sentence summary of this news article content. Focus on the key facts and main points:\n\n"}
            ]
            
            if title:
                messages[1]["content"] += f"Title: {title}\n\n"
            messages[1]["content"] += f"Content:\n{text}"

            response = openai.ChatCompletion.create(
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
