import logging
from pathlib import Path

from casino_dashboard.data.yfinance_client import fetch_universe_snapshot
from casino_dashboard.db.repository import save_snapshot
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
    snapshots = fetch_universe_snapshot(universe)

    fetched = 0
    for snap in snapshots:
        save_snapshot(snap, db_path)
        fetched += 1

    failed = len(all_tickers) - fetched
    logger.info("Done. %d/%d tickers fetched, %d failed.", fetched, len(all_tickers), failed)


if __name__ == "__main__":
    main()
