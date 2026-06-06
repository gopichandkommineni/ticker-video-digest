"""Shared HTTP helpers for tweet source adapters."""

from __future__ import annotations

import json
import logging
import socket
import time
import urllib.request
import urllib.error
from typing import Any

logger = logging.getLogger(__name__)

# Per-request retry schedule on HTTP 429 and transient network errors (seconds).
_DEFAULT_RETRY_DELAYS: tuple[int, ...] = (5, 30, 120)


class RateLimitExhausted(RuntimeError):
    """Raised when a request is still 429 after all per-request retries are exhausted."""


class NetworkErrorExhausted(RuntimeError):
    """Raised when a transient network/timeout error persists after all retries."""


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
    attempt = 0

    while True:
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

            # Non-429 HTTP error — no retry.
            body = exc.read()
            try:
                detail = json.loads(body)
            except Exception:
                detail = body.decode(errors="replace")
            logger.error("HTTP %d %s: %s", exc.code, url, detail)
            raise RuntimeError(f"HTTP {exc.code} from {url}: {detail}") from exc

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
