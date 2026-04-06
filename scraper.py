"""Twitter/X GraphQL API scraper using browser session tokens."""

import json
import os
import re
import time
import random
import logging
from datetime import datetime, timezone
from urllib.parse import quote

import requests

from config import REQUEST_TIMEOUT
from models import Tweet, UserProfile

logger = logging.getLogger(__name__)

# Twitter's public Bearer token (same for all users, embedded in the web app)
BEARER_TOKEN = (
    "AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs"
    "%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA"
)

GRAPHQL_FEATURES = {
    "rweb_video_screen_enabled": False,
    "profile_label_improvements_pcf_label_in_post_enabled": True,
    "responsive_web_profile_redirect_enabled": False,
    "rweb_tipjar_consumption_enabled": False,
    "verified_phone_label_enabled": False,
    "creator_subscriptions_tweet_preview_api_enabled": True,
    "responsive_web_graphql_timeline_navigation_enabled": True,
    "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
    "premium_content_api_read_enabled": False,
    "communities_web_enable_tweet_community_results_fetch": True,
    "c9s_tweet_anatomy_moderator_badge_enabled": True,
    "responsive_web_grok_analyze_button_fetch_trends_enabled": False,
    "responsive_web_grok_analyze_post_followups_enabled": True,
    "responsive_web_jetfuel_frame": True,
    "responsive_web_grok_share_attachment_enabled": True,
    "responsive_web_grok_annotations_enabled": True,
    "articles_preview_enabled": True,
    "responsive_web_edit_tweet_api_enabled": True,
    "graphql_is_translatable_rweb_tweet_is_translatable_enabled": True,
    "view_counts_everywhere_api_enabled": True,
    "longform_notetweets_consumption_enabled": True,
    "responsive_web_twitter_article_tweet_consumption_enabled": True,
    "content_disclosure_indicator_enabled": True,
    "content_disclosure_ai_generated_indicator_enabled": True,
    "responsive_web_grok_show_grok_translated_post": True,
    "responsive_web_grok_analysis_button_from_backend": True,
    "post_ctas_fetch_enabled": True,
    "freedom_of_speech_not_reach_fetch_enabled": True,
    "standardized_nudges_misinfo": True,
    "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True,
    "longform_notetweets_rich_text_read_enabled": True,
    "longform_notetweets_inline_media_enabled": False,
    "responsive_web_grok_image_annotation_enabled": True,
    "responsive_web_grok_imagine_annotation_enabled": True,
    "responsive_web_grok_community_note_auto_translation_is_enabled": False,
    "responsive_web_enhance_cards_enabled": False,
}

FIELD_TOGGLES = {"withArticlePlainText": False}

# GraphQL endpoint IDs (from Twitter's web app)
USER_TWEETS_ENDPOINT = "x3B_xLqC0yZawOB7WQhaVQ/UserTweets"
USER_BY_SCREEN_NAME_ENDPOINT = "qW5u-DAen47o2oBGUOGIeg/UserByScreenName"


def _load_tokens() -> tuple[str, str]:
    """Load auth tokens from .env file or environment variables."""
    auth_token = os.environ.get("AUTH_TOKEN", "")
    ct0 = os.environ.get("CT0", "")

    # Try loading from .env file if not in environment
    if not auth_token or not ct0:
        env_path = os.path.join(os.path.dirname(__file__), ".env")
        if os.path.exists(env_path):
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("#") or "=" not in line:
                        continue
                    key, val = line.split("=", 1)
                    key, val = key.strip(), val.strip()
                    if key == "AUTH_TOKEN":
                        auth_token = val
                    elif key == "CT0":
                        ct0 = val

    if not auth_token or not ct0:
        raise ValueError(
            "Missing auth tokens. Set AUTH_TOKEN and CT0 in .env file.\n"
            "See .env.example for instructions on getting these from your browser."
        )
    return auth_token, ct0


