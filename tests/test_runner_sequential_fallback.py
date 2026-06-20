"""Sequential ↔ pool equivalence (worker pool v1 spec §8 regression)."""

from __future__ import annotations

import datetime

from storage.db import get_connection
from orchestration.runner import run_days
from orchestration.worker_pool import PoolConfig

from tests.worker_pool_helpers import MockAdapter, source_factory


def _statuses(db) -> dict[tuple[str, str, str], str]:
    conn = get_connection(db)
    try:
        rows = conn.execute(
            "SELECT handle, date, provider, status FROM day_fetch_log"
        ).fetchall()
        return {(r["handle"], r["date"], r["provider"]): r["status"] for r in rows}
    finally:
        conn.close()


def _ids(provider: str, date: str, n: int) -> list[str]:
    return [f"{provider}-{date}-{i}" for i in range(n)]


def _build_sources():
    # 06-10: 100 vs 100 → ok.  06-11: 100 vs 50 → mismatch.  06-12: 0 vs 0 → ok.
    gx = MockAdapter(
        tweets_by_day={
            "2026-06-10": _ids("getxapi", "2026-06-10", 100),
            "2026-06-11": _ids("getxapi", "2026-06-11", 100),
            "2026-06-12": [],
        },
        reached_floor=True, provider="getxapi",
    )
    tw = MockAdapter(
        tweets_by_day={
            "2026-06-10": _ids("twitterapi", "2026-06-10", 100),
            "2026-06-11": _ids("twitterapi", "2026-06-11", 50),
            "2026-06-12": [],
        },
        reached_floor=True, provider="twitterapi",
    )
    return {"getxapi": gx, "twitterapi": tw}


def _pool_cfg() -> PoolConfig:
    return PoolConfig(
        pool_sizes={"getxapi": 2, "twitterapi": 2},
        rate_intervals_ms={"getxapi": 0, "twitterapi": 0},
        max_attempts=3, backoff_schedule_sec=[60, 300, 1800],
        stale_threshold_sec=600,
    )


def test_sequential_and_pool_produce_identical_results(tmp_path, monkeypatch):
    since = datetime.date(2026, 6, 10)
    until = datetime.date(2026, 6, 12)
    handles = ["accta"]

    # --- Sequential path (legacy loop). It resolves the provider through the
    #     factory, so patch the factory reference day_fetcher imported. ---
    seq_sources = _build_sources()
    monkeypatch.setattr(
        "orchestration.day_fetcher.get_source",
        source_factory(seq_sources),
    )
    db_seq = tmp_path / "seq.db"
    run_days(handles, since, until, sequential=True, db_path=db_seq)

    # --- Pool path. Inject the (fresh) mocks directly. ---
    pool_sources = _build_sources()
    db_pool = tmp_path / "pool.db"
    run_days(
        handles, since, until, db_path=db_pool,
        config=_pool_cfg(), get_source_fn=source_factory(pool_sources),
    )

    seq = _statuses(db_seq)
    pool = _statuses(db_pool)

    assert seq == pool, f"sequential={seq} pool={pool}"
    # Sanity: the fixture exercises both verdicts.
    assert ("accta", "2026-06-10", "getxapi") in seq
    assert seq[("accta", "2026-06-10", "getxapi")] == "ok"
    assert seq[("accta", "2026-06-11", "getxapi")] == "mismatch"
    assert seq[("accta", "2026-06-12", "getxapi")] == "ok"
