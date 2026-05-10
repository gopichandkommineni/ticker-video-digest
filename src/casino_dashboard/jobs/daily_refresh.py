import logging
from datetime import date
from pathlib import Path

from casino_dashboard.data.apewisdom_client import fetch_apewisdom_universe, filter_to_universe
from casino_dashboard.data.deal_log_loader import load_deal_log_from_yaml
from casino_dashboard.data.etf_flows_fetcher import (
    calculate_implied_flow,
    fetch_etf_snapshot_today,
    load_etf_mapping_from_yaml,
)
from casino_dashboard.data.manual_notes_loader import load_manual_notes_from_yaml
from casino_dashboard.data.yfinance_client import fetch_universe_snapshot
from casino_dashboard.data.yfinance_metadata import fetch_metadata_for_universe
from casino_dashboard.db.repository import (
    get_etf_flows,
    save_deal_log_entries,
    save_etf_flow,
    save_manual_note,
    save_sector_etf_mapping,
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
_ETF_MAPPING_PATH = Path("config/etf_mapping.yaml")
_DEAL_LOG_PATH = Path("config/deal_log.yaml")


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

    logger.info("Fetching ETF flows …")
    try:
        etf_mapping = load_etf_mapping_from_yaml(_ETF_MAPPING_PATH)
        all_etfs: set[str] = set()
        for sector, tickers in etf_mapping.items():
            for etf_ticker in tickers:
                all_etfs.add(etf_ticker)
                save_sector_etf_mapping(sector, etf_ticker, is_primary=True, db_path=db_path)

        for etf_ticker in sorted(all_etfs):
            snapshot = fetch_etf_snapshot_today(etf_ticker)
            if snapshot is None:
                logger.warning("No ETF snapshot for %s — skipping", etf_ticker)
                continue

            # Calculate implied net flow vs previous stored day
            prior_df = get_etf_flows(etf_ticker, days=2, db_path=db_path)
            net_flow: float | None = None
            if not prior_df.empty and len(prior_df) >= 1:
                prior_row = prior_df.iloc[0]
                if (
                    prior_row["aum_usd"] is not None
                    and prior_row["price"] is not None
                    and snapshot.aum_usd is not None
                ):
                    net_flow = calculate_implied_flow(
                        today_aum=snapshot.aum_usd,
                        yesterday_aum=float(prior_row["aum_usd"]),
                        today_price=snapshot.price,
                        yesterday_price=float(prior_row["price"]),
                    )

            save_etf_flow(
                etf_ticker=etf_ticker,
                flow_date=snapshot.date,
                net_flow_usd=net_flow,
                aum_usd=snapshot.aum_usd,
                price=snapshot.price,
                db_path=db_path,
            )
            logger.info(
                "ETF flow saved for %s: aum=%.0f, net_flow=%s",
                etf_ticker,
                snapshot.aum_usd or 0,
                f"{net_flow:+.0f}" if net_flow is not None else "n/a (first day)",
            )
        logger.info("ETF flows saved for %d ETFs", len(all_etfs))
    except Exception as exc:
        logger.error("ETF flow fetch failed (continuing): %s", exc)

    logger.info("Loading deal log from YAML …")
    try:
        deal_entries = load_deal_log_from_yaml(_DEAL_LOG_PATH)
        save_deal_log_entries(deal_entries, db_path)
        logger.info("Deal log: saved %d entries", len(deal_entries))
    except FileNotFoundError:
        logger.warning("Deal log YAML not found at %s — skipping", _DEAL_LOG_PATH)
    except Exception as exc:
        logger.error("Deal log load failed (continuing): %s", exc)


if __name__ == "__main__":
    main()
