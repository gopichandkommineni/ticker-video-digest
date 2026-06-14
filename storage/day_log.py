"""Read/write helpers for the day_fetch_log table."""

from __future__ import annotations

import datetime
import logging
from pathlib import Path
from typing import Any

from .db import get_connection

logger = logging.getLogger(__name__)

_UTC = datetime.timezone.utc


def _iso_now() -> str:
    return datetime.datetime.now(tz=_UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def populate_pending_days(
    handle: str,
    since: datetime.date,
    until: datetime.date,
    providers: tuple[str, ...] = ("getxapi", "twitterapi"),
    db_path: Path | str | None = None,
) -> int:
    """
    INSERT OR IGNORE one pending row per (handle, date, provider) in [since, until].
    Returns the number of rows actually inserted (existing rows are skipped).
    """
    rows: list[tuple] = []
    day = since
    while day <= until:
        for provider in providers:
            rows.append((handle, day.isoformat(), provider))
        day += datetime.timedelta(days=1)

    conn = get_connection(db_path)
    inserted = 0
    try:
        with conn:
            for handle_, date_, provider_ in rows:
                cur = conn.execute(
                    """
                    INSERT OR IGNORE INTO day_fetch_log (handle, date, provider, status)
                    VALUES (?, ?, ?, 'pending')
                    """,
                    (handle_, date_, provider_),
                )
                inserted += cur.rowcount
    finally:
        conn.close()
    logger.debug("populate_pending_days(%s): inserted %d / %d rows", handle, inserted, len(rows))
    return inserted


def get_pending_days(
    handle: str,
    providers: tuple[str, ...] = ("getxapi", "twitterapi"),
    db_path: Path | str | None = None,
) -> list[dict[str, Any]]:
    """Return all pending rows for handle, ordered date ASC."""
    conn = get_connection(db_path)
    try:
        placeholders = ",".join("?" * len(providers))
        rows = conn.execute(
            f"""
            SELECT handle, date, provider, status, retry_count
            FROM day_fetch_log
            WHERE handle = ? AND status = 'pending' AND provider IN ({placeholders})
            ORDER BY date ASC
            """,
            (handle, *providers),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_retryable_days(
    handle: str,
    max_retries: int = 3,
    providers: tuple[str, ...] = ("getxapi", "twitterapi"),
    db_path: Path | str | None = None,
) -> list[dict[str, Any]]:
    """Return failed/mismatch rows where retry_count < max_retries, date ASC."""
    conn = get_connection(db_path)
    try:
        placeholders = ",".join("?" * len(providers))
        rows = conn.execute(
            f"""
            SELECT handle, date, provider, status, retry_count
            FROM day_fetch_log
            WHERE handle = ?
              AND status IN ('failed', 'mismatch')
              AND retry_count < ?
              AND provider IN ({placeholders})
            ORDER BY date ASC
            """,
            (handle, max_retries, *providers),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_all_retryable_days(
    max_retries: int = 3,
    providers: tuple[str, ...] = ("getxapi", "twitterapi"),
    db_path: Path | str | None = None,
) -> list[dict[str, Any]]:
    """Return all failed/mismatch rows across all handles (for daily sweep)."""
    conn = get_connection(db_path)
    try:
        placeholders = ",".join("?" * len(providers))
        rows = conn.execute(
            f"""
            SELECT handle, date, provider, status, retry_count
            FROM day_fetch_log
            WHERE status IN ('failed', 'mismatch')
              AND retry_count < ?
              AND provider IN ({placeholders})
            ORDER BY handle ASC, date ASC
            """,
            (max_retries, *providers),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def mark_day(
    handle: str,
    date: str,
    provider: str,
    status: str,
    tweet_count: int | None = None,
    error: str | None = None,
    increment_retry: bool = False,
    db_path: Path | str | None = None,
) -> None:
    """Update a single day_fetch_log row."""
    conn = get_connection(db_path)
    try:
        with conn:
            conn.execute(
                """
                UPDATE day_fetch_log
                SET status      = ?,
                    tweet_count = COALESCE(?, tweet_count),
                    fetched_at  = ?,
                    error       = COALESCE(?, error),
                    retry_count = retry_count + ?
                WHERE handle = ? AND date = ? AND provider = ?
                """,
                (
                    status,
                    tweet_count,
                    _iso_now(),
                    error,
                    1 if increment_retry else 0,
                    handle, date, provider,
                ),
            )
    finally:
        conn.close()


def day_summary(
    handle: str,
    db_path: Path | str | None = None,
) -> dict[str, int]:
    """Return counts per status for a handle: {pending, ok, failed, mismatch}."""
    conn = get_connection(db_path)
    try:
        rows = conn.execute(
            """
            SELECT status, COUNT(*) AS n
            FROM day_fetch_log
            WHERE handle = ?
            GROUP BY status
            """,
            (handle,),
        ).fetchall()
        result: dict[str, int] = {"pending": 0, "ok": 0, "failed": 0, "mismatch": 0}
        for row in rows:
            result[row["status"]] = row["n"]
        return result
    finally:
        conn.close()


def coverage_floor(
    handle: str,
    db_path: Path | str | None = None,
) -> str | None:
    """
    Return the earliest date where ALL providers are ok, or None if no ok days.
    This replaces the old tweets_watermark_utc / reached_floor concept.
    """
    conn = get_connection(db_path)
    try:
        row = conn.execute(
            """
            SELECT MIN(date) AS floor
            FROM (
                SELECT date
                FROM day_fetch_log
                WHERE handle = ? AND status = 'ok'
                GROUP BY date
                HAVING COUNT(DISTINCT provider) = (
                    SELECT COUNT(DISTINCT provider)
                    FROM day_fetch_log
                    WHERE handle = ?
                )
            )
            """,
            (handle, handle),
        ).fetchone()
        return row["floor"] if row else None
    finally:
        conn.close()
