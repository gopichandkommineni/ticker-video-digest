"""Cached data loaders for the Casino Dashboard UI."""
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from casino_dashboard.db.repository import (
    get_deal_log_for_sector,
    get_history,
    get_latest_metadata_all_tickers,
    get_latest_signal_for_tickers,
    get_latest_signals_all_tickers,
    get_latest_social_mentions,
    get_manual_notes_all_tickers,
    get_news_count_for_tickers,
    get_recent_trades_for_members,
    get_sector_heat_latest,
    get_social_history,
    get_star_members,
    get_watched_members,
    save_user_annotations,
)
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


@st.cache_data(ttl=300)
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
def load_social_history(
    ticker: str, days: int = 30, db_path: str = str(_DEFAULT_DB_PATH)
) -> pd.DataFrame:
    """Return DataFrame[date, mention_count, mentions_24h_ago] for social mentions (newest-first)."""
    return get_social_history(ticker, "apewisdom", days, Path(db_path))


@st.cache_data(ttl=3600)
def load_latest_social_mentions(db_path: str = str(_DEFAULT_DB_PATH)) -> pd.DataFrame:
    """Return wide-format DataFrame of latest social mention counts, indexed by ticker."""
    return get_latest_social_mentions(Path(db_path))


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


# ── Sector heat loaders (5-minute TTL) ────────────────────────────────────────


@st.cache_data(ttl=300)
def load_sector_heat(db_path: str = str(_DEFAULT_DB_PATH)) -> pd.DataFrame:
    """Return sector_heat DataFrame indexed by sector (latest row per sector).

    Returns empty DataFrame if table has not yet been populated by the daily refresh.
    """
    return get_sector_heat_latest(Path(db_path))


@st.cache_data(ttl=300)
def load_sector_constituents_ranking(
    sector: str, db_path: str = str(_DEFAULT_DB_PATH)
) -> pd.DataFrame:
    """Return constituent-level ranking data for all tickers in a sector.

    Columns: ticker, return_1m, pct_above_sma50, rsi_14, near_breakout,
             near_breakdown, apewisdom_velocity_24h, news_7d_count
    """
    universe = load_universe()
    if sector not in universe.sectors:
        return pd.DataFrame()

    tickers = universe.sectors[sector].tickers
    path = Path(db_path)

    signal_names = [
        "return_1m", "pct_above_sma50", "rsi_14",
        "near_breakout", "near_breakdown", "apewisdom_velocity_24h",
    ]

    rows = []
    for ticker in tickers:
        row: dict = {"ticker": ticker}
        for sig in signal_names:
            vals = get_latest_signal_for_tickers([ticker], sig, db_path=path)
            row[sig] = vals.get(ticker)
        row["news_7d_count"] = get_news_count_for_tickers([ticker], days=7, db_path=path)
        rows.append(row)

    return pd.DataFrame(rows).set_index("ticker") if rows else pd.DataFrame()


@st.cache_data(ttl=300)
def load_recent_deals(
    sector: str, days: int = 30, db_path: str = str(_DEFAULT_DB_PATH)
) -> pd.DataFrame:
    """Return recent deal log entries for a sector within the trailing N days."""
    return get_deal_log_for_sector(sector, days=days, db_path=Path(db_path))


# ── Per-ticker detail page loaders (5-minute TTL) ─────────────────────────────


@st.cache_data(ttl=300)
def load_latest_snapshot_for_ticker(
    ticker: str, db_path: str = str(_DEFAULT_DB_PATH)
) -> dict | None:
    """Return the most recent snapshot fields for a single ticker, or None."""
    history = get_history(ticker, 1, Path(db_path))
    if not history:
        return None
    snap = history[0]
    return {
        "close": snap.close,
        "volume": snap.volume,
        "avg_volume_30d": snap.avg_volume_30d,
        "date": snap.date,
    }


@st.cache_data(ttl=300)
def load_ticker_metadata_all(db_path: str = str(_DEFAULT_DB_PATH)) -> pd.DataFrame:
    """Return ticker metadata DataFrame indexed by ticker (5-min TTL for detail page)."""
    return get_latest_metadata_all_tickers(Path(db_path))


@st.cache_data(ttl=300)
def load_manual_notes_all(db_path: str = str(_DEFAULT_DB_PATH)) -> pd.DataFrame:
    """Return manual notes DataFrame indexed by ticker (5-min TTL for detail page)."""
    return get_manual_notes_all_tickers(Path(db_path))


