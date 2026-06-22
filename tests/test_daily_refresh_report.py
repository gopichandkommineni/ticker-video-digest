"""Daily Refresh job-summary report.

The daily refresh writes a markdown report to $GITHUB_STEP_SUMMARY (defaulting
to /dev/null off CI) so each run's outcome is visible in the Actions UI, the
same way the FinTwit extraction jobs do.
"""

from __future__ import annotations

from datetime import datetime, timezone

from casino_dashboard.jobs.daily_refresh import _write_job_summary


def test_report_written_with_stage_table(tmp_path, monkeypatch):
    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))

    started = datetime(2026, 6, 22, 13, 0, tzinfo=timezone.utc)
    stages = [
        ("Universe", "80 tickers across 8 sectors"),
        ("Price snapshots", "✓ 12,345 rows · 78 tickers · 2 failed"),
        ("Social mentions", "✗ failed — boom"),
    ]

    _write_job_summary(stages, ["AAA", "BBB"], started)

    text = summary.read_text()
    assert "## Daily Refresh — 2026-06-22 13:00 UTC" in text
    assert "| Stage | Result |" in text
    assert "| Price snapshots | ✓ 12,345 rows · 78 tickers · 2 failed |" in text
    assert "| Social mentions | ✗ failed — boom |" in text
    assert "### Tickers that failed to fetch (2)" in text
    assert "AAA, BBB" in text


def test_no_failed_tickers_section_when_all_ok(tmp_path, monkeypatch):
    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))

    started = datetime(2026, 6, 22, 13, 0, tzinfo=timezone.utc)
    _write_job_summary([("Price snapshots", "✓ 100 rows")], [], started)

    text = summary.read_text()
    assert "Tickers that failed to fetch" not in text
