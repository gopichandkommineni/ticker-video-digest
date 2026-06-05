"""Adapter for api.twitterapi.io."""

from __future__ import annotations

import datetime
import logging
import urllib.parse
from typing import Any

from .base import TweetSource, Tweet, UserInfo, snowflake_to_utc, compute_type
from ._http import get_json, extract_media_urls

logger = logging.getLogger(__name__)

_BASE = "https://api.twitterapi.io"
_MAX_PAGES = 100


class TwitterApiIoSource(TweetSource):
    def __init__(self, api_key: str) -> None:
        self._headers = {"X-API-Key": api_key}

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
    ) -> list[Tweet]:
        """
        Fetch [start, end] inclusive.
        twitterapi.io until: is EXCLUSIVE → pass end + 1 day.
        Stop on empty page or when the oldest tweet in the page predates start.
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

        while pages < _MAX_PAGES:
            params: dict[str, str] = {
                "query": base_q,
                "queryType": "Latest",
                "count": "20",
            }
            if cursor:
                params["cursor"] = cursor

            url = f"{_BASE}/twitter/tweet/advanced_search?{urllib.parse.urlencode(params)}"
            logger.info("twitterapi.io request %d: %s", pages + 1, url)
            data = get_json(url, self._headers)
            pages += 1

            batch = data.get("tweets") or []
            if not batch:
                logger.debug("twitterapi.io: empty batch on page %d — stopping", pages)
                break

            reached_start = False
            for raw in batch:
                tweet = _normalize(raw)
                tweet_dt = datetime.datetime.strptime(tweet.created_at_utc, "%Y-%m-%dT%H:%M:%SZ")
                if tweet_dt < start_dt:
                    reached_start = True
                    break
                tweets.append(tweet)

            if reached_start:
                logger.debug("twitterapi.io: reached start boundary on page %d", pages)
                break

            cursor = data.get("next_cursor")
            if not cursor:
                break

        logger.info(
            "twitterapi.io fetch_tweets(%s, %s→%s): %d tweets in %d request(s)",
            handle, start, end, len(tweets), pages,
        )
        return tweets


def _normalize(raw: dict[str, Any]) -> Tweet:
    tweet_id = raw["id"]
    tweet_type, is_reply, is_quote = compute_type(raw)
    quoted = raw.get("quoted_tweet")
    media_urls = extract_media_urls(raw, "twitterapi")
    return Tweet(
        id=tweet_id,
        created_at_utc=snowflake_to_utc(tweet_id),
        text=raw.get("text"),
        type=tweet_type,
        is_reply=is_reply,
        is_quote=is_quote,
        in_reply_to_id=raw.get("inReplyToId"),
        quoted_tweet_id=quoted["id"] if quoted else None,
        quoted_author_id=quoted["author"]["id"] if quoted and quoted.get("author") else None,
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
    )
