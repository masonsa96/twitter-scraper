"""Shared utility functions."""

import re
from datetime import datetime, timedelta, timezone


def parse_engagement_number(text: str) -> int:
    """Convert '1.2K', '5M', '340' etc. to an integer."""
    text = text.strip().replace(",", "")
    if not text:
        return 0
    multipliers = {"K": 1_000, "M": 1_000_000, "B": 1_000_000_000}
    upper = text.upper()
    for suffix, mult in multipliers.items():
        if upper.endswith(suffix):
            try:
                return int(float(upper[:-1]) * mult)
            except ValueError:
                return 0
    try:
        return int(text)
    except ValueError:
        return 0


def parse_nitter_datetime(text: str) -> datetime | None:
    """Parse Nitter's datetime from the title attribute.

    Common formats:
      'Mar 15, 2026 · 2:30 PM UTC'
      'Jan 3, 2026 · 10:05 AM UTC'
    """
    if not text:
        return None
    # Remove the center dot separator
    text = text.replace("·", "").strip()
    text = re.sub(r"\s+", " ", text)
    # Remove trailing timezone name for parsing, assume UTC
    text = re.sub(r"\s*(UTC|GMT)\s*$", "", text).strip()
    for fmt in (
        "%b %d, %Y %I:%M %p",
        "%b %d, %Y %H:%M",
        "%d %b %Y %I:%M %p",
        "%d %b %Y %H:%M",
        "%Y-%m-%d %H:%M:%S",
    ):
        try:
            dt = datetime.strptime(text, fmt)
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def parse_relative_time(text: str) -> datetime | None:
    """Convert '2h ago', '3d ago', '15m ago' to a datetime."""
    now = datetime.now(timezone.utc)
    m = re.match(r"(\d+)\s*([smhdwMy])", text)
    if not m:
        return None
    val = int(m.group(1))
    unit = m.group(2)
    deltas = {
        "s": timedelta(seconds=val),
        "m": timedelta(minutes=val),
        "h": timedelta(hours=val),
        "d": timedelta(days=val),
        "w": timedelta(weeks=val),
        "M": timedelta(days=val * 30),
        "y": timedelta(days=val * 365),
    }
    delta = deltas.get(unit)
    if delta:
        return now - delta
    return None


STOPWORDS = {
    "the", "be", "to", "of", "and", "a", "in", "that", "have", "i",
    "it", "for", "not", "on", "with", "he", "as", "you", "do", "at",
    "this", "but", "his", "by", "from", "they", "we", "say", "her",
    "she", "or", "an", "will", "my", "one", "all", "would", "there",
    "their", "what", "so", "up", "out", "if", "about", "who", "get",
    "which", "go", "me", "when", "make", "can", "like", "time", "no",
    "just", "him", "know", "take", "people", "into", "year", "your",
    "good", "some", "could", "them", "see", "other", "than", "then",
    "now", "look", "only", "come", "its", "over", "think", "also",
    "back", "after", "use", "two", "how", "our", "work", "first",
    "well", "way", "even", "new", "want", "because", "any", "these",
    "give", "day", "most", "us", "is", "are", "was", "were", "been",
    "has", "had", "did", "does", "am", "being", "more", "very", "much",
    "too", "really", "still", "own", "here", "should", "where", "why",
    "don", "t", "s", "re", "ve", "ll", "m", "d", "rt", "via", "amp",
    "https", "http", "co", "www", "com",
}
