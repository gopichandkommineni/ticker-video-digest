"""Reddit scraper — authenticated PRAW client (direct backend).

Reddit shut down its unauthenticated public JSON API and put it behind
Cloudflare, so the credential-less scraping path was removed. This client works
only with a Reddit "script" app's credentials (OAuth to oauth.reddit.com, which
is not IP-blocked). It is a fallback backend, selected with REDDIT_BACKEND=direct;
the default free backend is Arctic Shift (see arctic_shift_client). Without
credentials it returns no posts.
"""
import logging
from datetime import datetime, timedelta, timezone

from core.config import (
    REDDIT_CLIENT_ID,
    REDDIT_CLIENT_SECRET,
    REDDIT_PASSWORD,
    REDDIT_USERNAME,
)
from core.social_media.base import SocialPost, SocialSignals, SocialScraper

logger = logging.getLogger(__name__)

_USER_AGENT = "casino-dashboard/0.1 (+https://github.com/gopichandkommineni/ticker-video-digest)"

# Subreddits searched for every ticker query.
_DEFAULT_SUBREDDITS = [
    "wallstreetbets",
    "stocks",
    "investing",
    "options",
    "StockMarket",
]


class RedditScraper(SocialScraper):
    """Fetches Reddit posts mentioning a ticker via authenticated PRAW."""

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
        return self._praw_reddit is not None

    def search_ticker(
        self,
        ticker: str,
        days_back: int = 7,
        max_posts: int = 50,
        subreddits: list[str] | None = None,
    ) -> SocialSignals:
        """Fetch posts mentioning *ticker* via PRAW. Pass *subreddits* to override
        the default finance subs (e.g. a ticker's discovered communities).

        Returns no posts when credentials are absent — use the Arctic Shift or
        Apify backend for credential-less access.
        """
        subs = subreddits or self._subreddits
        if self._praw_reddit is None:
            logger.info("Reddit direct client has no credentials; returning no posts for %s", ticker)
            posts: list[SocialPost] = []
        else:
            posts = self._fetch_via_praw(ticker, days_back, max_posts, subs)

        logger.info("Reddit: fetched %d posts for %s", len(posts), ticker)
        return SocialSignals(
            ticker=ticker,
            platform=self.platform_name,
            posts=posts,
            fetched_at=datetime.utcnow(),
        )

    # ------------------------------------------------------------------
    # PRAW client
    # ------------------------------------------------------------------

    def _build_praw_client(self):  # type: ignore[return]
        if not (REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET):
            logger.info(
                "Reddit PRAW credentials not set; the direct client is inactive "
                "(used only with REDDIT_BACKEND=direct + a Reddit app)."
            )
            return None
        try:
            import praw  # noqa: PLC0415

            kwargs = {
                "client_id": REDDIT_CLIENT_ID,
                "client_secret": REDDIT_CLIENT_SECRET,
                "user_agent": _USER_AGENT,
                # Wait out Reddit's rate limit instead of raising on 429.
                "ratelimit_seconds": 300,
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
            logger.warning("praw not installed; Reddit direct client unavailable")
            return None

    # ------------------------------------------------------------------
    # Auth introspection
    # ------------------------------------------------------------------

    def auth_status(self) -> str:
        """Human-readable description of the current Reddit auth mode."""
        if self._praw_reddit is None:
            return "direct client inactive (no Reddit credentials)"
        if REDDIT_USERNAME and REDDIT_PASSWORD:
            return f"authenticated (user grant, u/{REDDIT_USERNAME})"
        return "authenticated (read-only app-only OAuth)"

    def verify_auth(self) -> tuple[bool, str]:
        """Make one minimal live request to confirm the credentials actually work."""
        if self._praw_reddit is None:
            return False, "no credentials configured"
        try:
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


def _deduplicate(posts: list[SocialPost]) -> list[SocialPost]:
    seen: set[str] = set()
    unique: list[SocialPost] = []
    for p in posts:
        if p.post_id not in seen:
            seen.add(p.post_id)
            unique.append(p)
    return unique
