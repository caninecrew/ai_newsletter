import click
from ai_newsletter.feeds.fetcher import fetch_articles_from_all_feeds
from ai_newsletter.formatting.formatter import build_html
from ai_newsletter.email.sender import send_email

def run_newsletter():
    """Fetch, build, and send the newsletter."""
    articles = fetch_articles_from_all_feeds()
    if not articles:
        print("No articles fetched.")
        return

    html_content = build_html(articles)
    if not html_content:
        print("No content to send.")
        return

    send_email("AI Newsletter", html_content)

@click.command()
def cli():
    run_newsletter()

if __name__ == "__main__":
    cli()