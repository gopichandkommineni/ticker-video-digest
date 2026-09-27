"""data/reddit.db — the Reddit ingestion store.

Tables (one row each):
    runs          one ingestion run: window, counts, status, errors
    posts         one Reddit post, latest known score/comment count
    post_tickers  which stock a post was collected for, and how
                  (via 'subreddit' feed or keyword 'search')
    post_scores   a post's score over time — a new row only when it changed
    comments      top comments on notable posts, with their parent for threading

Posts are keyed by Reddit's id, so the same post seen by several runs (or for
several stocks) is one row. Every write is an upsert: re-running is safe.

The file is committed to git by the daily workflow, like fintwit.db, so it is
kept small on purpose — see `prune`.
"""
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

# This file is src/core/social_media/reddit/ingest/db.py; parents[5] is the repo.
_REPO_DB = Path(__file__).resolve().parents[5] / "data" / "reddit.db"


def default_db_path() -> Path:
    """REDDIT_DB_PATH if set, else data/reddit.db in the repository."""
    override = os.environ.get("REDDIT_DB_PATH", "").strip()
    return Path(override) if override else _REPO_DB


_SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    run_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at      TEXT NOT NULL,
    finished_at     TEXT,
    status          TEXT NOT NULL DEFAULT 'running',   -- running | ok | partial | failed
    window_start    TEXT NOT NULL,
    tickers         INTEGER NOT NULL DEFAULT 0,
    posts_new       INTEGER NOT NULL DEFAULT 0,
    posts_updated   INTEGER NOT NULL DEFAULT 0,
    comments_saved  INTEGER NOT NULL DEFAULT 0,
    pruned          INTEGER NOT NULL DEFAULT 0,
    errors          TEXT                                -- newline-separated
);

CREATE TABLE IF NOT EXISTS posts (
    post_id              TEXT PRIMARY KEY,
    subreddit            TEXT NOT NULL,
    author               TEXT NOT NULL DEFAULT '',
    title                TEXT NOT NULL DEFAULT '',
    body                 TEXT NOT NULL DEFAULT '',
    url                  TEXT NOT NULL DEFAULT '',
    created_at           TEXT NOT NULL,
    score                INTEGER NOT NULL DEFAULT 0,
    num_comments         INTEGER NOT NULL DEFAULT 0,
    first_seen           TEXT NOT NULL,
    last_seen            TEXT NOT NULL,
    comments_fetched_at  TEXT
);
CREATE INDEX IF NOT EXISTS idx_posts_created ON posts(created_at);
CREATE INDEX IF NOT EXISTS idx_posts_subreddit ON posts(subreddit, created_at);

CREATE TABLE IF NOT EXISTS post_tickers (
    post_id   TEXT NOT NULL,
    ticker    TEXT NOT NULL,
    via       TEXT NOT NULL,          -- 'subreddit' | 'search'
    matched   TEXT NOT NULL DEFAULT '',  -- the subreddit, or the keywords that hit
    PRIMARY KEY (post_id, ticker)
);
CREATE INDEX IF NOT EXISTS idx_post_tickers_ticker ON post_tickers(ticker);

CREATE TABLE IF NOT EXISTS post_scores (
    post_id       TEXT NOT NULL,
    seen_at       TEXT NOT NULL,
    score         INTEGER NOT NULL,
    num_comments  INTEGER NOT NULL,
    PRIMARY KEY (post_id, seen_at)
);

CREATE TABLE IF NOT EXISTS comments (
    comment_id   TEXT PRIMARY KEY,
    post_id      TEXT NOT NULL,
    parent_id    TEXT,               -- t3_<post> top-level, t1_<comment> reply
    author       TEXT NOT NULL DEFAULT '',
    body         TEXT NOT NULL DEFAULT '',
    score        INTEGER NOT NULL DEFAULT 0,
    created_at   TEXT NOT NULL,
    fetched_at   TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_comments_post ON comments(post_id);
"""


def connect(path: Path | None = None) -> sqlite3.Connection:
    """Open (creating if needed) the Reddit store with its schema in place."""
    path = path or default_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    return conn


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds")


# --- runs ---------------------------------------------------------------------

def start_run(conn: sqlite3.Connection, window_start: datetime, tickers: int, now: datetime) -> int:
    cur = conn.execute(
        "INSERT INTO runs (started_at, window_start, tickers) VALUES (?, ?, ?)",
        (iso(now), iso(window_start), tickers),
    )
    conn.commit()
    return int(cur.lastrowid)


def finish_run(
    conn: sqlite3.Connection, run_id: int, status: str, now: datetime,
    posts_new: int, posts_updated: int, comments_saved: int, pruned: int,
    errors: list[str],
) -> None:
    conn.execute(
        """UPDATE runs SET finished_at=?, status=?, posts_new=?, posts_updated=?,
               comments_saved=?, pruned=?, errors=? WHERE run_id=?""",
        (iso(now), status, posts_new, posts_updated, comments_saved, pruned,
         "\n".join(errors) or None, run_id),
    )
    conn.commit()


def last_good_run_start(conn: sqlite3.Connection) -> datetime | None:
    """When the last run that got anything done (ok or partial) started."""
    row = conn.execute(
        "SELECT started_at FROM runs WHERE status IN ('ok', 'partial') "
        "ORDER BY run_id DESC LIMIT 1"
    ).fetchone()
    return datetime.fromisoformat(row["started_at"]) if row else None


# --- posts --------------------------------------------------------------------

def upsert_post(
    conn: sqlite3.Connection, *, post_id: str, subreddit: str, author: str, title: str,
    body: str, url: str, created_at: datetime, score: int, num_comments: int,
    now: datetime,
) -> bool:
    """Insert or refresh a post. Returns True if it is new.

    A score snapshot is recorded whenever score or comment count changed, so
    `post_scores` holds the post's trajectory, not one row per run.
    """
    seen = iso(now)
    existing = conn.execute(
        "SELECT score, num_comments FROM posts WHERE post_id=?", (post_id,)
    ).fetchone()
    if existing is None:
        conn.execute(
            """INSERT INTO posts (post_id, subreddit, author, title, body, url, created_at,
                   score, num_comments, first_seen, last_seen)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (post_id, subreddit, author, title, body, url, iso(created_at),
             score, num_comments, seen, seen),
        )
        changed = True
    else:
        conn.execute(
            """UPDATE posts SET score=?, num_comments=?, last_seen=?,
                   title=CASE WHEN ?<>'' THEN ? ELSE title END,
                   body=CASE WHEN ?<>'' THEN ? ELSE body END
               WHERE post_id=?""",
            (score, num_comments, seen, title, title, body, body, post_id),
        )
        changed = (existing["score"], existing["num_comments"]) != (score, num_comments)
    if changed:
        conn.execute(
            "INSERT OR REPLACE INTO post_scores (post_id, seen_at, score, num_comments) "
            "VALUES (?, ?, ?, ?)",
            (post_id, seen, score, num_comments),
        )
    return existing is None


