"""
Tests for HTTP 429 + network-error retry logic, adapter pagination interaction,
and _normalize resilience.

H1. TRANSIENT 429: 429 on first attempt, 200 on second — get_json returns data,
    sleep called once with the right delay, no exception raised.
H2. EXHAUSTED RETRIES: 429 on all attempts — RateLimitExhausted raised,
    sleep called len(retry_delays) times total.
H3. NON-429 HTTP ERROR: 500 response — RuntimeError raised immediately, no retry.
H4. BUDGET EXHAUSTED: retry_budget["remaining"] <= 0 before first retry sleep —
    RateLimitExhausted raised immediately without sleeping.
H5. ADAPTER RECOVERY (integration): adapter gets 429 on page 2 then 200 — run
    continues pagination, reached_floor=True, all tweets collected.
H6. ADAPTER ABORT (integration): adapter gets persistent 429 on page 3 (retries
    exhausted mid-pagination) — reached_floor=False, status=incomplete (NOT ready),
    partial tweets from pages 1-2 are persisted.
H7. TRANSIENT TIMEOUT: socket read-timeout on first attempt, 200 on second —
    get_json retries and returns data; sleep called once.
H8. EXHAUSTED TIMEOUT RETRIES: persistent TimeoutError — NetworkErrorExhausted
    raised after len(retry_delays) retries.
H9. URLERROR WITH SOCKET REASON: URLError wrapping socket.timeout is treated as
    transient and retried, not propagated as-is.
H10. ADAPTER RECOVERY ON TIMEOUT (integration): page 2 gets a transient timeout,
     recovers, run completes with reached_floor=True.
H11. ADAPTER ABORT ON TIMEOUT (integration): persistent timeout on page 3 exhausts
     retries — reached_floor=False, status NOT ready, partial tweets persisted.
"""

from __future__ import annotations

import datetime
import json
import socket
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import patch, MagicMock, call

import pytest

from tweet_sources._http import get_json, RateLimitExhausted, NetworkErrorExhausted
from tweet_sources.base import Tweet, FetchResult

UTC = datetime.timezone.utc


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _tweet_raw(tweet_id: str) -> dict:
    """Minimal raw tweet dict accepted by getxapi._normalize."""
    return {
        "id": tweet_id,
        "text": f"tweet {tweet_id}",
        "isReply": False,
    }


def _make_http_error(code: int) -> urllib.error.HTTPError:
    import io
    body = json.dumps({"error": f"HTTP {code}"}).encode()
    return urllib.error.HTTPError(
        url="https://example.com",
        code=code,
        msg=f"Error {code}",
        hdrs=None,
        fp=io.BytesIO(body),
    )


def _make_200_response(body: dict):
    """Return a context-manager mock that simulates a 200 urlopen response."""
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read.return_value = json.dumps(body).encode()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


# ---------------------------------------------------------------------------
# H1 — transient 429, recovers on second attempt
# ---------------------------------------------------------------------------

def test_h1_transient_429_recovers():
    slept: list[float] = []
    responses = [_make_http_error(429), _make_200_response({"ok": True})]
    call_count = 0

    def fake_urlopen(req, timeout):
        nonlocal call_count
        r = responses[call_count]
        call_count += 1
        if isinstance(r, urllib.error.HTTPError):
            raise r
        return r

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        result = get_json(
            "https://example.com/test",
            headers={},
            retry_delays=(5, 30, 120),
            _sleep_fn=slept.append,
        )

    assert result == {"ok": True}
    assert slept == [5], f"expected one 5s sleep, got {slept}"
    assert call_count == 2


# ---------------------------------------------------------------------------
# H2 — all retries exhausted → RateLimitExhausted
# ---------------------------------------------------------------------------

def test_h2_exhausted_retries_raises():
    slept: list[float] = []

    def fake_urlopen(req, timeout):
        raise _make_http_error(429)

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        with pytest.raises(RateLimitExhausted):
            get_json(
                "https://example.com/test",
                headers={},
                retry_delays=(5, 30, 120),
                _sleep_fn=slept.append,
            )

    # 3 retries → 3 sleeps (5, 30, 120), then raises on the 4th attempt
    assert slept == [5, 30, 120], f"expected sleeps [5,30,120], got {slept}"


