"""Adapter for api.getxapi.com."""

from __future__ import annotations

import datetime
import logging
import urllib.parse
from typing import Any

from .base import (
    TweetSource, Tweet, FetchResult, UserInfo,
    snowflake_to_utc, compute_type, serialize_raw_json,
)
from ._http import get_json, extract_media_urls

logger = logging.getLogger(__name__)

_BASE = "https://api.getxapi.com"
_MAX_PAGES = 1000  # anti-infinite-loop guard; normal stop is the start-date floor

# Maximum seconds this fetch call may spend sleeping on 429 retries across all pages.
# Prevents a single throttled handle from consuming the whole Actions job timeout.
_MAX_RETRY_BUDGET_SECONDS = 300


class GetXApiSource(TweetSource):
    def __init__(self, api_key: str) -> None:
        self._headers = {"Authorization": f"Bearer {api_key}"}

    # ------------------------------------------------------------------
    # UserInfo
    # ------------------------------------------------------------------

    def fetch_user_info(self, handle: str) -> UserInfo:
        url = f"{_BASE}/twitter/user/info?userName={urllib.parse.quote(handle)}"
        data = get_json(url, self._headers)
        u = data["data"]
        # createdAt on user objects is a real ISO timestamp — parse directly.
        created = u.get("createdAt")
        if created and created.endswith(".000000Z"):
            created = created.replace(".000000Z", "Z")
        return UserInfo(
            handle=u.get("userName", handle),
            display_name=u.get("name"),
            user_id=u["id"],
            created_at_utc=created,
            followers_count=u.get("followers"),
            following_count=u.get("following"),
            bio=u.get("description"),
            is_verified=bool(u.get("isVerified", False)),
            is_blue_verified=bool(u.get("isBlueVerified", False)),
        )

    # ------------------------------------------------------------------
    # Tweets
    # ------------------------------------------------------------------

    def fetch_tweets(
        self,
        handle: str,
        start: datetime.date,
        end: datetime.date,
    ) -> FetchResult:
        """
        Fetch [start, end] inclusive.
        getxapi until: is EXCLUSIVE → pass end + 1 day.
        Stop on empty page or when the oldest tweet in the page predates start.
        reached_floor=True when stop was natural; False when _MAX_PAGES fired.
        """
        until_date = end + datetime.timedelta(days=1)
        base_q = (
            f"from:{handle} -filter:retweets"
            f" since:{start.isoformat()}"
            f" until:{until_date.isoformat()}"
        )
        start_dt = datetime.datetime.combine(start, datetime.time.min)

        tweets: list[Tweet] = []
        cursor: str | None = None
        pages = 0
        reached_floor = False
        skipped = 0
        # Shared 429-retry budget across all pages; prevents one throttled handle
        # from sleeping the entire Actions job into timeout.
        retry_budget: dict[str, float] = {"remaining": float(_MAX_RETRY_BUDGET_SECONDS)}

        while pages < _MAX_PAGES:
            params: dict[str, str] = {"q": base_q, "count": "20"}
            if cursor:
                params["cursor"] = cursor

            url = f"{_BASE}/twitter/tweet/advanced_search?{urllib.parse.urlencode(params)}"
            logger.info("getxapi request %d: %s", pages + 1, url)
            # PR A: errors (429 / 5xx / network / auth) propagate to the caller
            # (the worker), which decides retry-with-backoff vs. permanent fail.
            # Option A: partial pages collected before the error are discarded;
            # the worker re-runs the (handle, date) window and INSERT OR IGNORE
            # dedupes on retry. We no longer swallow to reached_floor=False.
            data = get_json(url, self._headers, retry_budget=retry_budget)
            pages += 1

            batch = data.get("tweets") or []
            if not batch:
                logger.debug("getxapi: empty batch on page %d — stopping", pages)
                reached_floor = True
                break

            hit_start = False
            for raw in batch:
                try:
                    tweet = _normalize(raw)
                except Exception as exc:
                    skipped += 1
                    logger.error(
                        "getxapi: skipping malformed tweet id=%s (%s)",
                        raw.get("id", "<unknown>"), exc,
                    )
                    continue
                tweet_dt = datetime.datetime.strptime(tweet.created_at_utc, "%Y-%m-%dT%H:%M:%SZ")
                if tweet_dt < start_dt:
                    hit_start = True
                    break
                tweets.append(tweet)

            if hit_start:
                logger.debug("getxapi: reached start boundary on page %d", pages)
                reached_floor = True
                break

            cursor = data.get("next_cursor")
            if not cursor:
                reached_floor = True
                break

        if not reached_floor:
            logger.warning(
                "getxapi: hit page cap (%d) before reaching floor %s for %s — backfill incomplete",
                _MAX_PAGES, start, handle,
            )

        logger.info(
            "getxapi fetch_tweets(%s, %s→%s): normalized %d, skipped %d malformed, in %d request(s) reached_floor=%s",
            handle, start, end, len(tweets), skipped, pages, reached_floor,
        )
        return FetchResult(tweets=tweets, reached_floor=reached_floor, skipped=skipped)


def _normalize(raw: dict[str, Any]) -> Tweet:
    tweet_id = raw["id"]
    tweet_type, is_reply, is_quote = compute_type(raw)
    quoted = raw.get("quoted_tweet")
    media_urls = extract_media_urls(raw, "getxapi")
    return Tweet(
        id=tweet_id,
        created_at_utc=snowflake_to_utc(tweet_id),
        text=raw.get("text"),
        type=tweet_type,
        is_reply=is_reply,
        is_quote=is_quote,
        in_reply_to_id=raw.get("inReplyToId"),
        quoted_tweet_id=quoted.get("id") if quoted else None,
        quoted_author_id=quoted["author"].get("id") if quoted and quoted.get("author") else None,
        conversation_id=raw.get("conversationId"),
        like_count=raw.get("likeCount"),
        retweet_count=raw.get("retweetCount"),
        reply_count=raw.get("replyCount"),
        quote_count=raw.get("quoteCount"),
        view_count=raw.get("viewCount"),
        bookmark_count=raw.get("bookmarkCount"),
        has_media=bool(media_urls),
        media_urls=media_urls,
        url=raw.get("url"),
        is_deleted=False,
        raw_json=raw,
        raw_provider_json=serialize_raw_json(tweet_id, raw),
    )
