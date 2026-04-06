"""Business insight analysis for scraped tweets."""

import re
from collections import Counter
from datetime import datetime, timezone
from statistics import mean, median

from textblob import TextBlob

from models import Tweet
from utils import STOPWORDS

DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


class TweetAnalyzer:
    """Analyze tweets for actionable business insights."""

    def __init__(self, tweets: list[Tweet], username: str):
        self.tweets = tweets
        self.username = username
        # Only use tweets with timestamps for time-based analysis
        self.timed_tweets = [t for t in tweets if t.timestamp]

    def posting_frequency(self) -> dict:
        """Analyze how often the user posts."""
        if not self.timed_tweets:
            return {"total_tweets": len(self.tweets), "note": "No timestamp data available"}

        sorted_tweets = sorted(self.timed_tweets, key=lambda t: t.timestamp)
        first = sorted_tweets[0].timestamp
        last = sorted_tweets[-1].timestamp
        span_days = max((last - first).days, 1)

        # Tweets per day-of-week
        dow_counts = Counter(t.timestamp.strftime("%A") for t in self.timed_tweets)

        # Tweets per hour
        hour_counts = Counter(t.timestamp.hour for t in self.timed_tweets)

        return {
            "total_tweets": len(self.tweets),
            "date_range": f"{first.strftime('%Y-%m-%d')} to {last.strftime('%Y-%m-%d')}",
            "span_days": span_days,
            "tweets_per_day": round(len(self.timed_tweets) / span_days, 2),
            "tweets_per_week": round(len(self.timed_tweets) / max(span_days / 7, 1), 2),
            "most_active_days": [d for d, _ in dow_counts.most_common(3)],
            "least_active_days": [d for d, _ in dow_counts.most_common()[-2:]],
            "peak_hours_utc": [h for h, _ in hour_counts.most_common(3)],
            "by_day_of_week": dict(dow_counts.most_common()),
            "by_hour": dict(sorted(hour_counts.items())),
        }

    def engagement_analysis(self) -> dict:
        """Analyze engagement metrics across tweets."""
        if not self.tweets:
            return {}

        likes = [t.likes for t in self.tweets]
        retweets = [t.retweets for t in self.tweets]
        replies = [t.replies for t in self.tweets]
        engagements = [t.total_engagement for t in self.tweets]

        # Top tweets by engagement
        top_tweets = sorted(self.tweets, key=lambda t: t.total_engagement, reverse=True)[:5]

        # Engagement by content type
        with_media = [t for t in self.tweets if t.media_type]
        without_media = [t for t in self.tweets if not t.media_type]
        avg_eng_media = mean([t.total_engagement for t in with_media]) if with_media else 0
        avg_eng_text = mean([t.total_engagement for t in without_media]) if without_media else 0

        return {
            "avg_likes": round(mean(likes), 1),
            "avg_retweets": round(mean(retweets), 1),
            "avg_replies": round(mean(replies), 1),
            "median_engagement": round(median(engagements), 1),
            "max_engagement": max(engagements),
            "total_engagement": sum(engagements),
            "top_tweets": [
                {"text": t.text[:120], "likes": t.likes, "retweets": t.retweets, "total": t.total_engagement}
                for t in top_tweets
            ],
            "avg_engagement_with_media": round(avg_eng_media, 1),
            "avg_engagement_text_only": round(avg_eng_text, 1),
            "media_engagement_lift": (
                f"{round((avg_eng_media / avg_eng_text - 1) * 100)}%"
                if avg_eng_text > 0 and avg_eng_media > 0
                else "N/A"
            ),
        }

    def best_posting_times(self) -> dict:
        """Find the best times to post based on engagement."""
        if not self.timed_tweets:
            return {"note": "No timestamp data available"}

        # Group by hour-of-day
        hour_engagement: dict[int, list[int]] = {}
        for t in self.timed_tweets:
            h = t.timestamp.hour
            hour_engagement.setdefault(h, []).append(t.total_engagement)

        hour_avg = {h: round(mean(engs), 1) for h, engs in hour_engagement.items()}

        # Group by day-of-week
        dow_engagement: dict[str, list[int]] = {}
        for t in self.timed_tweets:
            day = t.timestamp.strftime("%A")
            dow_engagement.setdefault(day, []).append(t.total_engagement)

        dow_avg = {d: round(mean(engs), 1) for d, engs in dow_engagement.items()}

        # Best hour
        best_hour = max(hour_avg, key=hour_avg.get) if hour_avg else None
        best_day = max(dow_avg, key=dow_avg.get) if dow_avg else None

        return {
            "best_hour_utc": best_hour,
            "best_day": best_day,
            "engagement_by_hour": dict(sorted(hour_avg.items())),
            "engagement_by_day": dow_avg,
            "top_3_hours": sorted(hour_avg, key=hour_avg.get, reverse=True)[:3] if hour_avg else [],
            "top_3_days": sorted(dow_avg, key=dow_avg.get, reverse=True)[:3] if dow_avg else [],
        }

    def topic_analysis(self) -> dict:
        """Analyze topics, hashtags, and keywords."""
        # Hashtags
        all_hashtags: list[str] = []
        for t in self.tweets:
            all_hashtags.extend(h.lower() for h in t.hashtags)
        hashtag_freq = Counter(all_hashtags).most_common(20)

        # Mentions
        all_mentions: list[str] = []
        for t in self.tweets:
            all_mentions.extend(m.lower() for m in t.mentions)
        mention_freq = Counter(all_mentions).most_common(20)

        # Keyword extraction (simple word frequency)
        all_words: list[str] = []
        for t in self.tweets:
            if t.is_retweet:
                continue
            words = re.findall(r"[a-zA-Z]{3,}", t.text.lower())
            all_words.extend(w for w in words if w not in STOPWORDS)
        keyword_freq = Counter(all_words).most_common(30)

        return {
            "top_hashtags": hashtag_freq,
            "top_mentions": mention_freq,
            "top_keywords": keyword_freq,
            "unique_hashtags": len(set(all_hashtags)),
            "unique_mentions": len(set(all_mentions)),
        }

    def content_themes(self) -> dict:
        """Categorize content types and themes."""
        total = len(self.tweets)
        if total == 0:
            return {}

        originals = [t for t in self.tweets if not t.is_retweet and not t.is_reply]
        rts = [t for t in self.tweets if t.is_retweet]
        replies = [t for t in self.tweets if t.is_reply]
        with_media = [t for t in self.tweets if t.media_type]
        with_urls = [t for t in self.tweets if t.urls]

        # Average tweet length
        lengths = [len(t.text) for t in self.tweets if t.text]

        return {
            "original_tweets": len(originals),
            "retweets": len(rts),
            "replies": len(replies),
            "pct_original": round(len(originals) / total * 100, 1),
            "pct_retweets": round(len(rts) / total * 100, 1),
            "pct_replies": round(len(replies) / total * 100, 1),
            "pct_with_media": round(len(with_media) / total * 100, 1),
            "pct_with_urls": round(len(with_urls) / total * 100, 1),
            "avg_tweet_length": round(mean(lengths), 1) if lengths else 0,
            "media_breakdown": dict(Counter(t.media_type for t in with_media).most_common()),
        }

    def sentiment_analysis(self) -> dict:
        """Analyze sentiment of tweets using TextBlob."""
        if not self.tweets:
            return {}

        sentiments = []
        for t in self.tweets:
            if t.is_retweet or not t.text:
                continue
            blob = TextBlob(t.text)
            sentiments.append({
                "polarity": blob.sentiment.polarity,
                "subjectivity": blob.sentiment.subjectivity,
                "text": t.text[:100],
            })

        if not sentiments:
            return {"note": "No original tweets to analyze"}

        polarities = [s["polarity"] for s in sentiments]
        positive = sum(1 for p in polarities if p > 0.1)
        negative = sum(1 for p in polarities if p < -0.1)
        neutral = len(polarities) - positive - negative

        sorted_by_pol = sorted(sentiments, key=lambda s: s["polarity"])

        return {
            "avg_polarity": round(mean(polarities), 3),
            "avg_subjectivity": round(mean([s["subjectivity"] for s in sentiments]), 3),
            "positive_count": positive,
            "negative_count": negative,
            "neutral_count": neutral,
            "pct_positive": round(positive / len(sentiments) * 100, 1),
            "pct_negative": round(negative / len(sentiments) * 100, 1),
            "pct_neutral": round(neutral / len(sentiments) * 100, 1),
            "most_positive": sorted_by_pol[-1]["text"] if sorted_by_pol else "",
            "most_negative": sorted_by_pol[0]["text"] if sorted_by_pol else "",
        }

    def generate_insights(self) -> list[str]:
        """Generate actionable business insights from all analyses."""
        insights = []
        freq = self.posting_frequency()
        eng = self.engagement_analysis()
        times = self.best_posting_times()
        topics = self.topic_analysis()
        themes = self.content_themes()
        sentiment = self.sentiment_analysis()

        # Posting frequency insight
        if "tweets_per_day" in freq:
            tpd = freq["tweets_per_day"]
            days = freq.get("most_active_days", [])
            if days:
                insights.append(
                    f"Posts ~{tpd} tweets/day, most active on {', '.join(days[:2])}."
                )

        # Peak times
        if times.get("best_hour_utc") is not None:
            bh = times["best_hour_utc"]
            bd = times.get("best_day", "N/A")
            insights.append(
                f"Peak engagement window: {bh}:00 UTC on {bd}s. "
                "Schedule interactions around this time."
            )

        # Top topics
        top_ht = topics.get("top_hashtags", [])
        if top_ht:
            tags = ", ".join(f"#{h}" for h, _ in top_ht[:5])
            insights.append(f"Key topics: {tags} -- engage on these themes to connect.")

        top_kw = topics.get("top_keywords", [])
        if top_kw:
            words = ", ".join(w for w, _ in top_kw[:5])
            insights.append(f"Most discussed terms: {words}.")

        # Media impact
        if eng.get("avg_engagement_with_media") and eng.get("avg_engagement_text_only"):
            lift = eng.get("media_engagement_lift", "N/A")
            if lift != "N/A":
                insights.append(
                    f"Media posts get {lift} more engagement than text-only. "
                    "Visual content drives interaction."
                )

        # Content mix
        if themes.get("pct_original"):
            insights.append(
                f"Content mix: {themes['pct_original']}% original, "
                f"{themes['pct_retweets']}% retweets, {themes['pct_replies']}% replies."
            )

        # Sentiment
        if sentiment.get("pct_positive"):
            insights.append(
                f"Sentiment: {sentiment['pct_positive']}% positive, "
                f"{sentiment['pct_negative']}% negative, "
                f"{sentiment['pct_neutral']}% neutral."
            )
            if sentiment["pct_positive"] > 60:
                insights.append("Predominantly positive tone -- brand-safe for partnerships.")
            elif sentiment["pct_negative"] > 40:
                insights.append("High negative sentiment -- approach with caution for partnerships.")

        # Top mentions (who they interact with)
        top_mentions = topics.get("top_mentions", [])
        if top_mentions:
            names = ", ".join(f"@{m}" for m, _ in top_mentions[:5])
            insights.append(f"Frequently interacts with: {names}. Potential networking contacts.")

        # Engagement summary
        if eng.get("top_tweets"):
            best = eng["top_tweets"][0]
            insights.append(
                f"Top performing tweet ({best['total']} engagements): \"{best['text'][:80]}...\""
            )

        return insights

    def full_analysis(self) -> dict:
        """Run all analyses and return combined results."""
        return {
            "posting_frequency": self.posting_frequency(),
            "engagement": self.engagement_analysis(),
            "best_posting_times": self.best_posting_times(),
            "topics": self.topic_analysis(),
            "content_themes": self.content_themes(),
            "sentiment": self.sentiment_analysis(),
            "insights": self.generate_insights(),
        }
