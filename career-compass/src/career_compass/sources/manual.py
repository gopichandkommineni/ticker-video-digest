"""The manual inbox — a first-class adapter, not an escape hatch.

Much of the best career signal is not automatable: postings behind a login,
what someone inside the company says over coffee, a talk with no transcript,
my own considered read of a posting. Systems that treat these as exceptions
make them second-class, and the highest-value data ends up in a notes app
(ADR-0006).

So manual input satisfies the same protocol as everything else and flows
through the identical path: raw store → normalize → extract → score. It
differs in `source.adapter` and in nothing else.
"""

from __future__ import annotations

from typing import Any, Iterator

from career_compass.models import NormalizedDocument, RawPayload, SourceKind


class ManualInboxAdapter:
    name = "manual.inbox"
    kind = SourceKind.MANUAL

    def validate(self, config: dict[str, Any]) -> None:
        """Requires `path` (default `manual/inbox`)."""
        raise NotImplementedError

    def fetch(self, config: dict[str, Any], ctx: Any) -> Iterator[RawPayload]:
        """Read files from the inbox. Touches disk, never the network.

        Files move to `manual/processed/<date>/` after a successful run.
        Content addressing means re-dropping an identical file is a harmless
        no-op, so there is no need to be careful about it.
        """
        raise NotImplementedError

    def normalize(self, raw: RawPayload) -> Iterator[NormalizedDocument]:
        """Parse YAML front-matter + markdown body.

        `company` and `kind` are required — there is no source config to infer
        them from — and a missing one fails loudly rather than guessing.
        `confidence` maps to a weight so a secondhand rumor scores below a
        copied posting without being excluded.
        """
        raise NotImplementedError
