"""Reddit-only refresh — pull posts into the DB without running the full daily
refresh.

Useful for running locally (from a residential IP, where Reddit's public API is
not blocked) to populate the reddit_posts table. Uses each ticker's subreddits
from config/ticker_subreddits.yaml when present, else the default finance subs.

Usage:
    python -m casino_dashboard.jobs.reddit_refresh                # whole universe
    python -m casino_dashboard.jobs.reddit_refresh RKLB ASTS COIN # specific tickers

Env:
    REDDIT_POSTS_PER_TICKER   max posts per ticker (default 25)
    REDDIT_CLIENT_ID/SECRET   optional — enables authenticated PRAW

NOTE: this writes to data/snapshots.db. Per CLAUDE.md that DB is production and
is normally committed only by the daily GitHub Action — review before committing
a local run.
"""
import logging
import os
import sys
from datetime import date
from pathlib import Path

from casino_dashboard.data.subreddit_map_loader import load_subreddit_map
from casino_dashboard.jobs.reddit_pull import pull_reddit_for_tickers

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

_DEFAULT_DB = Path("data/snapshots.db")


def _resolve_tickers(argv: list[str]) -> list[str]:
    if argv:
        return [a.strip().upper() for a in argv if a.strip()]
    from casino_dashboard.universe import load_universe  # noqa: PLC0415

    return sorted(load_universe().all_tickers())


def run(tickers: list[str], db_path: Path = _DEFAULT_DB) -> tuple[int, int]:
    per_ticker = int(os.environ.get("REDDIT_POSTS_PER_TICKER", "25"))
    subreddit_map = load_subreddit_map()
    mapped = sum(1 for t in tickers if t.upper() in subreddit_map)
    logger.info(
        "Reddit refresh: %d tickers (%d using discovered subreddits, rest default subs)",
        len(tickers), mapped,
    )
    total, covered = pull_reddit_for_tickers(
        tickers, date.today(), db_path, subreddit_map=subreddit_map, per_ticker=per_ticker
    )
    logger.info("Saved %d Reddit posts across %d/%d tickers", total, covered, len(tickers))
    return total, covered


def main() -> None:
    tickers = _resolve_tickers(sys.argv[1:])
    total, covered = run(tickers)
    print(f"\nReddit refresh complete: {total} posts saved across {covered}/{len(tickers)} tickers.")


if __name__ == "__main__":
    main()
