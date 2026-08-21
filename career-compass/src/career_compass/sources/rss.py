"""Atom/RSS adapter — the engineering-blog workhorse.

Deliberately the first adapter to build (roadmap M2): it exercises the whole
ingest path — conditional requests, content addressing, the run ledger — with
the simplest possible parsing.
"""

from __future__ import annotations

from typing import Any, Iterator

from career_compass.models import NormalizedDocument, RawPayload, SourceKind


class RssAdapter:
    name = "rss"
    kind = SourceKind.BLOG

    def validate(self, config: dict[str, Any]) -> None:
        """Requires `url`."""
        raise NotImplementedError

    def fetch(self, config: dict[str, Any], ctx: Any) -> Iterator[RawPayload]:
        """One payload: the feed document itself.

        Note it is the *feed* that is content-addressed, not each entry. An
        unchanged feed hashes identically and the whole fetch becomes a no-op.
        """
        raise NotImplementedError

    def normalize(self, raw: RawPayload) -> Iterator[NormalizedDocument]:
        """One NormalizedDocument per entry.

        Prefers full content over summary where the feed offers both — the
        extraction layer needs the body, and a truncated post produces
        confidently wrong themes. Strips markup to plain text.
        """
        raise NotImplementedError
