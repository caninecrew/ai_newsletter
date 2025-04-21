from fetch_news import fetch_articles_from_all_feeds
from summarize import summarize_articles

def run_newsletter():
    raw_articles = fetch_articles_from_all_feeds()
    summaries = summarize_articles(raw_articles)
    return summaries
