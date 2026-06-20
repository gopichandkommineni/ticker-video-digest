"""Shared HTTP helpers for tweet source adapters."""

from __future__ import annotations

import contextlib
import json
import logging
import socket
import threading
import time
import urllib.request
import urllib.error
from typing import Any

# Provider error hierarchy lives in base.py (PR A). Re-exported here so existing
# `from ._http import RateLimitExhausted, NetworkErrorExhausted` callsites and
# tests keep working unchanged.
from .base import (  # noqa: F401  (re-exported)
    ProviderError,
    TransientProviderError,
    PermanentProviderError,
    RateLimitExhausted,
    NetworkErrorExhausted,
    ServerError,
    AuthError,
    NotFoundError,
)

logger = logging.getLogger(__name__)

# Per-request retry schedule on HTTP 429 and transient network errors (seconds).
_DEFAULT_RETRY_DELAYS: tuple[int, ...] = (5, 30, 120)


# ---------------------------------------------------------------------------
# Per-provider rate limiting (worker pool v1 spec §3.3).
#
# get_json() must run every HTTP call through a provider's RateLimiter.wait()
# without the provider adapters (getxapi.py/twitterapi.py) needing changes. The
# worker scopes the right limiter to its own thread via use_rate_limiter();
# get_json reads it from this thread-local. A limiter passed explicitly to
# get_json (the DI seam used by tests) takes precedence. When neither is set —
# the sequential path — no limiting is applied and behavior is unchanged.
# ---------------------------------------------------------------------------
_thread_limiter = threading.local()


def _current_thread_limiter():
    return getattr(_thread_limiter, "limiter", None)


@contextlib.contextmanager
def use_rate_limiter(limiter):
    """Scope *limiter* to the current thread for the duration of the block.

    Nesting restores the previous limiter on exit. ``None`` disables limiting
    for the block.
    """
    prev = getattr(_thread_limiter, "limiter", None)
    _thread_limiter.limiter = limiter
    try:
        yield
    finally:
        _thread_limiter.limiter = prev


def _is_transient_network_error(exc: BaseException) -> bool:
    """True for socket read-timeouts and connection-level failures (not HTTP status errors)."""
    # TimeoutError is socket.timeout's parent on Python 3.11+; also check explicitly.
    if isinstance(exc, (TimeoutError, socket.timeout)):
        return True
    # urllib.error.URLError wraps socket errors; .reason may be a socket.timeout.
    if isinstance(exc, urllib.error.URLError) and not isinstance(exc, urllib.error.HTTPError):
        reason = exc.reason
        if isinstance(reason, (TimeoutError, socket.timeout, OSError)):
            return True
    return False


