"""Atomic claim concurrency tests (worker pool v1 spec §3.4, §8, §9).

These are the highest-value tests in the PR. They must not flake: each uses a
threading.Barrier to force genuine contention on the same write lock.
"""

from __future__ import annotations

import threading

from storage.db import get_connection
from storage.day_log import claim_day, get_eligible_jobs

from tests.worker_pool_helpers import (
    fresh_db, seed_pending, row, now_iso, shift_iso,
)


def _claim_in_thread(db, handle, date, provider, results, idx, barrier, now):
    conn = get_connection(db)
    try:
        barrier.wait()  # release all threads simultaneously
        results[idx] = claim_day(conn, handle, date, provider, max_attempts=3, now=now)
    finally:
        conn.close()


def test_single_row_claim_is_exclusive(tmp_path):
    db = fresh_db(tmp_path)
    seed_pending(db, "acct", "2026-06-10", "getxapi")

    n = 10
    results: list[bool | None] = [None] * n
    barrier = threading.Barrier(n)
    now = now_iso()
    threads = [
        threading.Thread(
            target=_claim_in_thread,
            args=(db, "acct", "2026-06-10", "getxapi", results, i, barrier, now),
        )
        for i in range(n)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert sum(1 for r in results if r is True) == 1
    assert sum(1 for r in results if r is False) == n - 1
    # The winning claim left exactly one attempt recorded.
    assert row(db, "acct", "2026-06-10", "getxapi")["retry_count"] == 1
    assert row(db, "acct", "2026-06-10", "getxapi")["status"] == "fetching"


def test_different_rows_claimed_in_parallel(tmp_path):
    db = fresh_db(tmp_path)
    n = 10
    dates = [f"2026-06-{10 + i:02d}" for i in range(n)]
    for d in dates:
        seed_pending(db, "acct", d, "getxapi")

    results: list[bool | None] = [None] * n
    barrier = threading.Barrier(n)
    now = now_iso()
    threads = [
        threading.Thread(
            target=_claim_in_thread,
            args=(db, "acct", dates[i], "getxapi", results, i, barrier, now),
        )
        for i in range(n)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert all(r is True for r in results)
    conn = get_connection(db)
    try:
        pending = conn.execute(
            "SELECT COUNT(*) FROM day_fetch_log WHERE status='pending'"
        ).fetchone()[0]
        fetching = conn.execute(
            "SELECT COUNT(*) FROM day_fetch_log WHERE status='fetching'"
        ).fetchone()[0]
    finally:
        conn.close()
    assert pending == 0
    assert fetching == n


def test_stale_fetching_row_reclaimed(tmp_path):
    """A 'fetching' row older than the stale threshold is reclaimable (§9)."""
    db = fresh_db(tmp_path)
    now = now_iso()
    conn = get_connection(db)
    try:
        # One stale fetching row (last activity 20 min ago) and one fresh one.
        with conn:
            conn.execute(
                "INSERT INTO day_fetch_log (handle, date, provider, status, retry_count, fetched_at) "
                "VALUES ('acct', '2026-06-10', 'getxapi', 'fetching', 1, ?)",
                (shift_iso(now, -20 * 60),),
            )
            conn.execute(
                "INSERT INTO day_fetch_log (handle, date, provider, status, retry_count, fetched_at) "
                "VALUES ('acct', '2026-06-11', 'getxapi', 'fetching', 1, ?)",
                (shift_iso(now, -60),),  # 1 min ago — not stale
            )
    finally:
        conn.close()

    conn = get_connection(db)
    try:
        # 10-min stale threshold (spec default).
        reclaimed = claim_day(conn, "acct", "2026-06-10", "getxapi", max_attempts=3,
                              now=now, stale_threshold_sec=600)
        fresh = claim_day(conn, "acct", "2026-06-11", "getxapi", max_attempts=3,
                          now=now, stale_threshold_sec=600)
    finally:
        conn.close()

    assert reclaimed is True
    assert fresh is False
    # Reclaim incremented attempts on the stale row.
    assert row(db, "acct", "2026-06-10", "getxapi")["retry_count"] == 2

    # And the dispatch query agrees: only the stale row is eligible.
    conn = get_connection(db)
    try:
        # Re-seed a stale fetching row to test get_eligible_jobs independently.
        with conn:
            conn.execute(
                "UPDATE day_fetch_log SET status='fetching', fetched_at=? "
                "WHERE date='2026-06-10'",
                (shift_iso(now, -20 * 60),),
            )
        jobs = get_eligible_jobs(conn, limit=10, now=now, stale_threshold_sec=600)
    finally:
        conn.close()
    eligible_dates = {j.date for j in jobs}
    assert "2026-06-10" in eligible_dates
    assert "2026-06-11" not in eligible_dates
