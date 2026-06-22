import logging
import os
from datetime import date, datetime, timezone
from pathlib import Path

from ticker_digest.social_media.reddit.apewisdom_client import fetch_apewisdom_universe, filter_to_universe
from casino_dashboard.data.congress_legislators_fetcher import fetch_committee_membership
from casino_dashboard.data.congress_trades_fetcher import fetch_recent_congress_trades
from casino_dashboard.data.deal_log_loader import load_deal_log_from_yaml
from casino_dashboard.data.etf_flows_fetcher import (
    calculate_implied_flow,
    fetch_etf_snapshot_today,
    load_etf_mapping_from_yaml,
)
from casino_dashboard.data.manual_notes_loader import load_manual_notes_from_yaml
from casino_dashboard.data.star_traders_loader import load_star_traders
from casino_dashboard.data.yfinance_client import fetch_ticker_history, fetch_universe_snapshot
from casino_dashboard.data.yfinance_metadata import fetch_ticker_metadata, fetch_metadata_for_universe
from casino_dashboard.db.repository import (
    get_etf_flows,
    get_user_added_tickers,
    save_deal_log_entries,
    save_etf_flow,
    save_manual_note,
    save_sector_etf_mapping,
    save_signal,
    save_snapshot,
    save_social_mention,
    save_ticker_metadata,
    set_user_ticker_status,
    upsert_congress_members,
    upsert_congress_trades,
)
from casino_dashboard.signals.orchestrator import (
    compute_and_save_all_signals,
    compute_signals_for_ticker,
    compute_social_signals_for_ticker,
)
from casino_dashboard.signals.sector_aggregator import compute_and_save_all_sector_heat
from casino_dashboard.universe import load_universe

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

_DEFAULT_DB = Path("data/snapshots.db")
_MANUAL_NOTES_PATH = Path("config/manual_notes.yaml")
_ETF_MAPPING_PATH = Path("config/etf_mapping.yaml")
_DEAL_LOG_PATH = Path("config/deal_log.yaml")
_STAR_TRADERS_PATH = Path("config/star_traders.yaml")


def main(db_path: Path = _DEFAULT_DB) -> None:
    # Each pipeline stage records one row here so the run ends with a single
    # human-readable report (written to the GitHub job summary). A finally block
    # writes the report even if an unguarded stage raises, so a crash still
    # leaves a record of how far the run got.
    stages: list[tuple[str, str]] = []
    failed_tickers: list[str] = []
    started = datetime.now(tz=timezone.utc)

    try:
        logger.info("Loading universe …")
        universe = load_universe()
        all_tickers = universe.all_tickers()
        logger.info("Universe: %d unique tickers across %d sectors", len(all_tickers), len(universe.sectors))
        stages.append(("Universe", f"{len(all_tickers)} tickers across {len(universe.sectors)} sectors"))

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
            stages.append(("Social mentions", f"✓ {len(universe_mentions)} saved"))
        except Exception as exc:
            logger.error("ApeWisdom fetch failed (continuing): %s", exc)
            stages.append(("Social mentions", f"✗ failed — {exc}"))

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

        logger.info("Computing signals …")
        try:
            compute_and_save_all_signals(universe, db_path)
            logger.info("Signals computed for %d tickers", len(all_tickers))
            stages.append(("Signals", f"✓ {len(all_tickers)} tickers"))
        except Exception as exc:
            logger.error("Signal computation failed (continuing): %s", exc)
            stages.append(("Signals", f"✗ failed — {exc}"))

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

        logger.info("Computing sector heat …")
        try:
            compute_and_save_all_sector_heat(universe, db_path)
            logger.info("Sector heat computed for %d sectors", len(universe.sectors))
            stages.append(("Sector heat", f"✓ {len(universe.sectors)} sectors"))
        except Exception as exc:
            logger.error("Sector heat computation failed (continuing): %s", exc)
            stages.append(("Sector heat", f"✗ failed — {exc}"))

        logger.info("Refreshing congress data …")
        try:
            _refresh_congress(db_path)
            stages.append(("Congress data", "✓ refreshed"))
        except Exception as exc:
            logger.error("Congress refresh failed (continuing — data may be stale): %s", exc)
            stages.append(("Congress data", f"✗ failed — {exc}"))

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
    finally:
        _write_job_summary(stages, failed_tickers, started)


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


