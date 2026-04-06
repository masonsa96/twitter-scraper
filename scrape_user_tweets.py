"""
Twitter/X User Tweets Scraper

Scrapes tweets from a user's profile using the X (Twitter) API endpoint
that the web client uses (UserTweets GraphQL endpoint).

Setup:
1. Open any Twitter/X profile in your browser
2. Right-click -> Inspect -> Network tab -> filter by XHR
3. Refresh the page
4. Find the "UserTweets" request
5. Right-click the request -> Copy -> Copy as cURL
6. Go to https://curlconverter.com and paste to get Python code
7. Copy the headers dict from the converted code into a .env file or
   update the HEADERS dict below

Usage:
    python3 scrape_user_tweets.py --username elonmusk --count 100
    python3 scrape_user_tweets.py --username elonmusk --count 100 --output tweets.json
"""

import argparse
import json
import sys
from urllib.parse import quote

import requests


# Default GraphQL endpoint for UserTweets
USER_TWEETS_URL = "https://x.com/i/api/graphql/Y5bVDjBhqewHKEwONRMjcA/UserTweets"

# You MUST replace these headers with your own from the browser.
# Use the cURL converter method described above to get fresh values.
HEADERS = {
    "accept": "*/*",
    "accept-language": "en-US,en;q=0.9",
    "authorization": "Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA",
    "content-type": "application/json",
    "x-twitter-active-user": "yes",
    "x-twitter-client-language": "en",
    # ---- YOU MUST FILL THESE IN FROM YOUR BROWSER ----
    # "x-csrf-token": "YOUR_CSRF_TOKEN_HERE",
    # "cookie": "YOUR_COOKIES_HERE",
    # --------------------------------------------------
}


