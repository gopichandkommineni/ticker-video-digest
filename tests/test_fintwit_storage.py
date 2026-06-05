"""Smoke tests for the FinTwit storage layer."""

import tempfile
from pathlib import Path

import pytest

from storage.db import init_db
from storage.tweets import upsert_tweets
from storage.handles import get_handle, list_handles
from storage.reads import get_tweets_by_handle, count_tweets


def _db(tmp_path: Path) -> Path:
    p = tmp_path / "fintwit.db"
    init_db(p)
    return p


def _make_tweet(tweet_id: str, handle: str, created_at: str, text: str = "hello") -> dict:
    return {
        "tweet_id": tweet_id,
        "account_handle": handle,
        "display_name": "Test User",
        "user_id": "u123",
        "text": text,
        "created_at_utc": created_at,
        "type": "original",
        "is_reply": 0,
        "is_quote": 0,
        "source_provider": "getxapi",
    }


HANDLE = "test_handle"
TWEETS = [
    _make_tweet("t1", HANDLE, "2026-06-01T10:00:00Z", "First tweet"),
    _make_tweet("t2", HANDLE, "2026-06-02T12:00:00Z", "Second tweet"),
    _make_tweet("t3", HANDLE, "2026-06-03T08:00:00Z", "Third tweet"),
]


class TestIdempotentUpsert:
    def test_first_insert_counts(self, tmp_path):
        db = _db(tmp_path)
        result = upsert_tweets(TWEETS, db_path=db)
        assert result.inserted == 3
        assert result.ignored == 0

    def test_second_insert_all_ignored(self, tmp_path):
        db = _db(tmp_path)
        upsert_tweets(TWEETS, db_path=db)
        result = upsert_tweets(TWEETS, db_path=db)
        assert result.inserted == 0
        assert result.ignored == 3

    def test_partial_overlap(self, tmp_path):
        db = _db(tmp_path)
        upsert_tweets(TWEETS[:2], db_path=db)
        # Insert all three; only t3 is new
        result = upsert_tweets(TWEETS, db_path=db)
        assert result.inserted == 1
        assert result.ignored == 2


class TestHandleAggregates:
    def test_total_tweets_after_insert(self, tmp_path):
        db = _db(tmp_path)
        upsert_tweets(TWEETS, db_path=db)
        row = get_handle(HANDLE, db_path=db)
        assert row["total_tweets"] == 3

    def test_watermark_equals_max_created_at(self, tmp_path):
        db = _db(tmp_path)
        upsert_tweets(TWEETS, db_path=db)
        row = get_handle(HANDLE, db_path=db)
        # Max of the three timestamps
        assert row["tweets_watermark_utc"] == "2026-06-03T08:00:00Z"
        assert row["latest_tweet_utc"] == "2026-06-03T08:00:00Z"

    def test_watermark_is_data_derived_not_wallclock(self, tmp_path):
        """Even if we insert in reverse order, watermark tracks data max."""
        db = _db(tmp_path)
        reversed_tweets = list(reversed(TWEETS))
        upsert_tweets(reversed_tweets, db_path=db)
        row = get_handle(HANDLE, db_path=db)
        assert row["tweets_watermark_utc"] == "2026-06-03T08:00:00Z"

    def test_no_double_count_on_re_insert(self, tmp_path):
        """Re-inserting same tweets must not increment total_tweets."""
        db = _db(tmp_path)
        upsert_tweets(TWEETS, db_path=db)
        upsert_tweets(TWEETS, db_path=db)
        row = get_handle(HANDLE, db_path=db)
        assert row["total_tweets"] == 3

    def test_earliest_tweet_set_once(self, tmp_path):
        """earliest_tweet_utc is set on first write and never moved backward."""
        db = _db(tmp_path)
        upsert_tweets(TWEETS[1:], db_path=db)  # t2, t3 — earliest = t2
        first_earliest = get_handle(HANDLE, db_path=db)["earliest_tweet_utc"]

        # Now insert an older tweet (t1)
        upsert_tweets(TWEETS[:1], db_path=db)
        row = get_handle(HANDLE, db_path=db)
        # earliest_tweet_utc must NOT move back to t1
        assert row["earliest_tweet_utc"] == first_earliest

    def test_watermark_advances_with_new_tweets(self, tmp_path):
        db = _db(tmp_path)
        upsert_tweets(TWEETS[:2], db_path=db)
        before = get_handle(HANDLE, db_path=db)["tweets_watermark_utc"]
        assert before == "2026-06-02T12:00:00Z"

        upsert_tweets(TWEETS[2:], db_path=db)
        after = get_handle(HANDLE, db_path=db)["tweets_watermark_utc"]
        assert after == "2026-06-03T08:00:00Z"


