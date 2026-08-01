"""PR A — adapter HTTP errors surface to the worker as typed exceptions.

Covers the exception hierarchy, _http.py status-code mapping, adapter
propagation (no swallow to reached_floor=False), and the worker's type-dispatch
exception handler. Never hits a real provider.
"""

from __future__ import annotations

import datetime
import urllib.error
from unittest.mock import patch

import pytest

from fintwit.tweet_sources.base import (
    ProviderError, TransientProviderError, PermanentProviderError,
    RateLimitExhausted, NetworkErrorExhausted, ServerError,
    AuthError, NotFoundError,
)
from fintwit.tweet_sources._http import get_json
from fintwit.storage.day_log import Job
from fintwit.orchestration.worker_pool import process_job, PoolConfig

from tests.worker_pool_helpers import (
    fresh_db, seed_pending, row, now_iso, shift_iso,
    MockAdapter, source_factory,
    rate_limit_exc, network_exc, server_exc, auth_exc, notfound_exc,
)


# ===========================================================================
# Hierarchy tests
# ===========================================================================

def test_rate_limit_is_transient_provider_error():
    e = RateLimitExhausted("x")
    assert isinstance(e, TransientProviderError)
    assert isinstance(e, ProviderError)


def test_server_error_is_transient_provider_error():
    e = ServerError(503)
    assert isinstance(e, TransientProviderError)
    assert isinstance(e, ProviderError)
    assert e.status_code == 503


def test_network_error_is_transient_provider_error():
    assert isinstance(NetworkErrorExhausted("x"), TransientProviderError)


def test_auth_error_is_permanent_provider_error():
    e = AuthError("x")
    assert isinstance(e, PermanentProviderError)
    assert isinstance(e, ProviderError)
    assert not isinstance(e, TransientProviderError)


def test_not_found_is_permanent_provider_error():
    assert isinstance(NotFoundError("x"), PermanentProviderError)


def test_existing_runtime_error_catches_still_work():
    # Pre-existing `except RuntimeError` keeps catching the typed errors (MRO).
    assert isinstance(RateLimitExhausted(), RuntimeError)
    assert isinstance(ServerError(500), RuntimeError)
    assert isinstance(AuthError(), RuntimeError)


# ===========================================================================
# _http.py status-code mapping
# ===========================================================================

def _http_error(code: int) -> urllib.error.HTTPError:
    import io
    return urllib.error.HTTPError(
        url="https://example.com/x", code=code, msg=f"err{code}",
        hdrs=None, fp=io.BytesIO(b'{"detail":"boom"}'),
    )


def _call_get_json():
    return get_json("https://example.com/x", headers={}, retry_delays=(5, 30, 120),
                    _sleep_fn=lambda s: None)


def test_http_429_raises_rate_limit_after_retries():
    with patch("urllib.request.urlopen", side_effect=_http_error(429)):
        with pytest.raises(RateLimitExhausted):
            _call_get_json()


def test_http_500_raises_server_error():
    with patch("urllib.request.urlopen", side_effect=_http_error(500)):
        with pytest.raises(ServerError) as ei:
            _call_get_json()
    assert ei.value.status_code == 500


def test_http_503_raises_server_error_with_503():
    with patch("urllib.request.urlopen", side_effect=_http_error(503)):
        with pytest.raises(ServerError) as ei:
            _call_get_json()
    assert ei.value.status_code == 503


def test_http_502_raises_server_error():
    with patch("urllib.request.urlopen", side_effect=_http_error(502)):
        with pytest.raises(ServerError) as ei:
            _call_get_json()
    assert ei.value.status_code == 502


def test_http_401_raises_auth_error():
    with patch("urllib.request.urlopen", side_effect=_http_error(401)):
        with pytest.raises(AuthError):
            _call_get_json()


def test_http_403_raises_auth_error():
    with patch("urllib.request.urlopen", side_effect=_http_error(403)):
        with pytest.raises(AuthError):
            _call_get_json()


def test_http_404_raises_not_found_error():
    with patch("urllib.request.urlopen", side_effect=_http_error(404)):
        with pytest.raises(NotFoundError):
            _call_get_json()


def test_http_418_raises_permanent_provider_error():
    # 418 (teapot): generic 4xx → permanent, not auth/not-found.
    with patch("urllib.request.urlopen", side_effect=_http_error(418)):
        with pytest.raises(PermanentProviderError) as ei:
            _call_get_json()
    assert not isinstance(ei.value, (AuthError, NotFoundError))


