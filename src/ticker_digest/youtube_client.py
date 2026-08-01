"""YouTube Data API v3 client: search_recent_videos, get_video_metadata."""
import logging
import re
from datetime import datetime, timedelta, timezone

from googleapiclient.discovery import build

from core.config import MIN_SUBSCRIBER_COUNT, MIN_VIDEO_DURATION_SECONDS, YOUTUBE_API_KEY
from core.models import VideoMetadata

log = logging.getLogger(__name__)


def _parse_iso8601_duration(duration: str) -> int:
    """Convert an ISO 8601 duration string (e.g. PT1H30M15S) to total seconds."""
    match = re.fullmatch(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", duration)
    if not match:
        return 0
    hours, minutes, seconds = (int(g or 0) for g in match.groups())
    return hours * 3600 + minutes * 60 + seconds


def search_recent_videos(
    ticker: str,
    company_name: str,
    days: int = 7,
) -> list[VideoMetadata]:
    """Return quality-filtered VideoMetadata for recent YouTube videos about *ticker*.

    Makes three batched API calls: search, videos.list, channels.list.
    Filters out videos shorter than MIN_VIDEO_DURATION_SECONDS or from channels
    with fewer than MIN_SUBSCRIBER_COUNT subscribers.
    Results are sorted by view_count descending.
    """
    youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

    published_after = (datetime.now(timezone.utc) - timedelta(days=days)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    query = f'"{ticker}" OR "{company_name}" stock'
    log.info("YouTube search: %r published after %s", query, published_after)

    search_resp = (
        youtube.search()
        .list(
            q=query,
            part="id",
            type="video",
            order="date",
            maxResults=50,
            publishedAfter=published_after,
            regionCode="US",
            relevanceLanguage="en",
        )
        .execute()
    )

    video_ids = [item["id"]["videoId"] for item in search_resp.get("items", [])]
    if not video_ids:
        log.info("No videos found for %r", query)
        return []

    # Single batched call for snippet + duration + view counts
    videos_resp = (
        youtube.videos()
        .list(
            id=",".join(video_ids),
            part="snippet,contentDetails,statistics",
        )
        .execute()
    )
    video_items = videos_resp.get("items", [])

    # Single batched call for subscriber counts
    channel_ids = list({item["snippet"]["channelId"] for item in video_items})
    channels_resp = (
        youtube.channels()
        .list(
            id=",".join(channel_ids),
            part="statistics",
        )
        .execute()
    )
    subscriber_map: dict[str, int] = {
        ch["id"]: int(ch["statistics"].get("subscriberCount", 0))
        for ch in channels_resp.get("items", [])
    }

    results: list[VideoMetadata] = []
    for item in video_items:
        snippet = item["snippet"]
        duration_s = _parse_iso8601_duration(item["contentDetails"]["duration"])
        channel_id = snippet["channelId"]
        subs = subscriber_map.get(channel_id, 0)

        if duration_s < MIN_VIDEO_DURATION_SECONDS:
            log.debug("Skipping %s: %ds < min duration", item["id"], duration_s)
            continue
        if subs < MIN_SUBSCRIBER_COUNT:
            log.debug("Skipping %s: %d subs < min subs", item["id"], subs)
            continue

        results.append(
            VideoMetadata(
                video_id=item["id"],
                title=snippet["title"],
                channel_id=channel_id,
                channel_title=snippet["channelTitle"],
                channel_subscriber_count=subs,
                published_at=datetime.fromisoformat(
                    snippet["publishedAt"].replace("Z", "+00:00")
                ),
                duration_seconds=duration_s,
                view_count=int(item["statistics"].get("viewCount", 0)),
            )
        )

    results.sort(key=lambda v: v.view_count, reverse=True)
    log.info("Returning %d videos after quality filter", len(results))
    return results
