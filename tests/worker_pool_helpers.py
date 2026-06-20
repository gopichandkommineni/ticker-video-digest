"""Shared fixtures and mock adapters for worker-pool tests (spec §8).

Never hits a real provider. Mock adapters can record concurrency (max in-flight)
and inject specific failure modes (rate-limit, network, permanent).
"""

from __future__ import annotations

import datetime
import threading
import time
from pathlib import Path

from storage.db import get_connection, init_db
from storage.tweets import upsert_tweets
from tweet_sources.base import Tweet, FetchResult, UserInfo
from tweet_sources._http import RateLimitExhausted, NetworkErrorExhausted

UTC = datetime.timezone.utc


def iso(dt: datetime.datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def now_iso() -> str:
    return iso(datetime.datetime.now(tz=UTC))


def shift_iso(base: str, seconds: int) -> str:
    dt = datetime.datetime.strptime(base, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    return iso(dt + datetime.timedelta(seconds=seconds))


def make_tweet(tweet_id: str, *, handle: str = "acct", created: str | None = None) -> Tweet:
    return Tweet(
        id=tweet_id,
        created_at_utc=created or "2026-06-10T12:00:00Z",
        text=f"tweet {tweet_id}",
        type="original", is_reply=False, is_quote=False,
        in_reply_to_id=None, quoted_tweet_id=None, quoted_author_id=None,
        conversation_id=None, like_count=0, retweet_count=0, reply_count=0,
        quote_count=0, view_count=None, bookmark_count=None,
        has_media=False, media_urls=[], url=None,
    )


def make_tweet_dicts(handle: str, ids: list[str], provider: str) -> list[dict]:
    """Build storage-row dicts (what upsert_tweets consumes) for *ids*."""
    rows = []
    for tid in ids:
        rows.append({
            "tweet_id": tid, "account_handle": handle, "display_name": None,
            "user_id": None, "text": f"t{tid}", "created_at_utc": "2026-06-10T12:00:00Z",
            "type": "original", "is_reply": 0, "is_quote": 0, "in_reply_to_id": None,
            "quoted_tweet_id": None, "quoted_author_id": None, "conversation_id": None,
            "like_count": 0, "retweet_count": 0, "reply_count": 0, "quote_count": 0,
            "view_count": None, "bookmark_count": None, "has_media": 0,
            "media_urls": None, "url": None, "is_deleted": 0,
            "fetched_at": now_iso(), "source_provider": provider, "raw_json": None,
        })
    return rows


def fresh_db(tmp_path: Path, name: str = "fintwit.db") -> Path:
    db = tmp_path / name
    init_db(db)
    return db


def seed_pending(db: Path, handle: str, date: str, provider: str) -> None:
    """Insert a single pending day_fetch_log row."""
    conn = get_connection(db)
    try:
        with conn:
            conn.execute(
                "INSERT OR IGNORE INTO day_fetch_log (handle, date, provider, status) "
                "VALUES (?, ?, ?, 'pending')",
                (handle, date, provider),
            )
    finally:
        conn.close()


def row(db: Path, handle: str, date: str, provider: str) -> dict:
    conn = get_connection(db)
    try:
        r = conn.execute(
            "SELECT * FROM day_fetch_log WHERE handle=? AND date=? AND provider=?",
            (handle, date, provider),
        ).fetchone()
        return dict(r) if r else {}
    finally:
        conn.close()


class ConcurrencyTracker:
    """Records the maximum number of simultaneously in-flight fetches."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.current = 0
        self.max_seen = 0

    def enter(self) -> None:
        with self._lock:
            self.current += 1
            self.max_seen = max(self.max_seen, self.current)

    def exit(self) -> None:
        with self._lock:
            self.current -= 1


class MockAdapter:
    """Configurable fake TweetSource.

    Parameters
    ----------
    tweets_by_day   : {date_str: [tweet_id, ...]} returned per day.
    reached_floor   : value placed on the returned FetchResult.
    raise_exc       : if set, fetch_tweets raises this exception instance.
    pre_upsert      : (handle, [tweet_id,...]) written to the DB *before*
                      raising raise_exc — simulates a partial fetch that
                      lands tweets then hits a 429.
    db_path         : required if pre_upsert is used.
    tracker         : ConcurrencyTracker to record in-flight count.
    delay           : seconds to sleep while "in-flight" (for concurrency tests).
    provider        : provider tag for stored rows.
    """

    def __init__(
        self,
        *,
        tweets_by_day: dict[str, list[str]] | None = None,
        reached_floor: bool = True,
        raise_exc: BaseException | None = None,
        pre_upsert: tuple[str, list[str]] | None = None,
        db_path: Path | None = None,
        tracker: ConcurrencyTracker | None = None,
        delay: float = 0.0,
        provider: str = "mock",
    ) -> None:
        self.tweets_by_day = tweets_by_day or {}
        self.reached_floor = reached_floor
        self.raise_exc = raise_exc
        self.pre_upsert = pre_upsert
        self.db_path = db_path
        self.tracker = tracker
        self.delay = delay
        self.provider = provider
        self.calls: list[tuple[str, datetime.date]] = []
        self._lock = threading.Lock()

    def fetch_user_info(self, handle: str) -> UserInfo:
        return UserInfo(handle=handle, display_name="Mock", user_id="1",
                        created_at_utc=None, followers_count=0, following_count=0,
                        bio=None, is_verified=False, is_blue_verified=False)

    def fetch_tweets(self, handle, start, end) -> FetchResult:
        if self.tracker:
            self.tracker.enter()
        try:
            with self._lock:
                self.calls.append((handle, start))
            if self.delay:
                time.sleep(self.delay)
            if self.pre_upsert is not None:
                ph, ids = self.pre_upsert
                upsert_tweets(make_tweet_dicts(ph, ids, self.provider), db_path=self.db_path)
            if self.raise_exc is not None:
                raise self.raise_exc
            ids = self.tweets_by_day.get(start.isoformat(), [])
            tweets = [make_tweet(i, handle=handle) for i in ids]
            return FetchResult(tweets=tweets, reached_floor=self.reached_floor)
        finally:
            if self.tracker:
                self.tracker.exit()


def source_factory(mapping: dict[str, MockAdapter]):
    """Return a get_source_fn that yields the right MockAdapter per provider."""
    def _get(provider: str) -> MockAdapter:
        return mapping[provider]
    return _get


def rate_limit_exc(msg: str = "429") -> RateLimitExhausted:
    return RateLimitExhausted(msg)


def network_exc(msg: str = "timeout") -> NetworkErrorExhausted:
    return NetworkErrorExhausted(msg)


def permanent_exc(msg: str = "HTTP 401 auth") -> RuntimeError:
    return RuntimeError(msg)
