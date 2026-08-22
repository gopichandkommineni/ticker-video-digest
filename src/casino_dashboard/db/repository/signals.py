"""Computed per-ticker numbers: returns, RSI, distance from high/low.

Split out of the original single repository.py — see that module's package
__init__ for the full map.
"""
import sqlite3
from datetime import date
from pathlib import Path

import pandas as pd

from casino_dashboard.db.schema import _DEFAULT_DB_PATH, init_db


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

def get_signal_for_ticker_on_date(
    ticker: str,
    signal_name: str,
    target_date: date,
    db_path: Path = _DEFAULT_DB_PATH,
) -> float | None:
    """Return the signal value for a ticker on or before target_date (latest available)."""
    init_db(db_path)
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT value FROM signals
            WHERE ticker = ? AND signal_name = ? AND date <= ?
            ORDER BY date DESC
            LIMIT 1
            """,
            (ticker, signal_name, target_date.isoformat()),
        ).fetchone()
    return row[0] if row else None

def get_latest_signal_for_tickers(
    tickers: list[str],
    signal_name: str,
    db_path: Path = _DEFAULT_DB_PATH,
) -> dict[str, float]:
    """Return {ticker: latest_value} for signal_name across a list of tickers.

    Only tickers that have a value are included in the result.
    """
    if not tickers:
        return {}
    init_db(db_path)
    placeholders = ",".join("?" * len(tickers))
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            f"""
            SELECT s.ticker, s.value
            FROM signals s
            INNER JOIN (
                SELECT ticker, MAX(date) AS max_date
                FROM signals
                WHERE ticker IN ({placeholders}) AND signal_name = ?
                GROUP BY ticker
            ) latest ON s.ticker = latest.ticker AND s.date = latest.max_date
            WHERE s.signal_name = ?
            """,
            (*tickers, signal_name, signal_name),
        ).fetchall()
    return {row[0]: row[1] for row in rows if row[1] is not None}

def get_news_count_for_tickers(
    tickers: list[str],
    days: int,
    db_path: Path = _DEFAULT_DB_PATH,
) -> int:
    """Count news_items rows for a list of tickers within the trailing N days.

    Filters by published_at (when the article was published) so that the
    count reflects actual news cadence, not scrape timing.
    """
    if not tickers:
        return 0
    init_db(db_path)
    placeholders = ",".join("?" * len(tickers))
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            f"""
            SELECT COUNT(*)
            FROM news_items
            WHERE ticker IN ({placeholders})
              AND date(published_at) >= date('now', ? || ' days')
            """,
            (*tickers, f"-{days}"),
        ).fetchone()
    return row[0] if row else 0
