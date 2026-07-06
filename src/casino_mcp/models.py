"""Pydantic output models for the casino-dashboard MCP tools.

Every row a tool returns carries a `Provenance` so the chat layer can cite
its source structurally — (table, ticker, date) for snapshots.db rows,
(tweet_id, handle, date) for fintwit.db rows — never through prose.

Two-null-states convention: a result with `rows=[]` (or `snapshot=None`)
means the database has no such data. "Not retrieved this run" is a state
only the caller can be in (it didn't call the tool); tools never conflate
the two.
"""
from typing import Literal

from pydantic import BaseModel

ResolveStatus = Literal["ok", "no_data_yet", "not_in_universe", "unknown_ticker"]


class Provenance(BaseModel):
    """Structural row-level citation: which db/table, keyed by the row's natural key."""

    db: Literal["snapshots", "fintwit"]
    table: str
    row_key: dict[str, str]


class ResolvedTicker(BaseModel):
    """Typed resolver result. `status` is a machine-readable reason code, not prose:

    - ok:              ticker is in the tracked universe and has snapshot data
    - no_data_yet:     in the universe (e.g. freshly user-added) but no rows yet
    - not_in_universe: snapshots.db has rows for it, but it is not in the
                       current universe (themes.yaml + user_added_tickers)
    - unknown_ticker:  nowhere in the universe or the database
    """

    status: ResolveStatus
    query: str
    ticker: str | None
    sectors: list[str]
    detail: str


class SnapshotRow(BaseModel):
    ticker: str
    date: str
    open: float
    high: float
    low: float
    close: float
    adj_close: float
    volume: int
    avg_volume_30d: float | None
    provenance: Provenance


class MetadataRow(BaseModel):
    ticker: str
    date: str
    fifty_two_week_high: float | None
    fifty_two_week_low: float | None
    short_pct_of_float: float | None
    short_ratio_days: float | None
    analyst_target_mean: float | None
    analyst_target_high: float | None
    analyst_target_low: float | None
    analyst_count: float | None
    held_pct_insiders: float | None
    held_pct_institutions: float | None
    market_cap: float | None
    revenue_ttm: float | None
    revenue_growth_yoy: float | None
    profit_margin: float | None
    beta: float | None
    next_earnings_date: str | None
    next_earnings_time: str | None
    last_earnings_date: str | None
    provenance: Provenance


class SnapshotResult(BaseModel):
    ticker: str
    snapshot: SnapshotRow | None
    metadata: MetadataRow | None


class SignalRow(BaseModel):
    signal_name: str
    value: float | None
    provenance: Provenance


class SignalsResult(BaseModel):
    ticker: str
    date: str | None
    signals: list[SignalRow]


class SectorHeatRow(BaseModel):
    sector: str
    date: str
    etf_flow_5d_30d_ratio: float | None
    deal_log_30d_total_usd: float | None
    deal_log_30d_count: int | None
    days_since_last_deal: int | None
    agg_social_velocity: float | None
    news_heat_ratio: float | None
    agg_return_30d: float | None
    pct_above_sma50: float | None
    agg_atr_pct_change_30d: float | None
    constituent_count: int
    provenance: Provenance


class SectorHeatResult(BaseModel):
    rows: list[SectorHeatRow]


class TweetRow(BaseModel):
    tweet_id: str
    account_handle: str
    created_at_utc: str
    text: str | None
    url: str | None
    like_count: int | None
    retweet_count: int | None
    view_count: int | None
    provenance: Provenance


class FintwitSearchResult(BaseModel):
    rows: list[TweetRow]
    truncated: bool  # True when more rows matched than `limit` allowed


class CongressTradeRow(BaseModel):
    trade_id: str
    full_name: str
    chamber: str
    party: str
    ticker: str
    asset_type: str | None
    transaction_type: str
    transaction_date: str
    disclosure_date: str
    amount_low: float | None
    amount_high: float | None
    filing_id: str | None
    provenance: Provenance


class CongressTradesResult(BaseModel):
    rows: list[CongressTradeRow]
    truncated: bool


class NewsRow(BaseModel):
    ticker: str
    title: str
    link: str
    publisher: str
    published_at: str
    provenance: Provenance


class NewsResult(BaseModel):
    rows: list[NewsRow]
    truncated: bool
