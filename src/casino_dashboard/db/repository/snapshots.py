"""Daily OHLCV rows and their attached news items.

Split out of the original single repository.py — see that module's package
__init__ for the full map.
"""
import sqlite3
from datetime import date, datetime, timezone
from pathlib import Path

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
    items = []
    for r in rows:
        try:
            pub = datetime.fromisoformat(r[3]) if r[3] else None
        except (ValueError, TypeError):
            pub = None
        if pub is None:
            continue
        items.append(NewsItem(title=r[0], link=r[1], publisher=r[2], published_at=pub))
    return items

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
