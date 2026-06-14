"""SQLite connection and schema management."""

import sqlite3
from pathlib import Path

_DEFAULT_DB = Path(__file__).parent.parent / "data" / "fintwit.db"

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS day_fetch_log (
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

CREATE INDEX IF NOT EXISTS idx_day_fetch_log_handle_status
    ON day_fetch_log (handle, status);

CREATE TABLE IF NOT EXISTS raw_tweets (
    tweet_id            TEXT PRIMARY KEY,
    account_handle      TEXT NOT NULL,
    display_name        TEXT,
    user_id             TEXT,
    text                TEXT,
    created_at_utc      TEXT NOT NULL,
    type                TEXT,
    is_reply            INTEGER,
    is_quote            INTEGER,
    in_reply_to_id      TEXT,
    quoted_tweet_id     TEXT,
    quoted_author_id    TEXT,
    conversation_id     TEXT,
    like_count          INTEGER,
    retweet_count       INTEGER,
    reply_count         INTEGER,
    quote_count         INTEGER,
    view_count          INTEGER,
    bookmark_count      INTEGER,
    has_media           INTEGER,
    media_urls          TEXT,
    url                 TEXT,
    is_deleted          INTEGER DEFAULT 0,
    fetched_at          TEXT,
    source_provider     TEXT,
    raw_json            TEXT
);

CREATE TABLE IF NOT EXISTS handles (
    handle                  TEXT PRIMARY KEY,
    display_name            TEXT,
    user_id                 TEXT,
    status                  TEXT,
    tweets_watermark_utc    TEXT,
    earliest_tweet_utc      TEXT,
    latest_tweet_utc        TEXT,
    total_tweets            INTEGER DEFAULT 0,
    last_fetch_at           TEXT,
    last_fetch_status       TEXT,
    status_since            TEXT,
    user_info_last_fetched  TEXT,
    added_at                TEXT
);

CREATE INDEX IF NOT EXISTS idx_raw_tweets_handle_created
    ON raw_tweets (account_handle, created_at_utc DESC);

CREATE TABLE IF NOT EXISTS ticker_mentions (
    tweet_id        TEXT    NOT NULL,
    account_handle  TEXT    NOT NULL,
    ticker          TEXT    NOT NULL,
    in_universe     INTEGER NOT NULL DEFAULT 0,
    created_at_utc  TEXT,
    PRIMARY KEY (tweet_id, ticker)
);

CREATE INDEX IF NOT EXISTS idx_ticker_mentions_ticker
    ON ticker_mentions (ticker);
CREATE INDEX IF NOT EXISTS idx_ticker_mentions_handle
    ON ticker_mentions (account_handle);
"""


def get_connection(db_path: Path | str | None = None) -> sqlite3.Connection:
    """Return a sqlite3 connection with WAL mode and row_factory set."""
    path = Path(db_path) if db_path else _DEFAULT_DB
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db(db_path: Path | str | None = None) -> None:
    """Create tables, indexes, and apply additive migrations."""
    conn = get_connection(db_path)
    with conn:
        conn.executescript(_SCHEMA_SQL)
    migrate_db(conn)
    conn.close()


def migrate_db(conn: sqlite3.Connection) -> None:
    """Apply additive column migrations to an existing schema (idempotent)."""
    cols = {
        row[1]
        for row in conn.execute("PRAGMA table_info(handles)").fetchall()
    }
    if "status_since" not in cols:
        with conn:
            conn.execute("ALTER TABLE handles ADD COLUMN status_since TEXT")


def close_connection(db_path: Path | str | None = None) -> None:
    """Checkpoint the WAL (TRUNCATE mode) and close cleanly.

    Call this before any git commit so the committed .db has no -wal/-shm
    sidecar and is not in a half-written state.
    """
    path = Path(db_path) if db_path else _DEFAULT_DB
    if not path.exists():
        return
    conn = sqlite3.connect(str(path))
    conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    conn.close()
