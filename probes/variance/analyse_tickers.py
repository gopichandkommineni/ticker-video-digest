"""
Ticker extraction and analytics across all handles.
Uses twitterapi_run1.json (most complete, stable run) per probe.
"""

import json
import re
from pathlib import Path
from collections import defaultdict
from datetime import datetime

# --- config ---
BASE = Path(__file__).parent
RUNS = {
    "speculator_io":  BASE / "2026-06-06_speculator_io/twitterapi_run1.json",
    "michaelsikand":  BASE / "2026-06-06_michaelsikand/twitterapi_run1.json",
    "zephyr_z9":      BASE / "2026-06-06_zephyr_z9/twitterapi_run1.json",
    "kawzinvests":    BASE / "2026-06-12_kawzinvests/twitterapi_run1.json",
}

# Match $TICKER: 1-5 uppercase letters only (excludes $1B, $100M, $2000 etc.)
TICKER_RE = re.compile(r'\$([A-Z]{1,5})(?=[^A-Z]|$)')

# Tokens that look like tickers but are currency/common words
FALSE_POSITIVES = {
    "I", "A", "US", "AI", "IPO", "CEO", "CFO", "EPS", "PE", "ETF",
    "AM", "PM", "GDP", "CPI", "FY", "Q", "S", "P", "VC", "DC",
    "OK", "OR", "IF", "IT", "AT", "BY", "IN", "ON", "BE", "DO",
    "GO", "IS", "OF", "AS", "UP", "NO", "SO", "TO", "VS",
}

# --- data structures ---
# ticker -> {handle -> [tweet_ids with dates]}
ticker_data: dict[str, dict[str, list[tuple[str, datetime]]]] = defaultdict(lambda: defaultdict(list))

# --- parse ---
for handle, path in RUNS.items():
    with open(path) as f:
        tweets = json.load(f)
    for tweet in tweets:
        text = tweet["text"]
        tweet_id = tweet["id"]
        date_str = tweet["created_at_utc"]
        date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        tickers = TICKER_RE.findall(text)
        for ticker in tickers:
            if ticker not in FALSE_POSITIVES:
                ticker_data[ticker][handle].append((tweet_id, date))

# --- aggregate ---
rows = []
for ticker, handle_map in ticker_data.items():
    total_mentions = sum(len(v) for v in handle_map.values())
    all_dates = [d for mentions in handle_map.values() for _, d in mentions]
    first_seen = min(all_dates)
    handles_present = sorted(handle_map.keys())
    per_handle = {h: len(v) for h, v in handle_map.items()}
    rows.append({
        "ticker": ticker,
        "total_mentions": total_mentions,
        "first_seen": first_seen,
        "handles": handles_present,
        "per_handle": per_handle,
    })

rows.sort(key=lambda r: (-r["total_mentions"], r["first_seen"]))

# --- print results ---
print(f"{'TICKER':<8} {'TOTAL':>6}  {'FIRST SEEN':<22}  {'HANDLES':<50}  PER-HANDLE BREAKDOWN")
print("-" * 130)
for r in rows:
    handle_str = ", ".join(r["handles"])
    breakdown = "  ".join(f"{h}:{n}" for h, n in sorted(r["per_handle"].items()))
    print(f"${r['ticker']:<7} {r['total_mentions']:>6}  {r['first_seen'].strftime('%Y-%m-%d %H:%M UTC'):<22}  {handle_str:<50}  {breakdown}")

print(f"\nTotal unique tickers: {len(rows)}")
print(f"Total mention events: {sum(r['total_mentions'] for r in rows)}")

# --- save CSV ---
import csv
out = BASE / "ticker_analytics.csv"
with open(out, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["ticker", "total_mentions", "first_seen_utc",
                "speculator_io", "michaelsikand", "zephyr_z9", "kawzinvests",
                "handles_count"])
    for r in rows:
        w.writerow([
            r["ticker"],
            r["total_mentions"],
            r["first_seen"].strftime("%Y-%m-%d %H:%M UTC"),
            r["per_handle"].get("speculator_io", 0),
            r["per_handle"].get("michaelsikand", 0),
            r["per_handle"].get("zephyr_z9", 0),
            r["per_handle"].get("kawzinvests", 0),
            len(r["handles"]),
        ])
print(f"\nCSV saved to: {out}")
