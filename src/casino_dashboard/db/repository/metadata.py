"""Company facts (name, market cap, earnings date) and hand-written notes.

Split out of the original single repository.py — see that module's package
__init__ for the full map.
"""
import sqlite3
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd

from casino_dashboard.data.yfinance_metadata import TickerMetadata
from casino_dashboard.db.schema import _DEFAULT_DB_PATH, init_db


def save_ticker_metadata(metadata: TickerMetadata, db_path: Path = _DEFAULT_DB_PATH) -> None:
    """INSERT OR REPLACE on (ticker, date) for idempotent re-runs."""
    init_db(db_path)
    today = date.today().isoformat()

    def _to_str(d: date | None) -> str | None:
        return d.isoformat() if d is not None else None

    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO ticker_metadata (
                ticker, date,
                fifty_two_week_high, fifty_two_week_low,
                short_pct_of_float, short_ratio_days,
                analyst_target_mean, analyst_target_high,
                analyst_target_low, analyst_count,
                held_pct_insiders, held_pct_institutions,
                market_cap, revenue_ttm, revenue_growth_yoy,
                profit_margin, beta,
                next_earnings_date, next_earnings_time, last_earnings_date
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                metadata.ticker,
                today,
                metadata.fifty_two_week_high,
                metadata.fifty_two_week_low,
                metadata.short_pct_of_float,
                metadata.short_ratio_days,
                metadata.analyst_target_mean,
                metadata.analyst_target_high,
                metadata.analyst_target_low,
                metadata.analyst_count,
                metadata.held_pct_insiders,
                metadata.held_pct_institutions,
                metadata.market_cap,
                metadata.revenue_ttm,
                metadata.revenue_growth_yoy,
                metadata.profit_margin,
                metadata.beta,
                _to_str(metadata.next_earnings_date),
                metadata.next_earnings_time,
                _to_str(metadata.last_earnings_date),
            ),
        )

def get_latest_metadata_all_tickers(db_path: Path = _DEFAULT_DB_PATH) -> pd.DataFrame:
    """Return wide-format DataFrame indexed by ticker with all metadata fields.

    Uses the most recent date per ticker. This is the primary read path for the UI.
    """
    init_db(db_path)
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT m.*
            FROM ticker_metadata m
            INNER JOIN (
                SELECT ticker, MAX(date) AS max_date
                FROM ticker_metadata
                GROUP BY ticker
            ) latest ON m.ticker = latest.ticker AND m.date = latest.max_date
            """
        ).fetchall()
        col_names = [desc[0] for desc in conn.execute(
            "SELECT * FROM ticker_metadata LIMIT 0"
        ).description or []]

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows, columns=col_names)
    return df.set_index("ticker")

def save_manual_note(
    ticker: str,
    catalyst: str | None,
    red_flag: str | None,
    db_path: Path = _DEFAULT_DB_PATH,
) -> None:
    """Upsert catalyst/red_flag for a ticker, preserving any existing notes/tags."""
    init_db(db_path)
    updated_at = datetime.now(tz=timezone.utc).isoformat()
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO manual_notes (ticker, catalyst, red_flag, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(ticker) DO UPDATE SET
                catalyst   = excluded.catalyst,
                red_flag   = excluded.red_flag,
                updated_at = excluded.updated_at
            """,
            (ticker, catalyst, red_flag, updated_at),
        )

def save_user_annotations(
    ticker: str,
    notes: str | None,
    tags: str | None,
    db_path: Path = _DEFAULT_DB_PATH,
) -> None:
    """Upsert user-editable notes/tags for a ticker, preserving catalyst/red_flag."""
    init_db(db_path)
    updated_at = datetime.now(tz=timezone.utc).isoformat()
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO manual_notes (ticker, notes, tags, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(ticker) DO UPDATE SET
                notes      = excluded.notes,
                tags       = excluded.tags,
                updated_at = excluded.updated_at
            """,
            (ticker, notes or None, tags or None, updated_at),
        )

def get_manual_notes_all_tickers(db_path: Path = _DEFAULT_DB_PATH) -> pd.DataFrame:
    """Return DataFrame indexed by ticker with catalyst, red_flag, notes, tags columns."""
    init_db(db_path)
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            "SELECT ticker, catalyst, red_flag, notes, tags FROM manual_notes"
        ).fetchall()
    if not rows:
        return pd.DataFrame(columns=["catalyst", "red_flag", "notes", "tags"])
    df = pd.DataFrame(rows, columns=["ticker", "catalyst", "red_flag", "notes", "tags"])
    return df.set_index("ticker")
