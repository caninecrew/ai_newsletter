"""Text processing utilities."""
import re
from typing import List
from bs4 import BeautifulSoup

def strip_html(html: str) -> str:
    """
    Convert HTML to plain text by removing HTML tags while preserving structure.
    
    Args:
        html: HTML content to convert
        
    Returns:
        Plain text version of the HTML content
    """
    if not html:
        return ""
        
    # Parse HTML with BeautifulSoup
    soup = BeautifulSoup(html, 'html.parser')
    
    # Remove script and style elements
    for script in soup(["script", "style"]):
        script.decompose()
    
    # Get text while preserving some structure
    lines = []
    for element in soup.descendants:
        # Skip NavigableString inside certain tags
        if element.parent and element.parent.name in ['style', 'script']:
            continue
            
        if element.name == 'p':
            lines.append("\n")
        elif element.name == 'br':
            lines.append("\n")
        elif element.name == 'h1':
            lines.append("\n" + "="*40 + "\n")
        elif element.name == 'h2':
            lines.append("\n" + "-"*30 + "\n")
        elif element.name == 'li':
            lines.append("\n* ")
        elif element.name == 'a' and element.string:
            lines.append(f"{element.string} ({element.get('href', '')})")
        elif element.string and element.string.strip():
            lines.append(element.string.strip())
            
    # Join lines and fix spacing
    text = ' '.join(lines)
    
    # Fix multiple newlines and spaces
    text = re.sub(r'\n\s*\n', '\n\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    
    return text.strip()

def get_key_takeaways(content: str) -> str:
    """
    Extract key takeaways from the article content in a TL;DR style.
    This uses a simple extraction approach based on the first few sentences.
    
    Args:
        content: The article content or summary
        
    Returns:
        HTML formatted key takeaways
    """
    if not content or content.strip() == "No content available to summarize." or content.strip() == "Summary not available.":
        # Fallback to a "No content available" message
        return """
        <div class="key-takeaways">
            <h4>🔑 Key Takeaways:</h4>
            <p class="no-content-notice">This article couldn't be summarized. Please refer to the original source for details.</p>
        </div>
        """
    
    # Split content into sentences
    sentences = re.split(r'(?<=[.!?])\s+', content)
    
    # Get first 2-3 sentences for key takeaways, depending on length
    num_sentences = min(3, len(sentences))
    if len(sentences[0]) > 100:  # If first sentence is very long
        num_sentences = min(2, len(sentences))
    
    takeaways = sentences[:num_sentences]
    
    # Format as bullet points
    if takeaways:
        bullet_points = "".join([f"<li>{sentence.strip()}</li>" for sentence in takeaways])
        
        return f"""
        <div class="key-takeaways">
            <h4>🔑 Key Takeaways:</h4>
            <ul class="takeaway-bullets">
                {bullet_points}
            </ul>
        </div>
        """
    else:
        # Fallback if no sentences were extracted
        return """
        <div class="key-takeaways">
            <h4>🔑 Key Takeaways:</h4>
            <p class="no-content-notice">Key points not available. Please check the original article.</p>
        </div>
        """