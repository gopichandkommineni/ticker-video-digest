"""Pool dispatch behavior: size limits and per-provider isolation (spec §8)."""

from __future__ import annotations

import datetime

from fintwit.orchestration.worker_pool import run_pool, PoolConfig

from tests.worker_pool_helpers import (
    fresh_db, MockAdapter, ConcurrencyTracker, source_factory,
)


def _days(provider: str, since: datetime.date, n: int) -> dict[str, list[str]]:
    out = {}
    for i in range(n):
        d = (since + datetime.timedelta(days=i)).isoformat()
        out[d] = [f"{provider}-{d}-{j}" for j in range(3)]
    return out


def test_pool_respects_size_limits(tmp_path):
    """With pool size 3, never more than 3 concurrent in-flight fetches."""
    db = fresh_db(tmp_path)
    since = datetime.date(2026, 6, 1)
    until = datetime.date(2026, 6, 14)  # 14 days → plenty of jobs to saturate
    tracker = ConcurrencyTracker()
    src = MockAdapter(
        tweets_by_day=_days("getxapi", since, 14),
        reached_floor=True, provider="getxapi",
        tracker=tracker, delay=0.02,
    )
    cfg = PoolConfig(
        pool_sizes={"getxapi": 3}, rate_intervals_ms={"getxapi": 0},
        max_attempts=3, backoff_schedule_sec=[60, 300, 1800], stale_threshold_sec=600,
    )
    summary = run_pool(
        ["accta"], (since, until), config=cfg, db_path=db,
        get_source_fn=source_factory({"getxapi": src}),
    )
    assert tracker.max_seen <= 3
    assert tracker.max_seen >= 2  # actually used the pool, not serialized
    assert summary["by_status"]["complete"] == 14


def test_per_provider_isolation(tmp_path):
    """A slow provider does not block the other provider's workers."""
    db = fresh_db(tmp_path)
    since = datetime.date(2026, 6, 1)
    until = datetime.date(2026, 6, 6)  # 6 days each

    gx_tracker = ConcurrencyTracker()
    tw_tracker = ConcurrencyTracker()
    # getxapi is slow; twitterapi is fast. Both should run concurrently.
    gx = MockAdapter(tweets_by_day=_days("getxapi", since, 6), reached_floor=True,
                     provider="getxapi", tracker=gx_tracker, delay=0.05)
    tw = MockAdapter(tweets_by_day=_days("twitterapi", since, 6), reached_floor=True,
                     provider="twitterapi", tracker=tw_tracker, delay=0.0)
    cfg = PoolConfig(
        pool_sizes={"getxapi": 2, "twitterapi": 3},
        rate_intervals_ms={"getxapi": 0, "twitterapi": 0},
        max_attempts=3, backoff_schedule_sec=[60, 300, 1800], stale_threshold_sec=600,
    )
    summary = run_pool(
        ["accta"], (since, until), config=cfg, db_path=db,
        get_source_fn=source_factory({"getxapi": gx, "twitterapi": tw}),
    )
    assert gx_tracker.max_seen <= 2
    assert tw_tracker.max_seen <= 3
    assert summary["by_status"]["complete"] == 12  # 6 days × 2 providers
    assert summary["error_class"] == {}


def test_pool_marks_complete_and_exhausted_by_reached_floor(tmp_path):
    db = fresh_db(tmp_path)
    since = datetime.date(2026, 6, 1)
    until = datetime.date(2026, 6, 3)
    gx = MockAdapter(tweets_by_day=_days("getxapi", since, 3), reached_floor=False,
                     provider="getxapi")
    cfg = PoolConfig(
        pool_sizes={"getxapi": 2}, rate_intervals_ms={"getxapi": 0},
        max_attempts=3, backoff_schedule_sec=[60, 300, 1800], stale_threshold_sec=600,
    )
    summary = run_pool(
        ["accta"], (since, until), config=cfg, db_path=db,
        get_source_fn=source_factory({"getxapi": gx}),
    )
    assert summary["by_status"]["exhausted"] == 3
    assert "complete" not in summary["by_status"]
