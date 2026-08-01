"""Cross-provider reconciliation tests (worker pool v1 spec §3.6, §8)."""

from __future__ import annotations

from fintwit.storage.db import get_connection
from fintwit.storage.day_log import mark_day_outcome
from fintwit.orchestration.reconciler import reconcile_completed_days

from tests.worker_pool_helpers import fresh_db, seed_pending, row


def _terminal(db, handle, date, provider, status, fetched):
    """Put a single-provider terminal row in place via mark_day_outcome."""
    seed_pending(db, handle, date, provider)
    conn = get_connection(db)
    try:
        mark_day_outcome(
            conn, handle, date, provider, status,
            reached_floor=(status == "complete"), error_class=None,
            tweets_fetched=fetched, tweets_written=fetched, next_eligible_at=None,
        )
    finally:
        conn.close()


def test_both_complete_agree_marks_ok(tmp_path):
    db = fresh_db(tmp_path)
    _terminal(db, "acct", "2026-06-10", "getxapi", "complete", 100)
    _terminal(db, "acct", "2026-06-10", "twitterapi", "complete", 100)

    summary = reconcile_completed_days(get_connection(db))
    assert summary["ok"] == 1
    assert summary["mismatch"] == 0
    assert row(db, "acct", "2026-06-10", "getxapi")["status"] == "ok"
    assert row(db, "acct", "2026-06-10", "twitterapi")["status"] == "ok"


def test_both_complete_disagree_marks_mismatch(tmp_path):
    db = fresh_db(tmp_path)
    # 100 vs 50 → 50% diff, well above the 10% threshold.
    _terminal(db, "acct", "2026-06-10", "getxapi", "complete", 100)
    _terminal(db, "acct", "2026-06-10", "twitterapi", "exhausted", 50)

    summary = reconcile_completed_days(get_connection(db))
    assert summary["mismatch"] == 1
    assert row(db, "acct", "2026-06-10", "getxapi")["status"] == "mismatch"
    assert row(db, "acct", "2026-06-10", "twitterapi")["status"] == "mismatch"


def test_one_failed_skips_reconciliation(tmp_path):
    db = fresh_db(tmp_path)
    _terminal(db, "acct", "2026-06-10", "getxapi", "complete", 100)
    # twitterapi failed — not terminal for reconciliation.
    seed_pending(db, "acct", "2026-06-10", "twitterapi")
    conn = get_connection(db)
    try:
        mark_day_outcome(
            conn, "acct", "2026-06-10", "twitterapi", "failed",
            reached_floor=None, error_class="rate_limit",
            tweets_fetched=None, tweets_written=None, next_eligible_at=None,
        )
    finally:
        conn.close()

    summary = reconcile_completed_days(get_connection(db))
    assert summary["ok"] == 0
    assert summary["mismatch"] == 0
    assert summary["skipped"] == 1
    # The complete row is left untouched (failed retries first).
    assert row(db, "acct", "2026-06-10", "getxapi")["status"] == "complete"
    assert row(db, "acct", "2026-06-10", "twitterapi")["status"] == "failed"


def test_reconcile_is_idempotent(tmp_path):
    db = fresh_db(tmp_path)
    _terminal(db, "acct", "2026-06-10", "getxapi", "complete", 100)
    _terminal(db, "acct", "2026-06-10", "twitterapi", "complete", 100)

    first = reconcile_completed_days(get_connection(db))
    second = reconcile_completed_days(get_connection(db))
    assert first["ok"] == 1
    # Second pass: rows are already 'ok' (not terminal) → nothing to do.
    assert second["ok"] == 0
    assert row(db, "acct", "2026-06-10", "getxapi")["status"] == "ok"


# --- Single-provider mode (backfill=twitterapi / delta=getxapi split) --------


def test_single_provider_lone_terminal_marks_ok(tmp_path):
    """With a one-provider config, a lone terminal day reconciles to 'ok'."""
    db = fresh_db(tmp_path)
    _terminal(db, "acct", "2026-06-10", "twitterapi", "complete", 42)

    summary = reconcile_completed_days(
        get_connection(db), providers=("twitterapi",)
    )
    assert summary["ok"] == 1
    assert summary["mismatch"] == 0
    assert row(db, "acct", "2026-06-10", "twitterapi")["status"] == "ok"


def test_single_provider_zero_tweet_day_marks_ok(tmp_path):
    """An empty (0-tweet) single-provider day still reaches 'ok'."""
    db = fresh_db(tmp_path)
    _terminal(db, "acct", "2026-06-10", "getxapi", "complete", 0)

    summary = reconcile_completed_days(get_connection(db), providers=("getxapi",))
    assert summary["ok"] == 1
    assert row(db, "acct", "2026-06-10", "getxapi")["status"] == "ok"


def test_single_provider_non_terminal_skipped(tmp_path):
    """A failed/pending row for the configured provider is not reconciled."""
    db = fresh_db(tmp_path)
    seed_pending(db, "acct", "2026-06-10", "twitterapi")
    conn = get_connection(db)
    try:
        mark_day_outcome(
            conn, "acct", "2026-06-10", "twitterapi", "failed",
            reached_floor=None, error_class="rate_limit",
            tweets_fetched=None, tweets_written=None, next_eligible_at=None,
        )
    finally:
        conn.close()

    summary = reconcile_completed_days(
        get_connection(db), providers=("twitterapi",)
    )
    assert summary["ok"] == 0
    assert summary["skipped"] == 1
    assert row(db, "acct", "2026-06-10", "twitterapi")["status"] == "failed"


def test_configured_providers_wait_for_all(tmp_path):
    """With a 2-provider config, a day is not reconciled until BOTH are terminal
    — even though the group transiently holds a single terminal row."""
    db = fresh_db(tmp_path)
    _terminal(db, "acct", "2026-06-10", "getxapi", "complete", 100)
    # twitterapi hasn't reported yet (still pending).
    seed_pending(db, "acct", "2026-06-10", "twitterapi")

    summary = reconcile_completed_days(
        get_connection(db), providers=("getxapi", "twitterapi")
    )
    assert summary["ok"] == 0
    assert summary["skipped"] == 1
    assert row(db, "acct", "2026-06-10", "getxapi")["status"] == "complete"
