"""Single-provider outcome tests (worker pool v1 spec §3.5, §8)."""

from __future__ import annotations

from storage.db import get_connection
from storage.day_log import Job
from orchestration.worker_pool import process_job, PoolConfig

from tests.worker_pool_helpers import (
    fresh_db, seed_pending, row, now_iso,
    MockAdapter, source_factory, make_tweet_dicts,
    rate_limit_exc, permanent_exc,
)
from storage.tweets import upsert_tweets


def _cfg() -> PoolConfig:
    return PoolConfig(
        pool_sizes={"getxapi": 1}, rate_intervals_ms={"getxapi": 0},
        max_attempts=3, backoff_schedule_sec=[60, 300, 1800],
        stale_threshold_sec=600,
    )


def _run(db, src, *, attempts=0, now=None):
    job = Job("acct", "2026-06-10", "getxapi", "pending", attempts=attempts)
    return process_job(
        job, "getxapi", db_path=db, config=_cfg(),
        get_source_fn=source_factory({"getxapi": src}), now=now or now_iso(),
    )


def test_reached_floor_true_sets_complete(tmp_path):
    db = fresh_db(tmp_path)
    seed_pending(db, "acct", "2026-06-10", "getxapi")
    src = MockAdapter(tweets_by_day={"2026-06-10": ["1", "2", "3"]},
                      reached_floor=True, provider="getxapi")
    outcome = _run(db, src)
    assert outcome.status == "complete"
    r = row(db, "acct", "2026-06-10", "getxapi")
    assert r["status"] == "complete"
    assert r["reached_floor"] == 1
    assert r["error_class"] is None
    assert r["tweets_fetched"] == 3
    assert r["tweets_written"] == 3


def test_reached_floor_false_sets_exhausted(tmp_path):
    db = fresh_db(tmp_path)
    seed_pending(db, "acct", "2026-06-10", "getxapi")
    src = MockAdapter(tweets_by_day={"2026-06-10": ["1", "2"]},
                      reached_floor=False, provider="getxapi")
    outcome = _run(db, src)
    assert outcome.status == "exhausted"
    r = row(db, "acct", "2026-06-10", "getxapi")
    assert r["status"] == "exhausted"
    assert r["reached_floor"] == 0
    assert r["error_class"] is None


def test_rate_limit_marks_failed_with_backoff(tmp_path):
    """B7 fix: a 429 is failed+backoff, never ok/complete."""
    db = fresh_db(tmp_path)
    seed_pending(db, "acct", "2026-06-10", "getxapi")
    now = now_iso()
    src = MockAdapter(raise_exc=rate_limit_exc(), provider="getxapi")
    outcome = _run(db, src, now=now)
    assert outcome.status == "failed"
    assert outcome.error_class == "rate_limit"
    r = row(db, "acct", "2026-06-10", "getxapi")
    assert r["status"] == "failed"
    assert r["error_class"] == "rate_limit"
    # First attempt → 60s backoff.
    from tests.worker_pool_helpers import shift_iso
    assert r["next_eligible_at"] == shift_iso(now, 60)


def test_partial_tweets_commit_on_rate_limit(tmp_path):
    """Tweets that landed before a 429 stay committed; the row is still failed."""
    db = fresh_db(tmp_path)
    seed_pending(db, "acct", "2026-06-10", "getxapi")
    # Adapter writes 20 tweets, then raises 429.
    ids = [str(i) for i in range(20)]
    src = MockAdapter(raise_exc=rate_limit_exc(),
                      pre_upsert=("acct", ids), db_path=db, provider="getxapi")
    outcome = _run(db, src)
    assert outcome.status == "failed"
    assert outcome.error_class == "rate_limit"

    conn = get_connection(db)
    try:
        n = conn.execute(
            "SELECT COUNT(*) FROM raw_tweets WHERE account_handle='acct'"
        ).fetchone()[0]
    finally:
        conn.close()
    assert n == 20  # partial commit survived the failure


def test_permanent_error_skips_retries(tmp_path):
    db = fresh_db(tmp_path)
    seed_pending(db, "acct", "2026-06-10", "getxapi")
    src = MockAdapter(raise_exc=permanent_exc(), provider="getxapi")
    outcome = _run(db, src)
    assert outcome.status == "failed"
    assert outcome.error_class == "permanent"
    r = row(db, "acct", "2026-06-10", "getxapi")
    assert r["status"] == "failed"
    # attempts forced to the cap so dispatch never re-claims it.
    assert r["retry_count"] == _cfg().max_attempts
    assert r["next_eligible_at"] is None


def test_tweets_fetched_vs_written_diverge_on_dedupe(tmp_path):
    """50 fetched, 30 already present → fetched=50, written=20."""
    db = fresh_db(tmp_path)
    seed_pending(db, "acct", "2026-06-10", "getxapi")
    # Pre-seed 30 tweets (ids 0..29) so they dedupe on the next fetch.
    existing = [str(i) for i in range(30)]
    upsert_tweets(make_tweet_dicts("acct", existing, "getxapi"), db_path=db)

    # Adapter returns 50 tweets (ids 0..49): 30 dupes + 20 new.
    all_ids = [str(i) for i in range(50)]
    src = MockAdapter(tweets_by_day={"2026-06-10": all_ids},
                      reached_floor=True, provider="getxapi")
    outcome = _run(db, src)
    assert outcome.status == "complete"
    r = row(db, "acct", "2026-06-10", "getxapi")
    assert r["tweets_fetched"] == 50
    assert r["tweets_written"] == 20
