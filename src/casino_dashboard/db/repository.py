import sqlite3
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd

from casino_dashboard.data.yfinance_metadata import TickerMetadata
from casino_dashboard.db.schema import _DEFAULT_DB_PATH, init_db
from casino_dashboard.models import NewsItem, TickerSnapshot


# ---------------------------------------------------------------------------
# TYPE HINTS (forward-declared to avoid circular imports at module level)
# ---------------------------------------------------------------------------
# ETFDailySnapshot and DealLogEntry are imported locally inside functions
# that need them to keep this module free of circular-import risk.


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
                analyst_target_mean,
                held_pct_insiders, held_pct_institutions,
                market_cap, revenue_ttm, revenue_growth_yoy,
                profit_margin, beta,
                next_earnings_date, next_earnings_time, last_earnings_date
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                metadata.ticker,
                today,
                metadata.fifty_two_week_high,
                metadata.fifty_two_week_low,
                metadata.short_pct_of_float,
                metadata.short_ratio_days,
                metadata.analyst_target_mean,
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


# ---------------------------------------------------------------------------
# ETF flows
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Deal log
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Sector heat
# ---------------------------------------------------------------------------


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
