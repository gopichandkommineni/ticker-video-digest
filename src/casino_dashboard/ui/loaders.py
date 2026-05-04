"""Cached data loaders for the Casino Dashboard UI."""
import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st

from casino_dashboard.db.repository import get_history, get_latest_signals_all_tickers
from casino_dashboard.db.schema import _DEFAULT_DB_PATH, init_db
from casino_dashboard.models import NewsItem
from casino_dashboard.universe import load_universe


def resolve_sector_default(
    session_state: dict,
    query_params: dict,
    all_sector_ids: list[str],
) -> list[str]:
    """Return sector_id list to pre-select in the All Tickers multiselect.

    Priority: session_state["preselect_sector"] (set by card click via
    st.switch_page, which doesn't preserve query_params) → query_params["sector"]
    (for direct URL access) → all sectors as fallback.
    """
    sector_id = session_state.pop("preselect_sector", None) or query_params.get(
        "sector", None
    )
    if sector_id and sector_id in all_sector_ids:
        return [sector_id]
    return list(all_sector_ids)


@st.cache_data(ttl=3600)
def load_signals_matrix(db_path: str = str(_DEFAULT_DB_PATH)) -> pd.DataFrame:
    """Return wide-format DataFrame of latest signals for all tickers."""
    return get_latest_signals_all_tickers(Path(db_path))


@st.cache_data(ttl=3600)
def load_universe_for_ui() -> dict:
    """Return dict with 'sectors' (id→Sector) and 'ticker_to_sectors' (ticker→[id,...])."""
    universe = load_universe()
    ticker_to_sectors: dict[str, list[str]] = {}
    for sector_id, sector in universe.sectors.items():
        for ticker in sector.tickers:
            ticker_to_sectors.setdefault(ticker, []).append(sector_id)
    return {
        "sectors": universe.sectors,
        "ticker_to_sectors": ticker_to_sectors,
    }


@st.cache_data(ttl=3600)
def load_price_history(
    ticker: str, days: int = 60, db_path: str = str(_DEFAULT_DB_PATH)
) -> pd.DataFrame:
    """Return DataFrame with columns [date, close, volume] for a ticker, oldest-first."""
    history = get_history(ticker, days, Path(db_path))
    if not history:
        return pd.DataFrame(columns=["date", "close", "volume"])
    records = [
        {"date": snap.date, "close": snap.close, "volume": snap.volume}
        for snap in reversed(history)
    ]
    return pd.DataFrame(records)


@st.cache_data(ttl=3600)
def load_news_for_ticker(
    ticker: str, limit: int = 5, db_path: str = str(_DEFAULT_DB_PATH)
) -> list[NewsItem]:
    """Return most recent news items for a ticker."""
    history = get_history(ticker, 1, Path(db_path))
    if not history:
        return []
    return history[0].news_items[:limit]


@st.cache_data(ttl=3600)
def load_latest_prices(db_path: str = str(_DEFAULT_DB_PATH)) -> pd.DataFrame:
    """Return DataFrame with close prices indexed by ticker (latest available date)."""
    path = Path(db_path)
    init_db(path)
    with sqlite3.connect(path) as conn:
        rows = conn.execute(
            """
            SELECT s.ticker, s.close
            FROM ticker_snapshots s
            INNER JOIN (
                SELECT ticker, MAX(date) AS max_date
                FROM ticker_snapshots
                GROUP BY ticker
            ) latest ON s.ticker = latest.ticker AND s.date = latest.max_date
            """
        ).fetchall()
    if not rows:
        return pd.DataFrame(columns=["close"])
    return pd.DataFrame(rows, columns=["ticker", "close"]).set_index("ticker")
