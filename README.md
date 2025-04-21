# AI Newsletter Automation

This project automatically creates and sends a personalized daily news digest via email.

## Features

- Collects news from various sources across the political spectrum
- Categorizes articles into sections (global news, domestic headlines, personalized interests, etc.)
- Filters for articles published in the last 24 hours
- Deduplicates similar articles to avoid redundancy
- Formats content into a clean HTML email newsletter
- Automatically sends at 8:00 AM daily using GitHub Actions

## How It Works

1. **Article Collection**: Fetches articles from RSS feeds defined in `fetch_news.py`
2. **Date Filtering**: Filters for articles published in the last 24 hours
3. **Deduplication**: Removes redundant articles with similar content
4. **Categorization**: Sorts articles into different sections based on content and source
5. **Summarization**: Creates concise summaries of each article
6. **Delivery**: Formats and sends the final newsletter via email

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

3. **Enable GitHub Actions** in your repository settings
4. **Test the workflow** by manually triggering it via the "Actions" tab

## Customizing Your Newsletter

- Edit `USER_INTERESTS` in `formatter.py` to personalize your content
- Modify RSS feeds in `fetch_news.py` to change news sources
- Adjust the HTML template in `formatter.py` to change the newsletter appearance