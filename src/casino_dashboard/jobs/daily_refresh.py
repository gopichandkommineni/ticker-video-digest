import logging
from datetime import date
from pathlib import Path

from casino_dashboard.data.apewisdom_client import fetch_apewisdom_universe, filter_to_universe
from casino_dashboard.data.manual_notes_loader import load_manual_notes_from_yaml
from casino_dashboard.data.yfinance_client import fetch_universe_snapshot
from casino_dashboard.data.yfinance_metadata import fetch_metadata_for_universe
from casino_dashboard.db.repository import (
    save_manual_note,
    save_snapshot,
    save_social_mention,
    save_ticker_metadata,
)
from casino_dashboard.signals.orchestrator import compute_and_save_all_signals
from casino_dashboard.universe import load_universe

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

_DEFAULT_DB = Path("data/snapshots.db")
_MANUAL_NOTES_PATH = Path("config/manual_notes.yaml")


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

    logger.info("Fetching ticker metadata …")
    try:
        sorted_tickers = sorted(all_tickers)
        metadata_list = fetch_metadata_for_universe(sorted_tickers)
        populated = sum(
            1 for m in metadata_list
            if any(
                v is not None for v in [
                    m.fifty_two_week_high, m.fifty_two_week_low,
                    m.short_pct_of_float, m.short_ratio_days,
                    m.analyst_target_mean, m.held_pct_insiders,
                    m.held_pct_institutions, m.market_cap,
                    m.revenue_ttm, m.revenue_growth_yoy,
                    m.profit_margin, m.beta,
                    m.next_earnings_date, m.last_earnings_date,
                ]
            )
        )
        skipped_meta = len(metadata_list) - populated
        for meta in metadata_list:
            save_ticker_metadata(meta, db_path)
        logger.info("Fetched metadata for %d/%d tickers", populated, len(sorted_tickers))
        logger.info("Skipped %d tickers with no metadata", skipped_meta)
    except Exception as exc:
        logger.error("Ticker metadata fetch failed (continuing): %s", exc)

    logger.info("Loading manual notes from YAML …")
    try:
        notes = load_manual_notes_from_yaml(_MANUAL_NOTES_PATH)
        for ticker, note in notes.items():
            save_manual_note(
                ticker=ticker,
                catalyst=note["catalyst"],
                red_flag=note["red_flag"],
                db_path=db_path,
            )
        logger.info("Loaded %d manual notes from YAML", len(notes))
    except Exception as exc:
        logger.error("Manual notes load failed (continuing): %s", exc)

    logger.info("Computing signals …")
    compute_and_save_all_signals(universe, db_path)
    logger.info("Signals computed for %d tickers", len(all_tickers))


if __name__ == "__main__":
    main()
