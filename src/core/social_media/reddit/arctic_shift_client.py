"""Arctic Shift client — free, unauthenticated Reddit archive API.

Arctic Shift (https://arctic-shift.photon-reddit.com) is the community Pushshift
successor. It is NOT reddit.com, so it is not subject to Reddit's Cloudflare/IP
block — a plain HTTPS request works, from a laptop or from CI. Tradeoffs: ~1–2
day data-freshness lag (fresh posts start with score/comments 0, filled in within
~36h) and no uptime guarantee (community service).

Endpoints used:
- GET /api/posts/search      — posts by subreddit + query (title+selftext), after/before, limit
- GET /api/subreddits/search — subreddit metadata (incl. subscriber counts)

Response shape is `{"data": [ ...items... ]}` (we also tolerate a bare list).
Field access is defensive because archive schemas drift.
"""
import logging
import time
from datetime import datetime, timedelta, timezone

import requests

from core.social_media.base import SocialPost, SocialSignals, SocialScraper

logger = logging.getLogger(__name__)

_BASE = "https://arctic-shift.photon-reddit.com"
_POSTS_URL = _BASE + "/api/posts/search"
_SUBS_URL = _BASE + "/api/subreddits/search"
_USER_AGENT = "casino-dashboard/0.1 (+https://github.com/gopichandkommineni/ticker-video-digest)"

# Subreddits searched per ticker when no per-ticker map is supplied.
_DEFAULT_SUBREDDITS = ["wallstreetbets", "stocks", "investing", "options", "StockMarket"]

_RATE_LIMIT_BACKOFF = 5.0


def _first(item: dict, *keys, default=None):
    for k in keys:
        if item.get(k) is not None:
            return item[k]
    return default


def _get(url: str, params: dict, timeout: int = 20) -> list[dict]:
    """GET an Arctic Shift endpoint, returning the list of result items ([] on error).

    Retries once on HTTP 429 after the reset delay.
    """
    for attempt in (1, 2):
        try:
            resp = requests.get(
                url, params=params, headers={"User-Agent": _USER_AGENT}, timeout=timeout
            )
        except Exception as exc:  # network / proxy / any transport error
            logger.warning("Arctic Shift request error (%s): %s", url, exc)
            return []
        if resp.status_code == 429 and attempt == 1:
            wait = float(resp.headers.get("X-RateLimit-Reset", _RATE_LIMIT_BACKOFF) or _RATE_LIMIT_BACKOFF)
            logger.warning("Arctic Shift 429 — backing off %.0fs", wait)
            time.sleep(min(wait, 30.0))
            continue
        if resp.status_code != 200:
            logger.warning("Arctic Shift HTTP %d for %s", resp.status_code, url)
            return []
        try:
            payload = resp.json()
        except ValueError:
            return []
        if isinstance(payload, dict):
            data = payload.get("data", [])
        else:
            data = payload
        return data if isinstance(data, list) else []
    return []


def search_posts(
    subreddit: str | None = None,
    query: str | None = None,
    after: datetime | None = None,
    before: datetime | None = None,
    limit: int = 100,
    sort: str = "desc",
) -> list[dict]:
    """Raw Arctic Shift post search. Returns the list of post dicts."""
    params: dict = {"limit": min(max(limit, 1), 100), "sort": sort}
    if subreddit:
        params["subreddit"] = subreddit
    if query:
        params["query"] = query
    if after:
        params["after"] = int(after.timestamp())
    if before:
        params["before"] = int(before.timestamp())
    return _get(_POSTS_URL, params)


def search_subreddits(
    query: str | None = None,
    subreddit: str | None = None,
    limit: int = 20,
    min_subscribers: int | None = None,
    max_subscribers: int | None = None,
    sort: str | None = None,
    sort_type: str | None = None,
) -> list[dict]:
    """Raw Arctic Shift subreddit search. Returns the list of subreddit dicts.

    Note: /api/subreddits/search has NO 'query' param — a name lookup uses
    'subreddit' (exact) and a fuzzy lookup uses 'subreddit_prefix'. Sending
    'query' returns HTTP 400. So the *query* argument maps to subreddit_prefix.

    With neither name nor prefix, the endpoint enumerates subreddits by
    subscriber count (its default sort). Pass min/max_subscribers to bound the
    range and sort/sort_type to control ordering (defaults: sort=desc,
    sort_type=subscribers). limit may be up to 1000.
    """
    params: dict = {"limit": limit}
    if subreddit:
        params["subreddit"] = subreddit
    if query:
        params["subreddit_prefix"] = query
    if min_subscribers is not None:
        params["min_subscribers"] = min_subscribers
    if max_subscribers is not None:
        params["max_subscribers"] = max_subscribers
    if sort is not None:
        params["sort"] = sort
    if sort_type is not None:
        params["sort_type"] = sort_type
    return _get(_SUBS_URL, params)


