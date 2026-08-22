"""The run report: one row per stage, rendered into the GitHub job summary."""

import os
from datetime import (
    datetime,
    timezone,
)

# One row per pipeline stage: (stage name, human-readable outcome). The run
# ends by rendering these into a single report — see _write_job_summary.
Report = list[tuple[str, str]]

def _write_job_summary(
    stages: list[tuple[str, str]],
    failed_tickers: list[str],
    started: datetime,
) -> None:
    """Write a markdown report of the run to the GitHub job summary.

    Mirrors the FinTwit jobs: writes to $GITHUB_STEP_SUMMARY, defaulting to
    /dev/null for local runs so this is a no-op outside Actions.
    """
    elapsed = (datetime.now(tz=timezone.utc) - started).total_seconds()
    lines = [
        f"## Daily Refresh — {started.strftime('%Y-%m-%d %H:%M')} UTC",
        "",
        f"Completed in {elapsed:.0f}s.",
        "",
        "| Stage | Result |",
        "|-------|--------|",
    ]
    for name, detail in stages:
        lines.append(f"| {name} | {detail} |")

    if failed_tickers:
        lines += [
            "",
            f"### Tickers that failed to fetch ({len(failed_tickers)})",
            "",
            ", ".join(failed_tickers),
        ]

    summary_path = os.environ.get("GITHUB_STEP_SUMMARY", "/dev/null")
    with open(summary_path, "w") as f:
        f.write("\n".join(lines) + "\n")
