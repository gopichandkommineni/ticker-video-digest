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

from storage import close_connection, normalize_handle  # noqa: E402
from orchestration.runner import ingest_handle, run_days  # noqa: E402


def _write_summary(text: str) -> None:
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY", "/dev/null")
    with open(summary_path, "w") as f:
        f.write(text + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill FinTwit handles.")
    parser.add_argument("handles", help="comma-separated handle(s), with or without @")
    parser.add_argument("--since", type=datetime.date.fromisoformat, metavar="YYYY-MM-DD")
    parser.add_argument("--until", type=datetime.date.fromisoformat, metavar="YYYY-MM-DD")
    args = parser.parse_args()

    handles = [normalize_handle(h) for h in args.handles.split(",") if h.strip()]
    if not handles:
        parser.error("no handles given")
    if bool(args.since) != bool(args.until):
        parser.error("--since and --until must be given together")

    # Windowed range backfill: fills interior gaps that delta runs can't reach.
    if args.since:
        print(f"Range backfill {handles} over {args.since} → {args.until}")
        result = run_days(handles, args.since, args.until)
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
