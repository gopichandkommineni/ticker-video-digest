"""Manual backfill for one or more handles — called by fintwit-backfill.yml.

Usage:
  python scripts/run_backfill.py <handle>[,<handle>...]
  python scripts/run_backfill.py <handle>[,<handle>...] --since YYYY-MM-DD --until YYYY-MM-DD

Without a window, each handle runs through ingest_handle (backfill-or-delta) —
the original behavior. With --since/--until, the handles are range-backfilled
over [since, until] via run_days; this is the only path that can fill *interior*
coverage gaps, since a delta run only ever reaches the last 3 days.
"""

import argparse
import datetime
import os
import sys

from dotenv import load_dotenv

load_dotenv(".env")

from fintwit.storage import close_connection, normalize_handle, upsert_handle  # noqa: E402
from fintwit.storage.db import get_connection  # noqa: E402
from fintwit.storage.day_log import reopen_failed_days  # noqa: E402
from fintwit.orchestration.runner import ingest_handle, run_days  # noqa: E402


def _write_summary(text: str) -> None:
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY", "/dev/null")
    with open(summary_path, "w") as f:
        f.write(text + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill FinTwit handles.")
    parser.add_argument("handles", help="comma-separated handle(s), with or without @")
    parser.add_argument("--since", type=datetime.date.fromisoformat, metavar="YYYY-MM-DD")
    parser.add_argument("--until", type=datetime.date.fromisoformat, metavar="YYYY-MM-DD")
    parser.add_argument(
        "--reset-failed",
        action="store_true",
        help="Re-open terminally-failed day-slots in the window (retry_count reset "
             "to 0) before backfilling. Use to resume days that maxed out their "
             "attempts on a provider outage — e.g. HTTP 402 when credits ran out.",
    )
    args = parser.parse_args()
    if args.reset_failed and not args.since:
        parser.error("--reset-failed requires --since/--until")

    handles = [normalize_handle(h) for h in args.handles.split(",") if h.strip()]
    if not handles:
        parser.error("no handles given")
    if bool(args.since) != bool(args.until):
        parser.error("--since and --until must be given together")

    # Windowed range backfill: fills interior gaps that delta runs can't reach.
    if args.since:
        if args.reset_failed:
            conn = get_connection()
            try:
                reopened = sum(
                    reopen_failed_days(conn, h, args.since, args.until)
                    for h in handles
                )
            finally:
                conn.close()
            print(f"--reset-failed: reopened {reopened} failed day-slot(s)")
        print(f"Range backfill {handles} over {args.since} → {args.until}")
        result = run_days(handles, args.since, args.until)
        # Register the handles so the daily delta job keeps them fresh. The
        # --since/--until path calls run_days directly and never creates the
        # handle row that ingest_all() iterates via list_handles(); do it now
        # that run_days has initialised the DB. ingest_handle re-derives
        # backfill-vs-delta from the day ledger, so 'ready' is a status hint,
        # not a correctness dependency.
        for h in handles:
            upsert_handle(h, {"status": "ready"})
        print(result)
        _write_summary(
            f"## FinTwit Range Backfill — {', '.join('@' + h for h in handles)}\n"
            f"Window: `{args.since}` → `{args.until}`\n\n"
            f"```\n{result}\n```"
        )
        close_connection()
        return

    # Default: per-handle backfill-or-delta (original behavior, now over a list).
    exit_code = 0
    rows = [
        "## FinTwit Backfill",
        "| handle | outcome | days ok | mismatch | failed | coverage floor |",
        "|--------|---------|---------|----------|--------|----------------|",
    ]
    for handle in handles:
        print(f"Backfilling handle: {handle}")
        result = ingest_handle(handle)
        icon = "✓" if result.outcome == "ok" else ("~" if result.outcome == "incomplete" else "✗")
        print(
            f"  outcome={result.outcome} ok={result.days_ok} "
            f"mismatch={result.days_mismatch} failed={result.days_failed} "
            f"floor={result.coverage_floor}"
        )
        if result.error:
            print(f"  error: {result.error}")
        rows.append(
            f"| @{handle} | {icon} {result.outcome} | {result.days_ok} | "
            f"{result.days_mismatch} | {result.days_failed} | "
            f"{result.coverage_floor or 'none'} |"
        )
        if result.outcome == "failed":
            exit_code = 1
    _write_summary("\n".join(rows))

    close_connection()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
