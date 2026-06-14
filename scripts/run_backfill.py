"""Manual backfill for one handle — called by fintwit-backfill.yml.

Usage: python scripts/run_backfill.py <handle>
"""

import os
import sys

from dotenv import load_dotenv

load_dotenv(".env")

from storage import close_connection, normalize_handle  # noqa: E402
from orchestration.runner import ingest_handle  # noqa: E402

if len(sys.argv) != 2 or not sys.argv[1].strip():
    print("Usage: run_backfill.py <handle>", file=sys.stderr)
    sys.exit(1)

handle = normalize_handle(sys.argv[1])
print(f"Backfilling handle: {handle}")
result = ingest_handle(handle)

print(f"\n── Backfill result for @{handle} ──")
print(f"  outcome:         {result.outcome}")
print(f"  days ok:         {result.days_ok}")
print(f"  days mismatch:   {result.days_mismatch}")
print(f"  days failed:     {result.days_failed}")
print(f"  coverage_floor:  {result.coverage_floor}")
if result.outcome == "incomplete":
    print(f"  reason:          {result.reason!r}")
if result.error:
    print(f"  error:           {result.error}")

close_connection()

icon = "✓" if result.outcome == "ok" else ("~" if result.outcome == "incomplete" else "✗")
summary_lines = [
    f"## FinTwit Backfill — @{handle}",
    "| field | value |",
    "|-------|-------|",
    f"| outcome | {icon} {result.outcome} |",
    f"| days ok | {result.days_ok} |",
    f"| days mismatch | {result.days_mismatch} |",
    f"| days failed | {result.days_failed} |",
    f"| coverage floor | {result.coverage_floor or 'none'} |",
]
if result.outcome == "incomplete":
    summary_lines += [
        "",
        f"> **incomplete** — {result.reason}. The daily-delta job will retry outstanding days.",
    ]
if result.error:
    summary_lines.append(f"| error | {result.error} |")

summary_path = os.environ.get("GITHUB_STEP_SUMMARY", "/dev/null")
with open(summary_path, "w") as f:
    f.write("\n".join(summary_lines) + "\n")

if result.outcome == "failed":
    sys.exit(1)
