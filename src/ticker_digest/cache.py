"""SQLite cache wrapper: get/set for transcripts and metadata.

DB path: ~/.ticker_digest/cache.db by default, overridable via
TICKER_DIGEST_CACHE_DIR. TTLs: 30 days for transcripts (captions are
permanent), 7 days for metadata (view counts drift).
"""
import logging
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from ticker_digest.models import Transcript, VideoMetadata

log = logging.getLogger(__name__)

TRANSCRIPT_TTL = timedelta(days=30)
METADATA_TTL = timedelta(days=7)


def _cache_dir() -> Path:
    override = os.environ.get("TICKER_DIGEST_CACHE_DIR")
    return Path(override) if override else Path.home() / ".ticker_digest"


def _db_path() -> Path:
    d = _cache_dir()
    d.mkdir(parents=True, exist_ok=True)
    return d / "cache.db"


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_db_path())
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS transcripts (
            video_id TEXT PRIMARY KEY,
            transcript_json TEXT NOT NULL,
            cached_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS metadata (
            video_id TEXT PRIMARY KEY,
            metadata_json TEXT NOT NULL,
            cached_at TEXT NOT NULL
        );
        """
    )
    return conn


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _is_fresh(cached_at_iso: str, ttl: timedelta) -> bool:
    return _now() - datetime.fromisoformat(cached_at_iso) < ttl


def get_transcript(video_id: str) -> Transcript | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT transcript_json, cached_at FROM transcripts WHERE video_id = ?",
            (video_id,),
        ).fetchone()
    if row is None:
        return None
    transcript_json, cached_at = row
    if not _is_fresh(cached_at, TRANSCRIPT_TTL):
        log.debug("Transcript cache expired for %s", video_id)
        return None
    return Transcript.model_validate_json(transcript_json)


def set_transcript(video_id: str, transcript: Transcript) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO transcripts (video_id, transcript_json, cached_at) "
            "VALUES (?, ?, ?)",
            (video_id, transcript.model_dump_json(), _now().isoformat()),
        )
        conn.commit()


def get_metadata(video_id: str) -> VideoMetadata | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT metadata_json, cached_at FROM metadata WHERE video_id = ?",
            (video_id,),
        ).fetchone()
    if row is None:
        return None
    metadata_json, cached_at = row
    if not _is_fresh(cached_at, METADATA_TTL):
        log.debug("Metadata cache expired for %s", video_id)
        return None
    return VideoMetadata.model_validate_json(metadata_json)


def set_metadata(video_id: str, metadata: VideoMetadata) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO metadata (video_id, metadata_json, cached_at) "
            "VALUES (?, ?, ?)",
            (video_id, metadata.model_dump_json(), _now().isoformat()),
        )
        conn.commit()
