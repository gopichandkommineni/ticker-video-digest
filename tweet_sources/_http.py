"""Shared HTTP helpers for tweet source adapters."""

from __future__ import annotations

import json
import logging
import urllib.request
import urllib.error
from typing import Any

logger = logging.getLogger(__name__)


def get_json(
    url: str,
    headers: dict[str, str],
    timeout: int = 30,
) -> dict[str, Any]:
    """GET *url* with *headers*, return parsed JSON. Raises on HTTP errors."""
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
    except urllib.error.HTTPError as exc:
        body = exc.read()
        try:
            detail = json.loads(body)
        except Exception:
            detail = body.decode(errors="replace")
        raise RuntimeError(
            f"HTTP {exc.code} from {url}: {detail}"
        ) from exc
    return json.loads(body)


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
