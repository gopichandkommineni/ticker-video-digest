"""The thirteen stages of the daily refresh, in the order main() runs them.

Each stage appends exactly one row to `stages` and handles its own errors,
so a dead data source degrades one row instead of killing the run. The two
that are deliberately unguarded — universe and price snapshots — are the ones
with nothing useful to salvage if they fail.
"""

import logging
from datetime import date, datetime, timezone
from pathlib import Path

from core.social_media.reddit.apewisdom_client import (
    fetch_apewisdom_universe,
    filter_to_universe,
)
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
    get_user_added_tickers,
    save_deal_log_entries,
    save_etf_flow,
    save_manual_note,
    save_sector_etf_mapping,
    save_snapshot,
    save_social_mention,
    save_ticker_metadata,
    set_user_ticker_status,
)
from casino_dashboard.signals.orchestrator import compute_and_save_all_signals
from casino_dashboard.signals.sector_aggregator import compute_and_save_all_sector_heat
from casino_dashboard.universe import Universe, load_universe
from casino_dashboard.jobs.refresh_report import Report
from casino_dashboard.jobs.refresh_sources import (
    _refresh_apewisdom_by_subreddit,
    _refresh_congress,
    _refresh_reddit_posts,
    refresh_single_ticker,
)

logger = logging.getLogger(__name__)

_MANUAL_NOTES_PATH = Path("config/manual_notes.yaml")
_ETF_MAPPING_PATH = Path("config/etf_mapping.yaml")
_DEAL_LOG_PATH = Path("config/deal_log.yaml")



def _stage_universe(stages: Report) -> tuple[Universe, set[str]]:
    """Read config/themes.yaml: which stocks are we watching today?"""
    logger.info("Loading universe …")
    universe = load_universe()
    all_tickers = universe.all_tickers()
    logger.info("Universe: %d unique tickers across %d sectors", len(all_tickers), len(universe.sectors))
    stages.append(("Universe", f"{len(all_tickers)} tickers across {len(universe.sectors)} sectors"))
    return universe, all_tickers


def _stage_price_snapshots(
    stages: Report, universe: Universe, all_tickers: set[str], db_path: Path
) -> list[str]:
    """Download prices and volume for every stock. Returns the ones that failed."""
    logger.info("Fetching price snapshots …")
    snapshots_by_ticker = fetch_universe_snapshot(universe)

    total_rows = 0
    for ticker, snaps in snapshots_by_ticker.items():
        for snap in snaps:
            save_snapshot(snap, db_path)
        total_rows += len(snaps)

    fetched_tickers = len(snapshots_by_ticker)
    failed_tickers = sorted(set(all_tickers) - set(snapshots_by_ticker))
    logger.info(
        "Done. Saved %d rows across %d tickers, %d failed.",
        total_rows, fetched_tickers, len(failed_tickers),
    )
    stages.append((
        "Price snapshots",
        f"✓ {total_rows:,} rows · {fetched_tickers} tickers · {len(failed_tickers)} failed",
    ))
    return failed_tickers


def _stage_social_mentions(
    stages: Report, all_tickers: set[str], today: date, db_path: Path
) -> list[str]:
    """How much is each stock being talked about? Returns tickers by mention volume,
    which the Reddit post fetch below uses to spend its budget on names that matter."""
    logger.info("Fetching ApeWisdom social mentions …")
    # Tickers ApeWisdom reports as being discussed, most-mentioned first.
    # Used to focus the bounded per-post Reddit fetch on names that matter.
    reddit_priority: list[str] = []
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
        reddit_priority = [
            m.ticker for m in sorted(universe_mentions, key=lambda x: x.mentions, reverse=True)
        ]
        logger.info("Saved %d social mentions from ApeWisdom", len(universe_mentions))
        logger.info("Skipped %d tickers not in ApeWisdom data", skipped)
        stages.append(("Social mentions", f"✓ {len(universe_mentions)} saved"))
    except Exception as exc:
        logger.error("ApeWisdom fetch failed (continuing): %s", exc)
        stages.append(("Social mentions", f"✗ failed — {exc}"))
    return reddit_priority


