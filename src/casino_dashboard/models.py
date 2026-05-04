from datetime import date, datetime

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
