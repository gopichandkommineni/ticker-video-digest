"""Social media signal aggregation for ticker analysis.

To add a new platform:
1. Create src/ticker_digest/social_media/<platform>/client.py with a class
   that subclasses SocialScraper and implements platform_name, is_available,
   and search_ticker.
2. Import and register it in _ALL_SCRAPERS below.
"""
import logging
from typing import TYPE_CHECKING

from ticker_digest.social_media.base import SocialPost, SocialSignals, SocialScraper
from ticker_digest.social_media.reddit.client import RedditScraper
from ticker_digest.social_media.x.client import XScraper

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Registry — add new scrapers here when a new platform is introduced
# ---------------------------------------------------------------------------
_ALL_SCRAPERS: list[SocialScraper] = [
    RedditScraper(),
    XScraper(),
]


def get_available_scrapers() -> list[SocialScraper]:
    """Return only the scrapers whose credentials are configured."""
    return [s for s in _ALL_SCRAPERS if s.is_available]


def fetch_all_signals(
    ticker: str,
    days_back: int = 7,
    max_posts_per_platform: int = 50,
) -> list[SocialSignals]:
    """Run every available scraper and return one SocialSignals per platform."""
    results: list[SocialSignals] = []
    for scraper in get_available_scrapers():
        try:
            signals = scraper.search_ticker(ticker, days_back=days_back, max_posts=max_posts_per_platform)
            results.append(signals)
        except Exception as exc:
            logger.error("Scraper %s failed for %s: %s", scraper.platform_name, ticker, exc)
    return results


__all__ = [
    "SocialPost",
    "SocialSignals",
    "SocialScraper",
    "RedditScraper",
    "XScraper",
    "get_available_scrapers",
    "fetch_all_signals",
]
