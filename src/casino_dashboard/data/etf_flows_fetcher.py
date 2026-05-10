"""
ETF net flow estimation using the calculated-from-AUM approach (spec §3.1a option 4).

Implied net flow per day = AUM_change - (AUM_yesterday * price_return)
Removes price appreciation to isolate actual creation/redemption activity.

This approach is approximate — it assumes no distributions or fees within the window —
but is sufficient for relative ranking across sectors and trend detection.
Real flow data can replace this in v1.5 if noise proves unacceptable.
"""
import logging
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

import yfinance as yf

logger = logging.getLogger(__name__)

_MIN_HISTORY_DAYS = 35  # need 30d avg + 5d window, plus buffer


@dataclass
class ETFDailySnapshot:
    etf_ticker: str
    date: date
    price: float
    aum_usd: float | None


@dataclass
class ETFFlow:
    etf_ticker: str
    date: date
    net_flow_usd: float | None
    aum_usd: float | None


def fetch_etf_snapshot_today(etf_ticker: str) -> ETFDailySnapshot | None:
    """Fetch today's price and AUM for one ETF via yfinance.

    AUM comes from yf.Ticker.info['totalAssets']. Not always populated for
    all ETFs; returns None for aum_usd when unavailable rather than crashing.
    """
    try:
        ticker_obj = yf.Ticker(etf_ticker)
        hist = ticker_obj.history(period="2d")
        if hist.empty:
            logger.warning("No price history for ETF %s", etf_ticker)
            return None

        latest_row = hist.iloc[-1]
        price = float(latest_row["Close"])
        snap_date = hist.index[-1].date()

        info = ticker_obj.info or {}
        aum_usd: float | None = info.get("totalAssets")
        if aum_usd is not None:
            aum_usd = float(aum_usd)

        return ETFDailySnapshot(
            etf_ticker=etf_ticker,
            date=snap_date,
            price=price,
            aum_usd=aum_usd,
        )
    except Exception as exc:
        logger.error("Failed to fetch ETF snapshot for %s: %s", etf_ticker, exc)
        return None


def calculate_implied_flow(
    today_aum: float,
    yesterday_aum: float,
    today_price: float,
    yesterday_price: float,
) -> float | None:
    """Implied net flow = AUM_change - (AUM_yesterday * price_return).

    Removes price appreciation to isolate net creation/redemption activity.
    Returns None if yesterday_price is zero (division guard).
    """
    if yesterday_price == 0 or yesterday_aum == 0:
        return None
    price_return = (today_price - yesterday_price) / yesterday_price
    return today_aum - yesterday_aum - (yesterday_aum * price_return)


def compute_etf_flow_ratio(
    flows: list[ETFFlow],
    as_of_date: date,
    window_short: int = 5,
    window_long: int = 30,
) -> float | None:
    """Compute trailing 5-day net flow as % of trailing 30-day average.

    Captures flow acceleration rather than absolute size — meaningful because
    SMH has ~20x the AUM of BITQ so raw flows are not comparable across sectors.

    Returns None if insufficient data.
    """
    dated = {f.date: f.net_flow_usd for f in flows if f.net_flow_usd is not None}
    if not dated:
        return None

    short_flows = []
    long_flows = []
    for i in range(window_long):
        d = as_of_date - timedelta(days=i)
        if d in dated:
            long_flows.append(dated[d])
            if i < window_short:
                short_flows.append(dated[d])

    if len(long_flows) < window_long // 2:
        return None
    if not short_flows:
        return None

    avg_long = sum(long_flows) / len(long_flows)
    avg_short = sum(short_flows) / len(short_flows)

    if avg_long == 0:
        return None

    return avg_short / avg_long


def load_etf_mapping_from_yaml(path: Path) -> dict[str, list[str]]:
    """Parse config/etf_mapping.yaml and return {sector: [etf_ticker, ...]}."""
    import yaml

    if not path.exists():
        raise FileNotFoundError(f"ETF mapping YAML not found: {path}")

    with path.open("r") as fh:
        raw = yaml.safe_load(fh)

    if raw is None:
        return {}

    result: dict[str, list[str]] = {}
    for sector, entries in raw.items():
        if entries is None:
            result[sector] = []
            continue
        tickers = []
        for entry in entries:
            if isinstance(entry, dict) and "ticker" in entry:
                tickers.append(str(entry["ticker"]).upper())
            elif isinstance(entry, str):
                tickers.append(entry.upper())
        result[sector] = tickers

    return result
