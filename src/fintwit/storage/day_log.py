"""Read/write helpers for the day_fetch_log table."""

from __future__ import annotations

import datetime
import logging
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .db import get_connection

logger = logging.getLogger(__name__)

_UTC = datetime.timezone.utc


def _iso_now() -> str:
    return datetime.datetime.now(tz=_UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _iso(dt: datetime.datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


# Schema-mapping note (worker pool v1).
# ------------------------------------
# Spec §3.4/§9 are written against column names `attempts` and
# `last_attempted_at`. The live ledger v1 schema (and §4.2 "no other schema
# changes") provides neither; the worker pool maps onto the columns that DO
# exist:
#     spec `attempts`           -> day_fetch_log.retry_count
#     spec `last_attempted_at`  -> day_fetch_log.fetched_at (set at claim time
#                                  and reused as the last-activity timestamp for
#                                  stale-`fetching` detection)
# No columns are added beyond tweets_fetched / tweets_written (spec §4.1).


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


# ---------------------------------------------------------------------------
# Worker-pool dispatch + claim + outcome (worker pool v1 spec §3.4, §3.5, §9).
# These take an explicit connection because the worker owns one connection per
# thread and the claim must control its own BEGIN IMMEDIATE transaction.
# ---------------------------------------------------------------------------

@dataclass
class Job:
    """A dispatch-eligible day_fetch_log row (spec §3.4 unit of work)."""
    handle: str
    date: str
    provider: str
    status: str
    attempts: int          # day_fetch_log.retry_count


def _stale_cutoff(now: str, stale_threshold_sec: int) -> str:
    """ISO timestamp before which a 'fetching' row is considered crashed (§9)."""
    dt = datetime.datetime.strptime(now, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=_UTC)
    return _iso(dt - datetime.timedelta(seconds=stale_threshold_sec))


def get_eligible_jobs(
    conn: sqlite3.Connection,
    limit: int,
    now: str | None = None,
    *,
    max_attempts: int = 3,
    stale_threshold_sec: int = 600,
    handles: list[str] | None = None,
) -> list[Job]:
    """Return up to *limit* rows eligible for a claim, oldest date first.

    Eligible (spec §3.4 + §9):
      - status in (pending, failed), attempts < max, and either no backoff set
        or the backoff window (next_eligible_at) has elapsed; OR
      - status = fetching but stale (last activity older than the stale
        threshold) — a crashed worker's row, attempts < max.
    Reconciliation outcomes (ok/mismatch) and terminal complete/exhausted rows
    are never returned.

    *handles*, when given, restricts dispatch to those handles (PR B — lets a
    per-handle ingest run a pool scoped to itself). Default None preserves the
    global-dispatch behavior. An empty list is a caller bug (it would silently
    match nothing), so it raises ValueError.
    """
    if handles is not None and len(handles) == 0:
        raise ValueError("get_eligible_jobs: handles=[] is ambiguous; pass None for all")
    now = now or _iso_now()
    cutoff = _stale_cutoff(now, stale_threshold_sec)
    params: dict[str, Any] = {
        "max": max_attempts, "now": now, "cutoff": cutoff, "limit": limit,
    }
    handle_clause = ""
    if handles:
        names = {f"h{i}": h for i, h in enumerate(handles)}
        params.update(names)
        handle_clause = f"AND handle IN ({','.join(':' + k for k in names)})"
    rows = conn.execute(
        f"""
        SELECT handle, date, provider, status, retry_count
        FROM day_fetch_log
        WHERE
            (
              ( status IN ('pending', 'failed')
                AND retry_count < :max
                AND (next_eligible_at IS NULL OR next_eligible_at <= :now) )
              OR
              ( status = 'fetching'
                AND retry_count < :max
                AND (fetched_at IS NULL OR fetched_at < :cutoff) )
            )
            {handle_clause}
        ORDER BY date ASC, handle ASC, provider ASC
        LIMIT :limit
        """,
        params,
    ).fetchall()
    return [
        Job(handle=r["handle"], date=r["date"], provider=r["provider"],
            status=r["status"], attempts=r["retry_count"])
        for r in rows
    ]


def reopen_mismatch_days(
    conn: sqlite3.Connection,
    handle: str,
    max_attempts: int,
) -> int:
    """Re-open outstanding mismatch days for a handle so the pool re-dispatches
    them (PR B). Gated on the retry cap, mirroring get_retryable_days' mismatch
    arm — so this preserves, not changes, the existing mismatch-retry semantics.

    next_eligible_at is cleared so a reopened day is immediately eligible (it
    should not inherit backoff from any prior failed state). Idempotent: returns
    0 when no capped-under mismatch rows remain.
    """
    with conn:
        cur = conn.execute(
            """
            UPDATE day_fetch_log
            SET status = 'pending',
                next_eligible_at = NULL
            WHERE handle = ?
              AND status = 'mismatch'
              AND retry_count < ?
            """,
            (handle, max_attempts),
        )
    return cur.rowcount


def reopen_failed_days(
    conn: sqlite3.Connection,
    handle: str,
    since: datetime.date | None = None,
    until: datetime.date | None = None,
    providers: tuple[str, ...] | None = None,
) -> int:
    """Re-open terminally-failed days so a re-run re-fetches them.

    Sets status → 'pending', retry_count → 0, and clears next_eligible_at /
    error / error_class. Unlike reopen_mismatch_days this is deliberately NOT
    gated on the retry cap: it exists to unstick days that *exhausted* their
    attempts because of a provider-side outage (e.g. HTTP 402 when a credit
    balance ran out mid-backfill), giving them a clean retry budget once the
    balance is topped up. Optional [since, until] and provider filters scope
    the reset so unrelated failures aren't touched. Returns rows reopened.
    """
    clauses = ["status = 'failed'", "handle = ?"]
    params: list = [handle]
    if since is not None:
        clauses.append("date >= ?")
        params.append(since.isoformat())
    if until is not None:
        clauses.append("date <= ?")
        params.append(until.isoformat())
    if providers:
        clauses.append("provider IN (%s)" % ",".join("?" * len(providers)))
        params.extend(providers)
    with conn:
        cur = conn.execute(
            "UPDATE day_fetch_log "
            "SET status = 'pending', retry_count = 0, next_eligible_at = NULL, "
            "    error = NULL, error_class = NULL "
            "WHERE " + " AND ".join(clauses),
            params,
        )
    return cur.rowcount


def claim_day(
    conn: sqlite3.Connection,
    handle: str,
    date: str,
    provider: str,
    max_attempts: int,
    *,
    now: str | None = None,
    stale_threshold_sec: int = 600,
) -> bool:
    """Atomically transition a row to 'fetching' (spec §3.4).

    Uses BEGIN IMMEDIATE so two workers racing for the same row serialize: the
    first wins (rowcount == 1), the second matches zero rows (rowcount == 0).
    Eligible source states are pending/failed (respecting attempts + backoff)
    and stale 'fetching' (a crashed worker's row, §9). Increments retry_count
    and stamps fetched_at as the claim/last-activity time.

    Returns True if this worker claimed the row, False otherwise.
    """
    now = now or _iso_now()
    cutoff = _stale_cutoff(now, stale_threshold_sec)
    try:
        conn.execute("BEGIN IMMEDIATE")
        cur = conn.execute(
            """
            UPDATE day_fetch_log
            SET status             = 'fetching',
                retry_count        = retry_count + 1,
                first_attempted_at = COALESCE(first_attempted_at, :now),
                fetched_at         = :now
            WHERE handle = :h AND date = :d AND provider = :p
              AND (
                ( status IN ('pending', 'failed')
                  AND retry_count < :max
                  AND (next_eligible_at IS NULL OR next_eligible_at <= :now) )
                OR
                ( status = 'fetching'
                  AND retry_count < :max
                  AND (fetched_at IS NULL OR fetched_at < :cutoff) )
              )
            """,
            {"h": handle, "d": date, "p": provider,
             "max": max_attempts, "now": now, "cutoff": cutoff},
        )
        claimed = cur.rowcount == 1
        conn.commit()
        return claimed
    except Exception:
        conn.rollback()
        raise


def mark_day_outcome(
    conn: sqlite3.Connection,
    handle: str,
    date: str,
    provider: str,
    status: str,
    reached_floor: bool | None,
    error_class: str | None,
    tweets_fetched: int | None,
    tweets_written: int | None,
    next_eligible_at: str | None,
    *,
    attempts: int | None = None,
    error: str | None = None,
    now: str | None = None,
) -> None:
    """Write the terminal outcome of a single-provider fetch (spec §3.5).

    Wraps the column writes the old mark_day performed and adds the worker-pool
    columns. Does NOT increment retry_count — claim_day already did. Set
    *attempts* to force retry_count (e.g. to MAX_ATTEMPTS on a permanent error,
    so the row is never re-dispatched). error_class / reached_floor /
    next_eligible_at are written directly (not COALESCEd) so success clears any
    stale value: error_class is NULL on success (spec §10).
    """
    now = now or _iso_now()
    reached = None if reached_floor is None else (1 if reached_floor else 0)
    with conn:
        conn.execute(
            """
            UPDATE day_fetch_log
            SET status           = :status,
                reached_floor    = :reached,
                error_class      = :error_class,
                tweets_fetched   = COALESCE(:fetched, tweets_fetched),
                tweets_written   = COALESCE(:written, tweets_written),
                tweet_count      = COALESCE(:fetched, tweet_count),
                next_eligible_at = :next_eligible_at,
                fetched_at       = :now,
                last_succeeded_at = CASE
                    WHEN :status IN ('complete', 'exhausted', 'ok') THEN :now
                    ELSE last_succeeded_at END,
                retry_count      = COALESCE(:attempts, retry_count),
                error            = COALESCE(:error, error)
            WHERE handle = :h AND date = :d AND provider = :p
            """,
            {"status": status, "reached": reached, "error_class": error_class,
             "fetched": tweets_fetched, "written": tweets_written,
             "next_eligible_at": next_eligible_at, "now": now,
             "attempts": attempts, "error": error,
             "h": handle, "d": date, "p": provider},
        )


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
