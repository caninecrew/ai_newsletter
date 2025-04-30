"""Article rendering and formatting functions."""
from typing import List
from datetime import datetime
from ai_newsletter.core.types import Article
from ai_newsletter.formatting.components import format_summary_block, get_tags_html
from ai_newsletter.formatting.date_utils import format_date
from ai_newsletter.formatting.layout import wrap_with_css, build_header, build_footer
from ai_newsletter.formatting.text_utils import get_key_takeaways
from ai_newsletter.logging_cfg.logger import setup_logger

logger = setup_logger()