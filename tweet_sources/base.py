"""Abstract base and normalized data models for tweet source adapters."""

from __future__ import annotations

import datetime
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class UserInfo:
    handle: str
    display_name: str | None
    user_id: str
    created_at_utc: str | None      # ISO 8601 UTC; parsed directly from provider's ISO string
    followers_count: int | None
    following_count: int | None
    bio: str | None
    is_verified: bool               # legacy/notable verified
    is_blue_verified: bool          # paid X Blue — NEVER OR'd with is_verified


@dataclass
class Tweet:
    id: str
    created_at_utc: str             # Snowflake-decoded UTC ISO string
    text: str | None
    type: str                       # original | quote | reply | retweet (computed)
    is_reply: bool
    is_quote: bool
    in_reply_to_id: str | None
    quoted_tweet_id: str | None
    quoted_author_id: str | None
    conversation_id: str | None
    like_count: int | None
    retweet_count: int | None
    reply_count: int | None
    quote_count: int | None
    view_count: int | None
    bookmark_count: int | None
    has_media: bool
    media_urls: list[str]
    url: str | None
    is_deleted: bool = False        # always False at adapter layer
    raw_json: dict[str, Any] = field(default_factory=dict)


def snowflake_to_utc(tweet_id: str) -> str:
    """Decode a Twitter Snowflake ID to a UTC ISO 8601 string.

    Formula: ((int(id) >> 22) + 1288834974657) gives milliseconds since epoch.
    We do NOT trust the provider's displayed createdAt string (may be PDT or mangled).
    """
    ms = (int(tweet_id) >> 22) + 1288834974657
    dt = datetime.datetime.utcfromtimestamp(ms / 1000.0)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def compute_type(raw: dict[str, Any]) -> tuple[str, bool, bool]:
    """Return (type, is_reply, is_quote) computed from raw tweet fields."""
    is_reply: bool = bool(raw.get("isReply"))
    retweeted = raw.get("retweeted_tweet")
    quoted = raw.get("quoted_tweet")
    is_quote: bool = quoted is not None

    if retweeted is not None:
        tweet_type = "retweet"
    elif quoted is not None:
        tweet_type = "quote"
    elif is_reply:
        tweet_type = "reply"
    else:
        tweet_type = "original"

    return tweet_type, is_reply, is_quote


class TweetSource(ABC):
    """Abstract adapter interface. Implementations must be stateless per-call."""

    @abstractmethod
    def fetch_user_info(self, handle: str) -> UserInfo:
        """Fetch normalized profile info for *handle*. Single call, no pagination."""

    @abstractmethod
    def fetch_tweets(
        self,
        handle: str,
        start: datetime.date,
        end: datetime.date,
    ) -> list[Tweet]:
        """
        Fetch tweets for *handle* in the inclusive window [start, end].

        Pure: does NOT know about watermarks or "today". The caller computes
        the range. Excludes pure retweets (-filter:retweets server-side).
        Paginates to exhaustion (stop on empty batch or oldest tweet < start).
        Max-pages valve: 100.
        """
