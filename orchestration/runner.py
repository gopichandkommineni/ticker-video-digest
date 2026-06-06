"""Orchestration layer: decides fetch range, calls adapters, writes storage.

Entry point: ingest_handle(handle, provider=None) -> RunResult

Silent-failure rules enforced here:
  F1. Watermark advances ONLY after a clean, complete fetch + confirmed write.
  F2. Handles stuck in backfilling/fetching > STALE_THRESHOLD_MINUTES are stale.
  F3. Watermark is derived from confirmed-written rows in storage, never from the
      adapter's returned list.
  F4. A freshly in-progress handle returns RunResult(outcome="skipped").
"""

from __future__ import annotations

import datetime
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import config as cfg
from storage.db import init_db
from storage.handles import get_handle, list_handles, normalize_handle, upsert_handle
from storage.tweets import upsert_tweets
from tweet_sources.base import UserInfo
from tweet_sources.factory import get_source

logger = logging.getLogger(__name__)

_UTC = datetime.timezone.utc

_IN_PROGRESS_STATUSES = {"backfilling", "fetching"}


@dataclass
class RunResult:
    handle: str
    outcome: str          # "ok" | "skipped" | "failed"
    reason: str = ""
    inserted: int = 0
    ignored: int = 0
    watermark: str | None = None
    error: str = ""


def _now() -> datetime.datetime:
    return datetime.datetime.now(tz=_UTC)


