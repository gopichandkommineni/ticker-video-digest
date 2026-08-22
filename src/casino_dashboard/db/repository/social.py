"""Reddit mention counts and the posts behind them.

Split out of the original single repository.py — see that module's package
__init__ for the full map.
"""
import sqlite3
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from casino_dashboard.db.schema import _DEFAULT_DB_PATH, init_db


def save_social_mention(
    ticker: str,
    mention_date: date,
    source: str,
    mention_count: int,
    mentions_24h_ago: int | None,
    upvote_sum: int | None,
    subreddit: str = "",
    db_path: Path = _DEFAULT_DB_PATH,
) -> None:
    """INSERT OR REPLACE for idempotent daily re-runs."""
    init_db(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO social_mentions
                (ticker, date, source, mention_count, mentions_24h_ago, upvote_sum, subreddit)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (ticker, mention_date.isoformat(), source, mention_count,
             mentions_24h_ago, upvote_sum, subreddit),
        )

def get_social_history(
    ticker: str,
    source: str,
    days: int,
    db_path: Path = _DEFAULT_DB_PATH,
) -> pd.DataFrame:
    """Return DataFrame[date, mention_count, mentions_24h_ago] newest-first, up to `days` rows."""
    init_db(db_path)
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT date, mention_count, mentions_24h_ago
            FROM social_mentions
            WHERE ticker = ? AND source = ? AND (subreddit = '' OR subreddit IS NULL)
            ORDER BY date DESC
            LIMIT ?
            """,
            (ticker, source, days),
        ).fetchall()
    if not rows:
        return pd.DataFrame(columns=["date", "mention_count", "mentions_24h_ago"])
    return pd.DataFrame(rows, columns=["date", "mention_count", "mentions_24h_ago"])

def get_latest_social_mentions(db_path: Path = _DEFAULT_DB_PATH) -> pd.DataFrame:
    """Return wide-format DataFrame: index=ticker, columns=latest_mention_count, mentions_24h_ago."""
    init_db(db_path)
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT s.ticker, s.mention_count, s.mentions_24h_ago
            FROM social_mentions s
            INNER JOIN (
                SELECT ticker, source, MAX(date) AS max_date
                FROM social_mentions
                WHERE (subreddit = '' OR subreddit IS NULL)
                GROUP BY ticker, source
            ) latest ON s.ticker = latest.ticker
                     AND s.source = latest.source
                     AND s.date = latest.max_date
            WHERE (s.subreddit = '' OR s.subreddit IS NULL)
            """,
        ).fetchall()
    if not rows:
        return pd.DataFrame(columns=["latest_mention_count", "mentions_24h_ago"])
    df = pd.DataFrame(rows, columns=["ticker", "latest_mention_count", "mentions_24h_ago"])
    return df.set_index("ticker")

def save_reddit_posts(posts: "list[SocialPost]", db_path: Path = _DEFAULT_DB_PATH) -> int:
    """Persist individual Reddit posts. INSERT OR REPLACE keyed on (post_id, ticker)
    so re-runs are idempotent and an updated score/comment count overwrites the
    prior row. Returns the number of posts written.
    """
    from core.social_media.base import SocialPost  # noqa: PLC0415, F811

    if not posts:
        return 0
    init_db(db_path)
    fetched_at = datetime.now(tz=timezone.utc).isoformat()
    with sqlite3.connect(db_path) as conn:
        conn.executemany(
            """
            INSERT OR REPLACE INTO reddit_posts
                (post_id, ticker, subreddit, author, title, content, url,
                 score, comment_count, published_at, fetched_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    p.post_id, p.ticker, p.subreddit or "", p.author,
                    p.title or "", p.content, p.url,
                    p.score, p.comment_count, p.published_at.isoformat(), fetched_at,
                )
                for p in posts
            ],
        )
    return len(posts)

def get_recent_reddit_posts(
    ticker: str,
    days: int = 7,
    db_path: Path = _DEFAULT_DB_PATH,
) -> pd.DataFrame:
    """Return recent Reddit posts for *ticker*, newest-first, published within
    the last *days* days.
    """
    init_db(db_path)
    cutoff = (datetime.now(tz=timezone.utc) - timedelta(days=days)).isoformat()
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT post_id, subreddit, author, title, content, url,
                   score, comment_count, published_at
            FROM reddit_posts
            WHERE ticker = ? AND published_at >= ?
            ORDER BY published_at DESC
            """,
            (ticker, cutoff),
        ).fetchall()
    cols = [
        "post_id", "subreddit", "author", "title", "content", "url",
        "score", "comment_count", "published_at",
    ]
    if not rows:
        return pd.DataFrame(columns=cols)
    return pd.DataFrame(rows, columns=cols)
