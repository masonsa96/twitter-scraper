"""Nitter-based Twitter/X feed scraper."""

import re
import time
import random
import logging
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from config import NITTER_INSTANCES, REQUEST_HEADERS, REQUEST_TIMEOUT, MAX_PAGES
from models import Tweet, UserProfile
from utils import parse_engagement_number, parse_nitter_datetime, parse_relative_time

logger = logging.getLogger(__name__)


class NitterScraper:
    """Scrapes a Twitter/X user's feed via public Nitter instances."""

    def __init__(self, username: str, instance: str | None = None, max_pages: int = MAX_PAGES):
        self.username = username.lstrip("@")
        self.max_pages = max_pages
        self._user_instance = instance
        self._working_instance: str | None = None

    @property
    def base_url(self) -> str:
        if not self._working_instance:
            self._working_instance = self._find_working_instance()
        return self._working_instance

    def _find_working_instance(self) -> str:
        """Find a responding Nitter instance."""
        candidates = []
        if self._user_instance:
            candidates.append(self._user_instance.rstrip("/"))
        candidates.extend(url.rstrip("/") for url in NITTER_INSTANCES)

        for url in candidates:
            try:
                logger.info(f"Trying Nitter instance: {url}")
                resp = requests.get(
                    f"{url}/{self.username}",
                    headers=REQUEST_HEADERS,
                    timeout=REQUEST_TIMEOUT,
                    allow_redirects=True,
                )
                if resp.status_code == 200 and ("timeline" in resp.text.lower() or "tweet" in resp.text.lower()):
                    logger.info(f"Using instance: {url}")
                    return url
                logger.warning(f"Instance {url} returned status {resp.status_code}")
            except requests.RequestException as e:
                logger.warning(f"Instance {url} failed: {e}")
        raise ConnectionError(
            "No working Nitter instance found. All instances may be down.\n"
            "Try providing a specific instance with --instance <url>.\n"
            "You can find active instances at: https://github.com/zedeus/nitter/wiki/Instances"
        )

    def _fetch_page(self, url: str) -> BeautifulSoup | None:
        """Fetch a page and return parsed soup."""
        try:
            resp = requests.get(url, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT)
            if resp.status_code == 200:
                return BeautifulSoup(resp.text, "lxml")
            logger.warning(f"Got status {resp.status_code} for {url}")
        except requests.RequestException as e:
            logger.warning(f"Request failed for {url}: {e}")
        return None

    def scrape_profile(self) -> UserProfile:
        """Scrape the user's profile information."""
        url = f"{self.base_url}/{self.username}"
        soup = self._fetch_page(url)
        if not soup:
            return UserProfile(username=self.username)

        profile = UserProfile(username=self.username)

        # Display name
        el = soup.select_one(".profile-card-fullname")
        if el:
            profile.display_name = el.get_text(strip=True)

        # Bio
        el = soup.select_one(".profile-bio")
        if el:
            profile.bio = el.get_text(strip=True)

        # Stats: tweets, following, followers, likes
        stat_nums = soup.select(".profile-stat-num")
        stat_labels = soup.select(".profile-stat-header")
        for num_el, label_el in zip(stat_nums, stat_labels):
            label = label_el.get_text(strip=True).lower()
            value = parse_engagement_number(num_el.get_text(strip=True))
            if "tweet" in label or "post" in label:
                profile.tweet_count = value
            elif "following" in label:
                profile.following = value
            elif "follower" in label:
                profile.followers = value

        # Join date
        el = soup.select_one(".profile-joindate span")
        if el:
            profile.joined = el.get_text(strip=True)

        # Verified badge
        profile.verified = bool(soup.select_one(".verified-icon"))

        return profile

    def scrape_tweets(self) -> list[Tweet]:
        """Scrape tweets from the user's timeline."""
        all_tweets: list[Tweet] = []
        url = f"{self.base_url}/{self.username}"

        for page in range(self.max_pages):
            logger.info(f"Scraping page {page + 1}/{self.max_pages} ...")
            soup = self._fetch_page(url)
            if not soup:
                break

            tweets = self._parse_tweets_from_soup(soup)
            if not tweets:
                logger.info("No tweets found on page, stopping.")
                break
            all_tweets.extend(tweets)

            # Get next page cursor
            next_url = self._get_next_page_url(soup)
            if not next_url:
                logger.info("No more pages.")
                break
            url = urljoin(self.base_url, next_url)

            # Polite delay between pages
            time.sleep(random.uniform(1.0, 3.0))

        logger.info(f"Scraped {len(all_tweets)} tweets total.")
        return all_tweets

    def _parse_tweets_from_soup(self, soup: BeautifulSoup) -> list[Tweet]:
        """Parse tweet elements from a page."""
        tweets = []
        # Nitter uses .timeline-item for each tweet container
        items = soup.select(".timeline-item")
        if not items:
            # Fallback selector
            items = soup.select(".tweet-item, .thread-line")

        for item in items:
            tweet = self._parse_single_tweet(item)
            if tweet:
                tweets.append(tweet)
        return tweets

    def _parse_single_tweet(self, item) -> Tweet | None:
        """Parse a single tweet element."""
        # Tweet text
        text_el = item.select_one(".tweet-content, .tweet-body")
        if not text_el:
            return None
        text = text_el.get_text(strip=True)

        # Tweet ID from permalink
        tweet_id = ""
        link_el = item.select_one(".tweet-link, a.tweet-date")
        if link_el:
            href = link_el.get("href", "")
            # Extract ID from path like /user/status/123456
            id_match = re.search(r"/status/(\d+)", href)
            if id_match:
                tweet_id = id_match.group(1)

        # Timestamp
        timestamp = None
        date_el = item.select_one(".tweet-date a")
        if date_el:
            # Prefer title attribute for absolute time
            title = date_el.get("title", "")
            if title:
                timestamp = parse_nitter_datetime(title)
            if not timestamp:
                timestamp = parse_relative_time(date_el.get_text(strip=True))

        # Engagement stats
        stats = {"replies": 0, "retweets": 0, "likes": 0, "quotes": 0}
        stat_map = {
            "comment": "replies",
            "retweet": "retweets",
            "heart": "likes",
            "quote": "quotes",
        }
        for icon_key, stat_name in stat_map.items():
            el = item.select_one(f".icon-{icon_key}")
            if el and el.parent:
                num_text = el.parent.get_text(strip=True)
                stats[stat_name] = parse_engagement_number(num_text)

        # Also try the tweet-stat elements
        for stat_el in item.select(".tweet-stat"):
            icon = stat_el.select_one("[class*='icon-']")
            if icon:
                classes = " ".join(icon.get("class", []))
                for icon_key, stat_name in stat_map.items():
                    if icon_key in classes:
                        num_text = stat_el.get_text(strip=True)
                        stats[stat_name] = parse_engagement_number(num_text)

        # Flags
        is_retweet = bool(item.select_one(".retweet-header"))
        is_reply = bool(item.select_one(".replying-to"))

        # Media type
        media_type = None
        if item.select_one(".gallery-row, .attachment.image"):
            media_type = "image"
        elif item.select_one(".gallery-gif"):
            media_type = "gif"
        elif item.select_one(".video-container, .attachment.video"):
            media_type = "video"

        # Extract hashtags, mentions, and URLs from text
        hashtags = re.findall(r"#(\w+)", text)
        mentions = re.findall(r"@(\w+)", text)
        urls = [a.get("href", "") for a in (text_el.select("a") if text_el else []) if "http" in a.get("href", "")]

        return Tweet(
            id=tweet_id,
            text=text,
            timestamp=timestamp,
            replies=stats["replies"],
            retweets=stats["retweets"],
            likes=stats["likes"],
            quotes=stats["quotes"],
            hashtags=hashtags,
            mentions=mentions,
            urls=urls,
            is_retweet=is_retweet,
            is_reply=is_reply,
            media_type=media_type,
        )

    def _get_next_page_url(self, soup: BeautifulSoup) -> str | None:
        """Extract the next-page URL from a 'Show more' or 'Load more' link."""
        for selector in (".show-more a", ".timeline-footer a", "a[href*='cursor']"):
            el = soup.select_one(selector)
            if el and el.get("href"):
                return el["href"]
        return None
