# AI Newsletter Project

A Python-based automated newsletter system that aggregates, summarizes, and delivers personalized AI and technology news via email. Developed for Dr. Grant Clary's Spring 2025 DS-3850-001 Business Applications course at Tennessee Tech University - Quarterly Assessment 4.

## Course Information
- **Course**: DS-3850-001 Business Applications
- **Term**: Spring 2025
- **Instructor**: Dr. Grant Clary
- **Project**: Quarterly Assessment 4 - AI-Powered News Newsletter

## Overview

This project automatically generates and sends a daily news digest by:
1. Fetching articles from GNews API and reliable news sources
2. Using OpenAI's API for intelligent article summarization
3. Applying smart categorization and deduplication
4. Delivering formatted newsletters via email
5. Running automated daily delivery through GitHub Actions

## Detailed Project Structure

```
ai_newsletter/
├── config/                   # Configuration and settings
│   ├── __init__.py
│   └── settings.py          # Core configuration parameters
│
├── core/                    # Core type definitions and constants
│   ├── __init__.py
│   ├── constants.py         # Project-wide constants
│   └── types.py            # TypeScript-like type definitions
│
├── deploy/                  # Deployment utilities
│   ├── __init__.py
│   └── url_builder.py      # URL generation for newsletters
│
├── email/                   # Email handling
│   ├── __init__.py
│   └── sender.py           # SMTP email sending functionality
│
├── feeds/                   # News source integration
│   ├── __init__.py
│   ├── fetcher.py          # Main article fetching logic
│   ├── filters.py          # Article filtering and validation
│   └── gnews_client.py     # GNews API integration
│
├── formatting/              # Content formatting
│   ├── __init__.py
│   ├── categorization.py   # Article category classification
│   ├── components.py       # Reusable HTML components
│   ├── date_utils.py       # Date handling and formatting
│   ├── deduplication.py    # Article deduplication logic
│   ├── formatter.py        # Main content formatting
│   ├── layout.py          # Email layout templates
│   ├── render.py          # HTML rendering
│   ├── tags.py            # Content tagging system
│   └── text_utils.py      # Text processing utilities
│
├── llm/                    # LLM integration
│   ├── __init__.py
│   ├── prompts.py         # OpenAI prompt templates
│   ├── summarize.py       # Article summarization
│   └── utils.py           # LLM utility functions
│
├── logging_cfg/            # Logging configuration
│   ├── __init__.py
│   └── logger.py          # Logging setup and utilities
│
├── utils/                  # General utilities
│   └── __init__.py
│
└── web/                    # Web integration (Future)
    ├── __init__.py
    ├── archive.py         # Newsletter archiving
    └── templates/         # Web templates
        ├── archive_index.html
        ├── robots.txt
        └── sitemap.xml

tests/                      # Test suite
├── __init__.py
├── test_email_send.py     # Email delivery tests
├── test_fetch_news.py     # News fetching tests
├── test_fetcher_validation.py  # Content validation tests
├── test_smtp_direct.py    # SMTP connection tests
└── test_web_archive.py    # Web archive tests (Future)

Root files:
├── cli.py                 # Command line interface
├── email.html            # Email template
├── main.py               # Application entry point
├── project_requirements.md  # Class Project requirements
├── pyproject.toml        # Python project metadata
├── README.md             # Project documentation
├── requirements.txt      # Package dependencies
├── setup.cfg            # Project configuration
└── todo.md              # Development tasks
```

## Current Features

### Content Management
- ✅ Intelligent article fetching using GNews API
- ✅ Smart deduplication to avoid redundant content
- ✅ Article categorization (World News, Technology, Business, etc.)
- ✅ Source balancing across political perspectives
- ✅ Content filtering by date and relevance

### Enhanced Formatting
- ✅ Article summaries and key points
- 🚧 Key Takeaways sections (In Progress)
- 🚧 "Why This Matters" contextual insights (In Progress)
- 🚧 Personalized content tags with emojis (In Progress)
- ✅ Clean, responsive email layout
- 🚧 Clickable Table of Contents (Planned)

### Technical Features
- ✅ OpenAI API integration for summarization
- ✅ Timezone-aware date handling (Central Time)
- ✅ Error logging and monitoring
- ✅ Retry mechanisms for API calls
- 🚧 Caching for improved performance (Planned)

### Web Integration (Future Implementation)
- 🚧 Automatic archiving of newsletters (Planned)
- 🚧 Responsive web design for archives (Planned)
- 🚧 Historical newsletter browsing (Planned)
- 🚧 Search and filtering capabilities (Planned)
- 🚧 RSS feed generation (Planned)

## Requirements

### Core Requirements
- Python 3.11+
- Required packages listed in `requirements.txt`
- Access to:
  - GNews API
  - OpenAI API
  - SMTP server for email delivery

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd ai_newsletter
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file with required credentials:
```env
GNEWS_API_KEY=your_gnews_api_key
OPENAI_API_KEY=your_openai_api_key
SMTP_SERVER=your_smtp_server
SMTP_PORT=587
SMTP_USERNAME=your_email
SMTP_PASSWORD=your_password
EMAIL_SENDER=sender_email
EMAIL_RECIPIENTS=recipient1@email.com,recipient2@email.com
```

## Configuration

### News Categories
Configure news categories and search queries in `config/settings.py`:
- Major domestic news
- International coverage
- Business and technology
- Specialized topics (configurable)

### Email Settings
Customize email settings including:
- Maximum articles per category/source
- Content balance preferences
- Layout and formatting options
- SMTP configuration

## Usage

### Manual Execution
Run the newsletter generator:
```bash
python main.py
```

### Automated Execution
The project includes GitHub Actions workflow for:
- Daily newsletter generation (8:00 AM CT)
- Error monitoring and logging

## Web Access

### Newsletter Archives
- All newsletters are archived at `https://samuelrumbley.com/newsletters/` (planned)
- Individual issues available at `https://samuelrumbley.com/newsletters/YYYY-MM-DD.html` (planned)
- Mobile-responsive design (planned)
- Search and filtering capabilities (planned)

### Archive Features
- Permanent links for sharing (planned)
- Historical browsing (planned)
- Categorized archives (planned)
- Full-text search (planned)
- Topic indexing (planned)

## Testing

Run the test suite:
```bash
pytest tests/
```

Current test coverage:
- ✅ Email delivery (`test_email_send.py`)
- ✅ News fetching (`test_fetch_news.py`)
- ✅ Content filtering (`test_fetcher_validation.py`)
- 🚧 Web archive deployment (Planned)

## Security

- ✅ Secure storage of API keys using environment variables
- ✅ Rate limiting for API calls
- ✅ TLS encryption for email
- ✅ Authentication handling
- 🚧 Web security features (Planned with web implementation)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

MIT License - See LICENSE file for details

## Support

For issues and feature requests:
- Submit GitHub issues
- Review documentation
- Contact contributors
