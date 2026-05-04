import logging
from datetime import date
from pathlib import Path

from casino_dashboard.data.apewisdom_client import fetch_apewisdom_universe, filter_to_universe
from casino_dashboard.data.reddit_client import fetch_reddit_mentions_for_universe, get_reddit_client
from casino_dashboard.data.yfinance_client import fetch_universe_snapshot
from casino_dashboard.db.repository import save_snapshot, save_social_mention
from casino_dashboard.signals.orchestrator import compute_and_save_all_signals
from casino_dashboard.universe import load_universe

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

_DEFAULT_DB = Path("data/snapshots.db")


def main(db_path: Path = _DEFAULT_DB) -> None:
    logger.info("Loading universe …")
    universe = load_universe()
    all_tickers = universe.all_tickers()
    logger.info("Universe: %d unique tickers across %d sectors", len(all_tickers), len(universe.sectors))

    logger.info("Fetching snapshots …")
    snapshots_by_ticker = fetch_universe_snapshot(universe)

    total_rows = 0
    for ticker, snaps in snapshots_by_ticker.items():
        for snap in snaps:
            save_snapshot(snap, db_path)
        total_rows += len(snaps)

    fetched_tickers = len(snapshots_by_ticker)
    failed = len(all_tickers) - fetched_tickers
    logger.info("Done. Saved %d rows across %d tickers, %d failed.", total_rows, fetched_tickers, failed)

    logger.info("Fetching ApeWisdom social mentions …")
    today = date.today()
    try:
        all_mentions = fetch_apewisdom_universe("all-stocks")
        universe_mentions = filter_to_universe(all_mentions, set(all_tickers))
        skipped = len(all_mentions) - len(universe_mentions)
        for m in universe_mentions:
            save_social_mention(
                ticker=m.ticker,
                mention_date=today,
                source="apewisdom",
                mention_count=m.mentions,
                mentions_24h_ago=m.mentions_24h_ago,
                upvote_sum=m.upvotes,
                db_path=db_path,
            )
        logger.info("Saved %d social mentions from ApeWisdom", len(universe_mentions))
        logger.info("Skipped %d tickers not in ApeWisdom data", skipped)
    except Exception as exc:
        logger.error("ApeWisdom fetch failed (continuing): %s", exc)

    logger.info("Fetching Reddit social mentions …")
    reddit = get_reddit_client()
    if reddit:
        try:
            reddit_mentions = fetch_reddit_mentions_for_universe(reddit, all_tickers)
            for m in reddit_mentions:
                save_social_mention(
                    ticker=m.ticker,
                    mention_date=today,
                    source=f"reddit_{m.subreddit}",
                    mention_count=m.mention_count,
                    mentions_24h_ago=None,
                    upvote_sum=m.upvote_sum,
                    subreddit=m.subreddit,
                    db_path=db_path,
                )
            logger.info(
                "Saved Reddit mentions for %d ticker-subreddit pairs", len(reddit_mentions)
            )
        except Exception as exc:
            logger.error("Reddit fetch failed (continuing): %s", exc)
    else:
        logger.warning("Reddit credentials not configured, skipping Reddit collection")

    logger.info("Computing signals …")
    compute_and_save_all_signals(universe, db_path)
    logger.info("Signals computed for %d tickers", len(all_tickers))


if __name__ == "__main__":
    main()