def get_user_id(username, headers):
    """Resolve a Twitter username to a numeric user ID via the UserByScreenName endpoint."""
    url = "https://x.com/i/api/graphql/xmU6X_CKVnQ5lSrCbAmJsg/UserByScreenName"
    variables = {
        "screen_name": username,
        "withSafetyModeUserFields": True,
    }
    features = {
        "hidden_profile_subscriptions_enabled": True,
        "rweb_tipjar_consumption_enabled": True,
        "responsive_web_graphql_exclude_directive_enabled": True,
        "verified_phone_label_enabled": False,
        "subscriptions_verification_info_is_identity_verified_enabled": True,
        "subscriptions_verification_info_verified_since_enabled": True,
        "highlights_tweets_tab_ui_enabled": True,
        "responsive_web_twitter_article_notes_tab_enabled": True,
        "subscriptions_feature_can_gift_premium": True,
        "creator_subscriptions_tweet_preview_api_enabled": True,
        "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
        "responsive_web_graphql_timeline_navigation_enabled": True,
    }
    params = {
        "variables": json.dumps(variables),
        "features": json.dumps(features),
    }
    resp = requests.get(url, headers=headers, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    try:
        return data["data"]["user"]["result"]["rest_id"]
    except (KeyError, TypeError):
        print(f"Error: Could not resolve user ID for @{username}")
        print("Response:", json.dumps(data, indent=2)[:500])
        sys.exit(1)


def scrape_user_tweets(user_id, count, headers):
    """Fetch tweets for a given user ID using the UserTweets GraphQL endpoint."""
    variables = {
        "userId": user_id,
        "count": count,
        "includePromotedContent": True,
        "withQuickPromoteEligibilityTweetFields": True,
        "withVoice": True,
        "withV2Timeline": True,
    }
    features = {
        "rweb_tipjar_consumption_enabled": True,
        "responsive_web_graphql_exclude_directive_enabled": True,
        "verified_phone_label_enabled": False,
        "creator_subscriptions_tweet_preview_api_enabled": True,
        "responsive_web_graphql_timeline_navigation_enabled": True,
        "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
        "communities_web_enable_tweet_community_results_fetch": True,
        "c9s_tweet_anatomy_moderator_badge_enabled": True,
        "articles_preview_enabled": True,
        "responsive_web_edit_tweet_api_enabled": True,
        "graphql_is_translatable_rweb_tweet_is_translatable_enabled": True,
        "view_counts_everywhere_api_enabled": True,
        "longform_notetweets_consumption_enabled": True,
        "responsive_web_twitter_article_tweet_consumption_enabled": True,
        "tweet_awards_web_tipping_enabled": False,
        "creator_subscriptions_quote_tweet_preview_enabled": False,
        "freedom_of_speech_not_reach_fetch_enabled": True,
        "standardized_nudges_misinfo": True,
        "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True,
        "rweb_video_timestamps_enabled": True,
        "longform_notetweets_rich_text_read_enabled": True,
        "longform_notetweets_inline_media_enabled": True,
        "responsive_web_enhance_cards_enabled": False,
    }
    params = {
        "variables": json.dumps(variables),
        "features": json.dumps(features),
    }
    resp = requests.get(USER_TWEETS_URL, headers=headers, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def extract_tweets(raw_response):
    """Parse the raw GraphQL response and return a list of simplified tweet dicts."""
    tweets = []
    try:
        instructions = raw_response["data"]["user"]["result"]["timeline_v2"]["timeline"]["instructions"]
    except (KeyError, TypeError):
        print("Warning: Unexpected response structure.")
        return tweets

    for instruction in instructions:
        entries = instruction.get("entries", [])
        for entry in entries:
            try:
                content = entry.get("content", {})
                item_content = content.get("itemContent") or {}
                tweet_results = item_content.get("tweet_results", {})
                result = tweet_results.get("result", {})

                # Skip promoted tweets or non-tweet types
                if result.get("__typename") not in ("Tweet", "TweetWithVisibilityResults"):
                    continue

                # Handle TweetWithVisibilityResults wrapper
                if result.get("__typename") == "TweetWithVisibilityResults":
                    result = result.get("tweet", result)

                legacy = result.get("legacy", {})
                core = result.get("core", {})
                user_legacy = (
                    core.get("user_results", {})
                    .get("result", {})
                    .get("legacy", {})
                )

                tweet = {
                    "id": legacy.get("id_str"),
                    "created_at": legacy.get("created_at"),
                    "full_text": legacy.get("full_text"),
                    "retweet_count": legacy.get("retweet_count"),
                    "favorite_count": legacy.get("favorite_count"),
                    "reply_count": legacy.get("reply_count"),
                    "quote_count": legacy.get("quote_count"),
                    "bookmark_count": legacy.get("bookmark_count"),
                    "views": result.get("views", {}).get("count"),
                    "lang": legacy.get("lang"),
                    "user": {
                        "screen_name": user_legacy.get("screen_name"),
                        "name": user_legacy.get("name"),
                    },
                }
                tweets.append(tweet)
            except (KeyError, TypeError, AttributeError):
                continue

    return tweets


def load_headers_from_file(path):
    """Load headers from a JSON file and merge with defaults."""
    with open(path, "r") as f:
        custom = json.load(f)
    merged = {**HEADERS, **custom}
    return merged


def main():
    parser = argparse.ArgumentParser(description="Scrape tweets from a Twitter/X user profile")
    parser.add_argument("--username", "-u", required=True, help="Twitter username (without @)")
    parser.add_argument("--count", "-c", type=int, default=100, help="Number of tweets to fetch (default: 100)")
    parser.add_argument("--output", "-o", help="Output file path (JSON). Prints to stdout if omitted.")
    parser.add_argument("--headers-file", help="Path to a JSON file with custom headers (must include x-csrf-token and cookie)")
    parser.add_argument("--raw", action="store_true", help="Output the raw API response instead of parsed tweets")
    args = parser.parse_args()

    headers = HEADERS.copy()
    if args.headers_file:
        headers = load_headers_from_file(args.headers_file)

    if "x-csrf-token" not in headers or headers.get("x-csrf-token", "").startswith("YOUR_"):
        print("Error: You must provide valid authentication headers.")
        print()
        print("To get your headers:")
        print("  1. Open https://x.com in your browser and log in")
        print("  2. Open DevTools (F12) -> Network tab -> filter XHR")
        print("  3. Navigate to any profile and find a 'UserTweets' request")
        print("  4. Right-click -> Copy as cURL -> paste at https://curlconverter.com")
        print("  5. Save the headers as JSON and pass with --headers-file,")
        print("     or edit HEADERS in this script directly.")
        sys.exit(1)

    print(f"Resolving user ID for @{args.username}...")
    user_id = get_user_id(args.username, headers)
    print(f"User ID: {user_id}")

    print(f"Scraping up to {args.count} tweets...")
    raw_response = scrape_user_tweets(user_id, args.count, headers)

    if args.raw:
        output = raw_response
    else:
        tweets = extract_tweets(raw_response)
        print(f"Scraped {len(tweets)} tweets.")
        output = tweets

    formatted = json.dumps(output, indent=2, ensure_ascii=False)

    if args.output:
        with open(args.output, "w") as f:
            f.write(formatted)
        print(f"Saved to {args.output}")
    else:
        print(formatted)


if __name__ == "__main__":
    main()
