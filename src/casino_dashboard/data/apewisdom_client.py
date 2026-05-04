"""ApeWisdom public API client — no auth required."""
import logging
import time
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
import json

from casino_dashboard.data.models import ApeWisdomMention

logger = logging.getLogger(__name__)

_BASE_URL = "https://apewisdom.io/api/v1.0/filter/{filter}/page/{page}"
_USER_AGENT = "casino-dashboard/0.1 (https://github.com/gopichandkommineni/ticker-video-digest)"
_PAGE_DELAY = 1.0
_RATE_LIMIT_BACKOFF = 30.0


def _fetch_page(filter: str, page: int) -> list[dict]:
    """Fetch one page from ApeWisdom. Returns list of result dicts, or [] on empty/error."""
    url = _BASE_URL.format(filter=filter, page=page)
    req = Request(url, headers={"User-Agent": _USER_AGENT})
    try:
        with urlopen(req, timeout=15) as resp:
            raw = resp.read()
    except HTTPError as exc:
        if exc.code == 429:
            logger.warning("ApeWisdom 429 on page %d — backing off %ds", page, _RATE_LIMIT_BACKOFF)
            time.sleep(_RATE_LIMIT_BACKOFF)
            # Retry once
            try:
                with urlopen(req, timeout=15) as resp:
                    raw = resp.read()
            except HTTPError as exc2:
                logger.error("ApeWisdom 429 on retry for page %d: %s", page, exc2)
                raise
        else:
            logger.error("ApeWisdom HTTP %d on page %d", exc.code, page)
            raise
    except URLError as exc:
        logger.error("ApeWisdom network error on page %d: %s", page, exc)
        raise

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.warning("ApeWisdom malformed JSON on page %d: %s — skipping", page, exc)
        return []

    results = data.get("results", [])
    if not isinstance(results, list):
        return []
    return results


def fetch_apewisdom_universe(filter: str = "all-stocks") -> list[ApeWisdomMention]:
    """Fetch all pages of ApeWisdom for the given filter.

    Walks pagination until an empty results page is returned.
    Polite: 1-second delay between pages.
    Returns list of ApeWisdomMention dataclasses.
    """
    mentions: list[ApeWisdomMention] = []
    page = 1
    while True:
        if page > 1:
            time.sleep(_PAGE_DELAY)
        results = _fetch_page(filter, page)
        if not results:
            break
        for item in results:
            ticker = item.get("ticker")
            if not ticker or not isinstance(ticker, str):
                continue
            mentions.append(
                ApeWisdomMention(
                    ticker=ticker.upper(),
                    mentions=int(item.get("mentions", 0) or 0),
                    mentions_24h_ago=_safe_int(item.get("mentions_24h_ago")),
                    upvotes=_safe_int(item.get("upvotes")),
                )
            )
        page += 1
    return mentions


def filter_to_universe(
    all_mentions: list[ApeWisdomMention],
    universe_tickers: set[str],
) -> list[ApeWisdomMention]:
    """Return only mentions whose ticker is in our universe (case-insensitive match)."""
    upper_universe = {t.upper() for t in universe_tickers}
    return [m for m in all_mentions if m.ticker.upper() in upper_universe]


def _safe_int(val: object) -> int | None:
    if val is None:
        return None
    try:
        return int(val)
    except (TypeError, ValueError):
        return None
