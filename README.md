# AI Newsletter Automation

This project automatically creates and sends a personalized daily news digest via email.

## Features

- Collects news from various sources across the political spectrum
- Categorizes articles into sections (global news, domestic headlines, personalized interests, etc.)
- Highlights key takeaways in a TL;DR style with expandable content
- Adds "Why This Matters" context to each article
- Uses personalization tags with emoji indicators (🔒 Legal, 🏫 Education, 🏥 Healthcare, etc.)
- Includes a clickable Table of Contents for easy navigation
- Filters for articles published in the last 24 hours
- Deduplicates similar articles to avoid redundancy
- Formats content into a clean, professional HTML email newsletter
- Automatically sends at 8:00 AM daily using GitHub Actions

## How It Works

1. **Article Collection**: Fetches articles from RSS feeds defined in `fetch_news.py`
2. **Date Filtering**: Filters for articles published in the last 24 hours
3. **Deduplication**: Removes redundant articles with similar content
4. **Summarization**: Creates concise summaries of each article using OpenAI's API
5. **Categorization**: Sorts articles into different sections based on content and source
6. **Enhancement**: Adds key takeaways, "Why This Matters" sections, and personalization tags
7. **Formatting**: Creates a professionally formatted HTML email with consistent styling
8. **Delivery**: Sends the final newsletter via email

## Email Format

The newsletter is formatted with the following elements:
- **Header**: Title and date of the newsletter
- **Table of Contents**: Clickable links to each section with article counts
- **Article Sections**: 
  - 🌍 Super Major International News
  - 🏛️ Major Domestic Headlines
  - 📌 Personalized Interest Stories
  - 🦊 Fox News Exclusive Reporting
- **Article Format**:
  - Title and source
  - Personalization tags with emojis
  - Key takeaways (TL;DR style)
  - Expandable full summary
  - "Why This Matters" section
  - Link to original article

## Automation with GitHub Actions

This newsletter runs automatically at 8:00 AM UTC daily through GitHub Actions. The workflow:
- Checks out the repository code
- Sets up Python and required dependencies
- Runs the newsletter script
- Archives logs for troubleshooting

## Setup Instructions

1. **Fork this repository** to your GitHub account
2. **Add the following secrets** to your repository:
   - `RECIPIENT_EMAIL`: Email address to receive the newsletter
   - `SMTP_EMAIL`: Sender email address
   - `SMTP_SERVER`: SMTP server (e.g., smtp.gmail.com)
   - `SMTP_PORT`: SMTP port (typically 587 for TLS or 465 for SSL)
   - `SMTP_PASS`: Password for the sender email
   - `OPENAI_API_KEY`: Your OpenAI API key for article summarization

3. **Enable GitHub Actions** in your repository settings
4. **Test the workflow** by manually triggering it via the "Actions" tab

## Customizing Your Newsletter

- Edit `USER_INTERESTS` in `formatter.py` to personalize your content
- Modify `PERSONALIZATION_TAGS` in `formatter.py` to change tag emojis
- Update RSS feeds in `fetch_news.py` to change news sources
- Adjust styling in the HTML template in `formatter.py`

## Components

- `fetch_news.py`: Collects articles from various RSS feeds
- `summarize.py`: Processes and summarizes article content using OpenAI's API
- `formatter.py`: Formats articles into an HTML email with enhanced features
- `send_email.py`: Handles email delivery via SMTP
- `main.py`: Coordinates the entire process
- `.github/workflows/daily-newsletter.yml`: GitHub Actions workflow for automation

## Updates

### Configuration
- Added a configuration file for RSS feeds to replace hardcoded values.
- Integrated GNews API as an alternative to RSS feeds.

### Enhancements
- Implemented OpenAI API for summarization.
- Added caching mechanisms to reduce API calls and improve performance.
- Improved error logging and monitoring for GitHub Actions workflows.

### GitHub Actions
- Enhanced workflow to include error notifications and retry logic for failed tasks.