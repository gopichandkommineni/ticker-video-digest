"""Abstract base and normalized data models for tweet source adapters."""

from __future__ import annotations

import datetime
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# Per-row cap on the serialized provider payload stored in raw_tweets.raw_json
# (spec §3.8). Prevents one pathological tweet from bloating the table.
MAX_RAW_JSON_BYTES = 50 * 1024


# ---------------------------------------------------------------------------
# Provider error hierarchy (PR A).
#
# All provider-side failures subclass ProviderError, which subclasses
# RuntimeError so any pre-existing `except RuntimeError` keeps catching them
# (Python MRO). The Transient/Permanent split is what the worker pool dispatches
# on: transient → failed + backoff + retry; permanent → failed, no retry.
#
#   429              -> RateLimitExhausted      (transient)
#   network/timeout  -> NetworkErrorExhausted   (transient)
#   5xx              -> ServerError(status)      (transient)
#   401/403          -> AuthError               (permanent)
#   404              -> NotFoundError           (permanent)
#   other 4xx        -> PermanentProviderError  (permanent)
# ---------------------------------------------------------------------------

class ProviderError(RuntimeError):
    """Base for all provider-related errors."""


class TransientProviderError(ProviderError):
    """Provider error that should retry with backoff."""


class PermanentProviderError(ProviderError):
    """Provider error that should NOT retry."""


class RateLimitExhausted(TransientProviderError):
    """HTTP 429 — rate limit hit, retries exhausted."""


class NetworkErrorExhausted(TransientProviderError):
    """Network/connection/timeout — retries exhausted."""


class ServerError(TransientProviderError):
    """HTTP 5xx — upstream is unhealthy."""

    def __init__(self, status_code: int, message: str = "") -> None:
        self.status_code = status_code
        super().__init__(message or f"HTTP {status_code}")


class AuthError(PermanentProviderError):
    """HTTP 401/403 — authentication or authorization failure."""


class NotFoundError(PermanentProviderError):
    """HTTP 404 — resource not found."""



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
    # Serialized (json.dumps) per-tweet provider payload, size-capped, for
    # persistence to raw_tweets.raw_json (spec §3.8). None if not captured.
    raw_provider_json: str | None = None


def serialize_raw_json(tweet_id: str, raw: dict[str, Any]) -> str:
    """Serialize a per-tweet provider payload, capped at MAX_RAW_JSON_BYTES.

    If the JSON exceeds the cap it is truncated and a warning is logged. Used by
    both adapters to populate Tweet.raw_provider_json for persistence.
    """
    raw_json_str = json.dumps(raw)
    if len(raw_json_str) > MAX_RAW_JSON_BYTES:
        logger.warning(
            "raw_json for tweet %s truncated from %d to %d bytes",
            tweet_id, len(raw_json_str), MAX_RAW_JSON_BYTES,
        )
        raw_json_str = raw_json_str[:MAX_RAW_JSON_BYTES]
    return raw_json_str


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


@dataclass
class FetchResult:
    tweets: list[Tweet]
    reached_floor: bool   # True = stopped naturally; False = cap forced exit before start date
    skipped: int = 0      # count of tweets dropped due to normalization errors


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
    ) -> FetchResult:
        """
        Fetch tweets for *handle* in the inclusive window [start, end].

        Pure: does NOT know about watermarks or "today". The caller computes
        the range. Excludes pure retweets (-filter:retweets server-side).
        Paginates to exhaustion (stop on empty batch or oldest tweet < start).
        reached_floor=True when stop was natural; False when the page cap fired
        before the start boundary was crossed.
        Max-pages valve: 1000 (anti-infinite-loop guard only).
        """