# ---------------------------------------------------------------------------
# H3 — non-429 HTTP error → RuntimeError, no retry
# ---------------------------------------------------------------------------

def test_h3_non_429_raises_immediately():
    slept: list[float] = []
    call_count = 0

    def fake_urlopen(req, timeout):
        nonlocal call_count
        call_count += 1
        raise _make_http_error(500)

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        with pytest.raises(RuntimeError, match="HTTP 500"):
            get_json(
                "https://example.com/test",
                headers={},
                retry_delays=(5, 30, 120),
                _sleep_fn=slept.append,
            )

    assert slept == [], "no sleep on non-429 error"
    assert call_count == 1, "only one attempt for non-429"


# ---------------------------------------------------------------------------
# H4 — retry budget exhausted → no sleep, raises immediately
# ---------------------------------------------------------------------------

def test_h4_budget_exhausted_raises_without_sleeping():
    slept: list[float] = []

    def fake_urlopen(req, timeout):
        raise _make_http_error(429)

    budget = {"remaining": 0.0}
    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        with pytest.raises(RateLimitExhausted):
            get_json(
                "https://example.com/test",
                headers={},
                retry_delays=(5, 30, 120),
                retry_budget=budget,
                _sleep_fn=slept.append,
            )

    assert slept == [], "must not sleep when budget is 0"


# ---------------------------------------------------------------------------
# H5 — adapter-level recovery: 429 on page 2, then 200 — run continues
# ---------------------------------------------------------------------------

def test_h5_adapter_recovery_continues_pagination():
    """
    GetXApiSource.fetch_tweets: page 1 returns 2 tweets, page 2 gets a transient 429
    (recovers on retry), page 3 returns empty → reached_floor=True, all tweets collected.
    """
    from tweet_sources.getxapi import GetXApiSource

    # Snowflake IDs that decode to dates in the current year (within test tolerance).
    # We'll use deterministic IDs; the adapter uses snowflake_to_utc to parse them.
    # For simplicity, patch _normalize to control created_at_utc directly.
    year = datetime.datetime.now(UTC).year

    page1_tweets = [_tweet_raw("111"), _tweet_raw("112")]
    page2_tweets = [_tweet_raw("113"), _tweet_raw("114")]

    page_responses = [
        {"tweets": page1_tweets, "next_cursor": "cur1"},   # page 1: 200
        {"tweets": page2_tweets, "next_cursor": "cur2"},   # page 2: 429 then 200
        {"tweets": []},                                     # page 3: empty → floor
    ]
    page_idx = 0
    page2_attempted = 0
    slept: list[float] = []

    def fake_urlopen(req, timeout):
        nonlocal page_idx, page2_attempted
        # page 2 (index 1) gets a 429 on first attempt
        if page_idx == 1 and page2_attempted == 0:
            page2_attempted += 1
            raise _make_http_error(429)
        resp = _make_200_response(page_responses[page_idx])
        page_idx += 1
        return resp

    src = GetXApiSource(api_key="test-key")
    start = datetime.date(year, 1, 1)
    end = datetime.date(year, 6, 1)

    def fake_normalize(raw):
        # Return a Tweet with a created_at_utc well within the fetch window
        from tweet_sources.base import Tweet
        return Tweet(
            id=raw["id"], created_at_utc=f"{year}-03-01T10:00:00Z",
            text=raw.get("text"), type="original", is_reply=False, is_quote=False,
            in_reply_to_id=None, quoted_tweet_id=None, quoted_author_id=None,
            conversation_id=None, like_count=None, retweet_count=None, reply_count=None,
            quote_count=None, view_count=None, bookmark_count=None,
            has_media=False, media_urls=[], url=None,
        )

    with patch("urllib.request.urlopen", side_effect=fake_urlopen), \
         patch("tweet_sources.getxapi._normalize", side_effect=fake_normalize), \
         patch("tweet_sources._http.time.sleep", side_effect=slept.append):
        result = src.fetch_tweets("testuser", start, end)

    print(f"\nH5: tweets={len(result.tweets)} reached_floor={result.reached_floor} slept={slept}")
    assert result.reached_floor is True, "transient 429 must not abort — run should complete"
    assert len(result.tweets) == 4, f"all 4 tweets from pages 1+2 expected, got {len(result.tweets)}"
    assert slept == [5], "one 5s sleep for the transient 429"


