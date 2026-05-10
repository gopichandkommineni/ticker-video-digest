import logging
import time
from dataclasses import dataclass
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

import yfinance as yf

try:
    import lxml  # noqa: F401
except ImportError as e:
    raise ImportError(
        "lxml is required for yfinance earnings_dates parsing. "
        "Install with: pip install lxml"
    ) from e

logger = logging.getLogger(__name__)

_ET = ZoneInfo("America/New_York")
_MARKET_OPEN = (9, 30)   # 9:30 AM ET
_MARKET_CLOSE = (16, 0)  # 4:00 PM ET


@dataclass
class TickerMetadata:
    ticker: str
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
    next_earnings_date: date | None
    next_earnings_time: str | None
    last_earnings_date: date | None


def _safe_float(value: object) -> float | None:
    """Return float or None; never 0 as a fallback for missing data."""
    if value is None:
        return None
    try:
        result = float(value)
        import math
        if math.isnan(result) or math.isinf(result):
            return None
        return result
    except (ValueError, TypeError):
        return None


def _classify_earnings_time(dt: datetime) -> str | None:
    """Classify a datetime as BMO, AMC, or None based on ET time-of-day."""
    try:
        if dt.tzinfo is None:
            et_dt = dt.replace(tzinfo=_ET)
        else:
            et_dt = dt.astimezone(_ET)
        h, m = et_dt.hour, et_dt.minute
        if (h, m) < _MARKET_OPEN:
            return "BMO"
        if (h, m) >= _MARKET_CLOSE:
            return "AMC"
        return None
    except Exception:
        return None


def _parse_earnings_dates(ticker_obj: yf.Ticker) -> tuple[date | None, str | None, date | None]:
    """Return (next_earnings_date, next_earnings_time, last_earnings_date).

    Reads Ticker.earnings_dates (a DataFrame indexed by datetime). Splits into
    future and past rows relative to today.
    """
    try:
        ed = ticker_obj.earnings_dates
        if ed is None or len(ed.index) == 0:
            return None, None, None
    except Exception as exc:
        logger.debug("earnings_dates unavailable: %s", exc)
        return None, None, None

    now = datetime.now(tz=timezone.utc)
    future_dates = []
    past_dates = []

    for idx in ed.index:
        try:
            if hasattr(idx, "to_pydatetime"):
                dt = idx.to_pydatetime()
            else:
                dt = idx
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            if dt >= now:
                future_dates.append(dt)
            else:
                past_dates.append(dt)
        except Exception:
            continue

    next_dt: datetime | None = min(future_dates) if future_dates else None
    last_dt: datetime | None = max(past_dates) if past_dates else None

    next_date = next_dt.date() if next_dt else None
    next_time = _classify_earnings_time(next_dt) if next_dt else None
    last_date = last_dt.date() if last_dt else None

    return next_date, next_time, last_date


def fetch_ticker_metadata(ticker: str) -> TickerMetadata:
    """Fetch all 15 metadata fields for a single ticker from yfinance.

    Each field is wrapped individually so one bad field never aborts the fetch.
    Returns None for any field that is missing or invalid.
    """
    t = yf.Ticker(ticker)

    try:
        info = t.info or {}
    except Exception as exc:
        logger.warning("Could not fetch info for %s: %s", ticker, exc)
        info = {}

    def _get(key: str) -> float | None:
        try:
            return _safe_float(info.get(key))
        except (ValueError, KeyError, TypeError) as exc:
            logger.debug("Field %r missing for %s: %s", key, ticker, exc)
            return None

    fifty_two_week_high = _get("fiftyTwoWeekHigh")
    fifty_two_week_low = _get("fiftyTwoWeekLow")
    short_pct_of_float = _get("shortPercentOfFloat")
    short_ratio_days = _get("shortRatio")
    analyst_target_mean = _get("targetMeanPrice")
    analyst_target_high = _get("targetHighPrice")
    analyst_target_low = _get("targetLowPrice")
    analyst_count = _get("numberOfAnalystOpinions")
    held_pct_insiders = _get("heldPercentInsiders")
    held_pct_institutions = _get("heldPercentInstitutions")
    market_cap = _get("marketCap")
    revenue_ttm = _get("totalRevenue")
    revenue_growth_yoy = _get("revenueGrowth")
    profit_margin = _get("profitMargins")
    beta = _get("beta")

    try:
        next_earnings_date, next_earnings_time, last_earnings_date = _parse_earnings_dates(t)
    except Exception as exc:
        logger.warning("Earnings dates parse failed for %s: %s", ticker, exc)
        next_earnings_date, next_earnings_time, last_earnings_date = None, None, None

    return TickerMetadata(
        ticker=ticker,
        fifty_two_week_high=fifty_two_week_high,
        fifty_two_week_low=fifty_two_week_low,
        short_pct_of_float=short_pct_of_float,
        short_ratio_days=short_ratio_days,
        analyst_target_mean=analyst_target_mean,
        analyst_target_high=analyst_target_high,
        analyst_target_low=analyst_target_low,
        analyst_count=analyst_count,
        held_pct_insiders=held_pct_insiders,
        held_pct_institutions=held_pct_institutions,
        market_cap=market_cap,
        revenue_ttm=revenue_ttm,
        revenue_growth_yoy=revenue_growth_yoy,
        profit_margin=profit_margin,
        beta=beta,
        next_earnings_date=next_earnings_date,
        next_earnings_time=next_earnings_time,
        last_earnings_date=last_earnings_date,
    )


def fetch_metadata_for_universe(tickers: list[str]) -> list[TickerMetadata]:
    """Fetch metadata for all tickers in the universe.

    Logs progress every 10 tickers. Sleeps 0.5s between calls.
    Per-ticker exceptions are caught and an all-None record is returned.
    """
    results: list[TickerMetadata] = []
    for i, ticker in enumerate(tickers, start=1):
        try:
            meta = fetch_ticker_metadata(ticker)
        except Exception as exc:
            logger.warning("Unhandled exception fetching metadata for %s: %s", ticker, exc)
            meta = TickerMetadata(
                ticker=ticker,
                fifty_two_week_high=None,
                fifty_two_week_low=None,
                short_pct_of_float=None,
                short_ratio_days=None,
                analyst_target_mean=None,
                analyst_target_high=None,
                analyst_target_low=None,
                analyst_count=None,
                held_pct_insiders=None,
                held_pct_institutions=None,
                market_cap=None,
                revenue_ttm=None,
                revenue_growth_yoy=None,
                profit_margin=None,
                beta=None,
                next_earnings_date=None,
                next_earnings_time=None,
                last_earnings_date=None,
            )
        results.append(meta)
        if i % 10 == 0:
            logger.info("Fetched metadata for %d/%d tickers so far", i, len(tickers))
        if i < len(tickers):
            time.sleep(0.5)
    return results
