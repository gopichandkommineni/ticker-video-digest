"""Digest tables in data/reddit.db, and the read side the dashboard uses.

    digests   one row per stock per day: summary, mood, status, model
    insights  the insight list for that digest, in order, each with its
              source posts (url, title, subreddit, score) stored alongside —
              so a link still works after ingestion prunes the post itself

Re-running a day replaces that day's digest for the stock.
"""
import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from pydantic import BaseModel, Field

from core.social_media.reddit.ingest import db

_SCHEMA = """
CREATE TABLE IF NOT EXISTS digests (
    ticker            TEXT NOT NULL,
    digest_date       TEXT NOT NULL,          -- YYYY-MM-DD (UTC)
    created_at        TEXT NOT NULL,
    status            TEXT NOT NULL,          -- ok | quiet | failed
    model             TEXT,
    posts_considered  INTEGER NOT NULL DEFAULT 0,
    summary           TEXT NOT NULL DEFAULT '',
    mood              TEXT,                   -- bullish | bearish | mixed | neutral
    error             TEXT,
    PRIMARY KEY (ticker, digest_date)
);

CREATE TABLE IF NOT EXISTS insights (
    insight_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker        TEXT NOT NULL,
    digest_date   TEXT NOT NULL,
    rank          INTEGER NOT NULL,
    kind          TEXT NOT NULL,
    stance        TEXT NOT NULL,
    headline      TEXT NOT NULL,
    detail        TEXT NOT NULL,
    sources       TEXT NOT NULL              -- JSON list of SourcePost
);
CREATE INDEX IF NOT EXISTS idx_insights_ticker ON insights(ticker, digest_date);
"""


class SourcePost(BaseModel):
    post_id: str
    url: str
    title: str
    subreddit: str
    score: int = 0


class Insight(BaseModel):
    kind: str
    stance: str
    headline: str
    detail: str
    sources: list[SourcePost] = Field(default_factory=list)


class Digest(BaseModel):
    ticker: str
    digest_date: str
    created_at: str
    status: str
    model: str | None = None
    posts_considered: int = 0
    summary: str = ""
    mood: str | None = None
    error: str | None = None
    insights: list[Insight] = Field(default_factory=list)


def connect(path: Path | None = None) -> sqlite3.Connection:
    """The ingestion store, with the digest tables in place."""
    conn = db.connect(path)
    conn.executescript(_SCHEMA)
    return conn


def last_digest_at(conn: sqlite3.Connection, ticker: str, before_date: str) -> datetime | None:
    """When the last digest that read posts (ok or quiet) was written, on a day
    before *before_date* — so re-running a day rebuilds that day's digest from
    everything since the previous day's, rather than from the morning run."""
    row = conn.execute(
        "SELECT created_at FROM digests WHERE ticker=? AND status IN ('ok','quiet') "
        "AND digest_date < ? ORDER BY created_at DESC LIMIT 1",
        (ticker, before_date),
    ).fetchone()
    return datetime.fromisoformat(row["created_at"]) if row else None


def has_ok_digest(conn: sqlite3.Connection, ticker: str, digest_date: str) -> bool:
    return conn.execute(
        "SELECT 1 FROM digests WHERE ticker=? AND digest_date=? AND status='ok'",
        (ticker, digest_date),
    ).fetchone() is not None


def save_digest(conn: sqlite3.Connection, digest: Digest) -> None:
    conn.execute(
        "DELETE FROM insights WHERE ticker=? AND digest_date=?",
        (digest.ticker, digest.digest_date),
    )
    conn.execute(
        """INSERT OR REPLACE INTO digests (ticker, digest_date, created_at, status, model,
               posts_considered, summary, mood, error)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (digest.ticker, digest.digest_date, digest.created_at, digest.status, digest.model,
         digest.posts_considered, digest.summary, digest.mood, digest.error),
    )
    for rank, ins in enumerate(digest.insights):
        conn.execute(
            """INSERT INTO insights (ticker, digest_date, rank, kind, stance, headline, detail, sources)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (digest.ticker, digest.digest_date, rank, ins.kind, ins.stance, ins.headline,
             ins.detail, json.dumps([s.model_dump() for s in ins.sources])),
        )
    conn.commit()


def prune_digests(conn: sqlite3.Connection, now: datetime, keep_days: int) -> int:
    cutoff = (now - timedelta(days=keep_days)).date().isoformat()
    conn.execute("DELETE FROM insights WHERE digest_date < ?", (cutoff,))
    cur = conn.execute("DELETE FROM digests WHERE digest_date < ?", (cutoff,))
    conn.commit()
    return cur.rowcount


def load_recent(ticker: str, days: int = 7, path: Path | None = None,
                today: datetime | None = None) -> list[Digest]:
    """Digests for *ticker* from the last *days* days, newest first.

    Read-only: never creates reddit.db (the dashboard must not leave a stray
    file in data/). Returns [] when there is no database or no digest yet.
    """
    path = path or db.default_db_path()
    if not path.exists():
        return []
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "digests" not in tables:
            return []
        since = ((today or datetime.utcnow()) - timedelta(days=days)).date().isoformat()
        rows = conn.execute(
            "SELECT * FROM digests WHERE ticker=? AND digest_date >= ? ORDER BY digest_date DESC",
            (ticker.upper(), since),
        ).fetchall()
        return [_digest(conn, r) for r in rows]
    finally:
        conn.close()


def _digest(conn: sqlite3.Connection, row: sqlite3.Row) -> Digest:
    """A digests row with its insights."""
    d = Digest(**{k: row[k] for k in row.keys()})
    d.insights = [
        Insight(kind=i["kind"], stance=i["stance"], headline=i["headline"],
                detail=i["detail"],
                sources=[SourcePost(**s) for s in json.loads(i["sources"])])
        for i in conn.execute(
            "SELECT * FROM insights WHERE ticker=? AND digest_date=? ORDER BY rank",
            (d.ticker, d.digest_date),
        )
    ]
    return d


def merge_recent(src: Path, dst: Path, since_date: str) -> list[str]:
    """Copy digests dated *since_date* or later from *src* into *dst*.

    For a digest written away from the main copy (the local job): *src* is the
    file it wrote, *dst* the latest production reddit.db. Only digest rows move,
    so posts ingested into *dst* in the meantime are kept. Same rules as a
    re-run: a newer digest replaces an older one, but a quiet or failed one never
    replaces a good one. Returns "TICKER date" for each digest copied.
    """
    s = sqlite3.connect(f"file:{src}?mode=ro", uri=True)
    s.row_factory = sqlite3.Row
    d = connect(dst)
    copied: list[str] = []
    try:
        for row in s.execute("SELECT * FROM digests WHERE digest_date >= ?", (since_date,)):
            new = _digest(s, row)
            have = d.execute("SELECT created_at, status FROM digests WHERE ticker=? AND digest_date=?",
                             (new.ticker, new.digest_date)).fetchone()
            if have and (have["created_at"] >= new.created_at
                         or (have["status"] == "ok" and new.status != "ok")):
                continue
            save_digest(d, new)
            copied.append(f"{new.ticker} {new.digest_date}")
    finally:
        s.close()
        d.close()
    return copied
