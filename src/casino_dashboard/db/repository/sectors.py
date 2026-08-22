"""Theme-level data: ETF flows, the deal log, and sector heat rollups.

Split out of the original single repository.py — see that module's package
__init__ for the full map.
"""
import sqlite3
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd

from casino_dashboard.db.schema import _DEFAULT_DB_PATH, init_db


def save_etf_flow(
    etf_ticker: str,
    flow_date: date,
    net_flow_usd: float | None,
    aum_usd: float | None,
    price: float | None,
    db_path: Path = _DEFAULT_DB_PATH,
) -> None:
    """Upsert one ETF daily snapshot. net_flow_usd may be None on first day."""
    init_db(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO etf_flows (etf_ticker, date, net_flow_usd, aum_usd, price)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(etf_ticker, date) DO UPDATE SET
                net_flow_usd = excluded.net_flow_usd,
                aum_usd      = excluded.aum_usd,
                price        = excluded.price
            """,
            (etf_ticker, flow_date.isoformat(), net_flow_usd, aum_usd, price),
        )

def get_etf_flows(
    etf_ticker: str,
    days: int,
    db_path: Path = _DEFAULT_DB_PATH,
) -> pd.DataFrame:
    """Return DataFrame[date, net_flow_usd, aum_usd, price] newest-first."""
    init_db(db_path)
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT date, net_flow_usd, aum_usd, price
            FROM etf_flows
            WHERE etf_ticker = ?
            ORDER BY date DESC
            LIMIT ?
            """,
            (etf_ticker, days),
        ).fetchall()
    if not rows:
        return pd.DataFrame(columns=["date", "net_flow_usd", "aum_usd", "price"])
    return pd.DataFrame(rows, columns=["date", "net_flow_usd", "aum_usd", "price"])

