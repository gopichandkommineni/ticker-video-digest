"""Apify-backed Reddit scraper.

Reddit shut down its public JSON API and put remaining access behind Cloudflare,
so direct fetches (even browser-impersonated, even via residential proxy) are
unreliable. Apify runs managed scrapers that solve the Cloudflare challenge and
return structured results; we call its API and map the output onto our
SocialPost model.

Enabled when APIFY_TOKEN is set. The actor is configurable (APIFY_REDDIT_ACTOR);
because actor input/output schemas vary, the input is built from a permissive
default (overridable via APIFY_REDDIT_INPUT as JSON with a {query} placeholder)
and the output mapping tries several common field names.
"""
import json
import logging
import os
from datetime import datetime, timedelta, timezone

import requests

from core.config import APIFY_REDDIT_ACTOR, APIFY_TOKEN
from core.social_media.base import SocialPost, SocialSignals, SocialScraper

logger = logging.getLogger(__name__)

_RUN_URL = "https://api.apify.com/v2/acts/{actor}/run-sync-get-dataset-items"
_ME_URL = "https://api.apify.com/v2/users/me"
_DEFAULT_SUBREDDITS = ["wallstreetbets", "stocks", "investing", "options", "StockMarket"]


def _first(item: dict, *keys, default=None):
    """Return the first present, non-null value among *keys*."""
    for k in keys:
        if item.get(k) is not None:
            return item[k]
    return default


def _to_datetime(value) -> datetime | None:
    """Parse an epoch number or ISO-8601 string into an aware UTC datetime."""
    if value is None:
        return None
    try:
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value, tz=timezone.utc)
        s = str(value).strip().replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except (ValueError, OSError, OverflowError):
        return None


class ApifyRedditScraper(SocialScraper):
    """Fetches Reddit posts for a ticker via an Apify actor."""

    def __init__(self, subreddits: list[str] | None = None) -> None:
        self._subreddits = subreddits or _DEFAULT_SUBREDDITS
        self._token = APIFY_TOKEN
        self._actor = APIFY_REDDIT_ACTOR

    @property
    def platform_name(self) -> str:
        return "reddit"

    @property
    def is_available(self) -> bool:
        return bool(self._token)

    def auth_status(self) -> str:
        if not self._token:
            return "Apify not configured (APIFY_TOKEN unset)"
        return f"Apify managed scraper (actor: {self._actor})"

    def verify_auth(self) -> tuple[bool, str]:
        """Cheaply confirm the Apify token is valid (no actor run, no cost)."""
        if not self._token:
            return False, "APIFY_TOKEN not set"
        try:
            resp = requests.get(_ME_URL, params={"token": self._token}, timeout=15)
            if resp.status_code == 200:
                return True, self.auth_status()
            return False, f"Apify token rejected (HTTP {resp.status_code})"
        except requests.RequestException as exc:
            return False, f"Apify check failed: {exc}"

    # ------------------------------------------------------------------

    def _build_input(self, ticker: str, subreddits: list[str], max_posts: int) -> dict:
        template = os.environ.get("APIFY_REDDIT_INPUT", "").strip()
        if template:
            return json.loads(template.replace("{query}", ticker))
        # Permissive default that the common Reddit actors accept.
        return {
            "searches": [ticker],
            "type": "posts",
            "sort": "new",
            "time": "week",
            "maxItems": max_posts,
            "maxPostCount": max_posts,
            "maxComments": 0,
            "proxy": {"useApifyProxy": True},
        }

    def search_ticker(
        self,
        ticker: str,
        days_back: int = 7,
        max_posts: int = 50,
        subreddits: list[str] | None = None,
    ) -> SocialSignals:
        subs = subreddits or self._subreddits
        posts: list[SocialPost] = []
        if not self._token:
            logger.warning("Apify token not set; returning no posts for %s", ticker)
            return SocialSignals(ticker=ticker, platform=self.platform_name, posts=posts)

        payload = self._build_input(ticker, subs, max_posts)
        try:
            resp = requests.post(
                _RUN_URL.format(actor=self._actor),
                params={"token": self._token},
                json=payload,
                timeout=180,  # actor runs can take a while
            )
            resp.raise_for_status()
            items = resp.json()
        except Exception as exc:
            logger.warning("Apify run failed for %s: %s", ticker, exc)
            return SocialSignals(ticker=ticker, platform=self.platform_name, posts=posts)

        if not isinstance(items, list):
            logger.warning("Apify returned unexpected payload for %s", ticker)
            return SocialSignals(ticker=ticker, platform=self.platform_name, posts=posts)

        cutoff = datetime.now(tz=timezone.utc) - timedelta(days=days_back)
        for item in items:
            if not isinstance(item, dict):
                continue
            # Skip non-post rows (comments/communities) when the actor tags them.
            dtype = str(_first(item, "dataType", "type", default="")).lower()
            if dtype and "comment" in dtype:
                continue

            created = _to_datetime(_first(item, "createdAt", "created_utc", "created", "createdAtISO"))
            if created is not None and created < cutoff:
                continue

            post_id = _first(item, "id", "postId", "post_id")
            if not post_id:
                continue

            posts.append(
                SocialPost(
                    platform=self.platform_name,
                    post_id=str(post_id),
                    author=str(_first(item, "username", "author", default="[unknown]")),
                    title=_first(item, "title", default="") or "",
                    content=(_first(item, "body", "text", "selftext", "content", default="") or "")[:2000],
                    url=_first(item, "url", "link", "permalink", default="") or "",
                    published_at=created or datetime.now(tz=timezone.utc),
                    score=int(_first(item, "upVotes", "score", "ups", "upvotes", default=0) or 0),
                    comment_count=int(_first(item, "numberOfComments", "numComments", "num_comments", "comments", default=0) or 0),
                    ticker=ticker,
                    subreddit=_first(item, "parsedCommunityName", "communityName", "subreddit", default="") or "",
                )
            )

        logger.info("Apify: fetched %d posts for %s", len(posts), ticker)
        return SocialSignals(
            ticker=ticker, platform=self.platform_name,
            posts=posts[:max_posts], fetched_at=datetime.utcnow(),
        )
