"""
Congress trades fetcher — pulls STOCK Act disclosures from FMP.

FMP endpoints used:
  GET /api/v4/senate-trading?apikey=KEY
  GET /api/v4/house-disclosure?apikey=KEY

If either endpoint returns HTTP 404, we raise immediately with a clear
message naming the endpoint — this signals a plan-access issue.

Asset-type filter (applied before returning):
  Keep: Stock, Common Stock, Stock Option, Call Option, Put Option,
        sector ETFs (anything not on the explicit drop list).
  Drop: Bond, Municipal Bond, Treasury, Mutual Fund, and broad-market
        ETFs (SPY, VOO, VTI, QQQ, BND, IVV, SCHB, VT, ITOT, SPTM).
  Ambiguous asset_type strings → keep and log WARNING.

Bioguide matching: FMP does not return bioguide_ids. We attempt
name-matching against the legislators-current snapshot loaded by the
caller (via bioguide_filter). Unmatched names are logged but kept with
bioguide_id=None.
"""
import hashlib
import json
import logging
import os
import re
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from casino_dashboard.models import CongressTrade

logger = logging.getLogger(__name__)

_FMP_BASE = "https://financialmodelingprep.com/api/v4"

# Broad-market ETFs to exclude (sector ETFs are kept — directional bets)
_BROAD_MARKET_ETFS = {"SPY", "VOO", "VTI", "QQQ", "BND", "IVV", "SCHB", "VT", "ITOT", "SPTM"}

_DROP_ASSET_KEYWORDS = {
    "bond", "municipal", "treasury", "mutual fund", "money market",
}

_TRANSACTION_TYPE_MAP = {
    "purchase": "buy",
    "sale (full)": "sell",
    "sale (partial)": "sell",
    "sale": "sell",
    "exchange": "exchange",
}

# Canonical amount-range strings → (low, high)
_AMOUNT_RANGES = [
    (r"\$1,001\s*[-–]\s*\$15,000", 1_001, 15_000),
    (r"\$15,001\s*[-–]\s*\$50,000", 15_001, 50_000),
    (r"\$50,001\s*[-–]\s*\$100,000", 50_001, 100_000),
    (r"\$100,001\s*[-–]\s*\$250,000", 100_001, 250_000),
    (r"\$250,001\s*[-–]\s*\$500,000", 250_001, 500_000),
    (r"\$500,001\s*[-–]\s*\$1,000,000", 500_001, 1_000_000),
    (r"\$1,000,001\s*[-–]\s*\$5,000,000", 1_000_001, 5_000_000),
    (r"\$5,000,001\s*[-–]\s*\$25,000,000", 5_000_001, 25_000_000),
    (r"\$25,000,001\s*[-–]\s*\$50,000,000", 25_000_001, 50_000_000),
]


def _parse_amount(raw: str | None) -> tuple[float | None, float | None]:
    """Parse FMP amount range string into (low, high) floats."""
    if not raw:
        return None, None
    raw = raw.strip()
    for pattern, low, high in _AMOUNT_RANGES:
        if re.search(pattern, raw, re.IGNORECASE):
            return float(low), float(high)
    # Over $50M
    if re.search(r"over\s*\$50,000,000|50,000,001", raw, re.IGNORECASE):
        return 50_000_001.0, None
    # Generic two-number fallback
    nums = re.findall(r"[\d,]+", raw)
    if len(nums) >= 2:
        try:
            return float(nums[0].replace(",", "")), float(nums[1].replace(",", ""))
        except ValueError:
            pass
    if len(nums) == 1:
        try:
            v = float(nums[0].replace(",", ""))
            return v, None
        except ValueError:
            pass
    logger.warning("Could not parse amount range %r — returning (None, None)", raw)
    return None, None


def _parse_transaction_type(raw: str | None) -> str:
    if not raw:
        return "other"
    return _TRANSACTION_TYPE_MAP.get(raw.strip().lower(), "other")


def _should_drop_asset(ticker: str, asset_type: str | None) -> bool:
    """Return True if this trade should be excluded from results."""
    if ticker.upper() in _BROAD_MARKET_ETFS:
        return True
    if asset_type:
        at_lower = asset_type.lower()
        if any(kw in at_lower for kw in _DROP_ASSET_KEYWORDS):
            return True
    return False