def save_sector_etf_mapping(
    sector: str,
    etf_ticker: str,
    is_primary: bool,
    db_path: Path = _DEFAULT_DB_PATH,
) -> None:
    """Upsert one sector→ETF mapping row."""
    init_db(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO sector_etf_mapping (sector, etf_ticker, is_primary)
            VALUES (?, ?, ?)
            ON CONFLICT(sector, etf_ticker) DO UPDATE SET
                is_primary = excluded.is_primary
            """,
            (sector, etf_ticker, 1 if is_primary else 0),
        )

def get_sector_etf_mapping(db_path: Path = _DEFAULT_DB_PATH) -> pd.DataFrame:
    """Return DataFrame[sector, etf_ticker, is_primary]."""
    init_db(db_path)
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            "SELECT sector, etf_ticker, is_primary FROM sector_etf_mapping ORDER BY sector, is_primary DESC"
        ).fetchall()
    if not rows:
        return pd.DataFrame(columns=["sector", "etf_ticker", "is_primary"])
    return pd.DataFrame(rows, columns=["sector", "etf_ticker", "is_primary"])

def save_deal_log_entries(
    entries: list,  # list[DealLogEntry]
    db_path: Path = _DEFAULT_DB_PATH,
) -> None:
    """Upsert all deal log entries. Uses deal_id as primary key for idempotency."""
    from casino_dashboard.data.deal_log_loader import DealLogEntry  # local import

    init_db(db_path)
    loaded_at = datetime.now(tz=timezone.utc).isoformat()
    with sqlite3.connect(db_path) as conn:
        for entry in entries:
            if not isinstance(entry, DealLogEntry):
                continue
            conn.execute(
                """
                INSERT INTO deal_log
                    (deal_id, date, sector, amount_usd, deal_type,
                     primary_ticker, source_url, summary, loaded_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(deal_id) DO UPDATE SET
                    amount_usd     = excluded.amount_usd,
                    deal_type      = excluded.deal_type,
                    primary_ticker = excluded.primary_ticker,
                    source_url     = excluded.source_url,
                    summary        = excluded.summary,
                    loaded_at      = excluded.loaded_at
                """,
                (
                    entry.deal_id,
                    entry.date.isoformat(),
                    entry.sector,
                    entry.amount_usd,
                    entry.deal_type,
                    entry.primary_ticker,
                    entry.source_url,
                    entry.summary,
                    loaded_at,
                ),
            )

def get_deal_log_for_sector(
    sector: str,
    days: int,
    db_path: Path = _DEFAULT_DB_PATH,
) -> pd.DataFrame:
    """Return DataFrame of deal log entries for a sector within the trailing N days."""
    init_db(db_path)
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT deal_id, date, sector, amount_usd, deal_type,
                   primary_ticker, source_url, summary, loaded_at
            FROM deal_log
            WHERE sector = ?
              AND date >= date('now', ? || ' days')
            ORDER BY date DESC
            """,
            (sector, f"-{days}"),
        ).fetchall()
    cols = ["deal_id", "date", "sector", "amount_usd", "deal_type",
            "primary_ticker", "source_url", "summary", "loaded_at"]
    if not rows:
        return pd.DataFrame(columns=cols)
    return pd.DataFrame(rows, columns=cols)

def get_deal_log_latest_date_per_sector(
    db_path: Path = _DEFAULT_DB_PATH,
) -> dict[str, str | None]:
    """Return {sector: latest_deal_date_iso} for all sectors that appear in the deal log."""
    init_db(db_path)
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT sector, MAX(date) AS latest_date
            FROM deal_log
            GROUP BY sector
            """
        ).fetchall()
    return {row[0]: row[1] for row in rows}

def save_sector_heat(
    sector: str,
    heat_date: date,
    etf_flow_5d_30d_ratio: float | None,
    deal_log_30d_total_usd: float | None,
    deal_log_30d_count: int | None,
    days_since_last_deal: int | None,
    agg_social_velocity: float | None,
    news_heat_ratio: float | None,
    agg_return_30d: float | None,
    pct_above_sma50: float | None,
    agg_atr_pct_change_30d: float | None,
    constituent_count: int,
    db_path: Path = _DEFAULT_DB_PATH,
) -> None:
    """Upsert one sector_heat row for today."""
    init_db(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO sector_heat (
                sector, date,
                etf_flow_5d_30d_ratio, deal_log_30d_total_usd, deal_log_30d_count,
                days_since_last_deal, agg_social_velocity, news_heat_ratio,
                agg_return_30d, pct_above_sma50, agg_atr_pct_change_30d,
                constituent_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(sector, date) DO UPDATE SET
                etf_flow_5d_30d_ratio  = excluded.etf_flow_5d_30d_ratio,
                deal_log_30d_total_usd = excluded.deal_log_30d_total_usd,
                deal_log_30d_count     = excluded.deal_log_30d_count,
                days_since_last_deal   = excluded.days_since_last_deal,
                agg_social_velocity    = excluded.agg_social_velocity,
                news_heat_ratio        = excluded.news_heat_ratio,
                agg_return_30d         = excluded.agg_return_30d,
                pct_above_sma50        = excluded.pct_above_sma50,
                agg_atr_pct_change_30d = excluded.agg_atr_pct_change_30d,
                constituent_count      = excluded.constituent_count
            """,
            (
                sector,
                heat_date.isoformat(),
                etf_flow_5d_30d_ratio,
                deal_log_30d_total_usd,
                deal_log_30d_count,
                days_since_last_deal,
                agg_social_velocity,
                news_heat_ratio,
                agg_return_30d,
                pct_above_sma50,
                agg_atr_pct_change_30d,
                constituent_count,
            ),
        )

def get_sector_heat_latest(db_path: Path = _DEFAULT_DB_PATH) -> pd.DataFrame:
    """Return one row per sector with the latest sector_heat values.

    Indexed by sector. Used by the sector ranking UI.
    """
    init_db(db_path)
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT sh.*
            FROM sector_heat sh
            INNER JOIN (
                SELECT sector, MAX(date) AS max_date
                FROM sector_heat
                GROUP BY sector
            ) latest ON sh.sector = latest.sector AND sh.date = latest.max_date
            ORDER BY sh.sector
            """
        ).fetchall()
        col_names = [desc[0] for desc in conn.execute(
            "SELECT * FROM sector_heat LIMIT 0"
        ).description or []]

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows, columns=col_names)
    return df.set_index("sector")
