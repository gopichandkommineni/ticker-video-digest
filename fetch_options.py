"""
Standalone script to fetch live options data for a given ticker.
Uses Yahoo Finance (no API key required).

Options contracts are standardized by the OCC, so strikes/expirations
are identical across brokers. Bid/ask may differ slightly per platform.

Usage:
    python fetch_options.py AAPL
    python fetch_options.py RKLB --expiry 2025-07-18
    python fetch_options.py SPY --type puts
"""

import sys
import argparse
from datetime import datetime
import yfinance as yf
import pandas as pd

pd.set_option("display.max_columns", None)
pd.set_option("display.width", 120)


def fetch_options(ticker: str, expiry: str | None = None, opt_type: str = "both") -> None:
    t = yf.Ticker(ticker)

    expirations = t.options
    if not expirations:
        print(f"No options data available for {ticker}")
        return

    print(f"\n{ticker.upper()} — available expirations:")
    for i, exp in enumerate(expirations):
        print(f"  [{i}] {exp}")

    target = expiry if expiry else expirations[0]
    if target not in expirations:
        print(f"\nExpiry {target!r} not found. Using nearest: {expirations[0]}")
        target = expirations[0]

    chain = t.option_chain(target)
    calls, puts = chain.calls, chain.puts

    # Current price for context
    info = t.fast_info
    current_price = getattr(info, "last_price", None)
    print(f"\nCurrent price: ${current_price:.2f}" if current_price else "")
    print(f"Expiry: {target}\n")

    cols = ["strike", "lastPrice", "bid", "ask", "volume", "openInterest", "impliedVolatility", "inTheMoney"]

    def show(df: pd.DataFrame, label: str) -> None:
        df = df[cols].copy()
        df["impliedVolatility"] = (df["impliedVolatility"] * 100).round(1).astype(str) + "%"
        df["inTheMoney"] = df["inTheMoney"].map({True: "ITM", False: "OTM"})
        print(f"--- {label} ({len(df)} contracts) ---")
        print(df.to_string(index=False))
        print()

    if opt_type in ("both", "calls"):
        show(calls, "CALLS")
    if opt_type in ("both", "puts"):
        show(puts, "PUTS")

    # Summary stats
    print("--- Summary ---")
    if opt_type in ("both", "calls"):
        print(f"Calls  — total OI: {calls['openInterest'].sum():,.0f}  |  total volume: {calls['volume'].sum():,.0f}")
    if opt_type in ("both", "puts"):
        print(f"Puts   — total OI: {puts['openInterest'].sum():,.0f}  |  total volume: {puts['volume'].sum():,.0f}")
    if opt_type == "both":
        total_call_oi = calls["openInterest"].sum()
        total_put_oi = puts["openInterest"].sum()
        ratio = total_put_oi / total_call_oi if total_call_oi else float("inf")
        print(f"Put/Call OI ratio: {ratio:.2f}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch live options chain from Yahoo Finance")
    parser.add_argument("ticker", help="Stock ticker (e.g. AAPL, RKLB, SPY)")
    parser.add_argument("--expiry", help="Expiration date YYYY-MM-DD (default: nearest)")
    parser.add_argument("--type", dest="opt_type", choices=["calls", "puts", "both"], default="both")
    args = parser.parse_args()

    fetch_options(args.ticker.upper(), args.expiry, args.opt_type)


if __name__ == "__main__":
    main()
