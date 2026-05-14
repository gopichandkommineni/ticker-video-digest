"""X (Twitter) scraper — uses the Twitter API v2 recent-search endpoint.

Requires X_BEARER_TOKEN in the environment.  When the token is absent the
scraper returns an empty SocialSignals and logs a warning rather than
raising, so the rest of the pipeline degrades gracefully.
"""
import logging
from datetime import datetime, timedelta, timezone

import requests

from ticker_digest.config import X_BEARER_TOKEN
from ticker_digest.social_media.base import SocialPost, SocialSignals, SocialScraper

logger = logging.getLogger(__name__)

_SEARCH_URL = "https://api.twitter.com/2/tweets/search/recent"
_MAX_RESULTS_PER_PAGE = 100  # API cap for recent-search
_USER_LOOKUP_URL = "https://api.twitter.com/2/users"


class XScraper(SocialScraper):
    """Fetches recent X (Twitter) posts mentioning a ticker via API v2."""

    # ------------------------------------------------------------------
    # SocialScraper interface
    # ------------------------------------------------------------------

    @property
    def platform_name(self) -> str:
        return "x"

    @property
    def is_available(self) -> bool:
        return bool(X_BEARER_TOKEN)

    def search_ticker(
        self,
        ticker: str,
        days_back: int = 7,
        max_posts: int = 100,
    ) -> SocialSignals:
        if not self.is_available:
            logger.warning(
                "X_BEARER_TOKEN not set — skipping X scrape for %s", ticker
            )
            return SocialSignals(
                ticker=ticker,
                platform=self.platform_name,
                fetched_at=datetime.utcnow(),
            )

        posts = self._fetch(ticker, days_back, max_posts)
        logger.info("X: fetched %d posts for %s", len(posts), ticker)
        return SocialSignals(
            ticker=ticker,
            platform=self.platform_name,
            posts=posts,
            fetched_at=datetime.utcnow(),
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _fetch(self, ticker: str, days_back: int, max_posts: int) -> list[SocialPost]:
        start_time = (
            datetime.now(tz=timezone.utc) - timedelta(days=days_back)
        ).strftime("%Y-%m-%dT%H:%M:%SZ")

        # Cashtag search; exclude retweets and replies for cleaner signal.
        query = f"${ticker} -is:retweet -is:reply lang:en"

        posts: list[SocialPost] = []
        next_token: str | None = None
        headers = {"Authorization": f"Bearer {X_BEARER_TOKEN}"}

        while len(posts) < max_posts:
            page_size = min(_MAX_RESULTS_PER_PAGE, max_posts - len(posts))
            params: dict = {
                "query": query,
                "max_results": max(10, page_size),  # API minimum is 10
                "start_time": start_time,
                "tweet.fields": "created_at,author_id,public_metrics,text",
                "expansions": "author_id",
                "user.fields": "username",
            }
            if next_token:
                params["next_token"] = next_token

            try:
                resp = requests.get(_SEARCH_URL, params=params, headers=headers, timeout=15)
                resp.raise_for_status()
            except requests.HTTPError as exc:
                logger.error("X API error for %s: %s", ticker, exc)
                break
            except requests.RequestException as exc:
                logger.error("X network error for %s: %s", ticker, exc)
                break

            payload = resp.json()
            tweets = payload.get("data", [])
            users = {
                u["id"]: u.get("username", "unknown")
                for u in payload.get("includes", {}).get("users", [])
            }

            for tweet in tweets:
                metrics = tweet.get("public_metrics", {})
                raw_time = tweet.get("created_at", "")
                try:
                    published_at = datetime.fromisoformat(raw_time.replace("Z", "+00:00"))
                except ValueError:
                    published_at = datetime.utcnow().replace(tzinfo=timezone.utc)

                author_id = tweet.get("author_id", "")
                posts.append(
                    SocialPost(
                        platform=self.platform_name,
                        post_id=tweet["id"],
                        author=users.get(author_id, author_id),
                        title=None,
                        content=tweet.get("text", ""),
                        url=f"https://x.com/i/web/status/{tweet['id']}",
                        published_at=published_at,
                        score=metrics.get("like_count", 0),
                        comment_count=metrics.get("reply_count", 0),
                        ticker=ticker,
                    )
                )

            meta = payload.get("meta", {})
            next_token = meta.get("next_token")
            if not next_token or not tweets:
                break

        return posts
