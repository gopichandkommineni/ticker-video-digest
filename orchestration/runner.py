"""Orchestration layer: decides fetch range, calls adapters, writes storage.

Entry points:
  ingest_handle(handle) -> RunResult   — backfill or delta for one handle
  ingest_all()          -> list[RunResult]

Architecture (v2 — day-queue):
  Both backfill and daily delta use day_fetcher, which slices the window into
  per-day requests fetched from both providers. Cross-provider count agreement
  replaces reached_floor as the completeness oracle. No watermark arithmetic.

Silent-failure rules:
  F1. Handle status advances to 'ready' only when day_fetcher reports all days ok.
  F2. Handles stuck in backfilling/fetching > STALE_THRESHOLD_MINUTES are stale.
  F4. A freshly in-progress handle returns RunResult(outcome="skipped").
"""

from __future__ import annotations

import datetime
import logging
from dataclasses import dataclass
from pathlib import Path
from . import config as cfg
from .day_fetcher import backfill_handle, delta_handle, DayFetchSummary, PROVIDERS
from .worker_pool import run_pool, PoolConfig, load_pool_config
from .reconciler import reconcile_completed_days
from storage.db import init_db, get_connection
from storage.day_log import day_summary, coverage_floor, reopen_mismatch_days
from storage.handles import get_handle, list_handles, normalize_handle, upsert_handle
from tweet_sources.base import UserInfo
from tweet_sources.factory import get_source  # used by refresh_user_info

logger = logging.getLogger(__name__)

_UTC = datetime.timezone.utc

_IN_PROGRESS_STATUSES = {"backfilling", "fetching"}


@dataclass
class RunResult:
    handle: str
    outcome: str          # "ok" | "incomplete" | "skipped" | "failed"
    reason: str = ""
    inserted: int = 0
    ignored: int = 0
    days_ok: int = 0
    days_mismatch: int = 0
    days_failed: int = 0
    coverage_floor: str | None = None
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



def ingest_handle(
    handle: str,
    provider: str | None = None,   # kept for API compat; day_fetcher always uses both
    db_path: Path | str | None = None,
    _backfill_since: datetime.date | None = None,  # test/override: skip Jan-1 default
    *,
    sequential: bool = False,
    config: PoolConfig | None = None,
) -> RunResult:
    """
    Fetch and store tweets for a single handle using the day-queue architecture.

    - No day_fetch_log entries → backfill from Jan 1 of the current year.
    - Has prior ok entries    → delta: last 3 days + retry any outstanding mismatch/failed.
    - A handle already in-progress and not stale is skipped (F4).

    Fetch mechanism (PR B): the default routes the day window through the worker
    pool (run_pool scoped to this handle, then reconcile). ``sequential=True``
    falls back to the legacy day_fetcher loop (delta_handle/backfill_handle),
    kept intact for debugging and one-commit rollback. Both write the same
    tables, so Step 6 (status/RunResult) is identical either way.
    """
    handle = normalize_handle(handle)
    init_db(db_path)

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

    now = _now()
    now_iso = _iso(now)

    # Step 3: decide backfill vs delta by checking whether any ok days exist.
    log_counts = day_summary(handle, db_path=db_path)
    has_prior_ok = log_counts.get("ok", 0) > 0

    if has_prior_ok:
        new_status = "fetching"
        logger.info("handle %s: delta run (last 3 days + retry outstanding)", handle)
    else:
        new_status = "backfilling"
        floor = _backfill_since or datetime.date(now.year, 1, 1)
        logger.info("handle %s: backfill from %s → %s", handle, floor, now.date())

    # Step 4: mark in-progress (F2 stale detection).
    upsert_handle(
        handle,
        {"status": new_status, "status_since": now_iso, "last_fetch_at": now_iso},
        db_path=db_path,
    )

    # Step 5: fetch the day window — via the worker pool (default) or the legacy
    # sequential loop (fallback). summary is a DayFetchSummary only in sequential
    # mode; the pool path derives RunResult.days_* from the ledger in Step 6.
    summary: DayFetchSummary | None = None
    try:
        if sequential:
            if has_prior_ok:
                summary = delta_handle(handle, overlap_days=3, db_path=db_path)
            else:
                summary = backfill_handle(handle, floor, now.date(), db_path=db_path)
        else:
            pool_config = config or load_pool_config()
            if has_prior_ok:
                # Delta: last 3 days, plus re-open outstanding mismatch days so the
                # pool re-dispatches them (failed days are already pool-eligible).
                since = now.date() - datetime.timedelta(days=2)
                until = now.date()
                conn = get_connection(db_path)
                try:
                    reopen_mismatch_days(conn, handle, pool_config.max_attempts)
                finally:
                    conn.close()
            else:
                since, until = floor, now.date()

            run_pool(
                [handle], (since, until), config=pool_config, db_path=db_path,
                handles_filter=[handle],
            )

            conn = get_connection(db_path)
            try:
                reconcile_completed_days(conn)
            finally:
                conn.close()
    except Exception as exc:
        logger.error("handle %s: fetch raised unexpectedly: %s", handle, exc)
        upsert_handle(
            handle,
            {"status": "failed", "last_fetch_at": _iso(_now()), "last_fetch_status": "error"},
            db_path=db_path,
        )
        return RunResult(handle=handle, outcome="failed", error=str(exc))

    # Step 6: determine final status from the day log.
    floor_date = coverage_floor(handle, db_path=db_path)
    final_counts = day_summary(handle, db_path=db_path)
    outstanding = final_counts.get("mismatch", 0) + final_counts.get("failed", 0)

    if outstanding > 0:
        outcome = "incomplete"
        reason = (
            f"{final_counts.get('mismatch', 0)} mismatch + "
            f"{final_counts.get('failed', 0)} failed day-slots remain"
        )
        upsert_handle(
            handle,
            {"status": "incomplete", "last_fetch_at": _iso(_now()), "last_fetch_status": "incomplete"},
            db_path=db_path,
        )
        logger.warning("handle %s: incomplete — %s", handle, reason)
    else:
        outcome = "ok"
        reason = ""
        upsert_handle(
            handle,
            {"status": "ready", "last_fetch_at": _iso(_now()), "last_fetch_status": "ok"},
            db_path=db_path,
        )
        logger.info("handle %s: ready; coverage_floor=%s", handle, floor_date)

    # days_* counts: sequential reports this-run's loop counts; the pool path has
    # no per-run summary, so it reports the handle's ledger counts (plan §4 — the
    # outcome and handle-status above are identical either way, derived from the
    # ledger).
    if summary is not None:
        days_ok, days_mismatch, days_failed = summary.ok, summary.mismatch, summary.failed
    else:
        days_ok = final_counts.get("ok", 0)
        days_mismatch = final_counts.get("mismatch", 0)
        days_failed = final_counts.get("failed", 0)

    return RunResult(
        handle=handle,
        outcome=outcome,
        reason=reason,
        days_ok=days_ok,
        days_mismatch=days_mismatch,
        days_failed=days_failed,
        coverage_floor=floor_date,
    )


