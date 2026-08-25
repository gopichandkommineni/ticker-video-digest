"""Deterministic source quality: which videos are worth transcribing, and in
what order.

Nothing here talks to the network or to an LLM. Given a ``VideoMetadata`` it
answers two questions:

- ``passes_quality_filters`` — should we spend a transcript + LLM call on this
  video at all? (duration, channel size, engagement-bait titles, relevance).
  Returns a categorised verdict, because a run that filters everything out has
  to be able to say which rule did it.
- ``reliability_score`` — how much should we trust it relative to the others?

Keeping this pure is deliberate: the ranking that decides what the user reads
should be inspectable and unit-testable without an API key.
"""
from __future__ import annotations

import logging
import math
import re
from datetime import datetime, timezone
from typing import NamedTuple

from core.config import (
    AMBIGUOUS_TICKER_LENGTH,
    COMPANY_NAME_STOPWORDS,
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


def distinctive_company_words(company_name: str) -> set[str]:
    """The words in a company name that actually identify it.

    "Planet Labs PBC" -> {planet, labs}. Corporate furniture and short words are
    dropped: matching on "Inc" or "PBC" would match every other filing entity
    on YouTube.
    """
    words = {
        word.lower().strip(".,")
        for word in company_name.split()
        if len(word.strip(".,")) >= 4
    }
    return {word for word in words if word and word not in COMPANY_NAME_STOPWORDS}


def mentions_subject(
    metadata: VideoMetadata, ticker: str, company_name: str = ""
) -> bool:
    """Does this video look like it is about *ticker* at all?

    Only asked of short tickers, and for a reason worth stating: searching
    YouTube for "PL" returns videos whose titles happen to contain the letters
    p and l. A three-minute family vlog is not commentary on Planet Labs.

    Evidence accepted: a distinctive word from the company name anywhere in the
    title or channel name, or the ticker written as its own upper-case word —
    which is how anyone discussing the stock writes it, and how the incidental
    matches do not.
    """
    symbol = ticker.strip().upper()
    if len(symbol) > AMBIGUOUS_TICKER_LENGTH:
        return True

    haystack = f"{metadata.title} {metadata.channel_title}"
    if re.search(rf"\b{re.escape(symbol)}\b", haystack):
        return True

    words = distinctive_company_words(company_name)
    if not words:
        # Nothing to match on. Better to read a doubtful video than to drop
        # every video for a company whose name is all stopwords.
        return True

    lowered = haystack.lower()
    return any(re.search(rf"\b{re.escape(word)}\b", lowered) for word in words)


class Verdict(NamedTuple):
    """Why a video was kept or dropped.

    *category* aggregates ("too short"); *detail* explains this one video
    ("too short (95s < 120s)"). A run that drops everything needs the first to
    say what happened and the second to prove it.
    """

    ok: bool
    category: str
    detail: str


PASSED = Verdict(True, "", "")


def passes_quality_filters(
    metadata: VideoMetadata, ticker: str | None = None, company_name: str = ""
) -> Verdict:
    """Should we spend a transcript and a model call on this video?"""
    if metadata.duration_seconds < MIN_VIDEO_DURATION_SECONDS:
        return Verdict(
            False,
            "too short",
            f"too short ({metadata.duration_seconds}s < {MIN_VIDEO_DURATION_SECONDS}s)",
        )
    if metadata.channel_subscriber_count < MIN_SUBSCRIBER_COUNT:
        return Verdict(
            False,
            "channel too small",
            f"channel too small ({metadata.channel_subscriber_count} subs "
            f"< {MIN_SUBSCRIBER_COUNT})",
        )
    if is_spam_title(metadata.title, ticker):
        return Verdict(False, "bait title", "title looks like engagement bait")
    if ticker and not mentions_subject(metadata, ticker, company_name):
        symbol = ticker.upper()
        return Verdict(
            False,
            f"no mention of {symbol}",
            f"nothing in the title or channel mentions {symbol}",
        )
    return PASSED


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
