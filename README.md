# Twitter/X Feed Scraper & Analyzer

Scrape any public Twitter/X user's feed via Nitter and get actionable business insights -- no API keys needed.

## Features

- Scrapes tweets via public Nitter instances (no Twitter API required)
- Automatic instance fallback if one is down
- Posting frequency and pattern analysis
- Engagement metrics and top-performing tweets
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

## Usage

```bash
# Basic usage - scrape and analyze
python main.py username

# Use a specific Nitter instance
python main.py username --instance https://nitter.privacydev.net

# Scrape more pages (default: 5)
python main.py username --max-pages 10

# Only scrape, skip analysis
python main.py username --no-analysis

# Re-analyze previously scraped data
python main.py username --load-json data/username_tweets.json

# Verbose output for debugging
python main.py username -v
```

## Output

- `data/<username>_tweets.json` - Raw scraped tweet data
- `data/<username>_report.json` - Full analysis report
- Console output with formatted report and key business insights

## Project Structure

| File | Purpose |
|------|---------|
| `main.py` | CLI entry point |
| `scraper.py` | Nitter scraping engine |
| `analyzer.py` | Business insight analysis |
| `reporter.py` | Report formatting and output |
| `models.py` | Tweet and UserProfile data classes |
| `config.py` | Nitter instances and constants |
| `utils.py` | Shared helper functions |

## Notes

- Nitter instances are community-run and may go down. The tool automatically tries multiple instances.
- If all built-in instances fail, provide a working one with `--instance`.
- Find active instances at: https://github.com/zedeus/nitter/wiki/Instances
- Be respectful of Nitter instances -- the tool includes built-in delays between requests.