def test_5xx_is_single_attempt_no_retry():
    # Unlike 429, a 5xx is one attempt — no in-request backoff sleeps.
    slept: list[float] = []
    with patch("urllib.request.urlopen", side_effect=_http_error(500)):
        with pytest.raises(ServerError):
            get_json("https://example.com/x", headers={}, retry_delays=(5, 30, 120),
                     _sleep_fn=slept.append)
    assert slept == []


# ===========================================================================
# Adapter propagation (both providers): no swallow to reached_floor=False
# ===========================================================================

def _patch_pages(provider_mod, pages, raise_after: int, exc):
    """Make get_json (as imported into the adapter module) return *pages* dicts,
    then raise *exc* on call index *raise_after* (0-based)."""
    state = {"i": 0}

    def fake_get_json(url, headers, **kw):
        i = state["i"]
        state["i"] += 1
        if i >= raise_after:
            raise exc
        return pages[i]

    return patch(f"fintwit.tweet_sources.{provider_mod}.get_json", side_effect=fake_get_json)


@pytest.mark.parametrize("provider_mod", ["getxapi", "twitterapi"])
def test_adapter_propagates_rate_limit(provider_mod):
    from fintwit.tweet_sources.getxapi import GetXApiSource
    from fintwit.tweet_sources.twitterapi import TwitterApiIoSource
    src = (GetXApiSource if provider_mod == "getxapi" else TwitterApiIoSource)("k")
    year = datetime.datetime.now(datetime.timezone.utc).year
    with _patch_pages(provider_mod, [{"tweets": [{"id": "1"}]}], raise_after=0,
                      exc=rate_limit_exc()):
        with pytest.raises(RateLimitExhausted):
            src.fetch_tweets("u", datetime.date(year, 1, 1), datetime.date(year, 6, 1))


@pytest.mark.parametrize("provider_mod", ["getxapi", "twitterapi"])
def test_adapter_propagates_server_error(provider_mod):
    from fintwit.tweet_sources.getxapi import GetXApiSource
    from fintwit.tweet_sources.twitterapi import TwitterApiIoSource
    src = (GetXApiSource if provider_mod == "getxapi" else TwitterApiIoSource)("k")
    year = datetime.datetime.now(datetime.timezone.utc).year
    with _patch_pages(provider_mod, [{"tweets": [{"id": "1"}]}], raise_after=0,
                      exc=server_exc(503)):
        with pytest.raises(ServerError):
            src.fetch_tweets("u", datetime.date(year, 1, 1), datetime.date(year, 6, 1))


@pytest.mark.parametrize("provider_mod", ["getxapi", "twitterapi"])
def test_adapter_does_not_swallow_to_reached_floor_false(provider_mod):
    """Error on page 2 of a multi-page fetch raises rather than returning a
    partial FetchResult(reached_floor=False)."""
    from fintwit.tweet_sources.getxapi import GetXApiSource
    from fintwit.tweet_sources.twitterapi import TwitterApiIoSource
    from fintwit.tweet_sources.base import Tweet
    src = (GetXApiSource if provider_mod == "getxapi" else TwitterApiIoSource)("k")
    year = datetime.datetime.now(datetime.timezone.utc).year

    # page 1 returns one tweet with a next cursor; page 2 raises.
    page1 = {"tweets": [{"id": "1"}], "next_cursor": "c1"}

    def fake_normalize(raw):
        return Tweet(
            id=raw["id"], created_at_utc=f"{year}-03-01T10:00:00Z", text="t",
            type="original", is_reply=False, is_quote=False, in_reply_to_id=None,
            quoted_tweet_id=None, quoted_author_id=None, conversation_id=None,
            like_count=None, retweet_count=None, reply_count=None, quote_count=None,
            view_count=None, bookmark_count=None, has_media=False, media_urls=[], url=None,
        )

    with _patch_pages(provider_mod, [page1], raise_after=1, exc=rate_limit_exc()), \
         patch(f"fintwit.tweet_sources.{provider_mod}._normalize", side_effect=fake_normalize):
        with pytest.raises(RateLimitExhausted):
            src.fetch_tweets("u", datetime.date(year, 1, 1), datetime.date(year, 6, 1))


# ===========================================================================
# Worker exception handler → ledger outcomes
# ===========================================================================

def _cfg() -> PoolConfig:
    return PoolConfig(
        pool_sizes={"getxapi": 1}, rate_intervals_ms={"getxapi": 0},
        max_attempts=3,
        backoff_schedule_sec=[60, 300, 1800],
        backoff_rate_limit_sec=[60, 300, 1800],
        backoff_transient_sec=[300, 900, 3600],
        stale_threshold_sec=600,
    )