def iter_subreddits_by_subscribers(
    min_subscribers: int = 1000,
    max_count: int = 50_000,
    page_size: int = 1000,
    sleep: float = 0.5,
):
    """Yield subreddit dicts sorted by subscriber count DESCENDING — from the
    largest down to *min_subscribers*, up to *max_count* subreddits.

    Pages via a descending max_subscribers cursor: each page requests
    subscribers <= the smallest count seen so far. Ties across a page boundary
    are handled by de-duping on name; if a page yields nothing new we stop
    (guards against an infinite loop on a large tie block).
    """
    page_size = min(max(page_size, 1), 1000)
    yielded = 0
    cursor: int | None = None
    seen: set[str] = set()

    while yielded < max_count:
        # Always request a full page: the first item of each page after the
        # first is the boundary-value duplicate, so a page shrunk to the leftover
        # budget could return only that dupe and stall. max_count is enforced by
        # the yield guard below instead.
        items = search_subreddits(
            limit=page_size,
            min_subscribers=min_subscribers,
            max_subscribers=cursor,
            sort="desc",
            sort_type="subscribers",
        )
        if not items:
            break

        page_min: int | None = None
        made_progress = False
        for it in items:
            name = _first(it, "display_name", "name")
            if name is None:
                continue
            key = str(name).lower()
            subs = int(_first(it, "subscribers", "subscriber_count", default=0) or 0)
            page_min = subs if page_min is None else min(page_min, subs)
            if key in seen:
                continue
            seen.add(key)
            made_progress = True
            yield it
            yielded += 1
            if yielded >= max_count:
                return

        if not made_progress or page_min is None:
            break
        cursor = page_min  # next page: subscribers <= this (inclusive; dedup handles ties)
        if sleep:
            time.sleep(sleep)


def count_posts_in_window(subreddit: str, days: int = 7) -> int:
    """Count a subreddit's posts in the last *days* days (lower bound, capped at 100)."""
    after = datetime.now(tz=timezone.utc) - timedelta(days=days)
    return len(search_posts(subreddit=subreddit, after=after, limit=100))


def _to_post(item: dict, ticker: str) -> SocialPost | None:
    post_id = _first(item, "id", "name")
    created = _first(item, "created_utc", "created")
    if post_id is None or created is None:
        return None
    try:
        published = datetime.fromtimestamp(float(created), tz=timezone.utc)
    except (ValueError, OSError, TypeError):
        return None
    permalink = _first(item, "permalink", default="")
    url = f"https://reddit.com{permalink}" if permalink else f"https://reddit.com/comments/{post_id}"
    return SocialPost(
        platform="reddit",
        post_id=str(post_id),
        author=str(_first(item, "author", default="[unknown]")),
        title=_first(item, "title", default="") or "",
        content=(_first(item, "selftext", "body", default="") or "")[:2000],
        url=url,
        published_at=published,
        score=int(_first(item, "score", "ups", default=0) or 0),
        comment_count=int(_first(item, "num_comments", "numComments", default=0) or 0),
        ticker=ticker,
        subreddit=str(_first(item, "subreddit", default="") or ""),
    )


def _deduplicate(posts: list[SocialPost]) -> list[SocialPost]:
    seen: set[str] = set()
    out: list[SocialPost] = []
    for p in posts:
        if p.post_id not in seen:
            seen.add(p.post_id)
            out.append(p)
    return out


class ArcticShiftScraper(SocialScraper):
    """Fetches Reddit posts for a ticker from the free Arctic Shift archive."""

    def __init__(self, subreddits: list[str] | None = None) -> None:
        self._subreddits = subreddits or _DEFAULT_SUBREDDITS

    @property
    def platform_name(self) -> str:
        return "reddit"

    @property
    def is_available(self) -> bool:
        return True  # free + unauthenticated

    def auth_status(self) -> str:
        return "Arctic Shift (free archive API, ~1–2 day lag)"

    def verify_auth(self) -> tuple[bool, str]:
        """Confirm the archive is reachable with a tiny query."""
        try:
            resp = requests.get(
                _SUBS_URL, params={"subreddit": "stocks", "limit": 1},
                headers={"User-Agent": _USER_AGENT}, timeout=15,
            )
            if resp.status_code == 200:
                return True, self.auth_status()
            return False, f"Arctic Shift HTTP {resp.status_code}"
        except requests.RequestException as exc:
            return False, f"Arctic Shift unreachable: {exc}"

    def search_ticker(
        self,
        ticker: str,
        days_back: int = 7,
        max_posts: int = 50,
        subreddits: list[str] | None = None,
    ) -> SocialSignals:
        subs = subreddits or self._subreddits
        after = datetime.now(tz=timezone.utc) - timedelta(days=days_back)
        per_sub = max(max_posts // max(len(subs), 1), 10)
        posts: list[SocialPost] = []
        for sub in subs:
            items = search_posts(subreddit=sub, query=ticker, after=after, limit=per_sub)
            for item in items:
                post = _to_post(item, ticker)
                if post is not None:
                    posts.append(post)
        logger.info("Arctic Shift: fetched %d posts for %s", len(posts), ticker)
        return SocialSignals(
            ticker=ticker, platform=self.platform_name,
            posts=_deduplicate(posts)[:max_posts], fetched_at=datetime.utcnow(),
        )
