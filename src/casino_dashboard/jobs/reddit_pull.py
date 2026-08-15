"""Shared Reddit post-pulling logic, used by both the daily refresh and the
standalone `reddit_refresh` entrypoint.

Pulls posts per ticker (using each ticker's discovered subreddits from the map
when available, else the scraper's default finance subs), stores every post in
`reddit_posts`, and writes per-subreddit aggregate rows into `social_mentions`
under source='reddit' with a non-empty subreddit (invisible to the ApeWisdom
queries that filter on subreddit='').
"""
import logging
from datetime import date
from pathlib import Path

from core.social_media.base import SocialSignals, SocialScraper
from core.social_media.reddit.client import RedditScraper
from casino_dashboard.db.repository import save_reddit_posts, save_social_mention

logger = logging.getLogger(__name__)


def make_reddit_scraper() -> SocialScraper:
    """Return the active Reddit scraper: Apify's managed scraper when APIFY_TOKEN
    is set (handles Cloudflare), else the direct client (PRAW if credentialed,
    otherwise the public path).
    """
    from core.config import APIFY_TOKEN  # noqa: PLC0415 — read current value

    if APIFY_TOKEN:
        from core.social_media.reddit.apify_client import ApifyRedditScraper  # noqa: PLC0415

        return ApifyRedditScraper()
    return RedditScraper()


def save_ticker_signals(
    ticker: str, signals: SocialSignals, today: date, db_path: Path
) -> int:
    """Persist one ticker's posts + per-subreddit aggregates. Returns posts saved."""
    if not signals.posts:
        return 0

    save_reddit_posts(signals.posts, db_path)

    by_sub: dict[str, list[int]] = {}
    for p in signals.posts:
        by_sub.setdefault(p.subreddit or "unknown", []).append(p.score)
    for sub_name, scores in by_sub.items():
        save_social_mention(
            ticker=ticker,
            mention_date=today,
            source="reddit",
            mention_count=len(scores),
            mentions_24h_ago=None,
            upvote_sum=sum(scores),
            subreddit=sub_name,
            db_path=db_path,
        )
    return len(signals.posts)


def pull_reddit_for_tickers(
    tickers: list[str],
    today: date,
    db_path: Path,
    subreddit_map: dict[str, list[str]] | None = None,
    per_ticker: int = 25,
    scraper: RedditScraper | None = None,
) -> tuple[int, int]:
    """Pull and persist Reddit posts for each ticker in *tickers*.

    *subreddit_map* ({TICKER: [subreddit, ...]}) targets each ticker's own
    communities; tickers absent from the map fall back to the scraper defaults.
    Per-ticker failures are logged and skipped. Returns (total_posts, covered).
    """
    subreddit_map = subreddit_map or {}
    scraper = scraper or make_reddit_scraper()

    total_posts = 0
    covered = 0
    for ticker in tickers:
        subs = subreddit_map.get(ticker.upper()) or None
        try:
            signals = scraper.search_ticker(
                ticker, days_back=7, max_posts=per_ticker, subreddits=subs
            )
        except Exception as exc:
            logger.warning("Reddit fetch failed for %s (continuing): %s", ticker, exc)
            continue

        saved = save_ticker_signals(ticker, signals, today, db_path)
        if saved:
            total_posts += saved
            covered += 1

    return total_posts, covered