# ---------------------------------------------------------------------------
# H6 — adapter abort: 429 exhausted mid-loop → reached_floor=False, status≠ready
# ---------------------------------------------------------------------------

def test_h6_adapter_abort_on_exhausted_429():
    """
    GetXApiSource.fetch_tweets: pages 1-2 succeed, page 3 gets persistent 429 (all
    retries exhausted). Adapter breaks with reached_floor=False.
    Then ingest_handle: outcome must NOT be 'ok', status must NOT be 'ready'.
    Partial tweets from pages 1-2 are persisted (self-healing).
    """
    from storage import init_db, get_handle
    from tweet_sources.getxapi import GetXApiSource
    import tempfile

    year = datetime.datetime.now(UTC).year

    page1_tweets = [_tweet_raw("201"), _tweet_raw("202")]
    page2_tweets = [_tweet_raw("203"), _tweet_raw("204")]

    page_responses = [
        {"tweets": page1_tweets, "next_cursor": "cur1"},
        {"tweets": page2_tweets, "next_cursor": "cur2"},
        # page 3: persistent 429 — all retries exhaust
    ]
    page_idx = 0
    slept: list[float] = []

    def fake_urlopen(req, timeout):
        nonlocal page_idx
        if page_idx >= len(page_responses):
            raise _make_http_error(429)
        resp = _make_200_response(page_responses[page_idx])
        page_idx += 1
        return resp

    def fake_normalize(raw):
        from tweet_sources.base import Tweet
        return Tweet(
            id=raw["id"], created_at_utc=f"{year}-03-15T10:00:00Z",
            text=raw.get("text"), type="original", is_reply=False, is_quote=False,
            in_reply_to_id=None, quoted_tweet_id=None, quoted_author_id=None,
            conversation_id=None, like_count=None, retweet_count=None, reply_count=None,
            quote_count=None, view_count=None, bookmark_count=None,
            has_media=False, media_urls=[], url=None,
        )

    with patch("urllib.request.urlopen", side_effect=fake_urlopen), \
         patch("tweet_sources.getxapi._normalize", side_effect=fake_normalize), \
         patch("tweet_sources._http.time.sleep", side_effect=slept.append):
        result = GetXApiSource(api_key="test-key").fetch_tweets(
            "throttled_user",
            datetime.date(year, 1, 1),
            datetime.date(year, 6, 1),
        )

    print(f"\nH6 adapter: tweets={len(result.tweets)} reached_floor={result.reached_floor} slept={slept}")

    # reached_floor must be False — this was NOT a clean stop
    assert result.reached_floor is False, (
        "exhausted 429 mid-pagination must NOT set reached_floor=True"
    )
    # Partial tweets from pages 1+2 are returned for storage
    assert len(result.tweets) == 4

    # Now run through ingest_handle: coverage-gap + reached_floor=False → incomplete
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "test.db"
        init_db(db)

        page_idx = 0  # reset for second run through ingest_handle
        slept.clear()

        from orchestration.runner import ingest_handle

        def fake_get_source(_provider):
            src = GetXApiSource(api_key="test-key")
            return src

        with patch("urllib.request.urlopen", side_effect=fake_urlopen), \
             patch("tweet_sources.getxapi._normalize", side_effect=fake_normalize), \
             patch("tweet_sources._http.time.sleep", side_effect=slept.append), \
             patch("orchestration.runner.get_source", side_effect=fake_get_source):
            ir = ingest_handle("throttled_user", provider="fake", db_path=db)

        row = get_handle("throttled_user", db_path=db)
        print(f"H6 ingest: outcome={ir.outcome}, status={row['status']}, inserted={ir.inserted}")

        # MUST NOT be ready — a 429-aborted run is not complete
        assert row["status"] != "ready", (
            f"status must not be 'ready' after exhausted 429 abort, got {row['status']!r}"
        )
        assert ir.outcome != "ok", (
            f"outcome must not be 'ok' after exhausted 429 abort, got {ir.outcome!r}"
        )
        # Partial tweets stored — available for retry
        assert ir.inserted == 4, f"4 partial tweets should be stored, got {ir.inserted}"


