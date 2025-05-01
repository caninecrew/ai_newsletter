"""
AI Newsletter - A Python-based automated newsletter system.

This module serves as the main entry point for the AI Newsletter system, which:
1. Fetches and aggregates news from reliable sources
2. Uses AI to summarize articles
3. Formats and delivers personalized newsletters via email

For detailed documentation, see README.md

Originally developed for Dr. Grant Clary's Spring 2025 DS-3850-001 Business Applications 
course at Tennessee Tech University.

MIT License - See LICENSE for details
"""
from ai_newsletter.cli import cli

if __name__ == "__main__":
    cli()