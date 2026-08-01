"""Unit tests for cache.py — all DB ops go to tmp_path, no filesystem pollution."""
import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

from core import cache
from core.models import Transcript, TranscriptSegment, VideoMetadata


@pytest.fixture
def tmp_cache_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("TICKER_DIGEST_CACHE_DIR", str(tmp_path))
    return tmp_path


@pytest.fixture
def sample_transcript() -> Transcript:
    return Transcript(
        video_id="vid123",
        language="en",
        segments=[
            TranscriptSegment(text="hello", start_seconds=0.0, duration_seconds=1.5),
            TranscriptSegment(text="world", start_seconds=1.5, duration_seconds=2.0),
        ],
    )


@pytest.fixture
def sample_metadata() -> VideoMetadata:
    return VideoMetadata(
        video_id="vid123",
        title="Test Video",
        channel_id="chan1",
        channel_title="Test Chan",
        channel_subscriber_count=1000,
        published_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        duration_seconds=300,
        view_count=5000,
    )


# ---------------------------------------------------------------------------
# Round-trip
# ---------------------------------------------------------------------------

def test_transcript_roundtrip(tmp_cache_dir, sample_transcript):
    cache.set_transcript("vid123", sample_transcript)
    result = cache.get_transcript("vid123")
    assert result == sample_transcript
    assert result.full_text == "hello world"


def test_metadata_roundtrip(tmp_cache_dir, sample_metadata):
    cache.set_metadata("vid123", sample_metadata)
    result = cache.get_metadata("vid123")
    assert result == sample_metadata
    assert result.url == "https://youtube.com/watch?v=vid123"


# ---------------------------------------------------------------------------
# Missing keys
# ---------------------------------------------------------------------------

def test_get_missing_transcript_returns_none(tmp_cache_dir):
    assert cache.get_transcript("nonexistent") is None


def test_get_missing_metadata_returns_none(tmp_cache_dir):
    assert cache.get_metadata("nonexistent") is None


# ---------------------------------------------------------------------------
# Overwrite (INSERT OR REPLACE)
# ---------------------------------------------------------------------------

def test_set_transcript_overwrites(tmp_cache_dir, sample_transcript):
    cache.set_transcript("vid123", sample_transcript)
    updated = sample_transcript.model_copy(update={"language": "fr"})
    cache.set_transcript("vid123", updated)
    result = cache.get_transcript("vid123")
    assert result.language == "fr"


# ---------------------------------------------------------------------------
# TTL expiry — directly manipulate cached_at in the DB
# ---------------------------------------------------------------------------

def _force_cached_at(db_path, table: str, video_id: str, when: datetime) -> None:
    conn = sqlite3.connect(db_path)
    conn.execute(
        f"UPDATE {table} SET cached_at = ? WHERE video_id = ?",
        (when.isoformat(), video_id),
    )
    conn.commit()
    conn.close()


def test_transcript_ttl_expiry(tmp_cache_dir, sample_transcript):
    cache.set_transcript("vid123", sample_transcript)
    # TRANSCRIPT_TTL is 30 days; put cached_at 31 days in the past
    old = datetime.now(timezone.utc) - timedelta(days=31)
    _force_cached_at(tmp_cache_dir / "cache.db", "transcripts", "vid123", old)
    assert cache.get_transcript("vid123") is None


def test_transcript_fresh_within_ttl(tmp_cache_dir, sample_transcript):
    cache.set_transcript("vid123", sample_transcript)
    # 29 days old — still fresh
    recent = datetime.now(timezone.utc) - timedelta(days=29)
    _force_cached_at(tmp_cache_dir / "cache.db", "transcripts", "vid123", recent)
    assert cache.get_transcript("vid123") == sample_transcript


def test_metadata_ttl_expiry(tmp_cache_dir, sample_metadata):
    cache.set_metadata("vid123", sample_metadata)
    # METADATA_TTL is 7 days; put cached_at 8 days in the past
    old = datetime.now(timezone.utc) - timedelta(days=8)
    _force_cached_at(tmp_cache_dir / "cache.db", "metadata", "vid123", old)
    assert cache.get_metadata("vid123") is None


def test_metadata_fresh_within_ttl(tmp_cache_dir, sample_metadata):
    cache.set_metadata("vid123", sample_metadata)
    recent = datetime.now(timezone.utc) - timedelta(days=6)
    _force_cached_at(tmp_cache_dir / "cache.db", "metadata", "vid123", recent)
    assert cache.get_metadata("vid123") == sample_metadata