def _stage_social_mentions_by_subreddit(
    stages: Report, all_tickers: set[str], today: date, db_path: Path
) -> None:
    """The same mention counts, split by individual subreddit."""
    logger.info("Fetching ApeWisdom per-subreddit mentions …")
    try:
        sub_saved, n_filters = _refresh_apewisdom_by_subreddit(all_tickers, today, db_path)
        logger.info("Saved %d per-subreddit mention rows across %d subs", sub_saved, n_filters)
        stages.append(("Social mentions (per-subreddit)", f"✓ {sub_saved} rows · {n_filters} subs"))
    except Exception as exc:
        logger.error("ApeWisdom per-subreddit fetch failed (continuing): %s", exc)
        stages.append(("Social mentions (per-subreddit)", f"✗ failed — {exc}"))


def _stage_reddit_posts(
    stages: Report,
    all_tickers: set[str],
    reddit_priority: list[str],
    today: date,
    db_path: Path,
) -> None:
    """Pull actual post text for the most-discussed names."""
    logger.info("Fetching Reddit posts …")
    try:
        posts_saved, tickers_covered = _refresh_reddit_posts(
            all_tickers, reddit_priority, today, db_path
        )
        logger.info("Saved %d Reddit posts across %d tickers", posts_saved, tickers_covered)
        stages.append(
            ("Reddit posts", f"✓ {posts_saved} posts · {tickers_covered} tickers")
        )
    except Exception as exc:
        logger.error("Reddit posts fetch failed (continuing): %s", exc)
        stages.append(("Reddit posts", f"✗ failed — {exc}"))


def _stage_ticker_metadata(stages: Report, all_tickers: set[str], db_path: Path) -> None:
    """Company facts: market cap, 52-week range, short interest, earnings dates."""
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
        stages.append(("Ticker metadata", f"✓ {populated}/{len(sorted_tickers)} populated"))
    except Exception as exc:
        logger.error("Ticker metadata fetch failed (continuing): %s", exc)
        stages.append(("Ticker metadata", f"✗ failed — {exc}"))


def _stage_manual_notes(stages: Report, db_path: Path) -> None:
    """Load the hand-written catalyst/red-flag notes from config/manual_notes.yaml."""
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
        stages.append(("Manual notes", f"✓ {len(notes)} loaded"))
    except Exception as exc:
        logger.error("Manual notes load failed (continuing): %s", exc)
        stages.append(("Manual notes", f"✗ failed — {exc}"))


def _stage_signals(
    stages: Report, universe: Universe, all_tickers: set[str], db_path: Path
) -> None:
    """Do the maths: returns, RSI, distance from high/low, volume spikes."""
    logger.info("Computing signals …")
    try:
        compute_and_save_all_signals(universe, db_path)
        logger.info("Signals computed for %d tickers", len(all_tickers))
        stages.append(("Signals", f"✓ {len(all_tickers)} tickers"))
    except Exception as exc:
        logger.error("Signal computation failed (continuing): %s", exc)
        stages.append(("Signals", f"✗ failed — {exc}"))


def _stage_etf_flows(stages: Report, db_path: Path) -> None:
    """Is money moving into the ETFs that represent each theme?"""
    logger.info("Fetching ETF flows …")
    try:
        etf_mapping = load_etf_mapping_from_yaml(_ETF_MAPPING_PATH)
        all_etfs: set[str] = set()
        for sector, tickers in etf_mapping.items():
            for etf_ticker in tickers:
                all_etfs.add(etf_ticker)
                save_sector_etf_mapping(sector, etf_ticker, is_primary=True, db_path=db_path)

        etfs_saved = 0
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
            etfs_saved += 1
            logger.info(
                "ETF flow saved for %s: aum=%.0f, net_flow=%s",
                etf_ticker,
                snapshot.aum_usd or 0,
                f"{net_flow:+.0f}" if net_flow is not None else "n/a (first day)",
            )
        logger.info("ETF flows saved for %d ETFs", len(all_etfs))
        stages.append(("ETF flows", f"✓ {etfs_saved}/{len(all_etfs)} ETFs"))
    except Exception as exc:
        logger.error("ETF flow fetch failed (continuing): %s", exc)
        stages.append(("ETF flows", f"✗ failed — {exc}"))


