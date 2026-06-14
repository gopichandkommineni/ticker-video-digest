"""Daily delta ingest — called by fintwit-daily.yml.

Runs ingest_all(), prints a per-handle summary, writes the GitHub job summary,
checkpoints the WAL, and exits non-zero if any handle is failed or incomplete.
"""

import os
import sys

from dotenv import load_dotenv

load_dotenv(".env")

from storage import close_connection  # noqa: E402
from orchestration.runner import ingest_all  # noqa: E402

results = ingest_all()

counts = {"ok": 0, "failed": 0, "incomplete": 0, "skipped": 0}
print("\n── FinTwit ingest summary ──")
for r in results:
    bucket = r.outcome if r.outcome in counts else "failed"
    counts[bucket] += 1
    if r.outcome == "ok":
        detail = (
            f"days_ok={r.days_ok} mismatch={r.days_mismatch} "
            f"failed={r.days_failed} floor={r.coverage_floor}"
        )
    elif r.outcome == "incomplete":
        detail = f"days_ok={r.days_ok} reason={r.reason!r} (will retry tomorrow)"
    elif r.outcome == "failed":
        detail = f"error={r.error!r}"
    else:
        detail = f"reason={r.reason!r}"
    flag = "✓" if r.outcome == "ok" else ("~" if r.outcome in ("skipped", "incomplete") else "✗")
    print(f"  {flag} {r.handle}: {r.outcome}  {detail}")

print(
    f"\n  ok={counts['ok']} failed={counts['failed']} "
    f"incomplete={counts['incomplete']} skipped={counts['skipped']}"
)

close_connection()

summary_lines = [
    "## FinTwit Daily Delta",
    "| outcome | count |",
    "|---------|-------|",
    f"| ✓ ok | {counts['ok']} |",
    f"| ~ incomplete | {counts['incomplete']} |",
    f"| ~ skipped | {counts['skipped']} |",
    f"| ✗ failed | {counts['failed']} |",
]
if counts["failed"] or counts["incomplete"]:
    summary_lines += ["", "### Handles needing attention"]
    for r in results:
        if r.outcome in ("failed", "incomplete"):
            summary_lines.append(
                f"- **{r.handle}**: {r.outcome} — {r.error or r.reason or ''}"
            )

summary_path = os.environ.get("GITHUB_STEP_SUMMARY", "/dev/null")
with open(summary_path, "w") as f:
    f.write("\n".join(summary_lines) + "\n")

if counts["failed"] or counts["incomplete"]:
    sys.exit(1)