def _iso(dt: datetime.datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def is_stale(row: dict[str, Any]) -> bool:
    """True if a handle stuck in backfilling/fetching has been so past STALE_THRESHOLD_MINUTES."""
    if row.get("status") not in _IN_PROGRESS_STATUSES:
        return False
    # status_since is written every time we enter an in-progress state.
    since_raw = row.get("status_since")
    if not since_raw:
        return True  # no timestamp recorded — assume stale to avoid deadlock
    try:
        since = datetime.datetime.fromisoformat(since_raw.replace("Z", "+00:00"))
        if since.tzinfo is None:
            since = since.replace(tzinfo=_UTC)
        age_min = (_now() - since).total_seconds() / 60
        return age_min > cfg.STALE_THRESHOLD_MINUTES
    except ValueError:
        return True


def _to_storage_rows(
    tweets: list,
    handle: str,
    provider: str,
    fetched_at: str,
) -> list[dict[str, Any]]:
    rows = []
    for t in tweets:
        rows.append({
            "tweet_id": t.id,
            "account_handle": handle,
            "display_name": None,
            "user_id": None,
            "text": t.text,
            "created_at_utc": t.created_at_utc,
            "type": t.type,
            "is_reply": int(t.is_reply),
            "is_quote": int(t.is_quote),
            "in_reply_to_id": t.in_reply_to_id,
            "quoted_tweet_id": t.quoted_tweet_id,
            "quoted_author_id": t.quoted_author_id,
            "conversation_id": t.conversation_id,
            "like_count": t.like_count,
            "retweet_count": t.retweet_count,
            "reply_count": t.reply_count,
            "quote_count": t.quote_count,
            "view_count": t.view_count,
            "bookmark_count": t.bookmark_count,
            "has_media": int(t.has_media),
            "media_urls": ",".join(t.media_urls) if t.media_urls else None,
            "url": t.url,
            "is_deleted": 0,
            "fetched_at": fetched_at,
            "source_provider": provider,
            "raw_json": None,
        })
    return rows


def ingest_handle(
    handle: str,
    provider: str | None = None,
    db_path: Path | str | None = None,
) -> RunResult:
    """
    Fetch and store tweets for a single handle.

    - No watermark → backfill from Jan 1 of the current year (computed at runtime).
    - Has watermark → delta from (watermark - 1h) to now.
    - Watermark advances ONLY on a clean, complete fetch + confirmed write (F1/F3).
    - Partial or failed fetch leaves watermark unchanged; status=failed (F1).
    - A handle already in-progress and not stale is skipped (F4).
    """
    handle = normalize_handle(handle)
    init_db(db_path)
    prov = provider or cfg.TWEET_PROVIDER

    # Step 1: read or create handle row.
    row = get_handle(handle, db_path=db_path)
    if row is None:
        upsert_handle(handle, {"status": "pending"}, db_path=db_path)
        row = get_handle(handle, db_path=db_path)

    # Step 2 (F4): skip if actively in-progress and not stale.
    status = (row or {}).get("status", "pending")
    if status in _IN_PROGRESS_STATUSES and not is_stale(row or {}):
        logger.info("handle %s is %s (not stale) — skipping", handle, status)
        return RunResult(handle=handle, outcome="skipped", reason="in progress")

    # Step 3: compute fetch range.
    now = _now()
    watermark_raw: str | None = (row or {}).get("tweets_watermark_utc")

    # An incomplete handle must re-backfill from the floor regardless of any
    # partial watermark the storage layer recorded from the incomplete run.
    if watermark_raw and status != "incomplete":
        wm_dt = datetime.datetime.fromisoformat(watermark_raw.replace("Z", "+00:00"))
        if wm_dt.tzinfo is None:
            wm_dt = wm_dt.replace(tzinfo=_UTC)
        start = (wm_dt - datetime.timedelta(hours=1)).date()
        new_status = "fetching"
    else:
        start = datetime.date(now.year, 1, 1)
        new_status = "backfilling"

    end = now.date()
    now_iso = _iso(now)

    logger.info("handle %s: %s [%s, %s]", handle, new_status, start, end)

    # Step 4: mark in-progress; write status_since for stale detection (F2).
    upsert_handle(
        handle,
        {"status": new_status, "status_since": now_iso, "last_fetch_at": now_iso},
        db_path=db_path,
    )

    # Step 5: fetch. Track whether it completed cleanly and reached the floor.
    source = get_source(prov)
    fetched: list = []
    fetch_clean = False
    floor_reached = False
    fetch_error = ""
    try:
        fetch_result = source.fetch_tweets(handle, start, end)
        fetched = fetch_result.tweets
        floor_reached = fetch_result.reached_floor
        fetch_clean = True
    except Exception as exc:
        fetch_error = str(exc)
        logger.warning("handle %s: fetch raised: %s", handle, exc)

    # Step 6: write whatever was fetched (idempotent; safe even if partial).
    write_ok = False
    upsert_result = None
    if fetched:
        rows = _to_storage_rows(fetched, handle, prov, _iso(_now()))
        try:
            upsert_result = upsert_tweets(rows, db_path=db_path)
            write_ok = True
        except Exception as exc:
            fetch_error = fetch_error or str(exc)
            logger.warning("handle %s: upsert raised: %s", handle, exc)
    else:
        write_ok = fetch_clean  # empty-but-clean fetch counts as successful

    # Step 7/8: advance state only on clean complete run + confirmed write (F1/F3).
    if fetch_clean and write_ok:
        # F3: read watermark from storage, not from the adapter's returned list.
        updated_row = get_handle(handle, db_path=db_path)
        new_watermark = (updated_row or {}).get("tweets_watermark_utc")

        if new_status == "backfilling":
            # Two independent ways a backfill can be incomplete:
            # (A) Page cap fired before reaching the floor — adapter reports reached_floor=False.
            # (B) Adapter reported reached_floor=True (empty-page stop) but the earliest
            #     tweet stored is materially later than the floor — the index ran dry early.
            #     An empty page is ambiguous; coverage must be verified from what we stored.
            floor_date = start  # Jan 1 of current year
            earliest_raw = (updated_row or {}).get("earliest_tweet_utc")
            earliest_date: datetime.date | None = None
            if earliest_raw:
                try:
                    earliest_date = datetime.datetime.fromisoformat(
                        earliest_raw.replace("Z", "+00:00")
                    ).date()
                except ValueError:
                    pass

            # Allow a 7-day grace window: index may not have tweets right at Jan 1.
            coverage_gap = (
                earliest_date is not None
                and (earliest_date - floor_date).days > 7
            )
            backfill_incomplete = (not floor_reached) or coverage_gap

            if backfill_incomplete:
                reason = (
                    "page cap reached before backfill floor"
                    if not floor_reached
                    else f"index ran dry early: earliest={earliest_raw} floor={floor_date.isoformat()}"
                )
                upsert_handle(
                    handle,
                    {
                        "status": "incomplete",
                        "last_fetch_at": _iso(_now()),
                        "last_fetch_status": "incomplete",
                    },
                    db_path=db_path,
                )
                logger.warning(
                    "handle %s: backfill incomplete (%s); watermark unchanged at %s",
                    handle, reason, watermark_raw,
                )
                return RunResult(
                    handle=handle,
                    outcome="incomplete",
                    inserted=upsert_result.inserted if upsert_result else 0,
                    ignored=upsert_result.ignored if upsert_result else 0,
                    watermark=watermark_raw,  # unchanged — did not reach floor
                    reason=reason,
                )

        upsert_handle(
            handle,
            {"status": "ready", "last_fetch_at": _iso(_now()), "last_fetch_status": "ok"},
            db_path=db_path,
        )
        logger.info("handle %s: ready; watermark=%s", handle, new_watermark)
        return RunResult(
            handle=handle,
            outcome="ok",
            inserted=upsert_result.inserted if upsert_result else 0,
            ignored=upsert_result.ignored if upsert_result else 0,
            watermark=new_watermark,
        )

    # Failure path: watermark stays at its last-good value; this run did not advance it.
    upsert_handle(
        handle,
        {"status": "failed", "last_fetch_at": _iso(_now()), "last_fetch_status": "error"},
        db_path=db_path,
    )
    logger.warning("handle %s: failed — %s", handle, fetch_error)
    return RunResult(
        handle=handle,
        outcome="failed",
        inserted=upsert_result.inserted if upsert_result else 0,
        ignored=upsert_result.ignored if upsert_result else 0,
        watermark=watermark_raw,  # last-good value, unchanged
        error=fetch_error,
    )


def ingest_all(
    provider: str | None = None,
    db_path: Path | str | None = None,
) -> list[RunResult]:
    """
    Run ingest_handle for every handle that is ready/failed/pending.
    Handles that are in-progress and not stale are skipped.
    One handle's failure does NOT abort the batch.
    """
    init_db(db_path)
    results: list[RunResult] = []
    for row in list_handles(db_path=db_path):
        handle = row["handle"]
        if row.get("status") in _IN_PROGRESS_STATUSES and not is_stale(row):
            results.append(RunResult(handle=handle, outcome="skipped", reason="in progress"))
            continue
        try:
            results.append(ingest_handle(handle, provider=provider, db_path=db_path))
        except Exception as exc:
            logger.error("handle %s: unexpected error in ingest_all: %s", handle, exc)
            results.append(RunResult(handle=handle, outcome="failed", error=str(exc)))
    return results


def user_info_is_stale(handle_row: dict[str, Any]) -> bool:
    """True if user_info_last_fetched is None or older than 6 months."""
    last_raw = handle_row.get("user_info_last_fetched")
    if not last_raw:
        return True
    try:
        last = datetime.datetime.fromisoformat(last_raw.replace("Z", "+00:00"))
        if last.tzinfo is None:
            last = last.replace(tzinfo=_UTC)
        return (_now() - last).days > 182
    except ValueError:
        return True


def refresh_user_info(
    handle: str,
    provider: str | None = None,
    db_path: Path | str | None = None,
) -> UserInfo:
    """
    Fetch and persist profile info for a handle.
    Independent of tweet ingestion — different cadence.
    """
    init_db(db_path)
    prov = provider or cfg.TWEET_PROVIDER
    info: UserInfo = get_source(prov).fetch_user_info(handle)
    upsert_handle(
        handle,
        {
            "display_name": info.display_name,
            "user_id": info.user_id,
            "user_info_last_fetched": _iso(_now()),
        },
        db_path=db_path,
    )
    logger.info("handle %s: user_info refreshed (display_name=%s)", handle, info.display_name)
    return info