@st.cache_data(ttl=300)
def load_signals_for_detail(db_path: str = str(_DEFAULT_DB_PATH)) -> pd.DataFrame:
    """Return signals matrix with 5-min TTL for use by the per-ticker detail page."""
    return get_latest_signals_all_tickers(Path(db_path))


# ── Congress page loaders (1-hour TTL — refreshed by daily job) ───────────────


def _format_congress_trades_df(df: pd.DataFrame, days_back: int) -> pd.DataFrame:
    """Shared formatting applied to both committee and star-trader trade tables."""
    if df.empty:
        return pd.DataFrame(
            columns=[
                "member", "party", "chamber", "ticker", "transaction_type",
                "transaction_date", "disclosure_date", "amount_est", "days_lag",
            ]
        )
    df = df.copy()
    df["amount_est"] = df.apply(
        lambda r: (
            f"${((r['amount_low'] + r['amount_high']) / 2):,.0f}"
            if pd.notna(r.get("amount_low")) and pd.notna(r.get("amount_high"))
            else (f"${r['amount_low']:,.0f}+" if pd.notna(r.get("amount_low")) else "—")
        ),
        axis=1,
    )
    df["transaction_date"] = pd.to_datetime(df["transaction_date"], errors="coerce").dt.strftime("%Y-%m-%d")
    df["disclosure_date"] = pd.to_datetime(df["disclosure_date"], errors="coerce").dt.strftime("%Y-%m-%d")
    df["days_lag"] = (
        pd.to_datetime(df["disclosure_date"], errors="coerce")
        - pd.to_datetime(df["transaction_date"], errors="coerce")
    ).dt.days
    df = df.rename(columns={"full_name": "member"})
    cols = ["member", "party", "chamber", "ticker", "transaction_type",
            "transaction_date", "disclosure_date", "amount_est", "days_lag"]
    existing = [c for c in cols if c in df.columns]
    return df[existing].sort_values("disclosure_date", ascending=False)


@st.cache_data(ttl=3600)
def load_committee_trades_table(
    days_back: int = 90,
    db_path: str = str(_DEFAULT_DB_PATH),
) -> pd.DataFrame:
    """Return trades for committee-watched members (is_watched=1), last days_back days.

    Columns: member, party, chamber, ticker, transaction_type,
             transaction_date, disclosure_date, amount_est, days_lag.
    """
    path = Path(db_path)
    init_db(path)
    members_df = get_watched_members(path)
    if members_df.empty:
        return _format_congress_trades_df(pd.DataFrame(), days_back)
    bioguide_ids = members_df["bioguide_id"].tolist()
    trades_df = get_recent_trades_for_members(bioguide_ids, days_back, path)
    return _format_congress_trades_df(trades_df, days_back)


@st.cache_data(ttl=3600)
def load_star_trader_trades_table(
    days_back: int = 90,
    db_path: str = str(_DEFAULT_DB_PATH),
) -> pd.DataFrame:
    """Return trades for star-flagged members (is_star=1), last days_back days.

    Same columns as load_committee_trades_table.
    """
    path = Path(db_path)
    init_db(path)
    members_df = get_star_members(path)
    if members_df.empty:
        return _format_congress_trades_df(pd.DataFrame(), days_back)
    bioguide_ids = members_df["bioguide_id"].tolist()
    trades_df = get_recent_trades_for_members(bioguide_ids, days_back, path)
    return _format_congress_trades_df(trades_df, days_back)


def get_last_congress_refresh_timestamp(db_path: str = str(_DEFAULT_DB_PATH)) -> str:
    """Return the most recent fetched_at timestamp from congress_trades, or 'never'."""
    path = Path(db_path)
    init_db(path)
    try:
        with sqlite3.connect(path) as conn:
            row = conn.execute(
                "SELECT MAX(fetched_at) FROM congress_trades"
            ).fetchone()
        if row and row[0]:
            return str(row[0])[:19].replace("T", " ") + " UTC"
    except Exception:
        pass
    return "never"


@st.cache_data(ttl=300)
def load_recent_news_all_dates(
    ticker: str, limit: int = 5, db_path: str = str(_DEFAULT_DB_PATH)
) -> list[NewsItem]:
    """Return the most recent news items for a ticker across all stored snapshot dates."""
    path = Path(db_path)
    init_db(path)
    with sqlite3.connect(path) as conn:
        rows = conn.execute(
            """
            SELECT title, link, publisher, published_at
            FROM news_items
            WHERE ticker = ?
            ORDER BY published_at DESC
            LIMIT ?
            """,
            (ticker, limit),
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
