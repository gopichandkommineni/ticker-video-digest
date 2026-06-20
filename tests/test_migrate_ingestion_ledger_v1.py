"""Tests for scripts/migrate_ingestion_ledger_v1.py (spec §4, §6).

A pre-v1 (old-schema) fixture DB is built programmatically so the migration's
ALTER TABLE / CREATE TABLE paths are genuinely exercised. data/fintwit.db is
never touched.
"""

from __future__ import annotations

import importlib.util
import sqlite3
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

# --- Old (pre-v1) schema: day_fetch_log and raw_tweets without the new columns,
#     no tweet_provenance / tweet_labels / mismatch_resolutions tables. ---
_OLD_SCHEMA = """
CREATE TABLE day_fetch_log (
    handle       TEXT    NOT NULL,
    date         TEXT    NOT NULL,
    provider     TEXT    NOT NULL,
    status       TEXT    NOT NULL DEFAULT 'pending',
    tweet_count  INTEGER,
    fetched_at   TEXT,
    retry_count  INTEGER NOT NULL DEFAULT 0,
    error        TEXT,
    PRIMARY KEY (handle, date, provider)
);

CREATE TABLE raw_tweets (
    tweet_id            TEXT PRIMARY KEY,
    account_handle      TEXT NOT NULL,
    text                TEXT,
    created_at_utc      TEXT NOT NULL,
    fetched_at          TEXT,
    source_provider     TEXT,
    raw_json            TEXT
);

CREATE TABLE handles (
    handle          TEXT PRIMARY KEY,
    display_name    TEXT,
    status          TEXT,
    total_tweets    INTEGER DEFAULT 0
);
"""


def _load_migrate():
    path = REPO / "scripts" / "migrate_ingestion_ledger_v1.py"
    spec = importlib.util.spec_from_file_location("migrate_v1", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _make_old_db(tmp_path: Path) -> Path:
    db = tmp_path / "fintwit.db"
    conn = sqlite3.connect(db)
    conn.executescript(_OLD_SCHEMA)
    # raw_tweets: 3 historical rows.
    conn.executemany(
        "INSERT INTO raw_tweets (tweet_id, account_handle, text, created_at_utc, "
        "fetched_at, source_provider, raw_json) VALUES (?, ?, ?, ?, ?, ?, ?)",
        [
            ("t1", "alice", "first", "2026-05-01T10:00:00Z", "2026-05-01T11:00:00Z", "getxapi", None),
            ("t2", "alice", "second", "2026-05-02T10:00:00Z", "2026-05-02T11:00:00Z", "twitterapi", None),
            ("t3", "bob", "third", "2026-05-03T10:00:00Z", "2026-05-03T11:00:00Z", "getxapi", None),
        ],
    )
    # day_fetch_log: 2 ok days (×2 providers) + 2 mismatch days (×2 providers).
    conn.executemany(
        "INSERT INTO day_fetch_log (handle, date, provider, status, tweet_count, fetched_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        [
            ("alice", "2026-05-01", "getxapi", "ok", 5, "2026-05-01T11:00:00Z"),
            ("alice", "2026-05-01", "twitterapi", "ok", 5, "2026-05-01T11:00:00Z"),
            ("bob", "2026-05-03", "getxapi", "ok", 3, "2026-05-03T11:00:00Z"),
            ("bob", "2026-05-03", "twitterapi", "ok", 3, "2026-05-03T11:00:00Z"),
            ("alice", "2026-05-10", "getxapi", "mismatch", 7, "2026-05-10T11:00:00Z"),
            ("alice", "2026-05-10", "twitterapi", "mismatch", 9, "2026-05-10T11:00:00Z"),
            ("bob", "2026-05-12", "getxapi", "mismatch", 1, "2026-05-12T11:00:00Z"),
            ("bob", "2026-05-12", "twitterapi", "mismatch", 4, "2026-05-12T11:00:00Z"),
        ],
    )
    conn.executemany(
        "INSERT INTO handles (handle, display_name, status, total_tweets) VALUES (?, ?, ?, ?)",
        [("alice", "Alice", "ready", 2), ("bob", "Bob", "ready", 1)],
    )
    conn.commit()
    conn.close()
    return db


def _dump(db: Path, table: str) -> list[tuple]:
    conn = sqlite3.connect(db)
    try:
        return conn.execute(f"SELECT * FROM {table} ORDER BY 1, 2, 3").fetchall()
    finally:
        conn.close()


def _counts(db: Path) -> dict[str, int]:
    conn = sqlite3.connect(db)
    try:
        return {
            t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            for t in ("raw_tweets", "day_fetch_log", "handles")
        }
    finally:
        conn.close()