def get_json(
    url: str,
    headers: dict[str, str],
    timeout: int = 30,
    retry_delays: tuple[int, ...] = _DEFAULT_RETRY_DELAYS,
    retry_budget: dict[str, float] | None = None,
    rate_limiter=None,
    _sleep_fn=None,
) -> dict[str, Any]:
    """GET *url* with *headers*, return parsed JSON.

    Retries (up to len(retry_delays) times) on:
      - HTTP 429  — rate-limited
      - socket read-timeout / URLError — transient network failure

    retry_delays controls the sleep before each retry attempt (default 5s/30s/120s).
    retry_budget ({"remaining": float}) caps total cross-page sleep; when exhausted
    the next retryable error raises immediately without sleeping.

    Logs HTTP status on every 2xx response (DEBUG) and on every retried/final error.
    Raises RateLimitExhausted when 429 retries are exhausted.
    Raises NetworkErrorExhausted when network-error retries are exhausted.
    Raises RuntimeError on any other non-retryable HTTP error.
    """
    sleep = _sleep_fn if _sleep_fn is not None else time.sleep
    limiter = rate_limiter if rate_limiter is not None else _current_thread_limiter()
    attempt = 0

    while True:
        if limiter is not None:
            limiter.wait()
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                status = resp.status
                body = resp.read()
            logger.debug("HTTP %d %s", status, url)
            return json.loads(body)

        except urllib.error.HTTPError as exc:
            if exc.code == 429:
                if attempt < len(retry_delays):
                    wait = retry_delays[attempt]
                    attempt += 1
                    if retry_budget is not None and retry_budget.get("remaining", 0) <= 0:
                        logger.error("HTTP 429 %s — retry budget exhausted, aborting", url)
                        raise RateLimitExhausted(
                            f"HTTP 429 from {url}: retry budget exhausted"
                        ) from exc
                    logger.warning(
                        "HTTP 429 %s — retry %d/%d in %ds (budget=%.0fs)",
                        url, attempt, len(retry_delays), wait,
                        retry_budget["remaining"] if retry_budget else float("inf"),
                    )
                    if retry_budget is not None:
                        retry_budget["remaining"] -= wait
                    sleep(wait)
                    continue
                logger.error(
                    "HTTP 429 %s — exhausted %d retries, giving up", url, len(retry_delays)
                )
                raise RateLimitExhausted(
                    f"HTTP 429 from {url}: exhausted {len(retry_delays)} retries"
                ) from exc

            # Non-429 HTTP error — single attempt, map to a typed error and
            # raise immediately (PR A). 5xx is transient (the worker backs off);
            # we do NOT retry-with-backoff inside the request, since that would
            # stall the worker thread for the minutes-to-hours 5xx schedule.
            body = exc.read()
            try:
                detail = json.dumps(json.loads(body))
            except Exception:
                detail = body.decode(errors="replace")
            detail = detail[:200]
            logger.error("HTTP %d %s: %s", exc.code, url, detail)
            msg = f"HTTP {exc.code} from {url}: {detail}"
            if 500 <= exc.code < 600:
                raise ServerError(exc.code, msg) from exc
            if exc.code in (401, 403):
                raise AuthError(msg) from exc
            if exc.code == 404:
                raise NotFoundError(msg) from exc
            # Any other 4xx (and any unexpected code) is a permanent client error.
            raise PermanentProviderError(msg) from exc

        except BaseException as exc:
            if _is_transient_network_error(exc):
                if attempt < len(retry_delays):
                    wait = retry_delays[attempt]
                    attempt += 1
                    if retry_budget is not None and retry_budget.get("remaining", 0) <= 0:
                        logger.error(
                            "Network error %s (%s) — retry budget exhausted, aborting",
                            url, exc,
                        )
                        raise NetworkErrorExhausted(
                            f"Network error from {url}: retry budget exhausted"
                        ) from exc
                    logger.warning(
                        "Network error %s (%s) — retry %d/%d in %ds (budget=%.0fs)",
                        url, exc, attempt, len(retry_delays), wait,
                        retry_budget["remaining"] if retry_budget else float("inf"),
                    )
                    if retry_budget is not None:
                        retry_budget["remaining"] -= wait
                    sleep(wait)
                    continue
                logger.error(
                    "Network error %s (%s) — exhausted %d retries, giving up",
                    url, exc, len(retry_delays),
                )
                raise NetworkErrorExhausted(
                    f"Network error from {url}: exhausted {len(retry_delays)} retries"
                ) from exc
            raise


def extract_media_urls(raw: dict[str, Any], provider: str) -> list[str]:
    """Extract media URLs from a raw tweet dict for the given provider."""
    urls: list[str] = []
    if provider == "getxapi":
        for m in raw.get("media") or []:
            u = m.get("url") or m.get("media_url_https") or m.get("media_url")
            if u:
                urls.append(u)
    else:  # twitterapi
        ext = raw.get("extendedEntities") or {}
        for m in ext.get("media") or []:
            u = m.get("media_url_https") or m.get("media_url")
            if u:
                urls.append(u)
    return urls
