"""Read-only query layer behind the casino-dashboard MCP tools.

Every connection is opened with SQLite URI `mode=ro`, so this layer cannot
write to the production databases even by accident. SQL semantics mirror
casino_dashboard.db.repository (latest-date-per-key joins, disclosure-date
windows); the repository functions themselves are not imported because they
open read-write connections and run init_db() migrations on every call.

The ticker resolver reuses casino_dashboard.universe.load_universe, which
merges config/themes.yaml with user_added_themes/user_added_tickers.
"""
import os
import sqlite3
from contextlib import closing
from pathlib import Path

from casino_dashboard.universe import load_universe

from casino_mcp.models import (
    CongressTradeRow,
    CongressTradesResult,
    FintwitSearchResult,
    MetadataRow,
    NewsResult,
    NewsRow,
    Provenance,
    ResolvedTicker,
    SectorHeatResult,
    SectorHeatRow,
    SignalRow,
    SignalsResult,
    SnapshotResult,
    SnapshotRow,
    TweetRow,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
MAX_LIMIT = 100


def snapshots_db_path() -> Path:
    return Path(os.environ.get("CASINO_SNAPSHOTS_DB", _REPO_ROOT / "data" / "snapshots.db"))


def fintwit_db_path() -> Path:
    return Path(os.environ.get("CASINO_FINTWIT_DB", _REPO_ROOT / "data" / "fintwit.db"))


def _ro_connect(db_path: Path) -> sqlite3.Connection:
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _clamp_limit(limit: int) -> int:
    return max(1, min(limit, MAX_LIMIT))


def resolve_ticker(
    query: str,
    *,
    snapshots_db: Path | None = None,
    themes_path: Path | None = None,
) -> ResolvedTicker:
    db = snapshots_db or snapshots_db_path()
    ticker = query.strip().lstrip("$").upper()
    if not ticker:
        return ResolvedTicker(
            status="unknown_ticker", query=query, ticker=None, sectors=[],
            detail="Empty query.",
        )

    kwargs: dict = {"db_path": db}
    if themes_path is not None:
        kwargs["path"] = themes_path
    universe = load_universe(**kwargs)

    with closing(_ro_connect(db)) as conn:
        has_rows = conn.execute(
            "SELECT 1 FROM ticker_snapshots WHERE ticker = ? LIMIT 1", (ticker,)
        ).fetchone() is not None

    if ticker in universe.all_tickers():
        sectors = universe.sectors_for(ticker)
        if has_rows:
            return ResolvedTicker(
                status="ok", query=query, ticker=ticker, sectors=sectors,
                detail=f"{ticker} is tracked in sectors: {', '.join(sectors)}.",
            )
        return ResolvedTicker(
            status="no_data_yet", query=query, ticker=ticker, sectors=sectors,
            detail=f"{ticker} is in the universe but has no snapshot rows yet "
                   "(likely user-added and awaiting the next daily refresh).",
        )
    if has_rows:
        return ResolvedTicker(
            status="not_in_universe", query=query, ticker=ticker, sectors=[],
            detail=f"{ticker} has historical rows in snapshots.db but is not in "
                   "the current universe (themes.yaml + user_added_tickers).",
        )
    return ResolvedTicker(
        status="unknown_ticker", query=query, ticker=ticker, sectors=[],
        detail=f"{ticker} is not in the universe and has no data in snapshots.db.",
    )


def get_snapshot(ticker: str, *, snapshots_db: Path | None = None) -> SnapshotResult:
    db = snapshots_db or snapshots_db_path()
    ticker = ticker.strip().upper()
    with closing(_ro_connect(db)) as conn:
        snap = conn.execute(
            """
            SELECT ticker, date, open, high, low, close, adj_close, volume, avg_volume_30d
            FROM ticker_snapshots WHERE ticker = ? ORDER BY date DESC LIMIT 1
            """,
            (ticker,),
        ).fetchone()
        meta = conn.execute(
            """
            SELECT ticker, date, fifty_two_week_high, fifty_two_week_low,
                   short_pct_of_float, short_ratio_days,
                   analyst_target_mean, analyst_target_high, analyst_target_low,
                   analyst_count, held_pct_insiders, held_pct_institutions,
                   market_cap, revenue_ttm, revenue_growth_yoy, profit_margin, beta,
                   next_earnings_date, next_earnings_time, last_earnings_date
            FROM ticker_metadata WHERE ticker = ? ORDER BY date DESC LIMIT 1
            """,
            (ticker,),
        ).fetchone()

    snapshot = None
    if snap is not None:
        snapshot = SnapshotRow(
            **dict(snap),
            provenance=_prov("snapshots", "ticker_snapshots",
                             ticker=snap["ticker"], date=snap["date"]),
        )
    metadata = None
    if meta is not None:
        metadata = MetadataRow(
            **dict(meta),
            provenance=_prov("snapshots", "ticker_metadata",
                             ticker=meta["ticker"], date=meta["date"]),
        )
    return SnapshotResult(ticker=ticker, snapshot=snapshot, metadata=metadata)


def get_signals(ticker: str, *, snapshots_db: Path | None = None) -> SignalsResult:
    db = snapshots_db or snapshots_db_path()
    ticker = ticker.strip().upper()
    with closing(_ro_connect(db)) as conn:
        rows = conn.execute(
            """
            SELECT signal_name, value, date FROM signals
            WHERE ticker = ? AND date = (SELECT MAX(date) FROM signals WHERE ticker = ?)
            ORDER BY signal_name
            """,
            (ticker, ticker),
        ).fetchall()
    if not rows:
        return SignalsResult(ticker=ticker, date=None, signals=[])
    return SignalsResult(
        ticker=ticker,
        date=rows[0]["date"],
        signals=[
            SignalRow(
                signal_name=r["signal_name"],
                value=r["value"],
                provenance=_prov("snapshots", "signals", ticker=ticker,
                                 date=r["date"], signal_name=r["signal_name"]),
            )
            for r in rows
        ],
    )


def get_sector_heat(
    sector: str | None = None, *, snapshots_db: Path | None = None
) -> SectorHeatResult:
    db = snapshots_db or snapshots_db_path()
    sql = """
        SELECT sh.* FROM sector_heat sh
        INNER JOIN (
            SELECT sector, MAX(date) AS max_date FROM sector_heat GROUP BY sector
        ) latest ON sh.sector = latest.sector AND sh.date = latest.max_date
    """
    params: tuple = ()
    if sector is not None:
        sql += " WHERE sh.sector = ?"
        params = (sector,)
    sql += " ORDER BY sh.sector"
    with closing(_ro_connect(db)) as conn:
        rows = conn.execute(sql, params).fetchall()
    return SectorHeatResult(
        rows=[
            SectorHeatRow(
                **dict(r),
                provenance=_prov("snapshots", "sector_heat",
                                 sector=r["sector"], date=r["date"]),
            )
            for r in rows
        ]
    )


def search_fintwit(
    query: str | None = None,
    ticker: str | None = None,
    handle: str | None = None,
    days: int = 30,
    limit: int = 25,
    *,
    fintwit_db: Path | None = None,
) -> FintwitSearchResult:
    if not query and not ticker and not handle:
        raise ValueError("Provide at least one of: query, ticker, handle.")
    db = fintwit_db or fintwit_db_path()
    limit = _clamp_limit(limit)

    where = ["COALESCE(is_deleted, 0) = 0", "created_at_utc >= date('now', ?)"]
    params: list = [f"-{max(1, days)} days"]
    if query:
        where.append("text LIKE ?")
        params.append(f"%{query}%")
    if ticker:
        t = ticker.strip().lstrip("$").upper()
        where.append(
            "(text LIKE ? OR tweet_id IN "
            " (SELECT tweet_id FROM tweet_labels"
            "  WHERE label_type = 'ticker' AND label_value = ?))"
        )
        params.extend([f"%${t}%", t])
    if handle:
        where.append("account_handle = ? COLLATE NOCASE")
        params.append(handle.lstrip("@"))

    with closing(_ro_connect(db)) as conn:
        rows = conn.execute(
            f"""
            SELECT tweet_id, account_handle, created_at_utc, text, url,
                   like_count, retweet_count, view_count
            FROM raw_tweets
            WHERE {" AND ".join(where)}
            ORDER BY created_at_utc DESC
            LIMIT ?
            """,
            (*params, limit + 1),
        ).fetchall()

    truncated = len(rows) > limit
    return FintwitSearchResult(
        rows=[
            TweetRow(
                **dict(r),
                provenance=_prov("fintwit", "raw_tweets",
                                 tweet_id=r["tweet_id"],
                                 handle=r["account_handle"],
                                 date=r["created_at_utc"]),
            )
            for r in rows[:limit]
        ],
        truncated=truncated,
    )


def get_congress_trades(
    ticker: str | None = None,
    member: str | None = None,
    days: int = 180,
    limit: int = 50,
    *,
    snapshots_db: Path | None = None,
) -> CongressTradesResult:
    db = snapshots_db or snapshots_db_path()
    limit = _clamp_limit(limit)

    where = ["disclosure_date >= date('now', ?)"]
    params: list = [f"-{max(1, days)} days"]
    if ticker:
        where.append("ticker = ?")
        params.append(ticker.strip().lstrip("$").upper())
    if member:
        where.append("full_name LIKE ?")
        params.append(f"%{member}%")

    with closing(_ro_connect(db)) as conn:
        rows = conn.execute(
            f"""
            SELECT trade_id, full_name, chamber, party, ticker, asset_type,
                   transaction_type, transaction_date, disclosure_date,
                   amount_low, amount_high, filing_id
            FROM congress_trades
            WHERE {" AND ".join(where)}
            ORDER BY disclosure_date DESC
            LIMIT ?
            """,
            (*params, limit + 1),
        ).fetchall()

    truncated = len(rows) > limit
    return CongressTradesResult(
        rows=[
            CongressTradeRow(
                **dict(r),
                provenance=_prov("snapshots", "congress_trades",
                                 trade_id=r["trade_id"],
                                 disclosure_date=r["disclosure_date"]),
            )
            for r in rows[:limit]
        ],
        truncated=truncated,
    )


def get_news(
    ticker: str,
    days: int = 14,
    limit: int = 25,
    *,
    snapshots_db: Path | None = None,
) -> NewsResult:
    db = snapshots_db or snapshots_db_path()
    ticker = ticker.strip().upper()
    limit = _clamp_limit(limit)

    with closing(_ro_connect(db)) as conn:
        rows = conn.execute(
            """
            SELECT ticker, title, link, publisher, published_at
            FROM news_items
            WHERE ticker = ? AND date(published_at) >= date('now', ?)
            ORDER BY published_at DESC
            LIMIT ?
            """,
            (ticker, f"-{max(1, days)} days", limit + 1),
        ).fetchall()

    truncated = len(rows) > limit
    return NewsResult(
        rows=[
            NewsRow(
                **dict(r),
                provenance=_prov("snapshots", "news_items",
                                 ticker=r["ticker"], link=r["link"],
                                 published_at=r["published_at"]),
            )
            for r in rows[:limit]
        ],
        truncated=truncated,
    )


def _prov(db: str, table: str, **row_key: str) -> Provenance:
    return Provenance(db=db, table=table, row_key={k: str(v) for k, v in row_key.items()})
