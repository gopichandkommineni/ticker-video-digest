"""SQLite connection and schema management."""

import sqlite3
from pathlib import Path

_DEFAULT_DB = Path(__file__).parent.parent / "data" / "fintwit.db"

# The seven valid values for day_fetch_log.status (spec §3.2). SQLite TEXT
# columns are unconstrained, so this is documentation + an optional pre-write
# check via is_valid_day_fetch_status(); existing rows are never retro-validated.
#   ok / mismatch          — reconciliation outcomes (two-provider view)
#   pending / fetching     — lifecycle states for the (future) worker pool
#   complete / exhausted   — single-provider fetch outcomes
#   failed                 — max retries exceeded
VALID_DAY_FETCH_STATUSES = frozenset({
    'ok', 'mismatch', 'pending', 'fetching',
    'complete', 'exhausted', 'failed',
})


def is_valid_day_fetch_status(status: str) -> bool:
    """Return True if *status* is one of the seven recognized day_fetch_log states.

    Callers may use this to validate before writing a status. Existing rows are
    not retroactively validated.
    """
    return status in VALID_DAY_FETCH_STATUSES

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

-- Authoritative per-(tweet, provider) provenance (spec §3.4). Replaces the
-- single source_provider column for provenance queries.
CREATE TABLE IF NOT EXISTS tweet_provenance (
    tweet_id        TEXT NOT NULL,
    provider        TEXT NOT NULL,    -- 'twitterapi' | 'getxapi'
    first_seen_at   TEXT NOT NULL,    -- when this provider first returned it
    last_seen_at    TEXT NOT NULL,    -- most recent fetch that returned it
    PRIMARY KEY (tweet_id, provider)
);

CREATE INDEX IF NOT EXISTS idx_tweet_provenance_provider
    ON tweet_provenance (provider, last_seen_at DESC);

-- Derived labels, kept separate from raw data and replayable per classifier
-- version (spec §3.5). Created but NOT populated in this PR.
CREATE TABLE IF NOT EXISTS tweet_labels (
    tweet_id              TEXT NOT NULL,
    label_type            TEXT NOT NULL,   -- 'ticker' | 'useful' | 'sentiment' | ...
    label_value           TEXT NOT NULL,   -- e.g. 'RKLB' for ticker
    classifier_version    TEXT NOT NULL,   -- e.g. 'regex-v1', 'llm-v2'
    confidence            REAL,            -- 0.0-1.0, NULL if not applicable
    labeled_at            TEXT NOT NULL,
    PRIMARY KEY (tweet_id, label_type, label_value, classifier_version)
);

CREATE INDEX IF NOT EXISTS idx_tweet_labels_ticker
    ON tweet_labels (label_value, label_type)
    WHERE label_type = 'ticker';

CREATE INDEX IF NOT EXISTS idx_tweet_labels_tweet
    ON tweet_labels (tweet_id, label_type);

-- One row per (handle, date) that ever had status='mismatch' (spec §3.6).
-- Makes non-investigation visible instead of silently accumulating.
CREATE TABLE IF NOT EXISTS mismatch_resolutions (
    handle              TEXT NOT NULL,
    date                TEXT NOT NULL,
    getxapi_count       INTEGER,
    twitterapi_count    INTEGER,
    resolution          TEXT NOT NULL,    -- 'unresolved' | 'truncation' | 'deletion' |
                                          -- 'provider_index_stale' | 'data_corruption' |
                                          -- 'accepted_drift'
    note                TEXT,             -- free-text from human investigator
    resolved_at         TEXT,             -- NULL while unresolved
    PRIMARY KEY (handle, date)
);
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


def _add_column_if_missing(
    conn: sqlite3.Connection, table: str, col: str, ddl: str
) -> None:
    """ALTER TABLE ADD COLUMN guarded by a PRAGMA table_info check.

    SQLite's ADD COLUMN is not idempotent on repeat, so we check first. Safe to
    call on every init.
    """
    cols = {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    if col not in cols:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {ddl}")


def migrate_db(conn: sqlite3.Connection) -> None:
    """Apply additive column migrations to an existing schema (idempotent)."""
    with conn:
        # handles: pre-existing migration.
        _add_column_if_missing(conn, "handles", "status_since", "TEXT")

        # day_fetch_log: retry-ledger columns (spec §3.1). All NULL on existing
        # rows; semantics documented in the spec.
        _add_column_if_missing(conn, "day_fetch_log", "next_eligible_at", "TEXT")
        _add_column_if_missing(conn, "day_fetch_log", "error_class", "TEXT")
        _add_column_if_missing(conn, "day_fetch_log", "reached_floor", "INTEGER")
        _add_column_if_missing(conn, "day_fetch_log", "first_attempted_at", "TEXT")
        _add_column_if_missing(conn, "day_fetch_log", "last_succeeded_at", "TEXT")

        # raw_tweets: ingest-tracking timestamps (spec §3.7). NULL on existing rows.
        _add_column_if_missing(conn, "raw_tweets", "first_seen_at", "TEXT")
        _add_column_if_missing(conn, "raw_tweets", "last_seen_at", "TEXT")

        # Partial dispatch index (spec §3.3). Created here, after the columns it
        # references exist. Stays tiny — only covers dispatch-eligible rows.
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_day_fetch_log_dispatch "
            "ON day_fetch_log (status, next_eligible_at) "
            "WHERE status IN ('pending', 'failed')"
        )


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
