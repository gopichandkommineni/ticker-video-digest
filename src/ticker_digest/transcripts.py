"""Transcript fetching with SQLite cache.

Prefers native English captions; falls back to translating any available
transcript to English. Returns None (does not raise) when captions are
unavailable, disabled, or the video is gone.
"""
import logging

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    NoTranscriptFound,
    TranscriptsDisabled,
    VideoUnavailable,
)

from core import cache
from core.models import Transcript, TranscriptSegment

log = logging.getLogger(__name__)


def _to_transcript(fetched, video_id: str) -> Transcript:
    segments = [
        TranscriptSegment(
            text=snip.text,
            start_seconds=snip.start,
            duration_seconds=snip.duration,
        )
        for snip in fetched.snippets
    ]
    return Transcript(
        video_id=video_id,
        segments=segments,
        language=fetched.language_code,
    )


def _translate_to_english(api: YouTubeTranscriptApi, video_id: str):
    """Try to find a translatable transcript and translate it to English.

    Returns a FetchedTranscript or None.
    """
    transcript_list = api.list(video_id)
    for transcript in transcript_list:
        if transcript.is_translatable:
            return transcript.translate("en").fetch()
    return None


def get_transcript(video_id: str) -> Transcript | None:
    cached = cache.get_transcript(video_id)
    if cached is not None:
        log.debug("Transcript cache hit for %s", video_id)
        return cached

    api = YouTubeTranscriptApi()
    try:
        fetched = api.fetch(video_id, languages=["en"])
    except NoTranscriptFound:
        try:
            fetched = _translate_to_english(api, video_id)
        except (TranscriptsDisabled, NoTranscriptFound, VideoUnavailable) as e:
            log.info("No captions for %s: %s", video_id, type(e).__name__)
            return None
        if fetched is None:
            log.info("No captions available for %s (nothing translatable)", video_id)
            return None
    except (TranscriptsDisabled, VideoUnavailable) as e:
        log.info("Cannot fetch transcript for %s: %s", video_id, type(e).__name__)
        return None

    transcript = _to_transcript(fetched, video_id)
    cache.set_transcript(video_id, transcript)
    log.info(
        "Fetched transcript for %s (%d segments, lang=%s)",
        video_id,
        len(transcript.segments),
        transcript.language,
    )
    return transcript