class TestReadFunctions:
    def test_count_tweets(self, tmp_path):
        db = _db(tmp_path)
        upsert_tweets(TWEETS, db_path=db)
        assert count_tweets(HANDLE, db_path=db) == 3

    def test_get_tweets_by_handle_ordered_newest_first(self, tmp_path):
        db = _db(tmp_path)
        upsert_tweets(TWEETS, db_path=db)
        rows = get_tweets_by_handle(HANDLE, limit=10, db_path=db)
        assert [r["tweet_id"] for r in rows] == ["t3", "t2", "t1"]

    def test_get_tweets_by_handle_limit(self, tmp_path):
        db = _db(tmp_path)
        upsert_tweets(TWEETS, db_path=db)
        rows = get_tweets_by_handle(HANDLE, limit=2, db_path=db)
        assert len(rows) == 2

    def test_get_tweets_since(self, tmp_path):
        db = _db(tmp_path)
        upsert_tweets(TWEETS, db_path=db)
        rows = get_tweets_by_handle(
            HANDLE, limit=10, since="2026-06-01T10:00:00Z", db_path=db
        )
        # Only t2 and t3 are strictly after t1's timestamp
        assert {r["tweet_id"] for r in rows} == {"t2", "t3"}

    def test_list_handles(self, tmp_path):
        db = _db(tmp_path)
        upsert_tweets(TWEETS, db_path=db)
        handles = list_handles(db_path=db)
        assert len(handles) == 1
        assert handles[0]["handle"] == HANDLE
        assert handles[0]["total_tweets"] == 3

    def test_get_handle_none_for_missing(self, tmp_path):
        db = _db(tmp_path)
        assert get_handle("nobody", db_path=db) is None

    def test_empty_db_no_tweets(self, tmp_path):
        db = _db(tmp_path)
        assert count_tweets(HANDLE, db_path=db) == 0
        assert get_tweets_by_handle(HANDLE, db_path=db) == []


class TestThreeSpecificChecks:
    """Targeted checks requested post-merge."""

    def test_out_of_order_insert_watermark_is_true_max(self, tmp_path):
        """Insert newest tweet first, then older ones — watermark must be data max."""
        db = _db(tmp_path)
        # Insert in reverse chronological order (newest first)
        upsert_tweets(list(reversed(TWEETS)), db_path=db)
        row = get_handle(HANDLE, db_path=db)
        # True max regardless of insertion order
        assert row["tweets_watermark_utc"] == "2026-06-03T08:00:00Z"
        assert row["latest_tweet_utc"] == "2026-06-03T08:00:00Z"
        assert row["total_tweets"] == 3

    def test_wal_checkpoint_no_sidecar(self, tmp_path):
        """After close_connection, no -wal file should remain alongside the db."""
        import os
        from storage.db import close_connection
        db = _db(tmp_path)
        upsert_tweets(TWEETS, db_path=db)
        # Manually open + checkpoint to verify the API works
        from storage.db import get_connection
        conn = get_connection(db)
        conn.execute("SELECT 1")  # ensure WAL has been written to
        close_connection(conn)
        wal_path = str(db) + "-wal"
        # After TRUNCATE checkpoint the -wal file should be absent or empty
        assert not os.path.exists(wal_path) or os.path.getsize(wal_path) == 0

    def test_sparse_tweet_missing_optional_fields(self, tmp_path):
        """Tweet with only required fields (null bookmark_count, no quoted_tweet_id) inserts without error."""
        db = _db(tmp_path)
        sparse = {
            "tweet_id": "sparse1",
            "account_handle": "sparse_handle",
            "created_at_utc": "2026-06-04T00:00:00Z",
            # All optional fields deliberately absent
        }
        result = upsert_tweets([sparse], db_path=db)
        assert result.inserted == 1
        rows = get_tweets_by_handle("sparse_handle", db_path=db)
        assert len(rows) == 1
        assert rows[0]["bookmark_count"] is None
        assert rows[0]["quoted_tweet_id"] is None
        assert rows[0]["text"] is None
