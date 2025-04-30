"""High-level formatting coordination."""
from typing import List, Dict
from ai_newsletter.core.types import Article
from ai_newsletter.logging_cfg.logger import setup_logger
from ai_newsletter.formatting.render import format_article, build_newsletter

logger = setup_logger()

# Re-export the core formatting functions
__all__ = ['format_article', 'build_newsletter']