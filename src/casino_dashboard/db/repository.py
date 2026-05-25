import sqlite3
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd

from casino_dashboard.data.yfinance_metadata import TickerMetadata
from casino_dashboard.db.schema import _DEFAULT_DB_PATH, init_db
from casino_dashboard.models import CongressTrade, NewsItem, TickerSnapshot


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


# ---------------------------------------------------------------------------
# Helpers for sector aggregation
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Congress members and trades
# ---------------------------------------------------------------------------


def upsert_congress_members(members: list[dict], db_path: Path = _DEFAULT_DB_PATH) -> None:
    """Upsert congress_members rows. members is a list of dicts with keys:
    bioguide_id, full_name, first_name, last_name, party, state, chamber,
    is_watched (int 0/1), is_star (int 0/1).

    Uses ON CONFLICT DO UPDATE so both is_watched and is_star flags are
    preserved when a member appears in both the committee list and the
    star-trader list (caller should pass both flags set on a merged dict).
    """
    updated_at = datetime.now(tz=timezone.utc).isoformat()
    with sqlite3.connect(db_path) as conn:
        for m in members:
            conn.execute(
                """
                INSERT INTO congress_members
                    (bioguide_id, full_name, first_name, last_name,
                     party, state, chamber, is_watched, is_star, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(bioguide_id) DO UPDATE SET
                    full_name  = excluded.full_name,
                    first_name = excluded.first_name,
                    last_name  = excluded.last_name,
                    party      = excluded.party,
                    state      = excluded.state,
                    chamber    = excluded.chamber,
                    is_watched = excluded.is_watched,
                    is_star    = excluded.is_star,
                    updated_at = excluded.updated_at
                """,
                (
                    m["bioguide_id"],
                    m.get("full_name", ""),
                    m.get("first_name", ""),
                    m.get("last_name", ""),
                    m.get("party", "I"),
                    m.get("state", ""),
                    m.get("chamber", ""),
                    int(m.get("is_watched", 0)),
                    int(m.get("is_star", 0)),
                    updated_at,
                ),
            )
            for comm in m.get("committees", []):
                conn.execute(
                    """
                    INSERT INTO congress_member_committees
                        (bioguide_id, committee_id, committee_name, title, rank)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(bioguide_id, committee_id) DO UPDATE SET
                        committee_name = excluded.committee_name,
                        title          = excluded.title,
                        rank           = excluded.rank
                    """,
                    (
                        m["bioguide_id"],
                        comm["committee_id"],
                        comm["committee_name"],
                        comm["title"],
                        comm.get("rank"),
                    ),
                )


def upsert_congress_trades(
    trades: list[CongressTrade], db_path: Path = _DEFAULT_DB_PATH
) -> None:
    """Upsert CongressTrade records. Idempotent via trade_id primary key."""
    fetched_at = datetime.now(tz=timezone.utc).isoformat()
    with sqlite3.connect(db_path) as conn:
        for t in trades:
            conn.execute(
                """
                INSERT INTO congress_trades (
                    trade_id, bioguide_id, full_name, chamber, party,
                    ticker, asset_type, transaction_type,
                    transaction_date, disclosure_date,
                    amount_low, amount_high, filing_id, fetched_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(trade_id) DO UPDATE SET
                    bioguide_id      = excluded.bioguide_id,
                    asset_type       = excluded.asset_type,
                    transaction_type = excluded.transaction_type,
                    amount_low       = excluded.amount_low,
                    amount_high      = excluded.amount_high,
                    filing_id        = excluded.filing_id,
                    fetched_at       = excluded.fetched_at
                """,
                (
                    t.trade_id,
                    t.bioguide_id,
                    t.full_name,
                    t.chamber,
                    t.party,
                    t.ticker,
                    t.asset_type,
                    t.transaction_type,
                    t.transaction_date.isoformat(),
                    t.disclosure_date.isoformat(),
                    t.amount_low,
                    t.amount_high,
                    t.filing_id,
                    fetched_at,
                ),
            )


def get_watched_members(db_path: Path = _DEFAULT_DB_PATH) -> pd.DataFrame:
    """Return DataFrame of congress_members where is_watched=1."""
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT bioguide_id, full_name, party, state, chamber,
                   is_watched, is_star
            FROM congress_members
            WHERE is_watched = 1
            ORDER BY last_name
            """
        ).fetchall()
    cols = ["bioguide_id", "full_name", "party", "state", "chamber", "is_watched", "is_star"]
    if not rows:
        return pd.DataFrame(columns=cols)
    return pd.DataFrame(rows, columns=cols)


def get_star_members(db_path: Path = _DEFAULT_DB_PATH) -> pd.DataFrame:
    """Return DataFrame of congress_members where is_star=1."""
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT bioguide_id, full_name, party, state, chamber,
                   is_watched, is_star
            FROM congress_members
            WHERE is_star = 1
            ORDER BY last_name
            """
        ).fetchall()
    cols = ["bioguide_id", "full_name", "party", "state", "chamber", "is_watched", "is_star"]
    if not rows:
        return pd.DataFrame(columns=cols)
    return pd.DataFrame(rows, columns=cols)


def get_recent_trades_for_members(
    bioguide_ids: list[str],
    days_back: int,
    db_path: Path = _DEFAULT_DB_PATH,
) -> pd.DataFrame:
    """Return congress_trades rows for the given members in the trailing days_back window.

    Sorted by disclosure_date DESC.
    """
    if not bioguide_ids:
        return pd.DataFrame()
    placeholders = ",".join("?" * len(bioguide_ids))
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            f"""
            SELECT
                ct.trade_id, ct.bioguide_id, ct.full_name, ct.chamber, ct.party,
                ct.ticker, ct.asset_type, ct.transaction_type,
                ct.transaction_date, ct.disclosure_date,
                ct.amount_low, ct.amount_high, ct.filing_id
            FROM congress_trades ct
            WHERE ct.bioguide_id IN ({placeholders})
              AND ct.disclosure_date >= date('now', ? || ' days')
            ORDER BY ct.disclosure_date DESC
            """,
            (*bioguide_ids, f"-{days_back}"),
        ).fetchall()
    cols = [
        "trade_id", "bioguide_id", "full_name", "chamber", "party",
        "ticker", "asset_type", "transaction_type",
        "transaction_date", "disclosure_date",
        "amount_low", "amount_high", "filing_id",
    ]
    if not rows:
        return pd.DataFrame(columns=cols)
    return pd.DataFrame(rows, columns=cols)


# ---------------------------------------------------------------------------
# User-managed universe tables
# ---------------------------------------------------------------------------


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
