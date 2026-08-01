"""Tests for scripts/shrink_fintwit_db.py — dropping stored raw_json to keep
data/fintwit.db under GitHub's 100MB file-size limit."""

from __future__ import annotations

from fintwit.storage.db import get_connection
from fintwit.storage.tweets import upsert_tweets
from scripts.shrink_fintwit_db import shrink

from tests.worker_pool_helpers import fresh_db, make_tweet_dicts


def _seed(db, handle, ids, *, raw_json):
    rows = make_tweet_dicts(handle, ids, "twitterapi")
    for r in rows:
        r["raw_json"] = raw_json
    upsert_tweets(rows, db_path=db)


def test_shrink_nulls_raw_json_and_preserves_rows(tmp_path):
    db = fresh_db(tmp_path)
    _seed(db, "acct", ["1", "2", "3"], raw_json='{"big":"payload"}')

    cleared = shrink(str(db))

    assert cleared == 3
    conn = get_connection(db)
    try:
        assert conn.execute("SELECT COUNT(*) FROM raw_tweets").fetchone()[0] == 3
        assert conn.execute(
            "SELECT COUNT(*) FROM raw_tweets WHERE raw_json IS NOT NULL"
        ).fetchone()[0] == 0
        # Parsed columns are untouched.
        assert conn.execute(
            "SELECT text FROM raw_tweets WHERE tweet_id = '1'"
        ).fetchone()[0] == "t1"
    finally:
        conn.close()


def test_shrink_is_idempotent(tmp_path):
    db = fresh_db(tmp_path)
    _seed(db, "acct", ["1", "2"], raw_json='{"x":1}')

    assert shrink(str(db)) == 2
    # Second pass: nothing left to clear.
    assert shrink(str(db)) == 0


def test_shrink_noop_when_already_clean(tmp_path):
    db = fresh_db(tmp_path)
    _seed(db, "acct", ["1"], raw_json=None)

    assert shrink(str(db)) == 0
