"""Twitter/X GraphQL API scraper."""

import json
import time
import random
import logging
from datetime import datetime
from urllib.parse import quote

import requests

from models import Tweet, UserProfile

logger = logging.getLogger(__name__)

# GraphQL endpoint IDs (from Twitter's web app)
USER_TWEETS_ENDPOINT = "x3B_xLqC0yZawOB7WQhaVQ/UserTweets"
USER_BY_SCREEN_NAME_ENDPOINT = "qW5u-DAen47o2oBGUOGIeg/UserByScreenName"

HEADERS = {
    "accept": "*/*",
    "accept-language": "en-US,en;q=0.9",
    "authorization": "Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA",
    "content-type": "application/json",
    "priority": "u=1, i",
    "sec-ch-ua": '"Chromium";v="146", "Not-A.Brand";v="24", "Google Chrome";v="146"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36",
    "x-csrf-token": "6c0527719f51d9f1c3ccfaad7ac31d18568c1bb56f63bc1c665359edfddd750bfd877f705d80d02d4828d1128fd7b435c86b6515ae49548f8e4d28606ee668b7024b48215983511a8348e7c94d28f197",
    "x-twitter-active-user": "yes",
    "x-twitter-auth-type": "OAuth2Session",
    "x-twitter-client-language": "en",
}

COOKIES = {
    "auth_token": "7619575179a5309df8700b8e028a9d75c997ff96",
    "ct0": "6c0527719f51d9f1c3ccfaad7ac31d18568c1bb56f63bc1c665359edfddd750bfd877f705d80d02d4828d1128fd7b435c86b6515ae49548f8e4d28606ee668b7024b48215983511a8348e7c94d28f197",
}

FEATURES = '{"rweb_video_screen_enabled":false,"profile_label_improvements_pcf_label_in_post_enabled":true,"responsive_web_profile_redirect_enabled":false,"rweb_tipjar_consumption_enabled":false,"verified_phone_label_enabled":false,"creator_subscriptions_tweet_preview_api_enabled":true,"responsive_web_graphql_timeline_navigation_enabled":true,"responsive_web_graphql_skip_user_profile_image_extensions_enabled":false,"premium_content_api_read_enabled":false,"communities_web_enable_tweet_community_results_fetch":true,"c9s_tweet_anatomy_moderator_badge_enabled":true,"responsive_web_grok_analyze_button_fetch_trends_enabled":false,"responsive_web_grok_analyze_post_followups_enabled":true,"responsive_web_jetfuel_frame":true,"responsive_web_grok_share_attachment_enabled":true,"responsive_web_grok_annotations_enabled":true,"articles_preview_enabled":true,"responsive_web_edit_tweet_api_enabled":true,"graphql_is_translatable_rweb_tweet_is_translatable_enabled":true,"view_counts_everywhere_api_enabled":true,"longform_notetweets_consumption_enabled":true,"responsive_web_twitter_article_tweet_consumption_enabled":true,"content_disclosure_indicator_enabled":true,"content_disclosure_ai_generated_indicator_enabled":true,"responsive_web_grok_show_grok_translated_post":true,"responsive_web_grok_analysis_button_from_backend":true,"post_ctas_fetch_enabled":true,"freedom_of_speech_not_reach_fetch_enabled":true,"standardized_nudges_misinfo":true,"tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled":true,"longform_notetweets_rich_text_read_enabled":true,"longform_notetweets_inline_media_enabled":false,"responsive_web_grok_image_annotation_enabled":true,"responsive_web_grok_imagine_annotation_enabled":true,"responsive_web_grok_community_note_auto_translation_is_enabled":false,"responsive_web_enhance_cards_enabled":false}'

FIELD_TOGGLES = '{"withArticlePlainText":false}'

# Target user ID (sam_allsopp_)
TARGET_USER_ID = "950472202679390208"

# 6 pages x 20 tweets = ~120 tweets
DEFAULT_MAX_PAGES = 6
REQUEST_TIMEOUT = 20


