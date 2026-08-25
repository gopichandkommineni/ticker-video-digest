"""Deterministic source quality: which videos are worth transcribing, and in
what order.

Nothing here talks to the network or to an LLM. Given a ``VideoMetadata`` it
answers two questions:

- ``passes_quality_filters`` — should we spend a transcript + LLM call on this
  video at all? (duration, channel size, engagement-bait titles)
- ``reliability_score`` — how much should we trust it relative to the others?

Keeping this pure is deliberate: the ranking that decides what the user reads
should be inspectable and unit-testable without an API key.
"""
from __future__ import annotations

import logging
import math
import re
from datetime import datetime, timezone

from core.config import (
    MIN_SUBSCRIBER_COUNT,
    MIN_VIDEO_DURATION_SECONDS,
    RELIABILITY_DEPTH_SATURATION_SECONDS,
    RELIABILITY_SUBSCRIBER_SATURATION,
    RELIABILITY_VIEW_SATURATION,
    RELIABILITY_WEIGHTS,
    SPAM_TITLE_CAPS_RATIO,
    SPAM_TITLE_EMOJI,
    SPAM_TITLE_MAX_EMOJI,
)
from core.models import ScoredVideo, VideoMetadata

log = logging.getLogger(__name__)

# Words worth judging for ALL-CAPS: three or more letters, so "AI", "EV" and
# "CEO" don't drag an otherwise normal title over the threshold.
_WORD_RE = re.compile(r"[A-Za-z]{3,}")

# Views-per-subscriber at which the engagement component saturates. A video
# seen by half the channel's subscriber base travelled well beyond the regulars.
_ENGAGEMENT_SATURATION = 0.5


def spam_emoji_count(title: str) -> int:
    """Number of hype emoji (🚀🔥💎…) in *title*, counting repeats."""
    return sum(title.count(emoji) for emoji in SPAM_TITLE_EMOJI)


def is_all_caps_title(title: str, ticker: str | None = None) -> bool:
    """True when most of the title is shouted.

    The ticker itself is excluded — "RKLB stock update" is a normal title, and
    every ticker is upper-case by definition. Titles with fewer than three
    judgeable words are never flagged; there isn't enough signal.
    """
    words = _WORD_RE.findall(title)
    if ticker:
        symbol = ticker.strip().upper()
        words = [w for w in words if w.upper() != symbol]
    if len(words) < 3:
        return False
    shouted = sum(1 for w in words if w.isupper())
    return shouted / len(words) >= SPAM_TITLE_CAPS_RATIO


def is_spam_title(title: str, ticker: str | None = None) -> bool:
    """True when the title reads as engagement bait rather than analysis."""
    return (
        is_all_caps_title(title, ticker)
        or spam_emoji_count(title) > SPAM_TITLE_MAX_EMOJI
    )


def passes_quality_filters(
    metadata: VideoMetadata, ticker: str | None = None
) -> tuple[bool, str]:
    """Return ``(ok, reason)``. *reason* is empty when the video passes.

    The reason string is kept so the caller can report *why* a video was
    dropped rather than silently returning a shorter list.
    """
    if metadata.duration_seconds < MIN_VIDEO_DURATION_SECONDS:
        return False, (
            f"too short ({metadata.duration_seconds}s < {MIN_VIDEO_DURATION_SECONDS}s)"
        )
    if metadata.channel_subscriber_count < MIN_SUBSCRIBER_COUNT:
        return False, (
            f"channel too small ({metadata.channel_subscriber_count} subs "
            f"< {MIN_SUBSCRIBER_COUNT})"
        )
    if is_spam_title(metadata.title, ticker):
        return False, "title looks like engagement bait"
    return True, ""


def _log_share(value: float, saturation: float) -> float:
    """Log-scaled 0..1 position of *value* on the way to *saturation*.

    Log-scaled because the difference between 1k and 10k subscribers matters
    far more than the difference between 400k and 410k.
    """
    if value <= 0:
        return 0.0
    share = math.log10(1.0 + value) / math.log10(1.0 + saturation)
    return max(0.0, min(1.0, share))


def reliability_score(
    metadata: VideoMetadata, now: datetime | None = None
) -> tuple[float, dict[str, float]]:
    """Score a video 0..1 on how much weight its claims deserve.

    Returns the weighted total plus the individual components, so the CLI can
    show why one video outranked another.
    """
    now = now or datetime.now(timezone.utc)

    subscribers = _log_share(
        metadata.channel_subscriber_count, RELIABILITY_SUBSCRIBER_SATURATION
    )
    views = _log_share(metadata.view_count, RELIABILITY_VIEW_SATURATION)

    subs = max(metadata.channel_subscriber_count, 1)
    engagement = min(1.0, (metadata.view_count / subs) / _ENGAGEMENT_SATURATION)

    depth = min(
        1.0, metadata.duration_seconds / RELIABILITY_DEPTH_SATURATION_SECONDS
    )

    published = metadata.published_at
    if published.tzinfo is None:
        published = published.replace(tzinfo=timezone.utc)
    age_days = max(0.0, (now - published).total_seconds() / 86400.0)
    # Half-weight at one week old, and never quite zero — an older video with
    # a genuinely new claim should still be able to place.
    recency = 1.0 / (1.0 + age_days / 7.0)

    components = {
        "subscribers": subscribers,
        "views": views,
        "engagement": engagement,
        "depth": depth,
        "recency": recency,
    }
    total = sum(RELIABILITY_WEIGHTS[name] * value for name, value in components.items())
    return round(total, 4), {k: round(v, 4) for k, v in components.items()}


def score_videos(
    videos: list[VideoMetadata], now: datetime | None = None
) -> list[ScoredVideo]:
    """Score every video and return them most-reliable first."""
    now = now or datetime.now(timezone.utc)
    scored = []
    for metadata in videos:
        total, components = reliability_score(metadata, now=now)
        scored.append(
            ScoredVideo(
                metadata=metadata,
                reliability_score=total,
                score_components=components,
            )
        )
    scored.sort(key=lambda sv: sv.reliability_score, reverse=True)
    return scored
