"""Resolve a free-form query (ticker OR company name) to a ticker symbol, and
look up a ticker's company name — used to seed subreddit discovery.

Name->ticker resolution uses yfinance's Search endpoint (network). Callers in
unit tests should mock `_yf_search`.
"""
import logging
import re

logger = logging.getLogger(__name__)

_TICKER_RE = re.compile(r"[A-Za-z]{1,6}([.\-][A-Za-z]{1,4})?")


def looks_like_ticker(query: str) -> bool:
    """Heuristic: a short, space-free, all-alpha token is treated as a ticker.

    'RKLB' -> True, 'Rocket Lab' -> False, 'coinbase' -> False (has a space? no,
    but length>6) — length and the absence of spaces are the discriminators.
    """
    q = query.strip()
    if not q or " " in q:
        return False
    return bool(_TICKER_RE.fullmatch(q)) and len(q.replace(".", "").replace("-", "")) <= 6


def _yf_search(query: str) -> list[dict]:
    """Thin wrapper around yfinance.Search so tests can patch it. Returns the
    raw `quotes` list (dicts with at least 'symbol', 'quoteType', 'longname').
    """
    import yfinance as yf  # noqa: PLC0415

    try:
        res = yf.Search(query, max_results=5)
        return list(getattr(res, "quotes", []) or [])
    except Exception as exc:  # network / API shape drift
        logger.warning("yfinance search failed for %r: %s", query, exc)
        return []


def resolve_ticker(query: str, universe: set[str] | None = None) -> str | None:
    """Resolve *query* to a ticker symbol.

    - If it already looks like a ticker, return it upper-cased (validated against
      *universe* when one is supplied but still returned if outside it).
    - Otherwise treat it as a company name and resolve via yfinance search,
      preferring equities/ETFs. Returns None when nothing resolves.
    """
    q = query.strip()
    if not q:
        return None

    if looks_like_ticker(q):
        return q.upper()

    for quote in _yf_search(q):
        symbol = (quote.get("symbol") or "").upper()
        qtype = (quote.get("quoteType") or "").upper()
        if symbol and qtype in ("", "EQUITY", "ETF"):
            if universe is None or symbol in universe:
                return symbol
            # Not in our universe, but a valid resolution — surface it anyway.
            return symbol
    return None


def company_name_for(ticker: str) -> str | None:
    """Best-effort company name for a ticker (enriches candidate generation).

    Returns the longname/shortname from a yfinance search whose symbol matches,
    or None.
    """
    ticker = ticker.strip().upper()
    for quote in _yf_search(ticker):
        if (quote.get("symbol") or "").upper() == ticker:
            name = quote.get("longname") or quote.get("shortname")
            if name:
                return str(name)
    return None
