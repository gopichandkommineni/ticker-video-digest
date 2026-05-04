import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

import yfinance as yf

from casino_dashboard.models import NewsItem, TickerSnapshot
from casino_dashboard.universe import Universe

logger = logging.getLogger(__name__)

_RETRY_DELAYS = (2, 4, 8)


def _fetch_with_retry(ticker: str, lookback_days: int) -> TickerSnapshot | None:
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
    return None


def _fetch_once(ticker: str, lookback_days: int) -> TickerSnapshot:
    yf_ticker = yf.Ticker(ticker)

    hist = yf_ticker.history(period="3mo", auto_adjust=False)
    if hist.empty:
        raise ValueError(f"Empty history for {ticker}")

    last = hist.iloc[-1]
    snap_date = hist.index[-1].date()

    # avg_volume_30d — last 30 rows of available history
    tail = hist.tail(30)
    avg_volume_30d: float | None = float(tail["Volume"].mean()) if not tail.empty else None

    # adj_close — yfinance returns "Adj Close" when auto_adjust=False
    adj_close_col = "Adj Close" if "Adj Close" in hist.columns else "Close"
    adj_close = float(last[adj_close_col])

    news_items = _parse_news(yf_ticker.news[:5])

    return TickerSnapshot(
        ticker=ticker,
        date=snap_date,
        open=float(last["Open"]),
        high=float(last["High"]),
        low=float(last["Low"]),
        close=float(last["Close"]),
        adj_close=adj_close,
        volume=int(last["Volume"]),
        avg_volume_30d=avg_volume_30d,
        news_items=news_items,
    )


def _parse_news(raw_news: list[dict]) -> list[NewsItem]:
    items: list[NewsItem] = []
    for item in raw_news:
        try:
            # providerPublishTime is a Unix timestamp (int)
            ts = item.get("providerPublishTime") or item.get("published", 0)
            published_at = datetime.fromtimestamp(int(ts), tz=timezone.utc)
            items.append(NewsItem(
                title=item.get("title", ""),
                link=item.get("link", ""),
                publisher=item.get("publisher", ""),
                published_at=published_at,
            ))
        except Exception as exc:
            logger.debug("Skipping malformed news item: %s", exc)
    return items


def fetch_ticker_snapshot(ticker: str, lookback_days: int = 90) -> TickerSnapshot | None:
    return _fetch_with_retry(ticker, lookback_days)


def fetch_universe_snapshot(universe: Universe) -> list[TickerSnapshot]:
    tickers = sorted(universe.all_tickers())
    results: list[TickerSnapshot] = []

    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = {pool.submit(fetch_ticker_snapshot, t): t for t in tickers}
        for future in as_completed(futures):
            ticker = futures[future]
            try:
                snap = future.result()
                if snap is not None:
                    results.append(snap)
                    logger.info("Fetched %s", ticker)
                else:
                    logger.warning("No snapshot returned for %s", ticker)
            except Exception as exc:
                logger.warning("Unexpected error for %s: %s", ticker, exc)

    return results
