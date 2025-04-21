# This module contains functions to format news articles for email or display purposes.

def format_article(article):
    """
    Formats a single article into a string for display or email.

    Args:
        article (dict): A dictionary containing article details like title, author, and content.

    Returns:
        str: A formatted string representation of the article.
    """
    title = article.get('title', 'No Title')
    author = article.get('author', 'Unknown Author')
    content = article.get('content', 'No Content')

    return f"Title: {title}\nAuthor: {author}\n\n{content}\n\n"

def format_articles(articles):
    """
    Formats a list of articles into a single string for display or email.

    Args:
        articles (list): A list of dictionaries, each containing article details.

    Returns:
        str: A formatted string representation of all articles.
    """
    return "\n---\n".join(format_article(article) for article in articles)