"""The daily refresh — the job that keeps `data/snapshots.db` current.

Run four times every weekday by .github/workflows/daily_refresh.yml.

This module is only the running order. The work lives next door:

  refresh_stages.py   the thirteen stages, one function each
  refresh_sources.py  the fetch helpers those stages call
  refresh_report.py   the per-run report written to the GitHub job summary

The names below are re-exported so existing imports of
`casino_dashboard.jobs.daily_refresh` keep resolving.
"""
import logging
from datetime import date, datetime, timezone
from pathlib import Path

from casino_dashboard.jobs.refresh_report import Report, _write_job_summary
from casino_dashboard.jobs.refresh_sources import (
    _refresh_apewisdom_by_subreddit,
    _refresh_congress,
    _refresh_reddit_posts,
    _select_reddit_tickers,
    refresh_single_ticker,
)
from casino_dashboard.jobs.refresh_stages import (
    _stage_congress,
    _stage_deal_log,
    _stage_etf_flows,
    _stage_manual_notes,
    _stage_price_snapshots,
    _stage_reddit_posts,
    _stage_sector_heat,
    _stage_signals,
    _stage_social_mentions,
    _stage_social_mentions_by_subreddit,
    _stage_ticker_metadata,
    _stage_universe,
    _stage_user_ticker_retries,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

_DEFAULT_DB = Path("data/snapshots.db")

__all__ = [
    "main",
    "refresh_single_ticker",
    "_write_job_summary",
    "_refresh_apewisdom_by_subreddit",
    "_select_reddit_tickers",
    "_refresh_reddit_posts",
    "_refresh_congress",
]


def main(db_path: Path = _DEFAULT_DB) -> None:
    """Run every stage of the daily refresh, in order.

    Each stage below owns its own error handling and appends one row to
    `stages`, so a dead data source degrades that row rather than killing the
    run. The two stages that are *not* guarded — universe and price snapshots —
    are the ones with nothing useful to salvage if they fail.

    The `finally` block writes the report either way, so a crash still leaves a
    record of how far the run got.
    """
    stages: Report = []
    failed_tickers: list[str] = []
    started = datetime.now(tz=timezone.utc)
    today = date.today()

    try:
        universe, all_tickers = _stage_universe(stages)
        failed_tickers = _stage_price_snapshots(stages, universe, all_tickers, db_path)
        reddit_priority = _stage_social_mentions(stages, all_tickers, today, db_path)
        _stage_social_mentions_by_subreddit(stages, all_tickers, today, db_path)
        _stage_reddit_posts(stages, all_tickers, reddit_priority, today, db_path)
        _stage_ticker_metadata(stages, all_tickers, db_path)
        _stage_manual_notes(stages, db_path)
        _stage_signals(stages, universe, all_tickers, db_path)
        _stage_etf_flows(stages, db_path)
        _stage_deal_log(stages, db_path)
        _stage_sector_heat(stages, universe, db_path)
        _stage_congress(stages, db_path)
        _stage_user_ticker_retries(stages, db_path)
    finally:
        _write_job_summary(stages, failed_tickers, started)


if __name__ == "__main__":
    main()
