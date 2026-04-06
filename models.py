"""Data models for tweets and user profiles."""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional


@dataclass
class Tweet:
    id: str
    text: str
    timestamp: Optional[datetime]
    replies: int = 0
    retweets: int = 0
    likes: int = 0
    quotes: int = 0
    hashtags: list[str] = field(default_factory=list)
    mentions: list[str] = field(default_factory=list)
    urls: list[str] = field(default_factory=list)
    is_retweet: bool = False
    is_reply: bool = False
    media_type: Optional[str] = None  # "image", "video", "gif", or None

    def to_dict(self) -> dict:
        d = asdict(self)
        if self.timestamp:
            d["timestamp"] = self.timestamp.isoformat()
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "Tweet":
        if d.get("timestamp"):
            d["timestamp"] = datetime.fromisoformat(d["timestamp"])
        return cls(**d)

    @property
    def total_engagement(self) -> int:
        return self.likes + self.retweets + self.replies + self.quotes


@dataclass
class UserProfile:
    username: str
    display_name: str = ""
    bio: str = ""
    followers: int = 0
    following: int = 0
    tweet_count: int = 0
    joined: str = ""
    verified: bool = False

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "UserProfile":
        return cls(**d)
