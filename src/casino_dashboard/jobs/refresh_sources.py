"""Fetch helpers the stages call — one function per awkward data source.

These live apart from the stages so each stays a single readable page, and
so tests can patch a source without importing the whole pipeline.
"""

import os
import logging
from datetime import date
from pathlib import Path

from core.social_media.reddit.apewisdom_client import (
    DEFAULT_SUBREDDIT_FILTERS,
    fetch_apewisdom_universe,
    filter_to_universe,
)
from casino_dashboard.data.subreddit_map_loader import load_subreddit_map
from casino_dashboard.jobs.reddit_pull import pull_reddit_for_tickers
from casino_dashboard.data.congress_legislators_fetcher import fetch_committee_membership
from casino_dashboard.data.congress_trades_fetcher import fetch_recent_congress_trades
from casino_dashboard.data.star_traders_loader import load_star_traders
from casino_dashboard.data.yfinance_client import fetch_ticker_history
from casino_dashboard.data.yfinance_metadata import fetch_ticker_metadata
from casino_dashboard.db.repository import (
    save_signal,
    save_snapshot,
    save_social_mention,
    save_ticker_metadata,
    upsert_congress_members,
    upsert_congress_trades,
)
from casino_dashboard.signals.orchestrator import (
    compute_signals_for_ticker,
    compute_social_signals_for_ticker,
)
from casino_dashboard.jobs.refresh_report import Report

logger = logging.getLogger(__name__)

_STAR_TRADERS_PATH = Path("config/star_traders.yaml")



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


def _refresh_apewisdom_by_subreddit(
    all_tickers: list[str],
    today: date,
    db_path: Path,
) -> tuple[int, int]:
    """Fetch ApeWisdom mention data per subreddit and store a breakdown.

    Saves rows as source='apewisdom' with a NON-empty subreddit, so they sit
    alongside the aggregate (subreddit='') without disturbing the existing
    aggregate queries. Subreddit filters come from APEWISDOM_SUBREDDITS
    (comma-separated) or DEFAULT_SUBREDDIT_FILTERS. Returns (rows_saved, n_subs).
    """
    env = os.environ.get("APEWISDOM_SUBREDDITS", "").strip()
    filters = (
        [s.strip() for s in env.split(",") if s.strip()]
        if env else list(DEFAULT_SUBREDDIT_FILTERS)
    )
    universe = set(all_tickers)
    saved = 0
    for sub in filters:
        try:
            mentions = fetch_apewisdom_universe(sub)
        except Exception as exc:
            logger.warning("ApeWisdom subreddit %s failed (continuing): %s", sub, exc)
            continue
        for m in filter_to_universe(mentions, universe):
            save_social_mention(
                ticker=m.ticker,
                mention_date=today,
                source="apewisdom",
                mention_count=m.mentions,
                mentions_24h_ago=m.mentions_24h_ago,
                upvote_sum=m.upvotes,
                subreddit=sub,
                db_path=db_path,
            )
            saved += 1
    return saved, len(filters)


def _select_reddit_tickers(
    all_tickers: list[str],
    priority: list[str],
    max_tickers: int,
) -> list[str]:
    """Pick which tickers to pull full Reddit posts for, capped at *max_tickers*.

    Priority tickers (those ApeWisdom flagged as discussed, most-mentioned first)
    come first; the rest of the universe fills any remaining slots in stable
    order. Bounding keeps the polite public-JSON fetch (5 subreddits/ticker) from
    ballooning into hundreds of requests and tripping Reddit's rate limits.
    """
    ordered: list[str] = []
    seen: set[str] = set()
    universe = set(all_tickers)
    for t in priority:
        if t in universe and t not in seen:
            ordered.append(t)
            seen.add(t)
    for t in all_tickers:
        if t not in seen:
            ordered.append(t)
            seen.add(t)
    return ordered[:max_tickers]


def _refresh_reddit_posts(
    all_tickers: list[str],
    priority: list[str],
    today: date,
    db_path: Path,
) -> tuple[int, int]:
    """Pull individual Reddit posts for a bounded set of tickers and persist them.

    Uses RedditScraper (PRAW when REDDIT_CLIENT_ID/SECRET are set, else the
    public JSON API — no credentials required). For each ticker it stores every
    post in the reddit_posts table and writes a per-subreddit aggregate row into
    social_mentions (source='reddit', subreddit=<name>) for future breakdowns.
    Those aggregate rows carry a non-empty subreddit, so they are invisible to
    the existing ApeWisdom queries that filter on subreddit=''.

    Returns (total_posts_saved, tickers_covered).

    Bound the fetch with REDDIT_POSTS_MAX_TICKERS (default 25). Set it to 0 to
    skip the stage entirely.
    """
    max_tickers = int(os.environ.get("REDDIT_POSTS_MAX_TICKERS", "25"))
    if max_tickers <= 0:
        logger.info("REDDIT_POSTS_MAX_TICKERS=%d — skipping Reddit posts stage", max_tickers)
        return 0, 0
    per_ticker = int(os.environ.get("REDDIT_POSTS_PER_TICKER", "25"))

    targets = _select_reddit_tickers(all_tickers, priority, max_tickers)
    subreddit_map = load_subreddit_map()
    return pull_reddit_for_tickers(
        targets, today, db_path, subreddit_map=subreddit_map, per_ticker=per_ticker
    )


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
