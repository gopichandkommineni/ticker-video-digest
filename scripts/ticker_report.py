"""Per-ticker mention report across all stored handles.

Rebuilds ticker_mentions from raw_tweets, then reports for each ticker how many
times it is mentioned (tweet-level) and by how many distinct handles. Universe
tickers and off-universe "discovery" cashtags are reported separately.

Usage:
  python scripts/ticker_report.py                 # console report
  python scripts/ticker_report.py --top 40        # show top N of each group
  python scripts/ticker_report.py --csv out.csv   # also write a flat CSV
  python scripts/ticker_report.py --matrix         # add per-handle breakdown
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from storage.db import get_connection, close_connection  # noqa: E402
from analysis.tickers import rebuild_mentions  # noqa: E402


def _ticker_totals(conn, in_universe: int):
    return conn.execute(
        """
        SELECT ticker,
               COUNT(*)                          AS mentions,
               COUNT(DISTINCT account_handle)    AS handles
        FROM ticker_mentions
        WHERE in_universe = ?
        GROUP BY ticker
        ORDER BY mentions DESC, ticker ASC
        """,
        (in_universe,),
    ).fetchall()


def _print_group(title: str, rows, top: int) -> None:
    print(f"\n## {title}  ({len(rows)} tickers)\n")
    print(f"  {'ticker':<8} {'mentions':>8} {'handles':>8}")
    print("  " + "-" * 26)
    for r in rows[:top]:
        print(f"  ${r['ticker']:<7} {r['mentions']:>8} {r['handles']:>8}")


def _print_matrix(conn, rows, top: int) -> None:
    handles = [
        h["account_handle"]
        for h in conn.execute(
            "SELECT DISTINCT account_handle FROM ticker_mentions ORDER BY account_handle"
        ).fetchall()
    ]
    short = [h[:8] for h in handles]
    print("\n## Per-handle matrix (universe, top tickers)\n")
    print("  " + f"{'ticker':<8}" + "".join(f"{s:>9}" for s in short) + f"{'TOTAL':>8}")
    for r in rows[:top]:
        counts = {
            row["account_handle"]: row["n"]
            for row in conn.execute(
                "SELECT account_handle, COUNT(*) n FROM ticker_mentions "
                "WHERE ticker = ? GROUP BY account_handle",
                (r["ticker"],),
            ).fetchall()
        }
        cells = "".join(f"{counts.get(h, 0):>9}" for h in handles)
        print(f"  ${r['ticker']:<7}{cells}{r['mentions']:>8}")


def _write_csv(rows_uni, rows_non, path: str) -> None:
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ticker", "mentions", "distinct_handles", "in_universe"])
        for r in rows_uni:
            w.writerow([r["ticker"], r["mentions"], r["handles"], 1])
        for r in rows_non:
            w.writerow([r["ticker"], r["mentions"], r["handles"], 0])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=30)
    ap.add_argument("--csv", default=None)
    ap.add_argument("--matrix", action="store_true")
    args = ap.parse_args()

    n = rebuild_mentions()
    conn = get_connection()
    try:
        rows_uni = _ticker_totals(conn, 1)
        rows_non = _ticker_totals(conn, 0)

        tweets = conn.execute("SELECT COUNT(*) FROM raw_tweets").fetchone()[0]
        print(f"# Ticker mention report")
        print(f"\n{n} mention rows from {tweets} tweets.")

        _print_group("Universe tickers", rows_uni, args.top)
        _print_group("Discovery cashtags (off-universe)", rows_non, args.top)

        if args.matrix:
            _print_matrix(conn, rows_uni, args.top)

        if args.csv:
            _write_csv(rows_uni, rows_non, args.csv)
            print(f"\nWrote CSV: {args.csv}")
    finally:
        conn.close()
    close_connection()


if __name__ == "__main__":
    main()