def _run(db, exc, *, attempts=0, now=None):
    seed_pending(db, "acct", "2026-06-10", "getxapi")
    src = MockAdapter(raise_exc=exc, provider="getxapi")
    job = Job("acct", "2026-06-10", "getxapi", "pending", attempts=attempts)
    return process_job(job, "getxapi", db_path=db, config=_cfg(),
                       get_source_fn=source_factory({"getxapi": src}),
                       now=now or now_iso())


def test_worker_rate_limit_marks_failed_with_rate_limit_class(tmp_path):
    db = fresh_db(tmp_path)
    now = now_iso()
    outcome = _run(db, rate_limit_exc(), now=now)
    assert outcome.error_class == "rate_limit"
    r = row(db, "acct", "2026-06-10", "getxapi")
    assert r["status"] == "failed"
    assert r["error_class"] == "rate_limit"
    assert r["next_eligible_at"] == shift_iso(now, 60)   # rate-limit schedule


def test_worker_server_error_marks_failed_with_server_class(tmp_path):
    db = fresh_db(tmp_path)
    now = now_iso()
    outcome = _run(db, server_exc(503), now=now)
    assert outcome.error_class == "server"
    r = row(db, "acct", "2026-06-10", "getxapi")
    assert r["status"] == "failed"
    assert r["error_class"] == "server"
    assert r["next_eligible_at"] == shift_iso(now, 300)   # transient schedule, 5min


def test_worker_network_error_uses_transient_schedule(tmp_path):
    db = fresh_db(tmp_path)
    now = now_iso()
    _run(db, network_exc(), now=now)
    r = row(db, "acct", "2026-06-10", "getxapi")
    assert r["error_class"] == "network"
    assert r["next_eligible_at"] == shift_iso(now, 300)


def test_worker_auth_error_marks_failed_permanent(tmp_path):
    db = fresh_db(tmp_path)
    outcome = _run(db, auth_exc())
    assert outcome.error_class == "auth"
    r = row(db, "acct", "2026-06-10", "getxapi")
    assert r["status"] == "failed"
    assert r["retry_count"] == _cfg().max_attempts   # forced to cap, no retry
    assert r["next_eligible_at"] is None


def test_worker_not_found_marks_failed_permanent(tmp_path):
    db = fresh_db(tmp_path)
    outcome = _run(db, notfound_exc())
    assert outcome.error_class == "not_found"
    r = row(db, "acct", "2026-06-10", "getxapi")
    assert r["retry_count"] == _cfg().max_attempts
    assert r["next_eligible_at"] is None


def test_worker_max_attempts_terminal(tmp_path):
    """Third rate-limit failure exhausts attempts → terminal, no next_eligible_at."""
    db = fresh_db(tmp_path)
    seed_pending(db, "acct", "2026-06-10", "getxapi")
    src = MockAdapter(raise_exc=rate_limit_exc(), provider="getxapi")
    base = now_iso()
    for attempt in range(1, 4):
        now = shift_iso(base, attempt * 7200)
        prev = row(db, "acct", "2026-06-10", "getxapi")["retry_count"] or 0
        job = Job("acct", "2026-06-10", "getxapi", "failed", attempts=prev)
        process_job(job, "getxapi", db_path=db, config=_cfg(),
                    get_source_fn=source_factory({"getxapi": src}), now=now)
    r = row(db, "acct", "2026-06-10", "getxapi")
    assert r["status"] == "failed"
    assert r["retry_count"] == 3
    assert r["next_eligible_at"] is None


def test_worker_unknown_exception_treated_conservatively(tmp_path):
    db = fresh_db(tmp_path)
    now = now_iso()
    outcome = _run(db, ValueError("totally unexpected"), now=now)
    assert outcome.error_class == "unknown"
    r = row(db, "acct", "2026-06-10", "getxapi")
    assert r["status"] == "failed"
    # Conservative: scheduled for retry on the transient schedule, not terminal.
    assert r["next_eligible_at"] == shift_iso(now, 300)
    assert r["retry_count"] == 1


# ===========================================================================
# Regression / parity
# ===========================================================================

def test_existing_429_test_still_passes(tmp_path):
    """The PR #102 assertion (429 → error_class='rate_limit', backoff ~60s) holds."""
    db = fresh_db(tmp_path)
    now = now_iso()
    _run(db, rate_limit_exc(), now=now)
    r = row(db, "acct", "2026-06-10", "getxapi")
    assert r["status"] == "failed"
    assert r["error_class"] == "rate_limit"
    assert r["next_eligible_at"] == shift_iso(now, 60)
