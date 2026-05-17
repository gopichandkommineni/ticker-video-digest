from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel


class NewsItem(BaseModel):
    title: str
    link: str
    publisher: str
    published_at: datetime


class TickerSnapshot(BaseModel):
    ticker: str
    date: date
    open: float
    high: float
    low: float
    close: float
    adj_close: float
    volume: int
    avg_volume_30d: float | None
    news_items: list[NewsItem]


class SectorSnapshot(BaseModel):
    sector_id: str
    date: date
    ticker_snapshots: list[TickerSnapshot]


class CongressTrade(BaseModel):
    """A single congressional trade disclosure (STOCK Act filing).

    trade_id is a deterministic hash of member+date+ticker+amount_range so
    re-fetching the same filing is idempotent (ON CONFLICT DO UPDATE).
    """

    trade_id: str
    bioguide_id: str | None
    full_name: str
    chamber: Literal["house", "senate"]
    party: Literal["D", "R", "I"]
    ticker: str
    asset_type: str
    transaction_type: Literal["buy", "sell", "exchange", "other"]
    transaction_date: date
    disclosure_date: date
    amount_low: float | None
    amount_high: float | None
    filing_id: str | None
