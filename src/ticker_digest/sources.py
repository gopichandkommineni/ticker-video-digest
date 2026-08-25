"""Pick which videos a digest run should read.

Two input shapes, one output shape:

- **ticker input** — the user names a stock and we go looking. YouTube search
  returns whatever it returns, so this path leans on
  :mod:`ticker_digest.quality` to drop junk and rank what is left by
  reliability metrics (channel size, views, engagement, depth, recency).
- **channel input** — the user already trusts a commentator and names the
  channel. We resolve the name/handle/URL to a channel, list its recent
  uploads (optionally narrowed to the ticker), and rank those.

Either way the caller gets ``list[ScoredVideo]``, most trustworthy first.
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
        "Search for %s: %d usable videos, taking the top %d by reliability",
        request.ticker,
        len(ranked),
        min(request.max_videos, len(ranked)),
    )
    return ranked[: request.max_videos]


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
    )
    if not videos:
        log.info(
            "%s published nothing about %s in the last %d days",
            channel.title,
            request.ticker,
            request.days,
        )
        return [], channel

    ranked = score_videos(videos)
    return ranked[: request.max_videos], channel
