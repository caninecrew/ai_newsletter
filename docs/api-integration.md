# API Integration Guide

This guide covers the integration with GNews and OpenAI APIs used by AI Newsletter.

## GNews API

### Setup
1. Sign up at [GNews](https://gnews.io)
2. Get your API key from the dashboard
3. Add to `.env`:
```ini
GNEWS_API_KEY=your_key_here
```

### Usage
The GNews client (`ai_newsletter/feeds/gnews_client.py`) handles:
- Article fetching
- Category filtering
- Rate limiting
- Error handling

### Rate Limits
- Free tier: 100 requests/day
- Basic tier: 1000 requests/day
- Check [GNews pricing](https://gnews.io/pricing) for current limits

### Error Handling
The client implements:
- Exponential backoff
- Request retries
- Error logging
- Quota management

## OpenAI API

### Setup
1. Create account at [OpenAI](https://platform.openai.com)
2. Generate API key in dashboard
3. Add to `.env`:
```ini
OPENAI_API_KEY=your_key_here
```

### Usage
The OpenAI integration (`ai_newsletter/llm/`) provides:
- Article summarization
- Content analysis
- Key point extraction
- Language optimization

### Models
Currently using:
- GPT-4 for summarization
- GPT-3.5-turbo for faster operations
- Ada for embeddings (future)

### Cost Management
Implemented strategies:
- Token counting
- Batch processing
- Caching
- Model selection optimization

## Rate Limiting

### Implementation
Rate limiting is handled by `ai_newsletter/llm/utils.py`:
```python
@retry_with_backoff(
    max_retries=3,
    initial_delay=1,
    max_delay=60
)
```

### Configuration
Adjust in `config/settings.py`:
```python
API_SETTINGS = {
    "rate_limit": 60,       # Requests per minute
    "timeout": 30,          # Request timeout
    "max_retries": 3        # Maximum retries
}
```

## Error Handling

### Common Errors
1. Authentication
   - Invalid API keys
   - Expired tokens
   - Permission issues

2. Rate Limits
   - Too many requests
   - Quota exceeded
   - Concurrent request limits

3. Network
   - Timeouts
   - Connection errors
   - DNS issues

### Error Recovery
Implemented strategies:
- Automatic retries
- Fallback options
- Error reporting
- Status monitoring

## Monitoring

### Metrics Tracked
- Request counts
- Response times
- Error rates
- Token usage
- Cost tracking

### Logging
All API interactions are logged:
- Request details
- Response status
- Error messages
- Performance metrics

## Best Practices

1. API Keys
   - Never commit keys
   - Rotate regularly
   - Use environment variables
   - Implement key validation

2. Rate Limiting
   - Respect API limits
   - Implement backoff
   - Monitor usage
   - Cache when possible

3. Error Handling
   - Log all errors
   - Implement retries
   - Provide fallbacks
   - Monitor patterns

4. Cost Management
   - Track usage
   - Set budgets
   - Optimize requests
   - Cache responses

## Testing

### API Tests
Run API integration tests:
```bash
pytest tests/ -m integration
```

### Mock Testing
Use provided mocks:
```python
from ai_newsletter.tests.mocks import MockGNewsClient, MockOpenAIClient
```

For more details on specific APIs:
- [GNews API Documentation](https://gnews.io/docs/v4)
- [OpenAI API Reference](https://platform.openai.com/docs/api-reference)
- [Rate Limiting Guide](./rate-limiting.md)