def _stage_deal_log(stages: Report, db_path: Path) -> None:
    """Load the deals recorded by hand in config/deal_log.yaml."""
    logger.info("Loading deal log from YAML …")
    try:
        deal_entries = load_deal_log_from_yaml(_DEAL_LOG_PATH)
        save_deal_log_entries(deal_entries, db_path)
        logger.info("Deal log: saved %d entries", len(deal_entries))
        stages.append(("Deal log", f"✓ {len(deal_entries)} entries"))
    except FileNotFoundError:
        logger.warning("Deal log YAML not found at %s — skipping", _DEAL_LOG_PATH)
        stages.append(("Deal log", "~ skipped — YAML not found"))
    except Exception as exc:
        logger.error("Deal log load failed (continuing): %s", exc)
        stages.append(("Deal log", f"✗ failed — {exc}"))


def _stage_sector_heat(stages: Report, universe: Universe, db_path: Path) -> None:
    """Roll every stock-level number up into one score per theme."""
    logger.info("Computing sector heat …")
    try:
        compute_and_save_all_sector_heat(universe, db_path)
        logger.info("Sector heat computed for %d sectors", len(universe.sectors))
        stages.append(("Sector heat", f"✓ {len(universe.sectors)} sectors"))
    except Exception as exc:
        logger.error("Sector heat computation failed (continuing): %s", exc)
        stages.append(("Sector heat", f"✗ failed — {exc}"))


def _stage_congress(stages: Report, db_path: Path) -> None:
    """Refresh congressional members, committees and disclosed trades."""
    logger.info("Refreshing congress data …")
    try:
        _refresh_congress(db_path)
        stages.append(("Congress data", "✓ refreshed"))
    except Exception as exc:
        logger.error("Congress refresh failed (continuing — data may be stale): %s", exc)
        stages.append(("Congress data", f"✗ failed — {exc}"))


def _stage_user_ticker_retries(stages: Report, db_path: Path) -> None:
    """Retry stocks added via the Add Stocks page whose first download failed."""
    # Retry user-added tickers that are 'pending' or 'failed'.
    # Safety net: Streamlit Cloud may restart mid-fetch leaving tickers stuck at
    # 'pending'; 'failed' tickers are retried daily until they succeed or are removed.
    try:
        retried = recovered = 0
        user_df = get_user_added_tickers(db_path)
        if not user_df.empty:
            retry_df = user_df[user_df["status"].isin(["pending", "failed"])]
            if not retry_df.empty:
                retried = len(retry_df)
                logger.info("Retrying %d user-added tickers (pending/failed) …", retried)
                for _, row in retry_df.iterrows():
                    success, error = refresh_single_ticker(row["ticker"], db_path)
                    now_iso = datetime.now(tz=timezone.utc).isoformat()
                    if success:
                        set_user_ticker_status(row["ticker"], "complete", None, now_iso, db_path)
                        recovered += 1
                        logger.info("User ticker %s: complete", row["ticker"])
                    else:
                        set_user_ticker_status(row["ticker"], "failed", error, now_iso, db_path)
                        logger.warning("User ticker %s: failed — %s", row["ticker"], error)
        stages.append(("User-added ticker retries", f"✓ {recovered}/{retried} recovered"))
    except Exception as exc:
        logger.error("User-ticker retry failed (continuing): %s", exc)
        stages.append(("User-added ticker retries", f"✗ failed — {exc}"))