def _make_trade_id(full_name: str, txn_date: str, ticker: str, amount_raw: str | None) -> str:
    raw = f"{full_name}|{txn_date}|{ticker}|{amount_raw or ''}"
    return hashlib.sha256(raw.encode()).hexdigest()[:24]


def _fmp_get(path: str, api_key: str) -> list[dict]:
    """GET a FMP endpoint and return the JSON list. Raises loudly on failure."""
    url = f"{_FMP_BASE}{path}?apikey={api_key}"
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:  # noqa: S310
            data = json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise RuntimeError(
                f"FMP endpoint {path} returned 404. "
                "The endpoint is not available on your current FMP plan. "
                "Upgrade your plan or contact FMP support."
            ) from exc
        if exc.code == 403:
            raise RuntimeError(
                f"FMP endpoint {path} returned 403 Forbidden. "
                "Your current FMP plan does not include congressional-trading data. "
                "Upgrade to a plan that includes Senate/House disclosure endpoints "
                "(e.g. FMP Professional or Enterprise) and retry."
            ) from exc
        raise RuntimeError(
            f"FMP endpoint {path} returned HTTP {exc.code}: {exc.reason}"
        ) from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Network error fetching FMP {path}: {exc.reason}") from exc

    if isinstance(data, dict) and "Error Message" in data:
        raise RuntimeError(
            f"FMP endpoint {path} returned error: {data['Error Message']}. "
            "Check your API key and plan access."
        )
    if not isinstance(data, list):
        raise RuntimeError(
            f"FMP endpoint {path} returned unexpected type {type(data).__name__!r} "
            f"(expected list). Raw: {str(data)[:200]}"
        )
    return data


def _normalize_row(
    row: dict,
    chamber: str,
    name_to_bioguide: dict[str, str],
) -> CongressTrade | None:
    """Parse one FMP row into a CongressTrade. Returns None to drop the row."""
    # FMP field names vary slightly between senate and house endpoints
    first = (row.get("firstName") or row.get("first_name") or "").strip()
    last = (row.get("lastName") or row.get("last_name") or "").strip()
    full_name = f"{first} {last}".strip() or row.get("name", "Unknown")

    ticker = (row.get("ticker") or row.get("symbol") or "").strip().upper()
    if not ticker:
        return None

    asset_type = (row.get("assetType") or row.get("asset_type") or "").strip()
    amount_raw = row.get("amount") or row.get("amountRange")

    if _should_drop_asset(ticker, asset_type):
        logger.debug("Dropping %s trade for %s (asset_type=%r)", ticker, full_name, asset_type)
        return None

    txn_date_str = (
        row.get("transactionDate")
        or row.get("transaction_date")
        or row.get("date")
        or ""
    )
    disc_date_str = (
        row.get("disclosureDate")
        or row.get("disclosure_date")
        or row.get("dateRecieved")  # FMP typo
        or ""
    )

    try:
        txn_date = date.fromisoformat(txn_date_str[:10])
    except (ValueError, TypeError):
        logger.warning("Unparseable transaction_date %r for %s — skipping row", txn_date_str, full_name)
        return None

    try:
        disc_date = date.fromisoformat(disc_date_str[:10]) if disc_date_str else txn_date
    except (ValueError, TypeError):
        disc_date = txn_date

    party_raw = (row.get("party") or "").strip()
    party: str
    if party_raw.upper() in ("D", "DEMOCRAT", "DEMOCRATIC"):
        party = "D"
    elif party_raw.upper() in ("R", "REPUBLICAN"):
        party = "R"
    else:
        party = "I"

    txn_type_raw = row.get("type") or row.get("transactionType") or ""
    transaction_type = _parse_transaction_type(txn_type_raw)

    amount_low, amount_high = _parse_amount(amount_raw)
    filing_id = row.get("link") or row.get("filing_id") or row.get("id")
    if filing_id:
        filing_id = str(filing_id)

    trade_id = _make_trade_id(full_name, txn_date_str[:10], ticker, str(amount_raw))

    # Attempt bioguide lookup by full name
    bioguide_id = name_to_bioguide.get(full_name.lower())
    if bioguide_id is None and full_name:
        # Try last-name only as fallback (less precise)
        bioguide_id = name_to_bioguide.get(last.lower())

    if bioguide_id is None and full_name and full_name != "Unknown":
        logger.warning(
            "No bioguide_id match for %r — keeping trade with bioguide_id=None", full_name
        )

    # If asset_type is ambiguous, keep but log
    if asset_type and not any(
        kw in asset_type.lower()
        for kw in ("stock", "option", "etf", "bond", "mutual", "treasury", "fund")
    ):
        logger.warning(
            "Ambiguous asset_type %r for %s/%s — keeping row for later filtering", asset_type, full_name, ticker
        )

    return CongressTrade(
        trade_id=trade_id,
        bioguide_id=bioguide_id,
        full_name=full_name,
        chamber=chamber,  # type: ignore[arg-type]
        party=party,  # type: ignore[arg-type]
        ticker=ticker,
        asset_type=asset_type,
        transaction_type=transaction_type,  # type: ignore[arg-type]
        transaction_date=txn_date,
        disclosure_date=disc_date,
        amount_low=amount_low,
        amount_high=amount_high,
        filing_id=filing_id,
    )


