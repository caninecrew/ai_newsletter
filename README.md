# AI Newsletter Project

A Python-based automated newsletter system that aggregates, summarizes, and delivers personalized AI and technology news via email.

## Overview

This project automatically generates and sends a daily news digest by:
1. Fetching articles from GNews API and reliable news sources
2. Using OpenAI's API for intelligent article summarization
3. Applying smart categorization and deduplication
4. Delivering formatted newsletters via email
5. Running automated daily delivery through GitHub Actions

## Project Structure

```
ai_newsletter/
├── config/               # Configuration and settings
├── core/                # Core types and constants
├── deploy/              # Deployment utilities
├── email/              # Email formatting and sending
├── feeds/              # News fetching and filtering
├── formatting/         # Newsletter layout and styling
├── llm/                # LLM integration (OpenAI)
├── logging_cfg/        # Logging configuration
└── utils/              # Utility functions
```

## Features

### Content Management
- Intelligent article fetching using GNews API
- Smart deduplication to avoid redundant content
- Article categorization (World News, Technology, Business, etc.)
- Source balancing across political perspectives
- Content filtering by date and relevance

### Enhanced Formatting
- Key Takeaways sections for quick reading
- "Why This Matters" contextual insights
- Personalized content tags with emojis
- Clean, responsive email layout
- Clickable Table of Contents

### Technical Features
- OpenAI API integration for summarization
- Timezone-aware date handling
- Error logging and monitoring
- Retry mechanisms for API calls
- Caching for improved performance

## Requirements

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
SMTP_EMAIL=your_email
SMTP_PASS=your_password
RECIPIENT_EMAIL=recipient_email
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

### User Interests
Define interests for personalized content filtering:
- Technology areas (AI, Cloud, etc.)
- Business sectors
- Geographic regions
- Custom topics

## Usage

### Manual Execution
Run the newsletter generator:
```bash
python main.py
```

### Command Line Options
```bash
python main.py --start-date YYYY-MM-DD --end-date YYYY-MM-DD
```

### Automated Execution
The project includes GitHub Actions workflows for:
- Daily newsletter generation (8:00 AM CT)
- Email system testing
- Error monitoring and logging

## Testing

Run the test suite:
```bash
pytest tests/
```

Key test areas:
- Email delivery (`test_email_send.py`)
- News fetching (`test_fetch_news.py`)
- Content filtering (`test_fetcher_validation.py`)

## Architecture

### Core Components
1. **Feed Management**
   - GNews API integration
   - Article filtering and validation
   - Source categorization

2. **Content Processing**
   - OpenAI-powered summarization
   - Deduplication logic
   - Category classification

3. **Email Generation**
   - HTML template rendering
   - Responsive styling
   - Multi-part email creation

4. **Deployment**
   - GitHub Actions automation
   - Error handling
   - Logging and monitoring

### Data Flow
1. Article collection from GNews API
2. Filtering and deduplication
3. AI-powered summarization
4. Newsletter formatting
5. Email delivery

## Best Practices

- Rate limiting for API calls
- Error handling and retries
- Secure credential management
- Comprehensive logging
- Test coverage
- Code documentation

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

MIT License - See LICENSE file for details