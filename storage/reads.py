"""Read-path queries for tweets."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .db import get_connection


def get_tweets_by_handle(
    handle: str,
    limit: int = 50,
    since: str | None = None,
    db_path: Path | str | None = None,
) -> list[dict[str, Any]]:
    """
    Return tweets for *handle*, newest first.

    Args:
        handle: account_handle to filter on.
        limit:  max rows to return.
        since:  if given, only return tweets with created_at_utc > since
                (ISO 8601 UTC string).
    """
    conn = get_connection(db_path)
    try:
        if since:
            rows = conn.execute(
                """
                SELECT * FROM raw_tweets
                WHERE account_handle = ? AND created_at_utc > ?
                ORDER BY created_at_utc DESC
                LIMIT ?
                """,
                (handle, since, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT * FROM raw_tweets
                WHERE account_handle = ?
                ORDER BY created_at_utc DESC
                LIMIT ?
                """,
                (handle, limit),
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def count_tweets(
    handle: str,
    db_path: Path | str | None = None,
) -> int:
    """Return stored tweet count for *handle* (queries raw_tweets directly)."""
    conn = get_connection(db_path)
    try:
        row = conn.execute(
            "SELECT COUNT(*) FROM raw_tweets WHERE account_handle = ?",
            (handle,),
        ).fetchone()
        return row[0]
    finally:
        conn.close()
