import logging
from pathlib import Path

from casino_dashboard.data.yfinance_client import fetch_universe_snapshot
from casino_dashboard.db.repository import save_snapshot
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

    logger.info("Computing signals …")
    compute_and_save_all_signals(universe, db_path)
    logger.info("Signals computed for %d tickers", len(all_tickers))


if __name__ == "__main__":
    main()
