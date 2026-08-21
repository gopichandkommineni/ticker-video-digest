"""The adapter contract.

Nothing downstream of ingest knows whether bytes came from an RSS feed, a
Greenhouse board, or my clipboard. See docs/03-ingestion-contracts.md.
"""

from __future__ import annotations

from typing import Any, Iterator, Protocol, runtime_checkable

from career_compass.models import NormalizedDocument, RawPayload, SourceKind


class FetchContext(Protocol):
    """Shared services handed to every adapter's `fetch`.

    Politeness is enforced here, centrally, rather than per adapter — so a new
    adapter cannot forget to rate limit or to check robots.txt
    (docs/08-legal-and-etiquette.md). There is deliberately no override flag.
    """

    def get(self, url: str, **kwargs: Any) -> RawPayload:
        """Rate-limited, robots-checked, conditional GET.

        Sends If-None-Match / If-Modified-Since from the previous fetch of
        this URL. Raises `Blocked` if robots.txt disallows the path.
        """
        ...

    def post(self, url: str, json: dict[str, Any], **kwargs: Any) -> RawPayload:
        """Same guarantees as `get`. Workday-style boards need POST search."""
        ...

    def previous_etag(self, url: str) -> str | None: ...


@runtime_checkable
class SourceAdapter(Protocol):
    """Every source implements exactly this.

    `fetch` and `normalize` live together because they share format knowledge,
    but they are called by different jobs at different times. `normalize`
    being pure is the load-bearing constraint — it is what makes a parser fix
    replayable across the entire raw store without re-fetching (ADR-0002).
    """

    name: str
    kind: SourceKind

    def validate(self, config: dict[str, Any]) -> None:
        """Raise ConfigError if this source's config is unusable.

        Called at load time so a typo fails immediately, not at 2am.
        """
        ...

    def fetch(self, config: dict[str, Any], ctx: FetchContext) -> Iterator[RawPayload]:
        """Yield raw payloads. May hit the network. Must not parse."""
        ...

    def normalize(self, raw: RawPayload) -> Iterator[NormalizedDocument]:
        """Pure. No network, no clock, no randomness.

        Given identical bytes, must return identical documents.
        """
        ...


class Blocked(Exception):
    """robots.txt disallowed the path, or the host returned 403.

    A block is an answer and the answer is respected: the source is disabled
    and a manual-inbox item is opened. Never retried from another address.
    """


class ParseError(Exception):
    """Fetched fine, normalize failed.

    Raw bytes are already stored, so the fix is a parser change plus a replay
    — not a re-crawl.
    """
