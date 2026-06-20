"""Schema tests for the ingestion ledger v1 additive changes (spec §3)."""

from __future__ import annotations

from pathlib import Path

from storage.db import VALID_DAY_FETCH_STATUSES, init_db


def _cols(conn, table: str) -> set[str]:
    return {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def _pk(conn, table: str) -> list[str]:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    pk = [r for r in rows if r[5]]  # r[5] = pk position (0 if not part of PK)
    return [r[1] for r in sorted(pk, key=lambda r: r[5])]


def _conn(tmp_path: Path):
    from storage.db import get_connection
    db = tmp_path / "fintwit.db"
    init_db(db)
    return get_connection(db)


def test_schema_includes_new_columns(tmp_path):
    conn = _conn(tmp_path)
    try:
        log_cols = _cols(conn, "day_fetch_log")
        for col in (
            "next_eligible_at", "error_class", "reached_floor",
            "first_attempted_at", "last_succeeded_at",
        ):
            assert col in log_cols, f"day_fetch_log missing {col}"

        raw_cols = _cols(conn, "raw_tweets")
        assert "first_seen_at" in raw_cols
        assert "last_seen_at" in raw_cols
    finally:
        conn.close()


def test_schema_includes_new_tables(tmp_path):
    conn = _conn(tmp_path)
    try:
        assert _pk(conn, "tweet_provenance") == ["tweet_id", "provider"]
        assert _pk(conn, "tweet_labels") == [
            "tweet_id", "label_type", "label_value", "classifier_version",
        ]
        assert _pk(conn, "mismatch_resolutions") == ["handle", "date"]
    finally:
        conn.close()


def test_dispatch_index_exists(tmp_path):
    conn = _conn(tmp_path)
    try:
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'index' "
            "AND name = 'idx_day_fetch_log_dispatch'"
        ).fetchone()
        assert row is not None
    finally:
        conn.close()


def test_valid_statuses_constant():
    assert VALID_DAY_FETCH_STATUSES == frozenset({
        "ok", "mismatch", "pending", "fetching",
        "complete", "exhausted", "failed",
    })


def test_init_db_is_idempotent(tmp_path):
    db = tmp_path / "fintwit.db"
    init_db(db)
    # Second init must not raise (ALTERs are guarded, CREATEs are IF NOT EXISTS).
    init_db(db)
