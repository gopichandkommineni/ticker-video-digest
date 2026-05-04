import logging
import math
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

import yfinance as yf

from casino_dashboard.models import NewsItem, TickerSnapshot
from casino_dashboard.universe import Universe

logger = logging.getLogger(__name__)

_RETRY_DELAYS = (2, 4, 8)


def _fetch_with_retry(ticker: str, lookback_days: int) -> list[TickerSnapshot]:
    last_exc: Exception | None = None
    for attempt, delay in enumerate((*_RETRY_DELAYS, None), start=1):
        try:
            return _fetch_once(ticker, lookback_days)
        except Exception as exc:
            last_exc = exc
            if delay is not None:
                logger.debug("Attempt %d for %s failed (%s); retrying in %ds", attempt, ticker, exc, delay)
                time.sleep(delay)
    logger.warning("All retries exhausted for %s: %s", ticker, last_exc)
    return []


def _fetch_once(ticker: str, lookback_days: int) -> list[TickerSnapshot]:
    yf_ticker = yf.Ticker(ticker)

    hist = yf_ticker.history(period="3mo", auto_adjust=False)
    if hist.empty:
        raise ValueError(f"Empty history for {ticker}")

    adj_close_col = "Adj Close" if "Adj Close" in hist.columns else "Close"
    news_items = _parse_news(yf_ticker.news[:5])

    # Rolling 30-day avg volume shifted by 1 so each row reflects the prior
    # window (not including the current day), matching "avg as of that day"
    rolling_avg = hist["Volume"].rolling(window=30, min_periods=1).mean().shift(1)

    snapshots: list[TickerSnapshot] = []
    last_idx = len(hist) - 1
    for i, (ts, row) in enumerate(hist.iterrows()):
        avg_vol = rolling_avg.iloc[i]
        snapshots.append(TickerSnapshot(
            ticker=ticker,
            date=ts.date(),
            open=float(row["Open"]),
            high=float(row["High"]),
            low=float(row["Low"]),
            close=float(row["Close"]),
            adj_close=float(row[adj_close_col]),
            volume=int(row["Volume"]),
            avg_volume_30d=None if math.isnan(avg_vol) else float(avg_vol),
            news_items=news_items if i == last_idx else [],
        ))

    return snapshots


def _parse_news(raw_news: list[dict]) -> list[NewsItem]:
    items: list[NewsItem] = []
    for item in raw_news:
        try:
            if "content" in item:
                # New yfinance format (2025+): fields nested under "content"
                content = item["content"]
                title = content.get("title") or ""
                link = (
                    (content.get("canonicalUrl") or {}).get("url")
                    or (content.get("clickThroughUrl") or {}).get("url")
                    or ""
                )
                publisher = (content.get("provider") or {}).get("displayName") or ""
                pub_date_str = content.get("pubDate") or ""
                published_at = (
                    datetime.fromisoformat(pub_date_str.replace("Z", "+00:00"))
                    if pub_date_str
                    else None
                )
            else:
                # Legacy yfinance format: flat dict
                title = item.get("title") or ""
                link = item.get("link") or ""
                publisher = item.get("publisher") or ""
                ts = item.get("providerPublishTime") or item.get("published")
                published_at = datetime.fromtimestamp(int(ts), tz=timezone.utc) if ts else None

            if not title:
                logger.warning("Skipping news item with empty title")
                continue
            if not link:
                logger.warning("Skipping news item with empty link for title=%r", title)
                continue
            if published_at is None:
                logger.warning("Skipping news item with missing publish date for title=%r", title)
                continue

            items.append(NewsItem(
                title=title,
                link=link,
                publisher=publisher,
                published_at=published_at,
            ))
        except Exception as exc:
            logger.debug("Skipping malformed news item: %s", exc)
    return items


def fetch_ticker_history(ticker: str, lookback_days: int = 90) -> list[TickerSnapshot]:
    return _fetch_with_retry(ticker, lookback_days)


def fetch_universe_snapshot(universe: Universe) -> dict[str, list[TickerSnapshot]]:
    tickers = sorted(universe.all_tickers())
    results: dict[str, list[TickerSnapshot]] = {}

    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = {pool.submit(fetch_ticker_history, t): t for t in tickers}
        for future in as_completed(futures):
            ticker = futures[future]
            try:
                snaps = future.result()
                if snaps:
                    results[ticker] = snaps
                    logger.info("Fetched %s (%d rows)", ticker, len(snaps))
                else:
                    logger.warning("No snapshots returned for %s", ticker)
            except Exception as exc:
                logger.warning("Unexpected error for %s: %s", ticker, exc)

    return results
