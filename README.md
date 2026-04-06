# Twitter/X Feed Scraper & Analyzer

Scrape any Twitter/X user's feed and get actionable business insights.

## Features

- Scrapes tweets via Twitter's internal GraphQL API (same API the website uses)
- Full engagement metrics: likes, retweets, replies, quotes
- Posting frequency and pattern analysis
- Best posting times by hour and day
- Topic/hashtag/keyword extraction
- Content theme breakdown (original vs retweets vs replies)
- Sentiment analysis
- Business-actionable insight generation
- JSON export for further analysis

## Setup

```bash
pip install -r requirements.txt
python -c "import nltk; nltk.download('punkt_tab')"
```

### Auth Tokens

The scraper uses your browser's Twitter session. To get your tokens:

1. Log into x.com in Chrome
2. Open DevTools (F12) -> Network tab
3. Refresh the page and click any request to `x.com/i/api/graphql/...`
4. From the request headers/cookies, copy:
   - `auth_token` (from Cookies)
   - `ct0` (from Cookies or `x-csrf-token` header)
5. Create a `.env` file (see `.env.example`):

```
AUTH_TOKEN=your_auth_token_here
CT0=your_csrf_token_here
```

## Usage

```bash
# Basic usage - scrape and analyze
python main.py sam_allsopp_

# Scrape more pages (default: 5, ~20 tweets per page)
python main.py sam_allsopp_ --max-pages 10

# Only scrape, skip analysis
python main.py sam_allsopp_ --no-analysis

# Re-analyze previously scraped data
python main.py sam_allsopp_ --load-json data/sam_allsopp__tweets.json

# Verbose output for debugging
python main.py sam_allsopp_ -v
```

## Output

- `data/<username>_tweets.json` - Raw scraped tweet data
- `data/<username>_report.json` - Full analysis report
- Console output with formatted report and key business insights

## Project Structure

| File | Purpose |
|------|---------|
| `main.py` | CLI entry point |
| `scraper.py` | Twitter GraphQL API scraper |
| `analyzer.py` | Business insight analysis |
| `reporter.py` | Report formatting and output |
| `models.py` | Tweet and UserProfile data classes |
| `config.py` | Constants and defaults |
| `utils.py` | Shared helper functions |

## Notes

- Auth tokens expire periodically. If you get 401/403 errors, refresh them from your browser.
- The tool includes delays between requests to avoid rate limiting.
- Scraped data is saved to JSON so you can re-analyze without re-scraping.
