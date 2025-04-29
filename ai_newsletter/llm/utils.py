"""Utility functions for LLM operations."""
import time
from functools import wraps
from typing import Any, Callable, TypeVar

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