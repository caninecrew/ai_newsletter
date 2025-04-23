# AI Newsletter Project TODO List

## Core Requirements
- [X] Fetch articles from reliable news sources
- [X] Implement LLM summarization with OpenAI API
- [X] Send formatted email to recipients
- [X] Set up automated daily delivery (GitHub Actions)
- [X] Add configuration file instead of hardcoding RSS feeds

## Email Format Enhancements
- [ ] Highlight Key Takeaways First (TL;DR Style) with "Read Full Summary" link below
- [ ] Add "Why This Matters" section to each article
- [ ] Add personalization tags for filtering: 🔒 Legal, 🏫 Education, 🏥 Healthcare, 📈 Economy, 🧭 Global Affairs, ⚡️ Technology, etc (include other tags that might be relevant)
- [ ] Create clickable Table of Contents at the top of the email
- [ ] Ensure email has clean, professional formatting with consistent styling
- [ ] Improve formatting of the bullet points

## Technical Enhancements
- [X] Implement OpenAI API integration for article summarization
- [X] Add configurable news sources (RSS vs GNews API)
- [X] Store API keys securely in environment variables
- [ ] Add error logging and monitoring for GitHub Actions workflow
- [ ] Implement user preference settings for personalization tags
- [ ] Create fallback mechanisms if primary news sources are unavailable
- [ ] Implement caching to reduce API calls and improve performance
- [ ] Add usage statistics tracking for API calls
- [ ] Add unit tests for key components

## News Sources Configuration
- [X] Implement GNews API integration as alternative to RSS feeds
- [ ] Add NewsAPI or other alternative news sources
- [ ] Improve source categorization and diversity
- [ ] Create a better balance of political perspectives
- [ ] Switch to Google News RSS feeds as primary source:
  - [ ] Remove "PRIMARY_NEWS_SOURCE" setting and GNews API options
  - [ ] Create new PRIMARY_NEWS_FEEDS configuration with Google News RSS feeds
  - [ ] Delete or comment out unused GNEWS_API_CONFIG section
- [ ] Refactor feed organization:
  - [ ] Consolidate "News Aggregators" into PRIMARY_NEWS_FEEDS
  - [ ] Move local (Tennessee) and personalized (Scouting) feeds to SECONDARY_FEEDS
  - [ ] Update feed processing logic to prioritize PRIMARY_NEWS_FEEDS
- [ ] Enhance international news filtering:
  - [ ] Use INCLUDE_INTERNATIONAL_KEYWORDS to filter international stories
  - [ ] Only include international news that matches user interest keywords

## Date Handling & Content Processing
- [ ] Handle missing or blank dates:
  - [ ] Extract date from article content using regex patterns
  - [ ] Check for metadata tags like <meta property="article:published_time">
  - [ ] Use feed retrieval timestamp as fallback with "Date estimated" note
  - [ ] Standardize all dates to America/Chicago timezone (Central Time)
- [ ] Improve article deduplication:
  - [ ] Compare URLs across all feeds to prevent duplicates
  - [ ] Implement fuzzy matching on article titles (using difflib or Levenshtein)
  - [ ] Track fetched URLs in a cache to prevent duplicate processing

## Performance Improvements
- [ ] Optimize feed fetching:
  - [ ] Replace slow WebDriver initialization with asynchronous requests (aiohttp)
  - [ ] Implement retry logic for failed fetches using alternative sources
  - [ ] Use newspaper3k or Hugging Face for article extraction and summarization
- [ ] Implement feed health monitoring:
  - [ ] Check feed health at startup
  - [ ] Log issues for feeds that fail or return no articles
  - [ ] Switch to backup feeds when primary sources fail

## Email Content Balance
- [ ] Implement balanced content distribution:
  - [ ] Limit articles per political category (Left, Center, Right, International)
  - [ ] Create daily summary statistics (e.g., "12 articles today | 4 Left, 4 Center, 3 Right, 1 International")
  - [ ] Add keyword alerts for personal interests (e.g., Scouting, BSA, camping)
- [ ] Improve error handling and logging:
  - [ ] Report empty feeds after filtering
  - [ ] Log feed statistics and performance metrics
  - [ ] Include source variety analysis in logs (articles per feed, percent contribution)

## GitHub Actions
- [ ] Update GitHub Actions workflow to support both RSS and GNews API
- [ ] Add proper error notifications (email/Slack) on workflow failures
- [ ] Implement scheduled runs at different times to improve coverage
- [ ] Optimize workflow to reduce execution time

## Documentation
- [ ] Create detailed README with setup instructions
- [ ] Document available configuration options
- [ ] Add usage examples and screenshots
- [ ] Document the architecture and design decisions

## Project Demonstration (Due Date: TBD)
- [ ] Prepare 5-8 minute demonstration script covering:
  - [ ] Overview of application workflow
  - [ ] Explanation of article fetching process
  - [ ] Demonstration of LLM summarization
  - [ ] Showcase of email formatting and delivery
  - [ ] Live example of the complete process
- [ ] Schedule presentation (In-person or pre-record video)
- [ ] Prepare documentation of any remaining issues and debugging efforts

## Testing & Validation
- [ ] Test across different news categories and sources
- [ ] Validate email formatting on different email clients
- [ ] Time the complete process to ensure reasonable performance
- [ ] Create test scripts for CI/CD pipeline