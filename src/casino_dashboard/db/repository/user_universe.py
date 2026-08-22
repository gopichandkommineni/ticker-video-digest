"""Tickers and themes added through the Add Stocks page, on top of themes.yaml.

Split out of the original single repository.py — see that module's package
__init__ for the full map.
"""
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from casino_dashboard.db.schema import _DEFAULT_DB_PATH, init_db


def add_user_ticker(
    ticker: str,
    theme_id: str,
    company_name: str | None,
    added_by: str | None,
    db_path: Path = _DEFAULT_DB_PATH,
) -> None:
    """Insert a new user-added ticker with status='pending'.

    Raises ValueError on duplicate ticker — callers must check for collisions first.
    """
    init_db(db_path)
    added_at = datetime.now(tz=timezone.utc).isoformat()
    try:
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                """
                INSERT INTO user_added_tickers
                    (ticker, theme_id, company_name, status, added_by, added_at)
                VALUES (?, ?, ?, 'pending', ?, ?)
                """,
                (ticker, theme_id, company_name, added_by, added_at),
            )
    except sqlite3.IntegrityError as exc:
        raise ValueError(f"Ticker {ticker!r} already exists in user_added_tickers") from exc

def add_user_theme(
    theme_id: str,
    display_name: str,
    description: str,
    speculative: bool,
    created_by: str | None,
    db_path: Path = _DEFAULT_DB_PATH,
) -> None:
    """Insert a new user-added theme.

    Raises ValueError on duplicate theme_id — callers must check for collisions first.
    """
    init_db(db_path)
    created_at = datetime.now(tz=timezone.utc).isoformat()
    try:
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                """
                INSERT INTO user_added_themes
                    (theme_id, display_name, description, speculative, created_by, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (theme_id, display_name, description, 1 if speculative else 0, created_by, created_at),
            )
    except sqlite3.IntegrityError as exc:
        raise ValueError(f"Theme {theme_id!r} already exists in user_added_themes") from exc

def set_user_ticker_status(
    ticker: str,
    status: str,
    status_detail: str | None,
    last_fetch_at: str | None,
    db_path: Path = _DEFAULT_DB_PATH,
) -> None:
    """Update the status (and optional detail + last_fetch_at) for a user-added ticker."""
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            UPDATE user_added_tickers
               SET status = ?, status_detail = ?, last_fetch_at = ?
             WHERE ticker = ?
            """,
            (status, status_detail, last_fetch_at, ticker),
        )

def remove_user_ticker(ticker: str, db_path: Path = _DEFAULT_DB_PATH) -> None:
    """Delete a user-added ticker row."""
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "DELETE FROM user_added_tickers WHERE ticker = ?",
            (ticker,),
        )

def get_user_added_tickers(db_path: Path = _DEFAULT_DB_PATH) -> pd.DataFrame:
    """Return all rows from user_added_tickers. Empty DataFrame if table doesn't exist."""
    cols = ["ticker", "theme_id", "company_name", "status", "status_detail",
            "added_by", "added_at", "last_fetch_at"]
    try:
        with sqlite3.connect(db_path) as conn:
            rows = conn.execute(
                "SELECT ticker, theme_id, company_name, status, status_detail, "
                "added_by, added_at, last_fetch_at FROM user_added_tickers"
            ).fetchall()
    except sqlite3.OperationalError:
        return pd.DataFrame(columns=cols)
    if not rows:
        return pd.DataFrame(columns=cols)
    return pd.DataFrame(rows, columns=cols)

def get_user_added_themes(db_path: Path = _DEFAULT_DB_PATH) -> pd.DataFrame:
    """Return all rows from user_added_themes. Empty DataFrame if table doesn't exist."""
    cols = ["theme_id", "display_name", "description", "speculative", "created_by", "created_at"]
    try:
        with sqlite3.connect(db_path) as conn:
            rows = conn.execute(
                "SELECT theme_id, display_name, description, speculative, created_by, created_at "
                "FROM user_added_themes"
            ).fetchall()
    except sqlite3.OperationalError:
        return pd.DataFrame(columns=cols)
    if not rows:
        return pd.DataFrame(columns=cols)
    return pd.DataFrame(rows, columns=cols)
