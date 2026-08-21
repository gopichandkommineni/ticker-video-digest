"""Content-addressed, append-only storage of fetched bytes.

`data/raw/<sha256[:2]>/<sha256>.<ext>` plus a `raw_document` provenance row.

Hashing rather than URL-keying buys two things for free (ADR-0002):
  * dedupe — a posting re-listed at a new URL hashes identically;
  * change detection — a new hash for the same external_id means the text
    changed, and that diff is itself signal.

Nothing downstream may ever modify what is written here.
"""

from __future__ import annotations

from pathlib import Path

from career_compass.models import RawPayload


def content_hash(payload: bytes) -> str:
    """sha256 hex digest. The identity of a document."""
    raise NotImplementedError


def store(payload: RawPayload, root: Path) -> tuple[str, Path]:
    """Write bytes if unseen. Returns (hash, path). Idempotent."""
    raise NotImplementedError


def load(content_hash: str, root: Path) -> bytes:
    """Read raw bytes back for replay. The whole point of this module."""
    raise NotImplementedError
