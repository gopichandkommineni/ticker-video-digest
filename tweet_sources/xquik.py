"""Adapter for the Xquik X API."""

from __future__ import annotations

import datetime
import logging
import re
import urllib.parse
from typing import Any

from ._http import get_json
from .base import (
    FetchResult,
    Tweet,
    TweetSource,
    UserInfo,
    compute_type,
    serialize_raw_json,
    snowflake_to_utc,
)

logger = logging.getLogger(__name__)

_BASE = "https://xquik.com"
_MAX_PAGES = 1000
_MAX_RETRY_BUDGET_SECONDS = 300
_UTC = datetime.timezone.utc
_HANDLE_PATTERN = re.compile(r"[A-Za-z0-9_]{1,15}")


class XquikSource(TweetSource):
    """Read normalized profiles and tweet-search pages from Xquik."""

    def __init__(self, api_key: str) -> None:
        self._headers = {"X-API-Key": api_key}

    def fetch_user_info(self, handle: str) -> UserInfo:
        normalized_handle = _normalize_handle(handle)
        encoded_handle = urllib.parse.quote(normalized_handle, safe="")
        data = get_json(
            f"{_BASE}/api/v1/x/users/{encoded_handle}",
            self._headers,
            transient_statuses=(424,),
        )
        return UserInfo(
            handle=data.get("username") or normalized_handle,
            display_name=data.get("name"),
            user_id=data["id"],
            created_at_utc=_optional_created_at(data.get("createdAt")),
            followers_count=data.get("followers"),
            following_count=data.get("following"),
            bio=data.get("description"),
            is_verified=bool(data.get("verified") or data.get("isVerified")),
            is_blue_verified=bool(data.get("isBlueVerified", False)),
        )

    def fetch_tweets(
        self,
        handle: str,
        start: datetime.date,
        end: datetime.date,
    ) -> FetchResult:
        normalized_handle = _normalize_handle(handle)
        until_date = end + datetime.timedelta(days=1)
        query = (
            f"from:{normalized_handle} -filter:retweets"
            f" since:{start.isoformat()}"
            f" until:{until_date.isoformat()}"
        )
        start_dt = datetime.datetime.combine(start, datetime.time.min)

        tweets: list[Tweet] = []
        cursor: str | None = None
        pages = 0
        reached_floor = False
        skipped = 0
        retry_budget: dict[str, float] = {"remaining": float(_MAX_RETRY_BUDGET_SECONDS)}

        while pages < _MAX_PAGES:
            data = _search(
                query,
                self._headers,
                cursor=cursor,
                retry_budget=retry_budget,
            )
            pages += 1

            hit_start = False
            for raw in data.get("tweets") or []:
                try:
                    tweet = _normalize(raw)
                except Exception as exc:
                    skipped += 1
                    logger.error(
                        "xquik: skipping malformed tweet id=%s (%s)",
                        raw.get("id", "<unknown>"),
                        exc,
                    )
                    continue
                tweet_dt = datetime.datetime.strptime(
                    tweet.created_at_utc,
                    "%Y-%m-%dT%H:%M:%SZ",
                )
                if tweet_dt < start_dt:
                    hit_start = True
                    break
                tweets.append(tweet)

            if hit_start:
                logger.debug("xquik: reached start boundary on page %d", pages)
                reached_floor = True
                break

            next_cursor = _next_cursor(data)
            if not data.get("has_next_page") or next_cursor is None:
                reached_floor = True
                break
            if next_cursor == cursor:
                logger.warning("xquik: repeated cursor on page %d", pages)
                break
            cursor = next_cursor

        if not reached_floor:
            logger.warning(
                "xquik: stopped before reaching floor %s for %s after %d page(s)",
                start,
                handle,
                pages,
            )

        logger.info(
            "xquik fetch_tweets(%s, %s to %s): normalized %d, "
            "skipped %d malformed, in %d request(s) reached_floor=%s",
            handle,
            start,
            end,
            len(tweets),
            skipped,
            pages,
            reached_floor,
        )
        return FetchResult(
            tweets=tweets,
            reached_floor=reached_floor,
            skipped=skipped,
        )


def _search(
    query: str,
    headers: dict[str, str],
    *,
    limit: int = 20,
    cursor: str | None = None,
    retry_budget: dict[str, float] | None = None,
) -> dict[str, Any]:
    params = {
        "q": query,
        "queryType": "Latest",
        "limit": str(limit),
    }
    if cursor is not None:
        params["cursor"] = cursor
    url = f"{_BASE}/api/v1/x/tweets/search?{urllib.parse.urlencode(params)}"
    logger.info("xquik request: %s", url)
    return get_json(
        url,
        headers,
        retry_budget=retry_budget,
        transient_statuses=(424,),
    )


def _next_cursor(data: dict[str, Any]) -> str | None:
    value = data.get("next_cursor")
    return value if isinstance(value, str) and value else None


def _normalize_handle(handle: str) -> str:
    value = handle.strip().lstrip("@")
    if _HANDLE_PATTERN.fullmatch(value) is None:
        raise ValueError("Invalid X handle. Use 1-15 letters, numbers, or underscores.")
    return value


def _normalize(raw: dict[str, Any]) -> Tweet:
    tweet_id = raw["id"]
    tweet_type, is_reply, is_quote = compute_type(raw)
    quoted = raw.get("quoted_tweet")
    author = raw.get("author") or {}
    media_urls = [
        url
        for item in raw.get("media") or []
        for url in (item.get("mediaUrl") or item.get("url"),)
        if url
    ]
    return Tweet(
        id=tweet_id,
        created_at_utc=_created_at(raw),
        text=raw.get("text"),
        type=tweet_type,
        is_reply=is_reply,
        is_quote=is_quote,
        in_reply_to_id=raw.get("inReplyToId"),
        quoted_tweet_id=quoted.get("id") if quoted else None,
        quoted_author_id=(quoted["author"].get("id") if quoted and quoted.get("author") else None),
        conversation_id=raw.get("conversationId"),
        like_count=raw.get("likeCount"),
        retweet_count=raw.get("retweetCount"),
        reply_count=raw.get("replyCount"),
        quote_count=raw.get("quoteCount"),
        view_count=raw.get("viewCount"),
        bookmark_count=raw.get("bookmarkCount"),
        has_media=bool(media_urls),
        media_urls=media_urls,
        url=raw.get("url") or _tweet_url(author.get("username"), tweet_id),
        is_deleted=False,
        raw_json=raw,
        raw_provider_json=serialize_raw_json(tweet_id, raw),
    )


def _created_at(raw: dict[str, Any]) -> str:
    created = raw.get("createdAt")
    if isinstance(created, str) and created:
        return _normalize_timestamp(created)
    return snowflake_to_utc(raw["id"])


def _optional_created_at(value: Any) -> str | None:
    return _normalize_timestamp(value) if isinstance(value, str) and value else None


def _normalize_timestamp(value: str) -> str:
    parsed = datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=_UTC)
    return parsed.astimezone(_UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _tweet_url(username: str | None, tweet_id: str) -> str | None:
    if not username:
        return None
    return f"https://x.com/{username}/status/{tweet_id}"