def refresh_single_ticker(ticker: str, db_path: Path) -> tuple[bool, str | None]:
    """Fetch price history, metadata, and signals for a single ticker.

    Reuses the same per-ticker functions the daily job calls for the full universe.
    Returns (success, error_message). On success, error_message is None.
    """
    try:
        snapshots = fetch_ticker_history(ticker)
        if not snapshots:
            return False, f"No price history returned for {ticker}"
        for snap in snapshots:
            save_snapshot(snap, db_path)
        logger.info("refresh_single_ticker: saved %d snapshots for %s", len(snapshots), ticker)
    except Exception as exc:
        return False, f"Price history fetch failed: {exc}"

    try:
        meta = fetch_ticker_metadata(ticker)
        save_ticker_metadata(meta, db_path)
    except Exception as exc:
        logger.warning("refresh_single_ticker: metadata fetch failed for %s: %s", ticker, exc)

    try:
        today = date.today()
        signals = compute_signals_for_ticker(ticker, db_path)
        social_signals = compute_social_signals_for_ticker(ticker, db_path)
        signals.update(social_signals)
        for signal_name, value in signals.items():
            save_signal(ticker, today, signal_name, value, db_path)
        logger.info("refresh_single_ticker: computed %d signals for %s", len(signals), ticker)
    except Exception as exc:
        logger.warning("refresh_single_ticker: signal compute failed for %s: %s", ticker, exc)

    return True, None


def _refresh_congress(db_path: Path) -> None:
    """Fetch and store committee membership, star traders, and recent trades.

    Steps:
      1. Fetch watched members from unitedstates/congress-legislators.
      2. Load star traders from config/star_traders.yaml.
      3. Merge both lists into congress_members (both is_watched + is_star flags).
      4. Upsert committee links into congress_member_committees.
      5. Fetch recent trades for the union of watched + star bioguide_ids.
      6. Upsert trades into congress_trades.

    If the congress refresh fails entirely the caller catches and logs — the
    rest of the pipeline is not affected. Congress data being a day stale is
    acceptable; yfinance failing is not.
    """
    logger.info("Fetching committee membership from congress-legislators …")
    membership = fetch_committee_membership()
    watched_members = membership["watched_members"]
    all_bioguide_ids: list[str] = membership.get("all_bioguide_ids", [])
    logger.info("Got %d watched members from committee filter", len(watched_members))

    # Validate star trader IDs against all current legislators (not just watched members).
    known_bioguides = set(all_bioguide_ids) if all_bioguide_ids else None
    star_entries = load_star_traders(_STAR_TRADERS_PATH, known_bioguides=known_bioguides)
    logger.info("Loaded %d star traders from YAML", len(star_entries))

    # Build merged member dict keyed by bioguide_id
    merged: dict[str, dict] = {}

    for m in watched_members:
        bid = m["bioguide_id"]
        merged[bid] = {**m, "is_watched": 1, "is_star": 0}

    for star in star_entries:
        bid = star["bioguide_id"]
        if bid in merged:
            merged[bid]["is_star"] = 1
        else:
            # Star trader not in the committee watch list — add minimal record
            merged[bid] = {
                "bioguide_id": bid,
                "full_name": star["name"],
                "first_name": star["name"].split()[0] if star["name"] else "",
                "last_name": star["name"].split()[-1] if star["name"] else "",
                "party": "I",
                "state": "",
                "chamber": "",
                "committees": [],
                "is_watched": 0,
                "is_star": 1,
            }

    logger.info("Upserting %d congress members …", len(merged))
    upsert_congress_members(list(merged.values()), db_path)

    # Fetch trades for the union of all tracked members
    all_bioguide_ids = list(merged.keys())
    all_legislator_records = list(merged.values())
    logger.info("Fetching FMP trades for %d members …", len(all_bioguide_ids))
    trades = fetch_recent_congress_trades(
        days_back=90,
        bioguide_filter=all_bioguide_ids,
        legislators=all_legislator_records,
    )
    logger.info("Got %d filtered trades — upserting …", len(trades))
    upsert_congress_trades(trades, db_path)
    logger.info("Congress refresh complete.")


if __name__ == "__main__":
    main()
