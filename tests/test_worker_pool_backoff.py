"""Backoff serialization and max-attempts tests (worker pool v1 spec §3.5, §8)."""

from __future__ import annotations

from fintwit.storage.db import get_connection
from fintwit.storage.day_log import get_eligible_jobs, Job
from fintwit.orchestration.worker_pool import process_job, PoolConfig

from tests.worker_pool_helpers import (
    fresh_db, seed_pending, row, now_iso, shift_iso,
    MockAdapter, source_factory, rate_limit_exc,
)


def _cfg(**kw) -> PoolConfig:
    base = dict(
        pool_sizes={"getxapi": 1}, rate_intervals_ms={"getxapi": 0},
        max_attempts=3, backoff_schedule_sec=[60, 300, 1800],
        stale_threshold_sec=600,
    )
    base.update(kw)
    return PoolConfig(**base)


def test_backoff_serialization(tmp_path):
    """A failed row with next_eligible_at in the future is not dispatched until time passes."""
    db = fresh_db(tmp_path)
    seed_pending(db, "acct", "2026-06-10", "getxapi")
    now = now_iso()

    # One worker fails the row with a 429 → failed, next_eligible_at = now + 60s.
    src = MockAdapter(raise_exc=rate_limit_exc(), provider="getxapi")
    job = Job("acct", "2026-06-10", "getxapi", "pending", attempts=0)
    outcome = process_job(
        job, "getxapi", db_path=db, config=_cfg(),
        get_source_fn=source_factory({"getxapi": src}), now=now,
    )
    assert outcome.status == "failed"
    r = row(db, "acct", "2026-06-10", "getxapi")
    assert r["status"] == "failed"
    assert r["next_eligible_at"] == shift_iso(now, 60)

    # Immediately after, the dispatch query does not return it (backoff not elapsed).
    conn = get_connection(db)
    try:
        jobs_now = get_eligible_jobs(conn, limit=10, now=now)
        jobs_before = get_eligible_jobs(conn, limit=10, now=shift_iso(now, 59))
        jobs_after = get_eligible_jobs(conn, limit=10, now=shift_iso(now, 61))
    finally:
        conn.close()

    assert all(j.date != "2026-06-10" for j in jobs_now)
    assert all(j.date != "2026-06-10" for j in jobs_before)
    assert any(j.date == "2026-06-10" for j in jobs_after)


def test_max_attempts_exhausted(tmp_path):
    """After max_attempts failed claims the row stays failed and is never re-dispatched."""
    db = fresh_db(tmp_path)
    seed_pending(db, "acct", "2026-06-10", "getxapi")
    src = MockAdapter(raise_exc=rate_limit_exc(), provider="getxapi")
    cfg = _cfg()

    base = now_iso()
    for attempt in range(1, cfg.max_attempts + 1):
        # Advance well past any prior backoff so the row is eligible each round.
        now = shift_iso(base, attempt * 3600)
        # Re-read current attempts so the Job mirrors the ledger.
        prev = row(db, "acct", "2026-06-10", "getxapi")["retry_count"] or 0
        job = Job("acct", "2026-06-10", "getxapi", "failed", attempts=prev)
        outcome = process_job(
            job, "getxapi", db_path=db, config=cfg,
            get_source_fn=source_factory({"getxapi": src}), now=now,
        )
        assert outcome.status == "failed"

    r = row(db, "acct", "2026-06-10", "getxapi")
    assert r["status"] == "failed"
    assert r["retry_count"] == cfg.max_attempts
    # Terminal: no backoff set, and dispatch never returns it again.
    assert r["next_eligible_at"] is None
    conn = get_connection(db)
    try:
        jobs = get_eligible_jobs(conn, limit=10, now=shift_iso(base, 10 * 3600))
    finally:
        conn.close()
    assert all(j.date != "2026-06-10" for j in jobs)
