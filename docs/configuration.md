# Configuration Guide

This guide covers all configuration options for AI Newsletter.

## Environment Variables

### Required Variables
| Variable | Description | Example |
|----------|-------------|---------|
| `GNEWS_API_KEY` | API key for GNews | `abc123...` |
| `OPENAI_API_KEY` | API key for OpenAI | `sk-abc123...` |
| `SMTP_SERVER` | SMTP server hostname | `smtp.gmail.com` |
| `SMTP_PORT` | SMTP server port | `587` |
| `SMTP_USERNAME` | SMTP authentication username | `user@example.com` |
| `SMTP_PASSWORD` | SMTP authentication password | `yourpassword` |
| `EMAIL_SENDER` | Sender email address | `newsletter@example.com` |
| `EMAIL_RECIPIENTS` | Comma-separated recipient list | `user1@example.com,user2@example.com` |

### Optional Variables
| Variable | Description | Default |
|----------|-------------|---------|
| `WEB_ARCHIVE_ENABLED` | Enable web archiving | `false` |
| `WEB_ARCHIVE_URL` | Base URL for archives | `None` |
| `WEB_ARCHIVE_PATH` | Local archive directory | `None` |
| `WEB_ARCHIVE_RETENTION_DAYS` | Days to keep archives | `30` |

## Settings File

Location: `ai_newsletter/config/settings.py`

### Newsletter Settings
```python
EMAIL_SETTINGS = {
    "max_articles_total": 10,        # Maximum articles per newsletter
    "max_articles_per_section": 5,   # Maximum articles per section
    "summary_length": 200,           # Target summary length
    "include_source_info": True,     # Include source reliability info
    "include_dates": True,           # Include article dates
}
```

### API Settings
```python
API_SETTINGS = {
    "rate_limit": 60,               # Requests per minute
    "timeout": 30,                  # Request timeout in seconds
    "max_retries": 3,              # Maximum retry attempts
    "batch_size": 10               # Articles per API batch
}
```

### Content Filters
```python
CONTENT_FILTERS = {
    "min_length": 100,             # Minimum article length
    "max_age_days": 7,            # Maximum article age
    "required_fields": [           # Required article fields
        "title",
        "description",
        "url"
    ],
    "blocked_domains": []         # Blocked source domains
}
```

## Customization

### Email Template
The email template (`email.html`) supports:
- Custom CSS styling
- Dynamic content blocks
- Responsive design
- Click tracking (optional)

### Topics and Categories
Edit `core/constants.py` to customize:
- News categories
- Topic keywords
- Source reliability thresholds
- Date formatting

## Advanced Configuration

### Logging
Configure logging in `logging_cfg/logger.py`:
- Log levels
- File rotation
- Format patterns
- Metrics tracking

### Web Archive
Configure web archive in `web/archive.py`:
- Storage structure
- URL patterns
- Retention policy
- Index generation

## Environment-Specific Settings

### Development
```ini
# .env.development
DEBUG=true
LOG_LEVEL=DEBUG
SKIP_EMAIL=true
```

### Production
```ini
# .env.production
DEBUG=false
LOG_LEVEL=INFO
SKIP_EMAIL=false
```

## Validation

Run configuration validation:
```bash
python -m ai_newsletter --validate-config
```

This will:
- Check environment variables
- Validate API keys
- Test SMTP connection
- Verify file permissions

For more details on specific settings, see:
- [API Integration Guide](./api-integration.md)
- [Email Setup Guide](./email-setup.md)
- [Web Features Guide](./web-features.md)