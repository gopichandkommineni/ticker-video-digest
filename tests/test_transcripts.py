"""Unit tests for transcripts.py — mocks youtube_transcript_api and cache."""
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from youtube_transcript_api._errors import (
    NoTranscriptFound,
    TranscriptsDisabled,
    VideoUnavailable,
)

from ticker_digest import transcripts
from core.models import Transcript, TranscriptSegment


def _make_fetched(language_code: str = "en", segments=None):
    """Build a duck-typed stand-in for FetchedTranscript."""
    if segments is None:
        segments = [
            SimpleNamespace(text="hello", start=0.0, duration=1.5),
            SimpleNamespace(text="world", start=1.5, duration=2.0),
        ]
    return SimpleNamespace(
        snippets=segments,
        video_id="vid_abc",
        language="English",
        language_code=language_code,
        is_generated=False,
    )


# ---------------------------------------------------------------------------
# Happy path: English transcript fetched and cached
# ---------------------------------------------------------------------------

def test_happy_path_fetches_and_caches(mocker):
    mocker.patch("ticker_digest.transcripts.cache.get_transcript", return_value=None)
    set_cache = mocker.patch("ticker_digest.transcripts.cache.set_transcript")
    api_cls = mocker.patch("ticker_digest.transcripts.YouTubeTranscriptApi")
    api_cls.return_value.fetch.return_value = _make_fetched()

    result = transcripts.get_transcript("vid_abc")

    assert result is not None
    assert result.video_id == "vid_abc"
    assert result.language == "en"
    assert len(result.segments) == 2
    assert result.segments[0] == TranscriptSegment(
        text="hello", start_seconds=0.0, duration_seconds=1.5
    )
    assert result.full_text == "hello world"
    set_cache.assert_called_once_with("vid_abc", result)
    api_cls.return_value.fetch.assert_called_once_with("vid_abc", languages=["en"])


# ---------------------------------------------------------------------------
# Cache hit short-circuits the API
# ---------------------------------------------------------------------------

def test_cache_hit_skips_api_call(mocker):
    cached = Transcript(
        video_id="vid_abc",
        language="en",
        segments=[TranscriptSegment(text="cached", start_seconds=0.0, duration_seconds=1.0)],
    )
    mocker.patch("ticker_digest.transcripts.cache.get_transcript", return_value=cached)
    api_cls = mocker.patch("ticker_digest.transcripts.YouTubeTranscriptApi")

    result = transcripts.get_transcript("vid_abc")

    assert result is cached
    api_cls.assert_not_called()


# ---------------------------------------------------------------------------
# Translation fallback: English missing, but a translatable transcript exists
# ---------------------------------------------------------------------------

def test_no_english_translates_available_transcript(mocker):
    mocker.patch("ticker_digest.transcripts.cache.get_transcript", return_value=None)
    set_cache = mocker.patch("ticker_digest.transcripts.cache.set_transcript")

    api_cls = mocker.patch("ticker_digest.transcripts.YouTubeTranscriptApi")
    api_instance = api_cls.return_value
    # First fetch() raises NoTranscriptFound
    api_instance.fetch.side_effect = NoTranscriptFound("vid_abc", ["en"], MagicMock())

    # list() returns a list-like with one translatable transcript
    translatable = MagicMock()
    translatable.is_translatable = True
    translatable.translate.return_value.fetch.return_value = _make_fetched(
        language_code="en"
    )
    api_instance.list.return_value = iter([translatable])

    result = transcripts.get_transcript("vid_abc")

    assert result is not None
    assert result.language == "en"
    translatable.translate.assert_called_once_with("en")
    set_cache.assert_called_once()


# ---------------------------------------------------------------------------
# No translatable transcript → returns None (does not raise)
# ---------------------------------------------------------------------------

def test_no_translatable_transcript_returns_none(mocker):
    mocker.patch("ticker_digest.transcripts.cache.get_transcript", return_value=None)
    set_cache = mocker.patch("ticker_digest.transcripts.cache.set_transcript")

    api_cls = mocker.patch("ticker_digest.transcripts.YouTubeTranscriptApi")
    api_instance = api_cls.return_value
    api_instance.fetch.side_effect = NoTranscriptFound("vid_abc", ["en"], MagicMock())

    non_translatable = MagicMock()
    non_translatable.is_translatable = False
    api_instance.list.return_value = iter([non_translatable])

    result = transcripts.get_transcript("vid_abc")

    assert result is None
    set_cache.assert_not_called()


# ---------------------------------------------------------------------------
# TranscriptsDisabled → None
# ---------------------------------------------------------------------------

def test_transcripts_disabled_returns_none(mocker):
    mocker.patch("ticker_digest.transcripts.cache.get_transcript", return_value=None)
    set_cache = mocker.patch("ticker_digest.transcripts.cache.set_transcript")

    api_cls = mocker.patch("ticker_digest.transcripts.YouTubeTranscriptApi")
    api_cls.return_value.fetch.side_effect = TranscriptsDisabled("vid_abc")

    assert transcripts.get_transcript("vid_abc") is None
    set_cache.assert_not_called()


# ---------------------------------------------------------------------------
# VideoUnavailable → None
# ---------------------------------------------------------------------------

def test_video_unavailable_returns_none(mocker):
    mocker.patch("ticker_digest.transcripts.cache.get_transcript", return_value=None)
    set_cache = mocker.patch("ticker_digest.transcripts.cache.set_transcript")

    api_cls = mocker.patch("ticker_digest.transcripts.YouTubeTranscriptApi")
    api_cls.return_value.fetch.side_effect = VideoUnavailable("vid_abc")

    assert transcripts.get_transcript("vid_abc") is None
    set_cache.assert_not_called()


# ---------------------------------------------------------------------------
# Translation fallback — translation itself throws
# ---------------------------------------------------------------------------

def test_translation_fallback_disabled_returns_none(mocker):
    mocker.patch("ticker_digest.transcripts.cache.get_transcript", return_value=None)
    set_cache = mocker.patch("ticker_digest.transcripts.cache.set_transcript")

    api_cls = mocker.patch("ticker_digest.transcripts.YouTubeTranscriptApi")
    api_instance = api_cls.return_value
    api_instance.fetch.side_effect = NoTranscriptFound("vid_abc", ["en"], MagicMock())
    api_instance.list.side_effect = TranscriptsDisabled("vid_abc")

    assert transcripts.get_transcript("vid_abc") is None
    set_cache.assert_not_called()
