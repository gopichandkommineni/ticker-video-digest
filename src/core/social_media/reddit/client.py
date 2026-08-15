"""Reddit scraper — uses PRAW when credentials are available, otherwise falls
back to Reddit's public JSON search API (no auth required, rate-limited)."""
import logging
import time
from datetime import datetime, timedelta, timezone

import requests

from core.config import (
    REDDIT_CLIENT_ID,
    REDDIT_CLIENT_SECRET,
    REDDIT_PASSWORD,
    REDDIT_USERNAME,
)
from core.social_media.base import SocialPost, SocialSignals, SocialScraper
from core.social_media.reddit._http import (
    reddit_get,
    reddit_proxy_url,
    reddit_user_agent,
)

logger = logging.getLogger(__name__)

# Subreddits searched for every ticker query.
_DEFAULT_SUBREDDITS = [
    "wallstreetbets",
    "stocks",
    "investing",
    "options",
    "StockMarket",
]

_PUBLIC_SEARCH_URL = "https://www.reddit.com/search.json"
_SUBREDDIT_SEARCH_URL = "https://www.reddit.com/r/{sub}/search.json"


class RedditScraper(SocialScraper):
    """Fetches Reddit posts mentioning a ticker from finance-focused subreddits."""

    def __init__(self, subreddits: list[str] | None = None) -> None:
        self._subreddits = subreddits or _DEFAULT_SUBREDDITS
        self._praw_reddit = self._build_praw_client()

    # ------------------------------------------------------------------
    # SocialScraper interface
    # ------------------------------------------------------------------

    @property
    def platform_name(self) -> str:
        return "reddit"

    @property
    def is_available(self) -> bool:
        return True  # public JSON API always available; PRAW enhances it

    def search_ticker(
        self,
        ticker: str,
        days_back: int = 7,
        max_posts: int = 50,
        subreddits: list[str] | None = None,
    ) -> SocialSignals:
        """Fetch posts mentioning *ticker*. Pass *subreddits* to override the
        default finance subs for this call (e.g. a ticker's own discovered
        communities); None uses the scraper's configured defaults.
        """
        subs = subreddits or self._subreddits
        if self._praw_reddit is not None:
            posts = self._fetch_via_praw(ticker, days_back, max_posts, subs)
        else:
            posts = self._fetch_via_public_api(ticker, days_back, max_posts, subs)

        logger.info("Reddit: fetched %d posts for %s", len(posts), ticker)
        return SocialSignals(
            ticker=ticker,
            platform=self.platform_name,
            posts=posts,
            fetched_at=datetime.utcnow(),
        )

    # ------------------------------------------------------------------
    # PRAW path (preferred — supports per-subreddit restrict_sr queries)
    # ------------------------------------------------------------------

    def _build_praw_client(self):  # type: ignore[return]
        if not (REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET):
            logger.warning(
                "Reddit API credentials not set (REDDIT_CLIENT_ID / REDDIT_CLIENT_SECRET) — "
                "falling back to the public JSON API, which Reddit now 403-blocks for most "
                "IPs (expect 0 results). Create a 'script' app at reddit.com/prefs/apps and "
                "set the credentials."
            )
            return None
        try:
            import praw  # noqa: PLC0415

            requestor_kwargs = None
            proxy = reddit_proxy_url()
            if proxy:
                session = requests.Session()
                session.proxies.update({"http": proxy, "https": proxy})
                requestor_kwargs = {"session": session}

            kwargs = {
                "client_id": REDDIT_CLIENT_ID,
                "client_secret": REDDIT_CLIENT_SECRET,
                "user_agent": reddit_user_agent(),
                # Wait out Reddit's rate limit instead of raising on 429.
                "ratelimit_seconds": 300,
                "requestor_kwargs": requestor_kwargs,
            }
            if REDDIT_USERNAME and REDDIT_PASSWORD:
                # "script" app full user (password) grant.
                kwargs["username"] = REDDIT_USERNAME
                kwargs["password"] = REDDIT_PASSWORD
                logger.info("Reddit: authenticating as u/%s (password grant)", REDDIT_USERNAME)
            else:
                # Confidential-client read-only (app-only) OAuth — enough to search.
                logger.info("Reddit: authenticating read-only (app-only OAuth)")
            return praw.Reddit(**kwargs)
        except ImportError:
            logger.warning("praw not installed; falling back to public Reddit API")
            return None

    # ------------------------------------------------------------------
    # Auth introspection
    # ------------------------------------------------------------------

    def auth_status(self) -> str:
        """Human-readable description of the current Reddit auth mode."""
        if self._praw_reddit is None:
            return "unauthenticated (public JSON API — Reddit blocks this for most IPs)"
        if REDDIT_USERNAME and REDDIT_PASSWORD:
            return f"authenticated (user grant, u/{REDDIT_USERNAME})"
        return "authenticated (read-only app-only OAuth)"

    def verify_auth(self) -> tuple[bool, str]:
        """Make one minimal live request to confirm the credentials actually work.

        Returns (ok, detail). ok=False either means no credentials or the token
        was rejected — the detail says which.
        """
        if self._praw_reddit is None:
            return False, "no credentials configured"
        try:
            # A tiny read that requires a valid OAuth token.
            next(iter(self._praw_reddit.subreddit("stocks").hot(limit=1)), None)
            return True, self.auth_status()
        except Exception as exc:
            return False, f"auth check failed: {exc}"

    def _fetch_via_praw(
        self, ticker: str, days_back: int, max_posts: int,
        subreddits: list[str] | None = None,
    ) -> list[SocialPost]:
        assert self._praw_reddit is not None
        subs = subreddits or self._subreddits
        cutoff = datetime.now(tz=timezone.utc) - timedelta(days=days_back)
        query = f"${ticker} OR {ticker}"
        posts: list[SocialPost] = []

        per_sub = max(max_posts // max(len(subs), 1), 10)
        for sub_name in subs:
            try:
                subreddit = self._praw_reddit.subreddit(sub_name)
                for submission in subreddit.search(query, sort="top", time_filter="week", limit=per_sub):
                    created = datetime.fromtimestamp(submission.created_utc, tz=timezone.utc)
                    if created < cutoff:
                        continue
                    posts.append(
                        SocialPost(
                            platform=self.platform_name,
                            post_id=submission.id,
                            author=str(submission.author) if submission.author else "[deleted]",
                            title=submission.title,
                            content=submission.selftext[:2000] if submission.selftext else "",
                            url=f"https://reddit.com{submission.permalink}",
                            published_at=created,
                            score=submission.score,
                            comment_count=submission.num_comments,
                            ticker=ticker,
                            subreddit=sub_name,
                        )
                    )
            except Exception as exc:
                logger.warning("PRAW fetch failed for r/%s: %s", sub_name, exc)

        return _deduplicate(posts)[:max_posts]

    # ------------------------------------------------------------------
    # Public JSON API fallback (no credentials needed)
    # ------------------------------------------------------------------

    def _fetch_via_public_api(
        self, ticker: str, days_back: int, max_posts: int,
        subreddits: list[str] | None = None,
    ) -> list[SocialPost]:
        subs = subreddits or self._subreddits
        cutoff = datetime.now(tz=timezone.utc) - timedelta(days=days_back)
        posts: list[SocialPost] = []

        for sub_name in subs:
            try:
                params = {
                    "q": f"${ticker}",
                    "sort": "top",
                    "t": "week",
                    "limit": min(max_posts, 25),
                    "restrict_sr": "1",
                }
                resp = reddit_get(
                    _SUBREDDIT_SEARCH_URL.format(sub=sub_name),
                    params=params,
                    timeout=10,
                )
                resp.raise_for_status()
                data = resp.json()
                for child in data.get("data", {}).get("children", []):
                    d = child.get("data", {})
                    created = datetime.fromtimestamp(
                        d.get("created_utc", 0), tz=timezone.utc
                    )
                    if created < cutoff:
                        continue
                    posts.append(
                        SocialPost(
                            platform=self.platform_name,
                            post_id=d.get("id", ""),
                            author=d.get("author", "[deleted]"),
                            title=d.get("title", ""),
                            content=(d.get("selftext") or "")[:2000],
                            url=f"https://reddit.com{d.get('permalink', '')}",
                            published_at=created,
                            score=d.get("score", 0),
                            comment_count=d.get("num_comments", 0),
                            ticker=ticker,
                            subreddit=sub_name,
                        )
                    )
                # be polite to the public API
                time.sleep(0.5)
            except Exception as exc:
                logger.warning("Public Reddit fetch failed for r/%s: %s", sub_name, exc)

        return _deduplicate(posts)[:max_posts]


def _deduplicate(posts: list[SocialPost]) -> list[SocialPost]:
    seen: set[str] = set()
    unique: list[SocialPost] = []
    for p in posts:
        if p.post_id not in seen:
            seen.add(p.post_id)
            unique.append(p)
    return unique
