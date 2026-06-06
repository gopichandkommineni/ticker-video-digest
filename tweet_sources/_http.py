"""Shared HTTP helpers for tweet source adapters."""

from __future__ import annotations

import json
import logging
import time
import urllib.request
import urllib.error
from typing import Any

logger = logging.getLogger(__name__)

# Per-request retry schedule on HTTP 429 (seconds to wait before each retry).
_DEFAULT_RETRY_DELAYS: tuple[int, ...] = (5, 30, 120)


class RateLimitExhausted(RuntimeError):
    """Raised when a request is still 429 after all per-request retries are exhausted."""


def get_json(
    url: str,
    headers: dict[str, str],
    timeout: int = 30,
    retry_delays: tuple[int, ...] = _DEFAULT_RETRY_DELAYS,
    retry_budget: dict[str, float] | None = None,
    _sleep_fn=None,
) -> dict[str, Any]:
    """GET *url* with *headers*, return parsed JSON.

    On HTTP 429: retries up to len(retry_delays) times, sleeping retry_delays[i] seconds
    before attempt i+1. If retry_budget is provided ({"remaining": float}), the sleep is
    skipped and RateLimitExhausted is raised immediately when the budget is exhausted —
    this prevents a single throttled handle from consuming the whole Actions timeout.

    Logs HTTP status on every 2xx response (DEBUG) and on every error (WARNING/ERROR).
    Raises RateLimitExhausted when 429 retries are exhausted.
    Raises RuntimeError on any other HTTP error.
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
                    # Guard: if a shared budget is provided and exhausted, give up now.
                    if retry_budget is not None and retry_budget.get("remaining", 0) <= 0:
                        logger.error(
                            "HTTP 429 %s — retry budget exhausted, aborting", url
                        )
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
                # All retries exhausted.
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