def _build_name_to_bioguide(legislators: list[dict] | None) -> dict[str, str]:
    """Build a lowercase full-name → bioguide_id lookup from legislators list."""
    if not legislators:
        return {}
    result: dict[str, str] = {}
    for leg in legislators:
        bid = leg.get("bioguide_id")
        if not bid:
            continue
        full = leg.get("full_name", "")
        if full:
            result[full.lower()] = bid
        last = leg.get("last_name", "")
        if last:
            result.setdefault(last.lower(), bid)
    return result


def fetch_recent_congress_trades(
    days_back: int = 90,
    bioguide_filter: list[str] | None = None,
    legislators: list[dict] | None = None,
) -> list[CongressTrade]:
    """Return CongressTrade records from FMP for the trailing days_back window.

    legislators: list of watched-member dicts (from fetch_committee_membership)
        used for name→bioguide matching. If None, all trades have bioguide_id=None.
    bioguide_filter: if provided, only return trades from those members.
        Filtering is done post-fetch (by bioguide_id or by name-match).

    If FMP returns HTTP 404 for any endpoint, raises immediately with a clear
    error naming the endpoint and suggesting a plan upgrade.
    """
    api_key = os.environ.get("FMP_API_KEY", "")
    if not api_key:
        raise RuntimeError(
            "FMP_API_KEY environment variable is not set. "
            "Set it to your Financial Modeling Prep API key."
        )

    name_to_bioguide = _build_name_to_bioguide(legislators or [])
    cutoff = date.today() - timedelta(days=days_back)

    all_trades: list[CongressTrade] = []

    for chamber, path in [("senate", "/senate-trading"), ("house", "/house-disclosure")]:
        logger.info("Fetching FMP %s trades from %s …", chamber, path)
        rows = _fmp_get(path, api_key)
        logger.info("FMP %s: %d raw rows returned", chamber, len(rows))

        for row in rows:
            trade = _normalize_row(row, chamber, name_to_bioguide)
            if trade is None:
                continue
            if trade.transaction_date < cutoff:
                continue
            all_trades.append(trade)

    logger.info(
        "fetch_recent_congress_trades: %d trades in trailing %d days before filtering",
        len(all_trades),
        days_back,
    )

    if bioguide_filter:
        filter_set = set(bioguide_filter)
        all_trades = [
            t for t in all_trades
            if t.bioguide_id in filter_set
        ]
        logger.info(
            "After bioguide_filter (%d ids): %d trades remain",
            len(filter_set),
            len(all_trades),
        )

    # Dedupe by trade_id (last one wins — safe for same-content rows)
    seen: dict[str, CongressTrade] = {}
    for trade in all_trades:
        seen[trade.trade_id] = trade

    return list(seen.values())
