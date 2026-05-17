"""
congress_top_trades.py — fetch all congressional trades from the past N days,
filter to plain stock trades, and print the most traded tickers.

Usage:
    FMP_API_KEY=your_key python scripts/congress_top_trades.py
    FMP_API_KEY=your_key python scripts/congress_top_trades.py --days 30 --top 25
"""
import argparse
import collections
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, timedelta

_FMP_BASE = "https://financialmodelingprep.com/api/v4"

# Asset types / tickers to drop
_BROAD_MARKET_ETFS = {"SPY", "VOO", "VTI", "QQQ", "BND", "IVV", "SCHB", "VT", "ITOT", "SPTM"}
_DROP_KEYWORDS = {"bond", "municipal", "treasury", "mutual fund", "money market", "note"}

# Only keep these asset-type strings as "stock"
_STOCK_KEYWORDS = {"stock", "common stock", "equity"}


def _fmp_get(path: str, api_key: str) -> list[dict]:
    url = f"{_FMP_BASE}{path}?apikey={api_key}"
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:  # noqa: S310
            data = json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        if exc.code == 403:
            sys.exit(
                f"ERROR: FMP returned 403 for {path}.\n"
                "Your FMP plan does not include congressional-trading data.\n"
                "Upgrade to FMP Professional/Enterprise and retry."
            )
        if exc.code == 404:
            sys.exit(f"ERROR: FMP endpoint {path} returned 404 — not on your plan.")
        sys.exit(f"ERROR: FMP {path} HTTP {exc.code}: {exc.reason}")
    except urllib.error.URLError as exc:
        sys.exit(f"ERROR: Network error fetching {path}: {exc.reason}")

    if isinstance(data, dict) and "Error Message" in data:
        sys.exit(f"ERROR: FMP returned: {data['Error Message']}")
    if not isinstance(data, list):
        sys.exit(f"ERROR: FMP returned unexpected type {type(data).__name__}")
    return data


def _is_plain_stock(ticker: str, asset_type: str) -> bool:
    """Return True only for plain equity trades (not options, ETFs, bonds)."""
    if ticker.upper() in _BROAD_MARKET_ETFS:
        return False
    at = asset_type.lower() if asset_type else ""
    # Drop bonds, treasuries, mutual funds
    if any(kw in at for kw in _DROP_KEYWORDS):
        return False
    # Drop options explicitly
    if "option" in at or "call" in at or "put" in at:
        return False
    # Drop ETF label (sector ETFs included in committee view, but we want stocks here)
    if "etf" in at or "exchange traded" in at:
        return False
    # Accept explicit stock labels
    if any(kw in at for kw in _STOCK_KEYWORDS):
        return True
    # If asset_type is blank or unrecognised, accept only if the ticker looks like
    # a normal equity symbol (1–5 uppercase letters, no spaces)
    if not at:
        return ticker.isalpha() and 1 <= len(ticker) <= 5
    # Unknown — keep it (log-style: we print a note below)
    return True


def _parse_name(row: dict) -> str:
    first = (row.get("firstName") or row.get("first_name") or "").strip()
    last = (row.get("lastName") or row.get("last_name") or "").strip()
    return f"{first} {last}".strip() or row.get("name", "Unknown")


def _parse_date(row: dict) -> date | None:
    raw = (
        row.get("transactionDate")
        or row.get("transaction_date")
        or row.get("date")
        or ""
    )
    try:
        return date.fromisoformat(str(raw)[:10])
    except (ValueError, TypeError):
        return None


def _parse_txn_type(row: dict) -> str:
    raw = (row.get("type") or row.get("transactionType") or "").strip().lower()
    if "purchase" in raw or raw == "buy":
        return "BUY"
    if "sale" in raw or raw == "sell":
        return "SELL"
    return "OTHER"


