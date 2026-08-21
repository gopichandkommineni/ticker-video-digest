"""The FetchContext implementation handed to adapters."""

from __future__ import annotations

from typing import Any

from career_compass.models import RawPayload


class HttpFetchContext:
    """Rate-limited, robots-checked, conditionally-cached HTTP.

    Sends If-None-Match / If-Modified-Since from the previous fetch of the
    same URL, so an unchanged feed costs one 304 and nothing else. Backs off
    on 429/503 honoring Retry-After, three attempts, then gives up and lets
    the run ledger record the source as failed.
    """

    def get(self, url: str, **kwargs: Any) -> RawPayload:
        raise NotImplementedError

    def post(self, url: str, json: dict[str, Any], **kwargs: Any) -> RawPayload:
        raise NotImplementedError

    def previous_etag(self, url: str) -> str | None:
        raise NotImplementedError
