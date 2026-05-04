import sqlite3
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd

from casino_dashboard.db.schema import _DEFAULT_DB_PATH, init_db
from casino_dashboard.models import NewsItem, TickerSnapshot


def save_snapshot(snap: TickerSnapshot, db_path: Path = _DEFAULT_DB_PATH) -> None:
    init_db(db_path)
    fetched_at = datetime.now(tz=timezone.utc).isoformat()

    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO ticker_snapshots
                (ticker, date, open, high, low, close, adj_close, volume, avg_volume_30d)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(ticker, date) DO UPDATE SET
                open          = excluded.open,
                high          = excluded.high,
                low           = excluded.low,
                close         = excluded.close,
                adj_close     = excluded.adj_close,
                volume        = excluded.volume,
                avg_volume_30d = excluded.avg_volume_30d
            """,
            (
                snap.ticker,
                snap.date.isoformat(),
                snap.open,
                snap.high,
                snap.low,
                snap.close,
                snap.adj_close,
                snap.volume,
                snap.avg_volume_30d,
            ),
        )
        if snap.news_items:
            existing_links = {row[0] for row in conn.execute(
                "SELECT link FROM news_items WHERE ticker = ?", (snap.ticker,)
            ).fetchall()}
            new_news = [item for item in snap.news_items if item.link not in existing_links]
            conn.executemany(
                """
                INSERT INTO news_items
                    (ticker, snap_date, title, link, publisher, published_at, fetched_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        snap.ticker,
                        snap.date.isoformat(),
                        item.title,
                        item.link,
                        item.publisher,
                        item.published_at.isoformat(),
                        fetched_at,
                    )
                    for item in new_news
                ],
            )


def get_snapshot(
    ticker: str, target_date: date, db_path: Path = _DEFAULT_DB_PATH
) -> TickerSnapshot | None:
    init_db(db_path)
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT ticker, date, open, high, low, close, adj_close, volume, avg_volume_30d
            FROM ticker_snapshots
            WHERE ticker = ? AND date = ?
            """,
            (ticker, target_date.isoformat()),
        ).fetchone()

    if row is None:
        return None

    news = _fetch_news(ticker, target_date, db_path)
    return _row_to_snapshot(row, news)


def get_history(
    ticker: str, days: int, db_path: Path = _DEFAULT_DB_PATH
) -> list[TickerSnapshot]:
    init_db(db_path)
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT ticker, date, open, high, low, close, adj_close, volume, avg_volume_30d
            FROM ticker_snapshots
            WHERE ticker = ?
            ORDER BY date DESC
            LIMIT ?
            """,
            (ticker, days),
        ).fetchall()

    snapshots = []
    for row in rows:
        snap_date = date.fromisoformat(row[1])
        news = _fetch_news(ticker, snap_date, db_path)
        snapshots.append(_row_to_snapshot(row, news))
    return snapshots


def save_signal(
    ticker: str, signal_date: date, signal_name: str, value: float, db_path: Path = _DEFAULT_DB_PATH
) -> None:
    init_db(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO signals (ticker, date, signal_name, value)
            VALUES (?, ?, ?, ?)
            """,
            (ticker, signal_date.isoformat(), signal_name, value),
        )


def get_signals(
    ticker: str, signal_date: date, db_path: Path = _DEFAULT_DB_PATH
) -> dict[str, float]:
    init_db(db_path)
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT signal_name, value
            FROM signals
            WHERE ticker = ? AND date = ?
            """,
            (ticker, signal_date.isoformat()),
        ).fetchall()
    return {row[0]: row[1] for row in rows}


def get_latest_signals_all_tickers(db_path: Path = _DEFAULT_DB_PATH) -> pd.DataFrame:
    init_db(db_path)
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT s.ticker, s.signal_name, s.value
            FROM signals s
            INNER JOIN (
                SELECT ticker, MAX(date) AS max_date
                FROM signals
                GROUP BY ticker
            ) latest ON s.ticker = latest.ticker AND s.date = latest.max_date
            """
        ).fetchall()

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows, columns=["ticker", "signal_name", "value"])
    return df.pivot(index="ticker", columns="signal_name", values="value")


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
            WHERE ticker = ? AND source = ? AND subreddit = ''
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
                WHERE subreddit = ''
                GROUP BY ticker, source
            ) latest ON s.ticker = latest.ticker
                     AND s.source = latest.source
                     AND s.date = latest.max_date
            WHERE s.subreddit = ''
            """,
        ).fetchall()
    if not rows:
        return pd.DataFrame(columns=["latest_mention_count", "mentions_24h_ago"])
    df = pd.DataFrame(rows, columns=["ticker", "latest_mention_count", "mentions_24h_ago"])
    return df.set_index("ticker")


def _fetch_news(ticker: str, snap_date: date, db_path: Path) -> list[NewsItem]:
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT title, link, publisher, published_at
            FROM news_items
            WHERE ticker = ?
              AND snap_date = ?
            ORDER BY published_at DESC
            """,
            (ticker, snap_date.isoformat()),
        ).fetchall()
    return [
        NewsItem(
            title=r[0],
            link=r[1],
            publisher=r[2],
            published_at=datetime.fromisoformat(r[3]),
        )
        for r in rows
    ]


def _row_to_snapshot(row: tuple, news: list[NewsItem]) -> TickerSnapshot:
    return TickerSnapshot(
        ticker=row[0],
        date=date.fromisoformat(row[1]),
        open=row[2],
        high=row[3],
        low=row[4],
        close=row[5],
        adj_close=row[6],
        volume=row[7],
        avg_volume_30d=row[8],
        news_items=news,
    )