def fetch_all_trades(days: int, api_key: str) -> list[dict]:
    cutoff = date.today() - timedelta(days=days)
    rows_out: list[dict] = []
    seen: set[str] = set()

    for chamber, path in [("Senate", "/senate-trading"), ("House", "/house-disclosure")]:
        print(f"  Fetching {chamber} ({path}) …", flush=True)
        raw_rows = _fmp_get(path, api_key)
        print(f"  → {len(raw_rows)} raw rows", flush=True)

        for row in raw_rows:
            txn_date = _parse_date(row)
            if txn_date is None or txn_date < cutoff:
                continue

            ticker = (row.get("ticker") or row.get("symbol") or "").strip().upper()
            if not ticker:
                continue

            asset_type = (row.get("assetType") or row.get("asset_type") or "").strip()
            if not _is_plain_stock(ticker, asset_type):
                continue

            name = _parse_name(row)
            txn_type = _parse_txn_type(row)
            amount_raw = str(row.get("amount") or row.get("amountRange") or "")

            dedup_key = f"{name}|{txn_date}|{ticker}|{amount_raw}"
            if dedup_key in seen:
                continue
            seen.add(dedup_key)

            rows_out.append({
                "chamber": chamber,
                "name": name,
                "ticker": ticker,
                "asset_type": asset_type,
                "txn_type": txn_type,
                "txn_date": txn_date,
                "amount": amount_raw,
            })

    return rows_out


def summarise(trades: list[dict], top_n: int) -> None:
    if not trades:
        print("\nNo stock trades found in the selected window.")
        return

    # Per-ticker aggregation
    ticker_count: dict[str, int] = collections.Counter()
    ticker_traders: dict[str, set[str]] = collections.defaultdict(set)
    ticker_buys: dict[str, int] = collections.Counter()
    ticker_sells: dict[str, int] = collections.Counter()

    for t in trades:
        tk = t["ticker"]
        ticker_count[tk] += 1
        ticker_traders[tk].add(t["name"])
        if t["txn_type"] == "BUY":
            ticker_buys[tk] += 1
        elif t["txn_type"] == "SELL":
            ticker_sells[tk] += 1

    ranked = ticker_count.most_common(top_n)

    print(f"\n{'Rank':<5} {'Ticker':<8} {'Trades':>6} {'Traders':>7} {'Buys':>6} {'Sells':>6}  Sentiment")
    print("-" * 60)
    for rank, (tk, count) in enumerate(ranked, 1):
        traders = len(ticker_traders[tk])
        buys = ticker_buys[tk]
        sells = ticker_sells[tk]
        net = buys - sells
        sentiment = f"{'↑' * min(buys, 3)}{'↓' * min(sells, 3)}" if (buys or sells) else "—"
        net_str = f"+{net}" if net > 0 else str(net)
        print(f"{rank:<5} {tk:<8} {count:>6} {traders:>7} {buys:>6} {sells:>6}  {sentiment}  (net {net_str})")

    # Buy-only and sell-only standouts
    buy_only = sorted(
        [(tk, ticker_buys[tk]) for tk in ticker_count if ticker_sells[tk] == 0 and ticker_buys[tk] >= 2],
        key=lambda x: -x[1],
    )[:5]
    sell_only = sorted(
        [(tk, ticker_sells[tk]) for tk in ticker_count if ticker_buys[tk] == 0 and ticker_sells[tk] >= 2],
        key=lambda x: -x[1],
    )[:5]

    if buy_only:
        print(f"\n  All-buy tickers (≥2 trades, zero sells): {', '.join(tk for tk, _ in buy_only)}")
    if sell_only:
        print(f"  All-sell tickers (≥2 trades, zero buys): {', '.join(tk for tk, _ in sell_only)}")

    print(f"\nTotal stock trades: {len(trades)} across {len(ticker_count)} unique tickers")
    print("Disclaimer: Aggregated from public STOCK Act disclosures. Not investment advice.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Most-traded stocks in congressional disclosures")
    parser.add_argument("--days", type=int, default=30, help="Look-back window in days (default 30)")
    parser.add_argument("--top", type=int, default=20, help="How many tickers to show (default 20)")
    args = parser.parse_args()

    api_key = os.environ.get("FMP_API_KEY", "")
    if not api_key:
        sys.exit("ERROR: FMP_API_KEY environment variable is not set.")

    print(f"Fetching congressional stock trades — last {args.days} days …")
    trades = fetch_all_trades(args.days, api_key)
    print(f"Found {len(trades)} qualifying stock trades after filtering.\n")
    summarise(trades, args.top)


if __name__ == "__main__":
    main()