# ---------------------------------------------------------------------------
# H7 — transient socket read-timeout, recovers on second attempt
# ---------------------------------------------------------------------------

def test_h7_transient_timeout_recovers():
    slept: list[float] = []
    call_count = 0

    def fake_urlopen(req, timeout):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise TimeoutError("timed out")
        return _make_200_response({"ok": True})

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        result = get_json(
            "https://example.com/test",
            headers={},
            retry_delays=(5, 30, 120),
            _sleep_fn=slept.append,
        )

    assert result == {"ok": True}
    assert slept == [5], f"expected one 5s sleep, got {slept}"
    assert call_count == 2


# ---------------------------------------------------------------------------
# H8 — persistent TimeoutError exhausts retries → NetworkErrorExhausted
# ---------------------------------------------------------------------------

def test_h8_exhausted_timeout_raises():
    slept: list[float] = []

    with patch("urllib.request.urlopen", side_effect=TimeoutError("timed out")):
        with pytest.raises(NetworkErrorExhausted):
            get_json(
                "https://example.com/test",
                headers={},
                retry_delays=(5, 30, 120),
                _sleep_fn=slept.append,
            )

    assert slept == [5, 30, 120], f"expected sleeps [5,30,120], got {slept}"


# ---------------------------------------------------------------------------
# H9 — URLError wrapping socket.timeout is treated as transient, retried
# ---------------------------------------------------------------------------

def test_h9_urlerror_socket_timeout_retried():
    slept: list[float] = []
    call_count = 0

    def fake_urlopen(req, timeout):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise urllib.error.URLError(reason=socket.timeout("timed out"))
        return _make_200_response({"data": 42})

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        result = get_json(
            "https://example.com/test",
            headers={},
            retry_delays=(5, 30, 120),
            _sleep_fn=slept.append,
        )

    assert result == {"data": 42}
    assert slept == [5]
    assert call_count == 2


# ---------------------------------------------------------------------------
# H10 — adapter recovery on transient timeout (integration)
# ---------------------------------------------------------------------------

def test_h10_adapter_recovery_on_timeout():
    """Page 2 gets a transient timeout, recovers on retry, run completes normally."""
    from tweet_sources.getxapi import GetXApiSource

    year = datetime.datetime.now(UTC).year
    page1_tweets = [_tweet_raw("301"), _tweet_raw("302")]
    page2_tweets = [_tweet_raw("303"), _tweet_raw("304")]

    page_responses = [
        {"tweets": page1_tweets, "next_cursor": "cur1"},
        {"tweets": page2_tweets, "next_cursor": "cur2"},
        {"tweets": []},
    ]
    page_idx = 0
    page2_attempted = 0
    slept: list[float] = []

    def fake_urlopen(req, timeout):
        nonlocal page_idx, page2_attempted
        if page_idx == 1 and page2_attempted == 0:
            page2_attempted += 1
            raise TimeoutError("read timed out")
        resp = _make_200_response(page_responses[page_idx])
        page_idx += 1
        return resp

    def fake_normalize(raw):
        from tweet_sources.base import Tweet
        return Tweet(
            id=raw["id"], created_at_utc=f"{year}-03-01T10:00:00Z",
            text=raw.get("text"), type="original", is_reply=False, is_quote=False,
            in_reply_to_id=None, quoted_tweet_id=None, quoted_author_id=None,
            conversation_id=None, like_count=None, retweet_count=None, reply_count=None,
            quote_count=None, view_count=None, bookmark_count=None,
            has_media=False, media_urls=[], url=None,
        )

    src = GetXApiSource(api_key="test-key")
    with patch("urllib.request.urlopen", side_effect=fake_urlopen), \
         patch("tweet_sources.getxapi._normalize", side_effect=fake_normalize), \
         patch("tweet_sources._http.time.sleep", side_effect=slept.append):
        result = src.fetch_tweets(
            "testuser",
            datetime.date(year, 1, 1),
            datetime.date(year, 6, 1),
        )

    print(f"\nH10: tweets={len(result.tweets)} reached_floor={result.reached_floor} slept={slept}")
    assert result.reached_floor is True, "transient timeout must not abort — run should complete"
    assert len(result.tweets) == 4
    assert slept == [5]


