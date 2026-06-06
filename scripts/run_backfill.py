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
print(f"  outcome:      {result.outcome}")
print(f"  inserted:     {result.inserted}")
print(f"  ignored:      {result.ignored}")
print(f"  watermark:    {result.watermark}")
if result.outcome == "incomplete":
    print(f"  reason:       {result.reason!r}")
else:
    print(f"  reached_floor: True (completed to floor)")
if result.error:
    print(f"  error:        {result.error}")

# R2: WAL checkpoint before git commit.
close_connection()

# GitHub job summary
icon = "✓" if result.outcome == "ok" else ("~" if result.outcome == "incomplete" else "✗")
summary_lines = [
    f"## FinTwit Backfill — @{handle}",
    "| field | value |",
    "|-------|-------|",
    f"| outcome | {icon} {result.outcome} |",
    f"| inserted | {result.inserted} |",
    f"| ignored | {result.ignored} |",
    f"| watermark | {result.watermark or 'none'} |",
]
if result.outcome == "incomplete":
    summary_lines.append(f"| reason | {result.reason} |")
    summary_lines.append("")
    summary_lines.append(
        "> **incomplete** — account is too large to finish in one run. "
        "The daily-delta job will retry until it reaches the Jan-1 floor."
    )
if result.error:
    summary_lines.append(f"| error | {result.error} |")

summary_path = os.environ.get("GITHUB_STEP_SUMMARY", "/dev/null")
with open(summary_path, "w") as f:
    f.write("\n".join(summary_lines) + "\n")

if result.outcome == "failed":
    sys.exit(1)
