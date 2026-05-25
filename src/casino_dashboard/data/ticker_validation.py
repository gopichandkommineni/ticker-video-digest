import logging

import yfinance as yf

logger = logging.getLogger(__name__)


def validate_ticker(ticker: str) -> tuple[bool, str | None, str | None]:
    """Return (is_valid, company_name, error_message).

    Makes one yfinance call that both validates the symbol and retrieves the
    company name for display. Valid means the symbol resolves AND has a usable
    longName or shortName and a non-zero price.
    """
    try:
        t = yf.Ticker(ticker)
        info = t.info or {}
    except Exception as exc:
        logger.debug("yfinance fetch failed for %r: %s", ticker, exc)
        return False, None, f"Could not fetch data for {ticker}: {exc}"

    # yfinance returns a minimal dict (e.g. just {"symbol": ..., "trailingPegRatio": None})
    # for unknown symbols; check for a usable name and price.
    company_name: str | None = info.get("longName") or info.get("shortName")
    price: float | None = (
        info.get("regularMarketPrice")
        or info.get("currentPrice")
        or info.get("previousClose")
    )

    if not company_name:
        return False, None, f"{ticker} did not resolve to a known symbol (no company name found)"

    if not price:
        return False, None, f"{ticker} resolved but has no price data"

    return True, company_name, None