class TwitterScraper:
    """Scrapes Twitter/X using the internal GraphQL API."""

    def __init__(self, username: str, max_pages: int = DEFAULT_MAX_PAGES):
        self.username = username.lstrip("@")
        self.max_pages = max_pages
        self._user_id: str | None = None

    def _get(self, url: str, params: dict | None = None) -> requests.Response:
        """Make a GET request with auth headers and cookies."""
        headers = {**HEADERS, "referer": f"https://x.com/{self.username}"}
        resp = requests.get(url, params=params, headers=headers, cookies=COOKIES, timeout=REQUEST_TIMEOUT)

        if resp.status_code == 429:
            wait = 60
            logger.warning(f"Rate limited. Waiting {wait}s...")
            time.sleep(wait)
            resp = requests.get(url, params=params, headers=headers, cookies=COOKIES, timeout=REQUEST_TIMEOUT)

        if resp.status_code in (401, 403):
            raise PermissionError(
                f"Auth failed (HTTP {resp.status_code}). "
                "Tokens may have expired -- update COOKIES and x-csrf-token in scraper.py."
            )

        resp.raise_for_status()
        return resp

    def _resolve_user_id(self) -> str:
        """Resolve username to numeric user ID."""
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

        params = {"variables": variables, "features": features}
        resp = self._get(f"https://x.com/i/api/graphql/{USER_BY_SCREEN_NAME_ENDPOINT}", params=params)
        data = resp.json()

        user_result = data.get("data", {}).get("user", {}).get("result", {})
        self._user_id = user_result.get("rest_id", "")
        if not self._user_id:
            raise ValueError(f"Could not find user ID for @{self.username}.")
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

        params = {"variables": variables, "features": features}
        resp = self._get(f"https://x.com/i/api/graphql/{USER_BY_SCREEN_NAME_ENDPOINT}", params=params)
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
        self._user_id = user.get("rest_id", "")
        return profile

    def scrape_tweets(self) -> list[Tweet]:
        """Fetch 100+ tweets from the user's timeline with cursor pagination."""
        user_id = self._resolve_user_id()
        all_tweets: list[Tweet] = []
        seen_ids: set[str] = set()
        cursor: str | None = None

        for page in range(self.max_pages):
            logger.info(f"Fetching page {page + 1}/{self.max_pages}...")

            variables = {
                "userId": user_id,
                "count": 20,
                "includePromotedContent": True,
                "withQuickPromoteEligibilityTweetFields": True,
                "withVoice": True,
            }
            if cursor:
                variables["cursor"] = cursor

            params = {
                "variables": json.dumps(variables),
                "features": FEATURES,
                "fieldToggles": FIELD_TOGGLES,
            }

            resp = self._get(f"https://x.com/i/api/graphql/{USER_TWEETS_ENDPOINT}", params=params)
            data = resp.json()

            tweets, next_cursor = self._parse_timeline_response(data)

            # Deduplicate
            new_tweets = []
            for t in tweets:
                if t.id and t.id not in seen_ids:
                    seen_ids.add(t.id)
                    new_tweets.append(t)

            if not new_tweets:
                logger.info("No new tweets found, stopping.")
                break

            all_tweets.extend(new_tweets)
            logger.info(f"  Got {len(new_tweets)} tweets (total: {len(all_tweets)})")

            if not next_cursor:
                logger.info("No next cursor, reached end of timeline.")
                break
            cursor = next_cursor

            # Polite delay
            time.sleep(random.uniform(1.5, 3.0))

        logger.info(f"Scraped {len(all_tweets)} tweets total.")
        return all_tweets

    def _parse_timeline_response(self, data: dict) -> tuple[list[Tweet], str | None]:
        """Parse GraphQL timeline response into Tweet objects."""
        tweets: list[Tweet] = []
        next_cursor: str | None = None

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
                entries.extend(instruction.get("entries", []))
            elif instruction.get("type") == "TimelineAddToModule":
                entries.extend(instruction.get("moduleItems", []))

        for entry in entries:
            entry_id = entry.get("entryId", "")

            # Pagination cursors
            if "cursor-bottom" in entry_id:
                next_cursor = entry.get("content", {}).get("value", "")
                continue
            if "cursor-top" in entry_id:
                continue

            # Single tweet
            if entry_id.startswith("tweet-"):
                tweet = self._extract_tweet_from_entry(entry)
                if tweet:
                    tweets.append(tweet)

            # Conversation thread
            elif entry_id.startswith("profile-conversation"):
                items = entry.get("content", {}).get("items", [])
                for item in items:
                    tweet = self._extract_tweet_from_item(item)
                    if tweet:
                        tweets.append(tweet)

        return tweets, next_cursor

    def _extract_tweet_from_entry(self, entry: dict) -> Tweet | None:
        item_content = entry.get("content", {}).get("itemContent", {})
        if item_content:
            return self._parse_tweet_result(item_content)
        return None

    def _extract_tweet_from_item(self, item: dict) -> Tweet | None:
        item_content = item.get("item", {}).get("itemContent", {})
        return self._parse_tweet_result(item_content)

    def _parse_tweet_result(self, item_content: dict) -> Tweet | None:
        """Parse a tweet from the GraphQL tweet_results structure."""
        result = item_content.get("tweet_results", {}).get("result", {})

        if result.get("__typename") == "TweetWithVisibilityResults":
            result = result.get("tweet", {})
        if not result or result.get("__typename") == "TweetTombstone":
            return None

        legacy = result.get("legacy", {})
        if not legacy:
            return None

        text = legacy.get("full_text", "")
        if not text:
            return None

        # Timestamp
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

        tweet_id = legacy.get("id_str", result.get("rest_id", ""))
        is_retweet = text.startswith("RT @") or "retweeted_status_result" in legacy
        is_reply = bool(legacy.get("in_reply_to_status_id_str"))

        # Media
        media_type = None
        media_entities = legacy.get("extended_entities", {}).get("media", [])
        if not media_entities:
            media_entities = legacy.get("entities", {}).get("media", [])
        if media_entities:
            mtype = media_entities[0].get("type", "")
            media_type = {"photo": "image", "video": "video", "animated_gif": "gif"}.get(mtype)

        # Entities
        entities = legacy.get("entities", {})
        hashtags = [h.get("text", "") for h in entities.get("hashtags", [])]
        mentions = [m.get("screen_name", "") for m in entities.get("user_mentions", [])]
        urls = [u.get("expanded_url", "") for u in entities.get("urls", []) if u.get("expanded_url")]

        # Expand t.co URLs in text
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
