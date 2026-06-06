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


class TestHandleNormalization:
    """normalize_handle is applied at every entry point; all variants map to one row."""

    def test_normalize_strips_at_sign(self):
        from storage.handles import normalize_handle
        assert normalize_handle("@Venu_7_") == "venu_7_"

    def test_normalize_trims_whitespace(self):
        from storage.handles import normalize_handle
        assert normalize_handle("  Venu_7_  ") == "venu_7_"

    def test_normalize_strips_at_and_whitespace_combined(self):
        from storage.handles import normalize_handle
        assert normalize_handle(" @Venu_7_ ") == "venu_7_"

    def test_normalize_lowercases(self):
        from storage.handles import normalize_handle
        assert normalize_handle("Venu_7_") == "venu_7_"

    def test_all_variants_create_one_row(self, tmp_path):
        """@Venu_7_, Venu_7_, ' @Venu_7_ ', and venu_7_ must all resolve to one handle row."""
        from storage.handles import normalize_handle, upsert_handle, get_handle, list_handles
        db = _db(tmp_path)

        variants = ["@Venu_7_", "Venu_7_", " @Venu_7_ ", "venu_7_"]
        for v in variants:
            upsert_handle(v, {"status": "pending"}, db_path=db)

        rows = list_handles(db_path=db)
        assert len(rows) == 1, (
            f"expected 1 handle row, got {len(rows)}: {[r['handle'] for r in rows]}"
        )
        assert rows[0]["handle"] == "venu_7_"

        # Every variant lookups up the same row
        for v in variants:
            row = get_handle(v, db_path=db)
            assert row is not None, f"get_handle({v!r}) returned None"
            assert row["handle"] == "venu_7_", f"variant {v!r} resolved to {row['handle']!r}"