# ---------------------------------------------------------------------------
# H11 — adapter abort on persistent timeout (integration)
# ---------------------------------------------------------------------------

def test_h11_adapter_abort_on_persistent_timeout():
    """Persistent timeout on page 3 exhausts retries → reached_floor=False, status≠ready."""
    from tweet_sources.getxapi import GetXApiSource
    from storage import init_db, get_handle
    import tempfile

    year = datetime.datetime.now(UTC).year
    page1_tweets = [_tweet_raw("401"), _tweet_raw("402")]
    page2_tweets = [_tweet_raw("403"), _tweet_raw("404")]

    page_responses = [
        {"tweets": page1_tweets, "next_cursor": "cur1"},
        {"tweets": page2_tweets, "next_cursor": "cur2"},
    ]
    page_idx = 0
    slept: list[float] = []

    def fake_urlopen(req, timeout):
        nonlocal page_idx
        if page_idx >= len(page_responses):
            raise TimeoutError("read timed out")
        resp = _make_200_response(page_responses[page_idx])
        page_idx += 1
        return resp

    def fake_normalize(raw):
        from tweet_sources.base import Tweet
        return Tweet(
            id=raw["id"], created_at_utc=f"{year}-03-15T10:00:00Z",
            text=raw.get("text"), type="original", is_reply=False, is_quote=False,
            in_reply_to_id=None, quoted_tweet_id=None, quoted_author_id=None,
            conversation_id=None, like_count=None, retweet_count=None, reply_count=None,
            quote_count=None, view_count=None, bookmark_count=None,
            has_media=False, media_urls=[], url=None,
        )

    # Adapter-level check first
    with patch("urllib.request.urlopen", side_effect=fake_urlopen), \
         patch("tweet_sources.getxapi._normalize", side_effect=fake_normalize), \
         patch("tweet_sources._http.time.sleep", side_effect=slept.append):
        result = GetXApiSource(api_key="test-key").fetch_tweets(
            "timeout_user",
            datetime.date(year, 1, 1),
            datetime.date(year, 6, 1),
        )

    print(f"\nH11 adapter: tweets={len(result.tweets)} reached_floor={result.reached_floor} slept={slept}")
    assert result.reached_floor is False
    assert len(result.tweets) == 4
    assert slept == [5, 30, 120]

    # Orchestrator check
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "test.db"
        init_db(db)
        page_idx = 0
        slept.clear()

        from orchestration.runner import ingest_handle

        def fake_get_source(_provider):
            return GetXApiSource(api_key="test-key")

        with patch("urllib.request.urlopen", side_effect=fake_urlopen), \
             patch("tweet_sources.getxapi._normalize", side_effect=fake_normalize), \
             patch("tweet_sources._http.time.sleep", side_effect=slept.append), \
             patch("orchestration.runner.get_source", side_effect=fake_get_source):
            ir = ingest_handle("timeout_user", provider="fake", db_path=db)

        row = get_handle("timeout_user", db_path=db)
        print(f"H11 ingest: outcome={ir.outcome}, status={row['status']}, inserted={ir.inserted}")

        assert row["status"] != "ready", f"timeout-aborted run must not be ready, got {row['status']!r}"
        assert ir.outcome != "ok", f"outcome must not be ok, got {ir.outcome!r}"
        assert ir.inserted == 4


# ---------------------------------------------------------------------------
# N1 — _normalize: stub quoted tweet missing "id" → quoted_tweet_id=None, no crash
# ---------------------------------------------------------------------------

def test_n1_normalize_stub_quoted_tweet_no_id():
    """A quoted_tweet object present but missing 'id' must not crash _normalize."""
    from tweet_sources.getxapi import _normalize as gx_normalize
    from tweet_sources.twitterapi import _normalize as tw_normalize

    raw = {
        "id": "1234567890000000000",
        "text": "quoting a deleted tweet",
        "isReply": False,
        "quoted_tweet": {},                    # stub: no 'id', no 'author'
    }

    for normalize in (gx_normalize, tw_normalize):
        tweet = normalize(raw)
        assert tweet.quoted_tweet_id is None, "stub quote with no id must yield quoted_tweet_id=None"
        assert tweet.quoted_author_id is None