def run_days(
    handles: list[str],
    since: datetime.date,
    until: datetime.date,
    *,
    sequential: bool = False,
    db_path: Path | str | None = None,
    config: PoolConfig | None = None,
    get_source_fn=None,
) -> dict:
    """Backfill *handles* over [since, until] (worker pool v1 spec §5.2).

    Default: dispatch to the worker pool, then run cross-provider
    reconciliation. ``sequential=True`` falls back to the legacy per-handle
    day loop (kept for debugging) — the same behavior as before the pool.

    Returns a summary dict combining the pool's per-status counts with the
    reconciliation verdict (or, in sequential mode, the aggregated
    DayFetchSummary).
    """
    init_db(db_path)

    if sequential:
        agg = {"ok": 0, "mismatch": 0, "failed": 0, "tweets_inserted": 0}
        for handle in handles:
            summary = backfill_handle(handle, since, until, db_path=db_path)
            agg["ok"] += summary.ok
            agg["mismatch"] += summary.mismatch
            agg["failed"] += summary.failed
            agg["tweets_inserted"] += summary.tweets_inserted
        return {"mode": "sequential", **agg}

    pool_kwargs = {}
    if get_source_fn is not None:
        pool_kwargs["get_source_fn"] = get_source_fn
    pool_summary = run_pool(
        handles, (since, until), config=config, db_path=db_path, **pool_kwargs
    )

    conn = get_connection(db_path)
    try:
        recon = reconcile_completed_days(conn)
    finally:
        conn.close()

    return {"mode": "pool", "pool": pool_summary, "reconcile": recon}


def ingest_all(
    provider: str | None = None,
    db_path: Path | str | None = None,
    _backfill_since: datetime.date | None = None,
    *,
    sequential: bool = False,
    config: PoolConfig | None = None,
) -> list[RunResult]:
    """
    Run ingest_handle for every handle that is ready/failed/pending.
    Handles that are in-progress and not stale are skipped.
    One handle's failure does NOT abort the batch.

    Stays a loop of per-handle (pool-scoped) ingest_handle calls — preserving
    per-handle RunResult attribution and the F4 skip. ``sequential`` is threaded
    through for the debug/rollback fallback (plan §2c).
    """
    init_db(db_path)
    results: list[RunResult] = []
    for row in list_handles(db_path=db_path):
        handle = row["handle"]
        if row.get("status") in _IN_PROGRESS_STATUSES and not is_stale(row):
            results.append(RunResult(handle=handle, outcome="skipped", reason="in progress"))
            continue
        try:
            results.append(ingest_handle(
                handle, provider=provider, db_path=db_path,
                _backfill_since=_backfill_since,
                sequential=sequential, config=config,
            ))
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
