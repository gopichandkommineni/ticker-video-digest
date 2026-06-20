"""Tests for the ingestion ledger v1 write-path changes (spec §3.7, §3.8, §3.4)."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from storage.db import get_connection, init_db
from storage.tweets import upsert_tweets
from tweet_sources.base import MAX_RAW_JSON_BYTES, serialize_raw_json


def _db(tmp_path: Path) -> Path:
    p = tmp_path / "fintwit.db"
    init_db(p)
    return p


def _tweet(tweet_id: str, provider: str = "getxapi", **extra) -> dict:
    row = {
        "tweet_id": tweet_id,
        "account_handle": "test_handle",
        "text": "hello",
        "created_at_utc": "2026-06-01T10:00:00Z",
        "type": "original",
        "is_reply": 0,
        "is_quote": 0,
        "source_provider": provider,
    }
    row.update(extra)
    return row


def _raw_row(db: Path, tweet_id: str) -> dict:
    conn = get_connection(db)
    try:
        return dict(conn.execute(
            "SELECT * FROM raw_tweets WHERE tweet_id = ?", (tweet_id,)
        ).fetchone())
    finally:
        conn.close()


def test_upsert_writes_raw_json(tmp_path):
    db = _db(tmp_path)
    payload = json.dumps({"id": "t1", "text": "hi", "likeCount": 3})
    upsert_tweets([_tweet("t1", raw_json=payload)], db_path=db)
    assert _raw_row(db, "t1")["raw_json"] == payload


def test_upsert_writes_first_seen_and_last_seen(tmp_path, monkeypatch):
    db = _db(tmp_path)

    import storage.tweets as st
    monkeypatch.setattr(st, "_iso_now", lambda: "2026-06-01T00:00:00Z")
    upsert_tweets([_tweet("t1")], db_path=db)
    first = _raw_row(db, "t1")
    assert first["first_seen_at"] == "2026-06-01T00:00:00Z"
    assert first["last_seen_at"] == "2026-06-01T00:00:00Z"

    # Re-fetch later: last_seen_at moves forward, first_seen_at stays put.
    monkeypatch.setattr(st, "_iso_now", lambda: "2026-06-02T00:00:00Z")
    upsert_tweets([_tweet("t1")], db_path=db)
    second = _raw_row(db, "t1")
    assert second["first_seen_at"] == "2026-06-01T00:00:00Z"
    assert second["last_seen_at"] == "2026-06-02T00:00:00Z"


def test_upsert_writes_tweet_provenance(tmp_path):
    db = _db(tmp_path)
    upsert_tweets([_tweet("t1", provider="twitterapi")], db_path=db)
    upsert_tweets([_tweet("t1", provider="getxapi")], db_path=db)

    conn = get_connection(db)
    try:
        rows = conn.execute(
            "SELECT provider FROM tweet_provenance WHERE tweet_id = ? ORDER BY provider",
            ("t1",),
        ).fetchall()
    finally:
        conn.close()
    # Same tweet_id, two providers → two rows (distinct PKs).
    assert [r["provider"] for r in rows] == ["getxapi", "twitterapi"]


def test_provenance_last_seen_refreshes_same_provider(tmp_path, monkeypatch):
    db = _db(tmp_path)
    import storage.tweets as st
    monkeypatch.setattr(st, "_iso_now", lambda: "2026-06-01T00:00:00Z")
    upsert_tweets([_tweet("t1", provider="getxapi")], db_path=db)
    monkeypatch.setattr(st, "_iso_now", lambda: "2026-06-05T00:00:00Z")
    upsert_tweets([_tweet("t1", provider="getxapi")], db_path=db)

    conn = get_connection(db)
    try:
        row = conn.execute(
            "SELECT first_seen_at, last_seen_at FROM tweet_provenance "
            "WHERE tweet_id = ? AND provider = ?",
            ("t1", "getxapi"),
        ).fetchone()
    finally:
        conn.close()
    assert row["first_seen_at"] == "2026-06-01T00:00:00Z"
    assert row["last_seen_at"] == "2026-06-05T00:00:00Z"


def test_raw_json_size_cap(caplog):
    big = {"id": "t1", "blob": "x" * (MAX_RAW_JSON_BYTES * 2)}
    with caplog.at_level(logging.WARNING):
        result = serialize_raw_json("t1", big)
    assert len(result) == MAX_RAW_JSON_BYTES
    assert any("truncated" in rec.message for rec in caplog.records)


def test_raw_json_under_cap_not_truncated(caplog):
    small = {"id": "t1", "text": "hi"}
    with caplog.at_level(logging.WARNING):
        result = serialize_raw_json("t1", small)
    assert result == json.dumps(small)
    assert not any("truncated" in rec.message for rec in caplog.records)
