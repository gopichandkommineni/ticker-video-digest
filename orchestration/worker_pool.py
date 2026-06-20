"""Ingestion worker pool (worker pool v1 spec §3.3–§3.5).

The ledger (`day_fetch_log`) is the work queue — the transactional-outbox
pattern. `run_pool` populates pending rows, then dispatches eligible rows to
per-provider ThreadPoolExecutors. Each worker atomically claims a row, fetches
that single (handle, date) from one provider through a per-provider rate
limiter, writes tweets, and records the terminal single-provider outcome.
Cross-provider reconciliation is a separate post-pool step (see reconciler.py).

Schema-mapping and adapter notes live in storage/day_log.py and the spec
deviations section of the PR description.
"""

from __future__ import annotations

import concurrent.futures
import datetime
import logging
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from storage.db import get_connection, init_db
from storage.day_log import (
    Job,
    claim_day,
    get_eligible_jobs,
    mark_day_outcome,
    populate_pending_days,
)
from storage.tweets import upsert_tweets
from tweet_sources._http import use_rate_limiter
from tweet_sources.factory import get_source as _factory_get_source
from tweet_sources.base import (
    RateLimitExhausted,
    NetworkErrorExhausted,
    ServerError,
    AuthError,
    NotFoundError,
    PermanentProviderError,
    TransientProviderError,
)

from .rate_limiter import RateLimiter, from_interval_ms
from . import config as cfg
from .day_fetcher import _to_storage_rows  # shared Tweet→storage-dict mapping

logger = logging.getLogger(__name__)

_UTC = datetime.timezone.utc


