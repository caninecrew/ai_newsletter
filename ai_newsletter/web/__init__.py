"""Web integration package exports."""
from ai_newsletter.web.archive import (
    archive_newsletter,
    get_archived_newsletters,
    cleanup_old_archives
)

__all__ = [
    'archive_newsletter',
    'get_archived_newsletters',
    'cleanup_old_archives'
]