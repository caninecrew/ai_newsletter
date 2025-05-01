"""Utility functions for LLM operations."""
import time
import os
from openai import OpenAI
import logging
from functools import wraps
from typing import Any, Callable, TypeVar, Optional

logger = logging.getLogger(__name__)

T = TypeVar('T')

def retry_with_backoff(max_retries: int = 3, base_delay: float = 1.0) -> Callable:
    """Decorator for retrying functions with exponential backoff."""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:  # Last attempt
                        raise
                    # Exponential backoff
                    delay = base_delay * (2 ** attempt)
                    time.sleep(delay)
            raise RuntimeError("Should not reach here")
        return wrapper
    return decorator

def test_openai_connection() -> bool:
    """Test OpenAI API connectivity.
    
    Returns:
        bool: True if connection successful
        
    Raises:
        Exception: If connection test fails
    """
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise Exception("OpenAI API key not found")
        
    try:
        client = OpenAI(api_key=api_key)
        
        # Test with minimal completion to validate API key
        response = client.completions.create(
            model="gpt-3.5-turbo-instruct",
            prompt="test",
            max_tokens=1
        )
        
        if not hasattr(response, 'choices') or not response.choices:
            raise Exception("Invalid API response structure")
            
        return True
        
    except Exception as e:
        raise Exception(f"OpenAI API connection failed: {str(e)}")