class TwitterScraper:
    """Scrapes Twitter/X using the internal GraphQL API."""

    def __init__(self, username: str, max_pages: int = 5):
        self.username = username.lstrip("@")
        self.max_pages = max_pages
        auth_token, ct0 = _load_tokens()

        self.session = requests.Session()
        self.session.headers.update({
            "accept": "*/*",
            "accept-language": "en-US,en;q=0.9",
            "authorization": f"Bearer {BEARER_TOKEN}",
            "content-type": "application/json",
            "x-csrf-token": ct0,
            "x-twitter-active-user": "yes",
            "x-twitter-auth-type": "OAuth2Session",
            "x-twitter-client-language": "en",
            "user-agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/146.0.0.0 Safari/537.36"
            ),
            "referer": f"https://x.com/{self.username}",
        })
        self.session.cookies.update({
            "auth_token": auth_token,
            "ct0": ct0,
        })

        self._user_id: str | None = None

    def _get_user_id(self) -> str:
        """Resolve username to user ID via GraphQL."""
        if self._user_id:
            return self._user_id

        variables = json.dumps({"screen_name": self.username, "withSafetyModeUserFields": True})
        features = json.dumps({
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
        })

        url = (
            f"https://x.com/i/api/graphql/{USER_BY_SCREEN_NAME_ENDPOINT}"
            f"?variables={quote(variables)}&features={quote(features)}"
        )

        resp = self.session.get(url, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()

        user_result = data.get("data", {}).get("user", {}).get("result", {})
        self._user_id = user_result.get("rest_id", "")
        if not self._user_id:
            raise ValueError(f"Could not find user ID for @{self.username}. Check the username.")
        logger.info(f"Resolved @{self.username} -> user ID {self._user_id}")
        return self._user_id

    def scrape_profile(self) -> UserProfile:
        """Fetch user profile info."""
        variables = json.dumps({"screen_name": self.username, "withSafetyModeUserFields": True})
        features = json.dumps({
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
        })

        url = (
            f"https://x.com/i/api/graphql/{USER_BY_SCREEN_NAME_ENDPOINT}"
            f"?variables={quote(variables)}&features={quote(features)}"
        )

        resp = self.session.get(url, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()

        user = data.get("data", {}).get("user", {}).get("result", {})
        legacy = user.get("legacy", {})

        profile = UserProfile(
            username=self.username,
            display_name=legacy.get("name", ""),
            bio=legacy.get("description", ""),
            followers=legacy.get("followers_count", 0),
            following=legacy.get("friends_count", 0),
            tweet_count=legacy.get("statuses_count", 0),
            joined=legacy.get("created_at", ""),
            verified=user.get("is_blue_verified", False),
        )

        # Cache user ID
        self._user_id = user.get("rest_id", "")

        return profile

    def scrape_tweets(self) -> list[Tweet]:
        """Fetch tweets from the user's timeline using GraphQL pagination."""
        user_id = self._get_user_id()
        all_tweets: list[Tweet] = []
        cursor: str | None = None

        for page in range(self.max_pages):
            logger.info(f"Fetching page {page + 1}/{self.max_pages}...")

            variables = {
                "userId": user_id,
                "count": 20,
                "includePromotedContent": False,
                "withQuickPromoteEligibilityTweetFields": True,
                "withVoice": True,
            }
            if cursor:
                variables["cursor"] = cursor

            url = (
                f"https://x.com/i/api/graphql/{USER_TWEETS_ENDPOINT}"
                f"?variables={quote(json.dumps(variables))}"
                f"&features={quote(json.dumps(GRAPHQL_FEATURES))}"
                f"&fieldToggles={quote(json.dumps(FIELD_TOGGLES))}"
            )

            resp = self.session.get(url, timeout=REQUEST_TIMEOUT)
            if resp.status_code == 429:
                logger.warning("Rate limited. Waiting 60 seconds...")
                time.sleep(60)
                resp = self.session.get(url, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()

            data = resp.json()
            tweets, next_cursor = self._parse_timeline_response(data)

            if not tweets:
                logger.info("No more tweets found.")
                break

            all_tweets.extend(tweets)
            logger.info(f"  Got {len(tweets)} tweets (total: {len(all_tweets)})")

            if not next_cursor:
                break
            cursor = next_cursor

            # Polite delay
            time.sleep(random.uniform(1.0, 2.5))

        logger.info(f"Scraped {len(all_tweets)} tweets total.")
        return all_tweets

    def _parse_timeline_response(self, data: dict) -> tuple[list[Tweet], str | None]:
        """Parse the GraphQL timeline response into Tweet objects."""
        tweets: list[Tweet] = []
        next_cursor: str | None = None

        # Navigate the nested response structure
        instructions = (
            data.get("data", {})
            .get("user", {})
            .get("result", {})
            .get("timeline_v2", {})
            .get("timeline", {})
            .get("instructions", [])
        )

        entries = []
        for instruction in instructions:
            if instruction.get("type") == "TimelineAddEntries":
                entries = instruction.get("entries", [])
            elif instruction.get("type") == "TimelineAddToModule":
                entries.extend(instruction.get("moduleItems", []))

        for entry in entries:
            entry_id = entry.get("entryId", "")

            # Pagination cursor
            if "cursor-bottom" in entry_id:
                content = entry.get("content", {})
                next_cursor = content.get("value", "")
                continue
            if "cursor-top" in entry_id:
                continue

            # Tweet entries
            if entry_id.startswith("tweet-") or entry_id.startswith("profile-conversation"):
                tweet = self._extract_tweet_from_entry(entry)
                if tweet:
                    tweets.append(tweet)
            # Conversation threads (multiple tweets)
            elif entry_id.startswith("profile-conversation"):
                items = (
                    entry.get("content", {})
                    .get("items", [])
                )
                for item in items:
                    tweet = self._extract_tweet_from_item(item)
                    if tweet:
                        tweets.append(tweet)

        return tweets, next_cursor

    def _extract_tweet_from_entry(self, entry: dict) -> Tweet | None:
        """Extract a Tweet from a timeline entry."""
        content = entry.get("content", {})
        # Single tweet
        item_content = content.get("itemContent", {})
        if not item_content:
            # Could be a conversation module
            items = content.get("items", [])
            for item in items:
                tweet = self._extract_tweet_from_item(item)
                if tweet:
                    return tweet
            return None

        return self._parse_tweet_result(item_content)

    def _extract_tweet_from_item(self, item: dict) -> Tweet | None:
        """Extract a Tweet from a module item."""
        item_content = item.get("item", {}).get("itemContent", {})
        return self._parse_tweet_result(item_content)

    def _parse_tweet_result(self, item_content: dict) -> Tweet | None:
        """Parse a tweet from the GraphQL tweet_results structure."""
        tweet_results = item_content.get("tweet_results", {})
        result = tweet_results.get("result", {})

        # Handle "TweetWithVisibilityResults" wrapper
        if result.get("__typename") == "TweetWithVisibilityResults":
            result = result.get("tweet", {})

        if not result or result.get("__typename") not in ("Tweet", None):
            if result.get("__typename") == "TweetTombstone":
                return None
            if not result.get("legacy"):
                return None

        legacy = result.get("legacy", {})
        core = result.get("core", {}).get("user_results", {}).get("result", {})
        user_legacy = core.get("legacy", {})

        text = legacy.get("full_text", "")
        if not text:
            return None

        # Parse timestamp
        timestamp = None
        created_at = legacy.get("created_at", "")
        if created_at:
            try:
                timestamp = datetime.strptime(created_at, "%a %b %d %H:%M:%S %z %Y")
            except ValueError:
                pass

        # Engagement
        likes = legacy.get("favorite_count", 0)
        retweets = legacy.get("retweet_count", 0)
        replies = legacy.get("reply_count", 0)
        quotes = legacy.get("quote_count", 0)

        # Tweet ID
        tweet_id = legacy.get("id_str", result.get("rest_id", ""))

        # Is retweet?
        is_retweet = text.startswith("RT @") or "retweeted_status_result" in legacy

        # Is reply?
        is_reply = bool(legacy.get("in_reply_to_status_id_str"))

        # Media
        media_type = None
        media_entities = legacy.get("extended_entities", {}).get("media", [])
        if not media_entities:
            media_entities = legacy.get("entities", {}).get("media", [])
        if media_entities:
            mtype = media_entities[0].get("type", "")
            if mtype == "photo":
                media_type = "image"
            elif mtype == "video":
                media_type = "video"
            elif mtype == "animated_gif":
                media_type = "gif"

        # Hashtags, mentions, urls from entities
        entities = legacy.get("entities", {})
        hashtags = [h.get("text", "") for h in entities.get("hashtags", [])]
        mentions = [m.get("screen_name", "") for m in entities.get("user_mentions", [])]
        urls = [u.get("expanded_url", "") for u in entities.get("urls", []) if u.get("expanded_url")]

        # Clean t.co URLs from display text
        for url_entity in entities.get("urls", []):
            short = url_entity.get("url", "")
            expanded = url_entity.get("expanded_url", "")
            if short and expanded:
                text = text.replace(short, expanded)

        # Remove media URLs from text
        for m in media_entities:
            media_url = m.get("url", "")
            if media_url:
                text = text.replace(media_url, "").strip()

        return Tweet(
            id=tweet_id,
            text=text,
            timestamp=timestamp,
            replies=replies,
            retweets=retweets,
            likes=likes,
            quotes=quotes,
            hashtags=hashtags,
            mentions=mentions,
            urls=urls,
            is_retweet=is_retweet,
            is_reply=is_reply,
            media_type=media_type,
        )