def test_migration_idempotent(tmp_path):
    mod = _load_migrate()
    db = _make_old_db(tmp_path)
    mod.migrate(db, dry_run=False)

    tables = ["raw_tweets", "day_fetch_log", "handles", "mismatch_resolutions",
              "tweet_provenance", "tweet_labels"]
    after_first = {t: _dump(db, t) for t in tables}

    mod.migrate(db, dry_run=False)
    after_second = {t: _dump(db, t) for t in tables}

    assert after_first == after_second


def test_existing_rows_preserved(tmp_path):
    mod = _load_migrate()
    db = _make_old_db(tmp_path)
    pre = _counts(db)

    # Capture a sample raw_tweets row's pre-existing values.
    conn = sqlite3.connect(db)
    sample_pre = conn.execute(
        "SELECT tweet_id, account_handle, text, created_at_utc, source_provider "
        "FROM raw_tweets WHERE tweet_id = 't2'"
    ).fetchone()
    conn.close()

    mod.migrate(db, dry_run=False)
    post = _counts(db)
    assert pre == post

    conn = sqlite3.connect(db)
    sample_post = conn.execute(
        "SELECT tweet_id, account_handle, text, created_at_utc, source_provider "
        "FROM raw_tweets WHERE tweet_id = 't2'"
    ).fetchone()
    conn.close()
    assert sample_pre == sample_post


def test_new_columns_nullable_for_existing_rows(tmp_path):
    mod = _load_migrate()
    db = _make_old_db(tmp_path)
    mod.migrate(db, dry_run=False)

    conn = sqlite3.connect(db)
    try:
        raw = conn.execute(
            "SELECT first_seen_at, last_seen_at FROM raw_tweets WHERE tweet_id = 't1'"
        ).fetchone()
        assert raw == (None, None)

        log = conn.execute(
            "SELECT next_eligible_at, reached_floor FROM day_fetch_log "
            "WHERE handle = 'alice' AND date = '2026-05-01' AND provider = 'getxapi'"
        ).fetchone()
        assert log == (None, None)
    finally:
        conn.close()


def test_last_succeeded_at_backfilled_for_ok_rows(tmp_path):
    mod = _load_migrate()
    db = _make_old_db(tmp_path)
    mod.migrate(db, dry_run=False)

    conn = sqlite3.connect(db)
    try:
        # 'ok' row: last_succeeded_at copied from fetched_at.
        ok = conn.execute(
            "SELECT fetched_at, last_succeeded_at FROM day_fetch_log "
            "WHERE handle = 'alice' AND date = '2026-05-01' AND provider = 'getxapi'"
        ).fetchone()
        assert ok[1] == ok[0] == "2026-05-01T11:00:00Z"

        # 'mismatch' row: last_succeeded_at stays NULL.
        mm = conn.execute(
            "SELECT last_succeeded_at FROM day_fetch_log "
            "WHERE handle = 'alice' AND date = '2026-05-10' AND provider = 'getxapi'"
        ).fetchone()
        assert mm[0] is None
    finally:
        conn.close()


def test_mismatch_resolutions_seeded(tmp_path):
    mod = _load_migrate()
    db = _make_old_db(tmp_path)
    mod.migrate(db, dry_run=False)

    conn = sqlite3.connect(db)
    try:
        rows = conn.execute(
            "SELECT handle, date, getxapi_count, twitterapi_count, resolution, resolved_at "
            "FROM mismatch_resolutions ORDER BY handle, date"
        ).fetchall()
    finally:
        conn.close()

    # Two distinct (handle, date) mismatch pairs → exactly 2 rows.
    assert len(rows) == 2
    assert all(r[4] == "unresolved" for r in rows)
    assert all(r[5] is None for r in rows)
    # Provider counts carried through from day_fetch_log.
    by_key = {(r[0], r[1]): (r[2], r[3]) for r in rows}
    assert by_key[("alice", "2026-05-10")] == (7, 9)
    assert by_key[("bob", "2026-05-12")] == (1, 4)


def test_dry_run_does_not_mutate(tmp_path):
    mod = _load_migrate()
    db = _make_old_db(tmp_path)

    before = {t: _dump(db, t) for t in ("raw_tweets", "day_fetch_log", "handles")}
    mod.migrate(db, dry_run=True)
    after = {t: _dump(db, t) for t in ("raw_tweets", "day_fetch_log", "handles")}
    assert before == after

    # Dry run must not create the new tables.
    conn = sqlite3.connect(db)
    try:
        tables = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()}
    finally:
        conn.close()
    assert "mismatch_resolutions" not in tables
    assert "tweet_provenance" not in tables
