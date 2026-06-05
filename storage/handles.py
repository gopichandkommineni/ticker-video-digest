"""Handle write operations (identity + operational state)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .db import get_connection


def upsert_handle(
    handle: str,
    fields: dict[str, Any],
    db_path: Path | str | None = None,
) -> None:
    """
    Insert or update a handle row with the given fields.

    Does NOT touch aggregate fields managed by the tweet write path
    (total_tweets, latest_tweet_utc, tweets_watermark_utc, earliest_tweet_utc).
    Use this for identity info and status updates.
    """
    allowed = {
        "display_name", "user_id", "status", "status_since",
        "last_fetch_at", "last_fetch_status",
        "user_info_last_fetched", "added_at",
    }
    clean = {k: v for k, v in fields.items() if k in allowed}

    conn = get_connection(db_path)
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO handles (handle, {cols})
                VALUES (:handle, {placeholders})
                ON CONFLICT(handle) DO UPDATE SET
                    {updates}
                """.format(
                    cols=", ".join(clean),
                    placeholders=", ".join(f":{k}" for k in clean),
                    updates=", ".join(f"{k} = excluded.{k}" for k in clean),
                ),
                {"handle": handle, **clean},
            )
    finally:
        conn.close()


def update_handle_status(
    handle: str,
    status: str,
    last_fetch_at: str | None = None,
    last_fetch_status: str | None = None,
    db_path: Path | str | None = None,
) -> None:
    """Convenience updater for job-run status fields."""
    fields: dict[str, Any] = {"status": status}
    if last_fetch_at is not None:
        fields["last_fetch_at"] = last_fetch_at
    if last_fetch_status is not None:
        fields["last_fetch_status"] = last_fetch_status
    upsert_handle(handle, fields, db_path=db_path)


def get_handle(
    handle: str,
    db_path: Path | str | None = None,
) -> dict[str, Any] | None:
    """Return the handle row as a dict, or None if not found."""
    conn = get_connection(db_path)
    try:
        row = conn.execute(
            "SELECT * FROM handles WHERE handle = ?", (handle,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def list_handles(
    db_path: Path | str | None = None,
) -> list[dict[str, Any]]:
    """Return all handle rows ordered by handle name."""
    conn = get_connection(db_path)
    try:
        rows = conn.execute(
            """
            SELECT handle, display_name, status,
                   total_tweets, tweets_watermark_utc,
                   earliest_tweet_utc, latest_tweet_utc,
                   last_fetch_at, last_fetch_status
            FROM handles
            ORDER BY handle
            """
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


