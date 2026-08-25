"""Pick which videos a digest run should read.

Two input shapes, one output shape:

- **ticker input** — the user names a stock and we go looking. YouTube search
  returns whatever it returns, so this path leans on
  :mod:`ticker_digest.quality` to drop junk and rank what is left by
  reliability metrics (channel size, views, engagement, depth, recency).
- **channel input** — the user already trusts a commentator and names the
  channel. We resolve the name/handle/URL to a channel, list its recent
  uploads (optionally narrowed to the ticker), and rank those.

Either way the caller gets ``list[ScoredVideo]``, most trustworthy first — the
*whole* ranked list, not a shortlist. How many a run can afford to analyse is
the pipeline's decision, and it needs the rest of the list to fall back on when
a video turns out to have no captions.
"""
from __future__ import annotations

import logging

from core.models import ChannelInfo, DigestRequest, ScoredVideo
from ticker_digest.quality import score_videos
from ticker_digest.youtube_client import (
    list_channel_videos,
    resolve_channel,
    search_recent_videos,
)

log = logging.getLogger(__name__)


class SourceResolutionError(RuntimeError):
    """Raised when the requested source cannot be turned into videos."""


def resolve_subject(query: str) -> str | None:
    """Turn what the user typed into a ticker, or None if it isn't a stock.

    "RKLB" is already one. "Planet Labs" is not, and resolving it beats making
    someone go and look up that Planet Labs trades as PL.
    """
    query = query.strip()
    if not query:
        return None
    try:
        from core.social_media.reddit.ticker_resolver import resolve_ticker

        return resolve_ticker(query)
    except Exception as exc:  # noqa: BLE001 — a lookup failure is not a crash
        log.debug("Ticker resolution failed for %r: %s", query, exc)
        # A bare symbol still works without the network; a name does not.
        return query.upper() if " " not in query else None


def resolve_company_name(ticker: str) -> str:
    """Best-effort company name for *ticker*, falling back to the symbol.

    Used to widen the YouTube query — commentators say "Rocket Lab" far more
    often than they say "RKLB".
    """
    try:
        from core.social_media.reddit.ticker_resolver import company_name_for

        name = company_name_for(ticker)
    except Exception as exc:  # noqa: BLE001 — name lookup is a nicety, not a gate
        log.debug("Company-name lookup failed for %s: %s", ticker, exc)
        return ticker.upper()
    return name or ticker.upper()


def select_videos(
    request: DigestRequest,
) -> tuple[list[ScoredVideo], ChannelInfo | None]:
    """Resolve *request* into a ranked shortlist and the channel, if any."""
    if request.source_kind == "channel":
        return _from_channel(request)
    return _from_ticker_search(request), None


def _from_ticker_search(request: DigestRequest) -> list[ScoredVideo]:
    videos = search_recent_videos(
        ticker=request.ticker,
        company_name=request.company_name,
        days=request.days,
    )
    if not videos:
        log.info("Search for %s returned no usable videos", request.ticker)
        return []
    ranked = score_videos(videos)
    log.info(
        "Search for %s: %d usable videos, ranked by reliability",
        request.ticker,
        len(ranked),
    )
    return ranked


def _from_channel(request: DigestRequest) -> tuple[list[ScoredVideo], ChannelInfo]:
    if not request.channel_query:
        raise SourceResolutionError("source_kind is 'channel' but no channel was given")

    channel = resolve_channel(request.channel_query)
    if channel is None:
        raise SourceResolutionError(
            f"No YouTube channel matched {request.channel_query!r}"
        )
    log.info(
        "Resolved %r to %s (%s, %d subscribers)",
        request.channel_query,
        channel.title,
        channel.channel_id,
        channel.subscriber_count,
    )

    # Ask the channel for the ticker specifically. A channel the user trusts
    # usually covers more than one name, and a digest about RKLB shouldn't
    # ingest their Bitcoin video.
    query = f"{request.ticker} OR {request.company_name}"
    videos = list_channel_videos(
        channel_id=channel.channel_id,
        days=request.days,
        query=query,
        ticker=request.ticker,
        company_name=request.company_name,
    )
    if not videos:
        log.info(
            "%s published nothing about %s in the last %d days",
            channel.title,
            request.ticker,
            request.days,
        )
        return [], channel

    return score_videos(videos), channel
