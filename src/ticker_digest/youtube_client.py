"""YouTube Data API v3 client.

Two ways in, matching the two ways a user asks for a digest:

- ``search_recent_videos`` — "what is YouTube saying about RKLB?"
- ``resolve_channel`` + ``list_channel_videos`` — "what did *this channel*
  say?", for when the user already trusts a specific commentator.

Both paths return plain ``VideoMetadata`` that has been through the quality
filter in :mod:`ticker_digest.quality`; ranking happens in
:mod:`ticker_digest.sources`.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from core.config import AMBIGUOUS_TICKER_LENGTH, YOUTUBE_API_KEY
from core.models import ChannelInfo, VideoMetadata
from ticker_digest.quality import passes_quality_filters

log = logging.getLogger(__name__)


class YouTubeAccessError(RuntimeError):
    """The YouTube API refused us — bad key, disabled API, or quota gone.

    Raised instead of letting googleapiclient's HttpError reach the user: the
    three ways this fails in practice each have a different fix, and a stack
    trace tells you none of them.
    """


def _execute(request, what: str):
    """Run an API request, turning the predictable refusals into plain English."""
    try:
        return request.execute()
    except HttpError as exc:
        reason = ""
        try:
            reason = exc.error_details[0].get("reason", "")  # type: ignore[index]
        except (AttributeError, IndexError, KeyError, TypeError):
            pass
        status = getattr(exc.resp, "status", None)

        if reason in {"quotaExceeded", "dailyLimitExceeded", "rateLimitExceeded"}:
            raise YouTubeAccessError(
                "YouTube API quota is used up for today. The daily free quota is "
                "10,000 units and one search costs 100. It resets at midnight "
                "Pacific."
            ) from exc
        if status in {400, 403} or reason in {"badRequest", "keyInvalid", "forbidden"}:
            raise YouTubeAccessError(
                f"YouTube API rejected the request ({what}): {exc.reason}.\n"
                "  Check YOUTUBE_API_KEY in .env is a real key, not a placeholder, "
                "and that\n"
                "  'YouTube Data API v3' is enabled for it in the Google Cloud console."
            ) from exc
        raise

# YouTube channel ids are always "UC" + 22 url-safe characters.
_CHANNEL_ID_RE = re.compile(r"^UC[\w-]{22}$")
_CHANNEL_URL_ID_RE = re.compile(r"youtube\.com/channel/(UC[\w-]{22})")
_HANDLE_RE = re.compile(r"@([A-Za-z0-9._-]+)")

# The API accepts at most 50 ids per videos.list / channels.list call.
_MAX_IDS_PER_CALL = 50


def _client():
    return build("youtube", "v3", developerKey=YOUTUBE_API_KEY)


def _parse_iso8601_duration(duration: str) -> int:
    """Convert an ISO 8601 duration string (e.g. PT1H30M15S) to total seconds."""
    match = re.fullmatch(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", duration)
    if not match:
        return 0
    hours, minutes, seconds = (int(g or 0) for g in match.groups())
    return hours * 3600 + minutes * 60 + seconds


def build_search_query(ticker: str, company_name: str = "") -> str:
    """The YouTube query for a ticker, hedged against short symbols.

    A long symbol like RKLB is distinctive enough to search for bare. A short
    one is not: searching "PL" returns anything containing those letters, so it
    only appears paired with "stock", and the company name leads.
    """
    symbol = ticker.strip().upper()
    company = company_name.strip()

    if not company or company.upper() == symbol:
        return f'"{symbol}" stock'
    if len(symbol) <= AMBIGUOUS_TICKER_LENGTH:
        return f'"{company}" stock OR "{symbol} stock"'
    return f'"{symbol}" OR "{company}" stock'


def _chunks(items: list[str], size: int = _MAX_IDS_PER_CALL):
    for start in range(0, len(items), size):
        yield items[start : start + size]


def _published_after(days: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


def _subscriber_counts(youtube, channel_ids: list[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for chunk in _chunks(channel_ids):
        resp = _execute(
            youtube.channels().list(id=",".join(chunk), part="statistics"),
            "channel lookup",
        )
        for channel in resp.get("items", []):
            counts[channel["id"]] = int(
                channel.get("statistics", {}).get("subscriberCount", 0)
            )
    return counts


def _hydrate_videos(youtube, video_ids: list[str]) -> list[VideoMetadata]:
    """Turn bare video ids into full metadata.

    Two batched calls: ``videos.list`` for snippet/duration/views, then one
    ``channels.list`` for the subscriber counts of every channel involved.
    """
    video_items: list[dict] = []
    for chunk in _chunks(video_ids):
        resp = _execute(
            youtube.videos().list(
                id=",".join(chunk), part="snippet,contentDetails,statistics"
            ),
            "video lookup",
        )
        video_items.extend(resp.get("items", []))

    if not video_items:
        return []

    channel_ids = list({item["snippet"]["channelId"] for item in video_items})
    subscriber_map = _subscriber_counts(youtube, channel_ids)

    videos: list[VideoMetadata] = []
    for item in video_items:
        snippet = item["snippet"]
        channel_id = snippet["channelId"]
        videos.append(
            VideoMetadata(
                video_id=item["id"],
                title=snippet["title"],
                channel_id=channel_id,
                channel_title=snippet["channelTitle"],
                channel_subscriber_count=subscriber_map.get(channel_id, 0),
                published_at=datetime.fromisoformat(
                    snippet["publishedAt"].replace("Z", "+00:00")
                ),
                duration_seconds=_parse_iso8601_duration(
                    item["contentDetails"]["duration"]
                ),
                view_count=int(item.get("statistics", {}).get("viewCount", 0)),
            )
        )
    return videos


def _apply_quality_filter(
    videos: list[VideoMetadata], ticker: str | None, company_name: str = ""
) -> list[VideoMetadata]:
    kept: list[VideoMetadata] = []
    for video in videos:
        ok, reason = passes_quality_filters(video, ticker, company_name)
        if ok:
            kept.append(video)
        else:
            log.debug("Skipping %s (%s): %s", video.video_id, video.title, reason)
    return kept


def search_recent_videos(
    ticker: str,
    company_name: str,
    days: int = 7,
    max_results: int = 50,
) -> list[VideoMetadata]:
    """Return quality-filtered videos about *ticker* published in the last *days*.

    Results are sorted by view count descending. Reliability ranking is a
    separate step — see :func:`ticker_digest.sources.select_videos`.
    """
    youtube = _client()

    published_after = _published_after(days)
    query = build_search_query(ticker, company_name)
    log.info("YouTube search: %r published after %s", query, published_after)

    search_resp = _execute(
        youtube.search().list(
            q=query,
            part="id",
            type="video",
            order="date",
            maxResults=min(max_results, _MAX_IDS_PER_CALL),
            publishedAfter=published_after,
            regionCode="US",
            relevanceLanguage="en",
        ),
        "video search",
    )

    video_ids = [item["id"]["videoId"] for item in search_resp.get("items", [])]
    if not video_ids:
        log.info("No videos found for %r", query)
        return []

    results = _apply_quality_filter(
        _hydrate_videos(youtube, video_ids), ticker, company_name
    )
    results.sort(key=lambda v: v.view_count, reverse=True)
    log.info("Returning %d videos after quality filter", len(results))
    return results


def _channel_info_by_id(youtube, channel_id: str) -> ChannelInfo | None:
    resp = _execute(
        youtube.channels().list(id=channel_id, part="snippet,statistics"),
        "channel lookup",
    )
    items = resp.get("items", [])
    if not items:
        return None
    return _to_channel_info(items[0])


def _to_channel_info(item: dict) -> ChannelInfo:
    snippet = item.get("snippet", {})
    stats = item.get("statistics", {})
    custom_url = snippet.get("customUrl") or ""
    handle_match = _HANDLE_RE.search(custom_url)
    return ChannelInfo(
        channel_id=item["id"],
        title=snippet.get("title", item["id"]),
        handle=f"@{handle_match.group(1)}" if handle_match else None,
        subscriber_count=int(stats.get("subscriberCount", 0)),
        video_count=int(stats.get("videoCount", 0)),
        view_count=int(stats.get("viewCount", 0)),
    )


def resolve_channel(query: str) -> ChannelInfo | None:
    """Resolve a channel id, ``@handle``, channel URL or plain name.

    Returns None when nothing matches, so the caller can tell the user their
    channel name was wrong rather than silently digesting the wrong creator.
    """
    query = query.strip()
    if not query:
        return None

    youtube = _client()

    url_match = _CHANNEL_URL_ID_RE.search(query)
    if url_match:
        return _channel_info_by_id(youtube, url_match.group(1))

    if _CHANNEL_ID_RE.match(query):
        return _channel_info_by_id(youtube, query)

    handle_match = _HANDLE_RE.search(query)
    if handle_match:
        handle = handle_match.group(1)
        try:
            resp = _execute(
                youtube.channels().list(forHandle=f"@{handle}", part="snippet,statistics"),
                "handle lookup",
            )
        except Exception as exc:  # noqa: BLE001 — older clients lack forHandle
            # Includes a genuinely bad key; the name search below hits the same
            # wall and reports it properly rather than blaming the handle.
            log.debug("forHandle lookup failed for @%s, falling back: %s", handle, exc)
        else:
            items = resp.get("items", [])
            if items:
                return _to_channel_info(items[0])
        query = handle  # fall through to a name search on the bare handle

    search_resp = _execute(
        youtube.search().list(q=query, part="snippet", type="channel", maxResults=1),
        "channel search",
    )
    items = search_resp.get("items", [])
    if not items:
        log.info("No channel matched %r", query)
        return None

    snippet_id = items[0]["id"]
    channel_id = snippet_id.get("channelId") if isinstance(snippet_id, dict) else snippet_id
    if not channel_id:
        return None
    return _channel_info_by_id(youtube, channel_id)


def list_channel_videos(
    channel_id: str,
    days: int = 30,
    query: str | None = None,
    max_results: int = 50,
    ticker: str | None = None,
    company_name: str = "",
) -> list[VideoMetadata]:
    """Return quality-filtered recent videos from one channel, newest first.

    *query* narrows the channel's uploads to a topic (usually the ticker or
    company name) — useful when the user trusts a generalist channel but only
    cares about one holding.
    """
    youtube = _client()

    params = {
        "channelId": channel_id,
        "part": "id",
        "type": "video",
        "order": "date",
        "maxResults": min(max_results, _MAX_IDS_PER_CALL),
        "publishedAfter": _published_after(days),
    }
    if query:
        params["q"] = query

    search_resp = _execute(youtube.search().list(**params), "channel video list")
    video_ids = [
        item["id"]["videoId"]
        for item in search_resp.get("items", [])
        if item.get("id", {}).get("videoId")
    ]
    if not video_ids:
        log.info("Channel %s has no matching videos in the last %d days", channel_id, days)
        return []

    results = _apply_quality_filter(
        _hydrate_videos(youtube, video_ids), ticker, company_name
    )
    results.sort(key=lambda v: v.published_at, reverse=True)
    log.info("Channel %s: %d videos after quality filter", channel_id, len(results))
    return results