def test_n1b_normalize_stub_quoted_tweet_has_id_no_author():
    """A quoted_tweet with 'id' but no 'author' must not crash and must surface the id."""
    from tweet_sources.getxapi import _normalize as gx_normalize
    from tweet_sources.twitterapi import _normalize as tw_normalize

    raw = {
        "id": "1234567890000000000",
        "text": "quoting something",
        "isReply": False,
        "quoted_tweet": {"id": "9999000000000000000"},   # id present, author absent
    }

    for normalize in (gx_normalize, tw_normalize):
        tweet = normalize(raw)
        assert tweet.quoted_tweet_id == "9999000000000000000"
        assert tweet.quoted_author_id is None


# ---------------------------------------------------------------------------
# N2 — fetch loop: one malformed tweet is skipped, others still returned
# ---------------------------------------------------------------------------

def test_n2_fetch_loop_skips_malformed_continues():
    """A tweet that raises in _normalize is skipped; the rest of the batch is kept."""
    from tweet_sources.getxapi import GetXApiSource

    year = datetime.datetime.now(UTC).year
    good1 = _tweet_raw("501")
    bad   = {"id": "502", "text": "bad", "isReply": False, "quoted_tweet": {"broken": True}}
    good2 = _tweet_raw("503")

    def fake_urlopen(req, timeout):
        return _make_200_response({"tweets": [good1, bad, good2], "next_cursor": None})

    def fake_normalize_raise_on_502(raw):
        if raw.get("id") == "502":
            raise ValueError("injected normalization failure")
        return Tweet(
            id=raw["id"], created_at_utc=f"{year}-03-01T10:00:00Z",
            text=raw.get("text"), type="original", is_reply=False, is_quote=False,
            in_reply_to_id=None, quoted_tweet_id=None, quoted_author_id=None,
            conversation_id=None, like_count=None, retweet_count=None, reply_count=None,
            quote_count=None, view_count=None, bookmark_count=None,
            has_media=False, media_urls=[], url=None,
        )

    src = GetXApiSource(api_key="test-key")
    with patch("urllib.request.urlopen", side_effect=fake_urlopen), \
         patch("tweet_sources.getxapi._normalize", side_effect=fake_normalize_raise_on_502):
        result = src.fetch_tweets(
            "testuser",
            datetime.date(year, 1, 1),
            datetime.date(year, 6, 1),
        )

    print(f"\nN2: tweets={len(result.tweets)} skipped={result.skipped}")
    assert result.skipped == 1, f"expected 1 skipped, got {result.skipped}"
    assert len(result.tweets) == 2
    assert {t.id for t in result.tweets} == {"501", "503"}


# ---------------------------------------------------------------------------
# N3 — fetch loop: skipped count is zero when no errors occur
# ---------------------------------------------------------------------------

def test_n3_skipped_zero_when_no_errors():
    """Normal run with no malformed tweets reports skipped=0."""
    from tweet_sources.getxapi import GetXApiSource

    year = datetime.datetime.now(UTC).year

    def fake_urlopen(req, timeout):
        return _make_200_response({"tweets": [_tweet_raw("601"), _tweet_raw("602")], "next_cursor": None})

    def fake_normalize(raw):
        return Tweet(
            id=raw["id"], created_at_utc=f"{year}-03-01T10:00:00Z",
            text=raw.get("text"), type="original", is_reply=False, is_quote=False,
            in_reply_to_id=None, quoted_tweet_id=None, quoted_author_id=None,
            conversation_id=None, like_count=None, retweet_count=None, reply_count=None,
            quote_count=None, view_count=None, bookmark_count=None,
            has_media=False, media_urls=[], url=None,
        )

    src = GetXApiSource(api_key="test-key")
    with patch("urllib.request.urlopen", side_effect=fake_urlopen), \
         patch("tweet_sources.getxapi._normalize", side_effect=fake_normalize):
        result = src.fetch_tweets(
            "testuser",
            datetime.date(year, 1, 1),
            datetime.date(year, 6, 1),
        )

    assert result.skipped == 0
    assert len(result.tweets) == 2
