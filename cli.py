"""
AI Newsletter CLI Entry Point.

This module provides access to the AI Newsletter command line interface.
Execute this script directly to generate and send newsletters:

    python cli.py

For configuration options and detailed usage, see README.md

MIT License - See LICENSE for details
"""
from ai_newsletter.cli import cli

if __name__ == "__main__":
    cli()