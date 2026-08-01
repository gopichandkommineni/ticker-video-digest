"""Tests for reopen_failed_days — unsticking days that maxed out their retry
budget on a provider-side outage (e.g. HTTP 402 when credits ran out)."""

from __future__ import annotations

import datetime

from fintwit.storage.db import get_connection
from fintwit.storage.day_log import mark_day_outcome, reopen_failed_days

from tests.worker_pool_helpers import fresh_db, seed_pending, row


def _exhausted_failure(db, handle, date, provider, *, attempts=3, error_class="permanent"):
    """Drive a day into the terminal-failed state a provider outage produces:
    status='failed', retry_count pinned at max, error/error_class set."""
    seed_pending(db, handle, date, provider)
    conn = get_connection(db)
    try:
        mark_day_outcome(
            conn, handle, date, provider, "failed",
            reached_floor=None, error_class=error_class,
            tweets_fetched=None, tweets_written=None,
            next_eligible_at="2026-07-01T00:00:00Z",
            attempts=attempts, error="HTTP 402 out of credits",
        )
    finally:
        conn.close()


def test_reopen_clears_terminal_failed_state(tmp_path):
    db = fresh_db(tmp_path)
    _exhausted_failure(db, "acct", "2026-06-10", "twitterapi")

    conn = get_connection(db)
    try:
        n = reopen_failed_days(conn, "acct")
    finally:
        conn.close()

    assert n == 1
    r = row(db, "acct", "2026-06-10", "twitterapi")
    assert r["status"] == "pending"
    assert r["retry_count"] == 0
    assert r["next_eligible_at"] is None
    assert r["error"] is None
    assert r["error_class"] is None


def test_reopen_scopes_to_window(tmp_path):
    db = fresh_db(tmp_path)
    _exhausted_failure(db, "acct", "2026-05-20", "twitterapi")  # before window
    _exhausted_failure(db, "acct", "2026-06-10", "twitterapi")  # inside window
    _exhausted_failure(db, "acct", "2026-07-20", "twitterapi")  # after window

    conn = get_connection(db)
    try:
        n = reopen_failed_days(
            conn, "acct",
            datetime.date(2026, 6, 1), datetime.date(2026, 6, 30),
        )
    finally:
        conn.close()

    assert n == 1
    assert row(db, "acct", "2026-05-20", "twitterapi")["status"] == "failed"
    assert row(db, "acct", "2026-06-10", "twitterapi")["status"] == "pending"
    assert row(db, "acct", "2026-07-20", "twitterapi")["status"] == "failed"


def test_reopen_scopes_to_provider(tmp_path):
    db = fresh_db(tmp_path)
    _exhausted_failure(db, "acct", "2026-06-10", "twitterapi")
    _exhausted_failure(db, "acct", "2026-06-10", "getxapi")

    conn = get_connection(db)
    try:
        n = reopen_failed_days(conn, "acct", providers=("twitterapi",))
    finally:
        conn.close()

    assert n == 1
    assert row(db, "acct", "2026-06-10", "twitterapi")["status"] == "pending"
    assert row(db, "acct", "2026-06-10", "getxapi")["status"] == "failed"


def test_reopen_ignores_non_failed_rows(tmp_path):
    db = fresh_db(tmp_path)
    # An 'ok' day and a pending day must be left alone — only 'failed' reopens.
    seed_pending(db, "acct", "2026-06-11", "twitterapi")  # pending
    seed_pending(db, "acct", "2026-06-12", "twitterapi")  # becomes 'ok' below
    conn = get_connection(db)
    try:
        mark_day_outcome(
            conn, "acct", "2026-06-12", "twitterapi", "ok",
            reached_floor=True, error_class=None,
            tweets_fetched=5, tweets_written=5, next_eligible_at=None,
        )
    finally:
        conn.close()

    conn = get_connection(db)
    try:
        n = reopen_failed_days(conn, "acct")
    finally:
        conn.close()

    assert n == 0
    assert row(db, "acct", "2026-06-11", "twitterapi")["status"] == "pending"
    assert row(db, "acct", "2026-06-12", "twitterapi")["status"] == "ok"


def test_reopen_scopes_to_handle(tmp_path):
    db = fresh_db(tmp_path)
    _exhausted_failure(db, "acct", "2026-06-10", "twitterapi")
    _exhausted_failure(db, "other", "2026-06-10", "twitterapi")

    conn = get_connection(db)
    try:
        n = reopen_failed_days(conn, "acct")
    finally:
        conn.close()

    assert n == 1
    assert row(db, "acct", "2026-06-10", "twitterapi")["status"] == "pending"
    assert row(db, "other", "2026-06-10", "twitterapi")["status"] == "failed"
