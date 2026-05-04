import sqlite3
from pathlib import Path

_DEFAULT_DB_PATH = Path("data/snapshots.db")


def init_db(db_path: Path = _DEFAULT_DB_PATH) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS ticker_snapshots (
                ticker        TEXT    NOT NULL,
                date          TEXT    NOT NULL,
                open          REAL    NOT NULL,
                high          REAL    NOT NULL,
                low           REAL    NOT NULL,
                close         REAL    NOT NULL,
                adj_close     REAL    NOT NULL,
                volume        INTEGER NOT NULL,
                avg_volume_30d REAL,
                PRIMARY KEY (ticker, date)
            );

            CREATE TABLE IF NOT EXISTS news_items (
                id           INTEGER PRIMARY KEY,
                ticker       TEXT    NOT NULL,
                snap_date    TEXT    NOT NULL,
                title        TEXT    NOT NULL,
                link         TEXT    NOT NULL,
                publisher    TEXT    NOT NULL,
                published_at TEXT    NOT NULL,
                fetched_at   TEXT    NOT NULL
            );

            CREATE TABLE IF NOT EXISTS signals (
                ticker       TEXT NOT NULL,
                date         TEXT NOT NULL,
                signal_name  TEXT NOT NULL,
                value        REAL,
                PRIMARY KEY (ticker, date, signal_name)
            );

            -- subreddit defaults to '' (empty string, not NULL) for the
            -- apewisdom aggregate row so the PRIMARY KEY constraint works.
            CREATE TABLE IF NOT EXISTS social_mentions (
                ticker            TEXT    NOT NULL,
                date              TEXT    NOT NULL,
                source            TEXT    NOT NULL,
                mention_count     INTEGER NOT NULL,
                mentions_24h_ago  INTEGER,
                upvote_sum        INTEGER,
                subreddit         TEXT    NOT NULL DEFAULT '',
                PRIMARY KEY (ticker, date, source, subreddit)
            );
        """)
