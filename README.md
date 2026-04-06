# Twitter/X Feed Scraper

Scrape tweets from any Twitter/X user profile using the same GraphQL API that the web client uses.

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Get your authentication headers:
   - Open [x.com](https://x.com) in your browser and log in
   - Open DevTools (F12) → **Network** tab → filter by **XHR**
   - Navigate to any user profile and refresh the page
   - Find the `UserTweets` request in the network list
   - Right-click → **Copy** → **Copy as cURL**
   - Go to [curlconverter.com](https://curlconverter.com) and paste to get Python code
   - Copy the `x-csrf-token` and `cookie` values into `headers_example.json` and rename it to `headers.json`

## Usage

```bash
# Basic usage — scrape 100 tweets from a user
python3 scrape_user_tweets.py --username elonmusk --headers-file headers.json

# Scrape 50 tweets and save to a file
python3 scrape_user_tweets.py -u elonmusk -c 50 --headers-file headers.json -o tweets.json

# Get the raw API response
python3 scrape_user_tweets.py -u elonmusk --headers-file headers.json --raw
```

## Output

Each tweet in the output includes:
- `id` — Tweet ID
- `created_at` — Timestamp
- `full_text` — Tweet content
- `retweet_count`, `favorite_count`, `reply_count`, `quote_count`, `bookmark_count` — Engagement metrics
- `views` — View count
- `user` — Author screen name and display name

## Notes

- Authentication headers expire periodically — refresh them from your browser when you get 401 errors.
- The `count` parameter controls how many tweets the API returns in a single request (max ~100).
- These are **not** guaranteed to be the latest tweets — Twitter's API may return a mix of recent and promoted content.