def _iso_now() -> str:
    return datetime.datetime.now(tz=_UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _iso(dt: datetime.datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

@dataclass
class PoolConfig:
    pool_sizes: dict[str, int]
    rate_intervals_ms: dict[str, int]
    max_attempts: int
    # backoff_schedule_sec is the legacy single schedule (= rate-limit). The two
    # explicit schedules (PR A) default to it when not supplied, so existing
    # PoolConfig(...) callers keep working unchanged.
    backoff_schedule_sec: list[int]
    backoff_rate_limit_sec: list[int] | None = None
    backoff_transient_sec: list[int] | None = None
    stale_threshold_sec: int = 600
    dispatch_batch: int = 200

    def __post_init__(self) -> None:
        if self.backoff_rate_limit_sec is None:
            self.backoff_rate_limit_sec = list(self.backoff_schedule_sec)
        if self.backoff_transient_sec is None:
            self.backoff_transient_sec = list(self.backoff_schedule_sec)


def load_pool_config() -> PoolConfig:
    """Build a PoolConfig from orchestration/config.py defaults (spec §5.3, PR A)."""
    return PoolConfig(
        pool_sizes=dict(cfg.WORKER_POOL_SIZES),
        rate_intervals_ms=dict(cfg.RATE_LIMITER_INTERVALS_MS),
        max_attempts=cfg.MAX_ATTEMPTS,
        backoff_schedule_sec=list(cfg.BACKOFF_SCHEDULE_RATE_LIMIT_SEC),
        backoff_rate_limit_sec=list(cfg.BACKOFF_SCHEDULE_RATE_LIMIT_SEC),
        backoff_transient_sec=list(cfg.BACKOFF_SCHEDULE_TRANSIENT_SEC),
        stale_threshold_sec=cfg.STALE_FETCHING_THRESHOLD_SEC,
    )


# ---------------------------------------------------------------------------
# Per-job worker
# ---------------------------------------------------------------------------

@dataclass
class JobOutcome:
    key: tuple[str, str, str]
    status: str                     # complete | exhausted | failed | lost
    error_class: str | None = None
    tweets_fetched: int = 0
    tweets_written: int = 0


def _commit_partials(partial_tweets, db_path) -> None:
    """Idempotently commit any tweets that landed before the error (PR A).

    For adapter-raised errors this is empty (Option A: the adapter discards
    in-flight pages and the worker re-runs the window; INSERT OR IGNORE dedupes).
    Kept as a seam so a caller that *does* have partials can persist them.
    """
    if partial_tweets:
        upsert_tweets(partial_tweets, db_path=db_path)


def _mark_transient_failure(
    conn,
    job: Job,
    provider: str,
    attempts: int,
    config: PoolConfig,
    now: str,
    *,
    error_class: str,
    backoff_schedule: list[int],
    error_detail: str,
    db_path=None,
    partial_tweets=None,
) -> JobOutcome:
    """Mark a retryable failure: failed + next_eligible_at, unless attempts are
    exhausted (then terminal failed with no next_eligible_at)."""
    key = (job.handle, job.date, provider)
    _commit_partials(partial_tweets, db_path)

    if attempts >= config.max_attempts:
        next_eligible = None  # terminal (spec §3.5)
    else:
        idx = min(attempts - 1, len(backoff_schedule) - 1)
        dt = datetime.datetime.strptime(now, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=_UTC)
        next_eligible = _iso(dt + datetime.timedelta(seconds=backoff_schedule[idx]))

    mark_day_outcome(
        conn, job.handle, job.date, provider, "failed",
        reached_floor=None, error_class=error_class,
        tweets_fetched=None, tweets_written=None, next_eligible_at=next_eligible,
        error=error_detail, now=now,
    )
    logger.warning("[%s] %s %s — %s (attempt %d/%d); next_eligible_at=%s",
                   provider, job.handle, job.date, error_class,
                   attempts, config.max_attempts, next_eligible)
    return JobOutcome(key, "failed", error_class)


def _mark_permanent_failure(
    conn,
    job: Job,
    provider: str,
    config: PoolConfig,
    now: str,
    *,
    error_class: str,
    error_detail: str,
) -> JobOutcome:
    """Mark a permanent failure: failed with attempts forced to the cap so the
    dispatch query never re-claims it; no next_eligible_at."""
    key = (job.handle, job.date, provider)
    mark_day_outcome(
        conn, job.handle, job.date, provider, "failed",
        reached_floor=None, error_class=error_class,
        tweets_fetched=None, tweets_written=None, next_eligible_at=None,
        attempts=config.max_attempts, error=error_detail, now=now,
    )
    logger.warning("[%s] %s %s — permanent error (%s); no retry",
                   provider, job.handle, job.date, error_class)
    return JobOutcome(key, "failed", error_class)


def process_job(
    job: Job,
    provider: str,
    *,
    db_path: Path | str | None,
    config: PoolConfig,
    limiter: RateLimiter | None = None,
    get_source_fn: Callable[[str], object] = _factory_get_source,
    now: str | None = None,
) -> JobOutcome:
    """Claim, fetch, store, and record the outcome for one (handle, date, provider).

    Protocol (spec §3.5): claim_day → adapter.fetch_tweets → upsert_tweets →
    mark_day_outcome. On a lost claim, returns immediately. On exception the
    outcome is failed with the mapped error_class and backoff (or terminal).
    Uses its own connection — one per call — so it is thread-safe.
    """
    now = now or _iso_now()
    key = (job.handle, job.date, provider)
    conn = get_connection(db_path)
    try:
        claimed = claim_day(
            conn, job.handle, job.date, provider, config.max_attempts,
            now=now, stale_threshold_sec=config.stale_threshold_sec,
        )
        if not claimed:
            return JobOutcome(key, "lost")

        attempts = job.attempts + 1  # claim incremented retry_count
        day = datetime.date.fromisoformat(job.date)
        src = get_source_fn(provider)

        # Adapter errors propagate here (PR A). Dispatch on type: transient →
        # failed + backoff; permanent → failed, no retry. Order matters — each
        # specific subclass precedes its base in the MRO. partial_tweets is empty
        # because the adapter discards in-flight pages on error (Option A); the
        # re-run re-fetches and INSERT OR IGNORE dedupes.
        try:
            with use_rate_limiter(limiter):
                result = src.fetch_tweets(job.handle, day, day)
            rows = _to_storage_rows(result.tweets, job.handle, provider)
            written = upsert_tweets(rows, db_path=db_path).inserted if rows else 0
        except RateLimitExhausted as exc:
            return _mark_transient_failure(
                conn, job, provider, attempts, config, now,
                error_class="rate_limit",
                backoff_schedule=config.backoff_rate_limit_sec,
                error_detail=str(exc), db_path=db_path, partial_tweets=[],
            )
        except NetworkErrorExhausted as exc:
            return _mark_transient_failure(
                conn, job, provider, attempts, config, now,
                error_class="network",
                backoff_schedule=config.backoff_transient_sec,
                error_detail=str(exc), db_path=db_path, partial_tweets=[],
            )
        except ServerError as exc:
            return _mark_transient_failure(
                conn, job, provider, attempts, config, now,
                error_class="server",
                backoff_schedule=config.backoff_transient_sec,
                error_detail=str(exc), db_path=db_path, partial_tweets=[],
            )
        except AuthError as exc:
            return _mark_permanent_failure(
                conn, job, provider, config, now,
                error_class="auth", error_detail=str(exc),
            )
        except NotFoundError as exc:
            return _mark_permanent_failure(
                conn, job, provider, config, now,
                error_class="not_found", error_detail=str(exc),
            )
        except PermanentProviderError as exc:
            return _mark_permanent_failure(
                conn, job, provider, config, now,
                error_class="permanent", error_detail=str(exc),
            )
        except TransientProviderError as exc:
            # Catch-all for any future transient type not handled above.
            return _mark_transient_failure(
                conn, job, provider, attempts, config, now,
                error_class="transient_unknown",
                backoff_schedule=config.backoff_transient_sec,
                error_detail=str(exc), db_path=db_path, partial_tweets=[],
            )
        except Exception as exc:  # noqa: BLE001 — truly unexpected; retry once
            return _mark_transient_failure(
                conn, job, provider, attempts, config, now,
                error_class="unknown",
                backoff_schedule=config.backoff_transient_sec,
                error_detail=str(exc), db_path=db_path, partial_tweets=[],
            )

        fetched = len(result.tweets)
        status = "complete" if result.reached_floor else "exhausted"
        mark_day_outcome(
            conn, job.handle, job.date, provider, status,
            reached_floor=result.reached_floor, error_class=None,
            tweets_fetched=fetched, tweets_written=written,
            next_eligible_at=None, now=now,
        )
        logger.debug("[%s] %s %s — %s (fetched=%d written=%d)",
                     provider, job.handle, job.date, status, fetched, written)
        return JobOutcome(key, status, None, fetched, written)
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Pool dispatcher
# ---------------------------------------------------------------------------

@dataclass
class PoolSummary:
    jobs_processed: int = 0
    by_status: Counter = field(default_factory=Counter)
    error_class: Counter = field(default_factory=Counter)
    tweets_fetched: int = 0
    tweets_written: int = 0

    def as_dict(self) -> dict:
        return {
            "jobs_processed": self.jobs_processed,
            "by_status": dict(self.by_status),
            "error_class": dict(self.error_class),
            "tweets_fetched": self.tweets_fetched,
            "tweets_written": self.tweets_written,
        }


def run_pool(
    handles: list[str],
    date_range: tuple[datetime.date, datetime.date],
    config: PoolConfig | None = None,
    db_path: Path | str | None = None,
    *,
    get_source_fn: Callable[[str], object] = _factory_get_source,
) -> dict:
    """Backfill *handles* over *date_range* through the per-provider worker pool.

    1. populate_pending_days for every handle (spec §3.1).
    2. Spin up one ThreadPoolExecutor and one RateLimiter per provider.
    3. Dispatch loop: poll the ledger for eligible rows (deduping in-flight
       keys), submit each to its provider's executor, and drain completions
       until no eligible row and no in-flight work remain.

    Rows left in backoff (failed with a future next_eligible_at) are NOT waited
    on — they are picked up by the next run (ledger-as-queue, spec §5.4).

    Returns a summary dict: jobs processed, by-status counts, error_class
    breakdown, and tweet totals.
    """
    config = config or load_pool_config()
    providers = tuple(config.pool_sizes.keys())
    since, until = date_range

    init_db(db_path)
    for handle in handles:
        populate_pending_days(handle, since, until, providers, db_path)

    executors = {
        p: concurrent.futures.ThreadPoolExecutor(
            max_workers=config.pool_sizes[p], thread_name_prefix=f"pool-{p}"
        )
        for p in providers
    }
    limiters = {p: from_interval_ms(config.rate_intervals_ms.get(p, 0)) for p in providers}

    summary = PoolSummary()
    in_flight: dict[concurrent.futures.Future, tuple[str, str, str]] = {}
    in_flight_keys: set[tuple[str, str, str]] = set()

    disp_conn = get_connection(db_path)
    try:
        while True:
            jobs = get_eligible_jobs(
                disp_conn, limit=config.dispatch_batch,
                max_attempts=config.max_attempts,
                stale_threshold_sec=config.stale_threshold_sec,
            )
            submitted_any = False
            for job in jobs:
                if job.provider not in executors:
                    continue
                key = (job.handle, job.date, job.provider)
                if key in in_flight_keys:
                    continue
                fut = executors[job.provider].submit(
                    process_job, job, job.provider,
                    db_path=db_path, config=config,
                    limiter=limiters[job.provider], get_source_fn=get_source_fn,
                )
                in_flight[fut] = key
                in_flight_keys.add(key)
                submitted_any = True

            if not in_flight:
                if submitted_any:
                    continue          # newly submitted; loop to drain
                break                 # nothing eligible, nothing running → done

            done, _ = concurrent.futures.wait(
                in_flight, return_when=concurrent.futures.FIRST_COMPLETED
            )
            for fut in done:
                key = in_flight.pop(fut)
                in_flight_keys.discard(key)
                try:
                    outcome: JobOutcome = fut.result()
                except Exception as exc:  # noqa: BLE001
                    logger.error("worker crashed on %s: %s", key, exc)
                    summary.jobs_processed += 1
                    summary.by_status["error"] += 1
                    continue
                if outcome.status == "lost":
                    # Claim lost (race / no longer eligible) — not counted as work.
                    continue
                summary.jobs_processed += 1
                summary.by_status[outcome.status] += 1
                if outcome.error_class:
                    summary.error_class[outcome.error_class] += 1
                summary.tweets_fetched += outcome.tweets_fetched
                summary.tweets_written += outcome.tweets_written
    finally:
        disp_conn.close()
        for ex in executors.values():
            ex.shutdown(wait=True)

    logger.info("run_pool done: %s", summary.as_dict())
    return summary.as_dict()