def link_ticker(conn: sqlite3.Connection, post_id: str, ticker: str, via: str, matched: str) -> None:
    """Record that *post_id* was collected for *ticker*. A subreddit-feed link
    wins over a search link (it is the stronger evidence)."""
    conn.execute(
        """INSERT INTO post_tickers (post_id, ticker, via, matched) VALUES (?, ?, ?, ?)
           ON CONFLICT(post_id, ticker) DO UPDATE SET
               via=CASE WHEN post_tickers.via='subreddit' THEN 'subreddit' ELSE excluded.via END,
               matched=CASE WHEN post_tickers.via='subreddit' THEN post_tickers.matched
                            ELSE excluded.matched END""",
        (post_id, ticker, via, matched),
    )


def posts_needing_comments(
    conn: sqlite3.Connection, *, now: datetime, min_score: int, min_comments: int,
    fresh_days: int, refetch_hours: int, limit: int,
) -> list[str]:
    """Notable posts whose comments are missing or may still be growing.

    Notable = score >= min_score OR num_comments >= min_comments. A post gets its
    comments fetched once, then again while it is younger than *fresh_days* and
    the last fetch is older than *refetch_hours*. Busiest first.
    """
    fresh_after = iso(now - timedelta(days=fresh_days))
    stale_before = iso(now - timedelta(hours=refetch_hours))
    rows = conn.execute(
        """SELECT post_id FROM posts
           WHERE (score >= ? OR num_comments >= ?)
             AND (comments_fetched_at IS NULL
                  OR (created_at >= ? AND comments_fetched_at < ?))
           ORDER BY num_comments DESC, score DESC
           LIMIT ?""",
        (min_score, min_comments, fresh_after, stale_before, limit),
    ).fetchall()
    return [r["post_id"] for r in rows]


def save_comments(
    conn: sqlite3.Connection, post_id: str, comments: list[dict], now: datetime,
) -> int:
    """Upsert comments for a post and stamp when they were fetched."""
    seen = iso(now)
    for c in comments:
        conn.execute(
            """INSERT INTO comments (comment_id, post_id, parent_id, author, body, score,
                   created_at, fetched_at)
               VALUES (:comment_id, :post_id, :parent_id, :author, :body, :score,
                       :created_at, :fetched_at)
               ON CONFLICT(comment_id) DO UPDATE SET
                   score=excluded.score, body=excluded.body, fetched_at=excluded.fetched_at""",
            {**c, "post_id": post_id, "fetched_at": seen},
        )
    conn.execute("UPDATE posts SET comments_fetched_at=? WHERE post_id=?", (seen, post_id))
    return len(comments)


# --- size control ---------------------------------------------------------------

def prune(
    conn: sqlite3.Connection, *, now: datetime, keep_days: int,
    quiet_days: int, quiet_score: int, quiet_comments: int,
) -> int:
    """Delete what is no longer worth keeping. Returns posts deleted.

    - Everything older than *keep_days*.
    - Quiet posts (score < quiet_score AND comments < quiet_comments) older than
      *quiet_days* — by then the archive has filled in their real score, so
      "quiet" is a verdict, not a symptom of the archive's lag.
    Their links, score history and comments go with them.
    """
    old = iso(now - timedelta(days=keep_days))
    quiet = iso(now - timedelta(days=quiet_days))
    doomed = [r["post_id"] for r in conn.execute(
        """SELECT post_id FROM posts
           WHERE created_at < ?
              OR (created_at < ? AND score < ? AND num_comments < ?)""",
        (old, quiet, quiet_score, quiet_comments),
    )]
    for chunk in (doomed[i:i + 500] for i in range(0, len(doomed), 500)):
        marks = ",".join("?" * len(chunk))
        for table in ("comments", "post_scores", "post_tickers", "posts"):
            conn.execute(f"DELETE FROM {table} WHERE post_id IN ({marks})", chunk)
    conn.commit()
    return len(doomed)
