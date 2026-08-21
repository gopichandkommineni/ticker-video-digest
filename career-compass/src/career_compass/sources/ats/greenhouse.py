"""Greenhouse public job board.

Build this one first (roadmap M4): the best-documented public board API of the
six, so the shape of `JobFields` gets validated against the easiest case
before the awkward ones.
"""

from __future__ import annotations

from typing import Any, Iterator

from career_compass.models import NormalizedDocument, RawPayload, SourceKind


class GreenhouseAdapter:
    name = "ats.greenhouse"
    kind = SourceKind.JOBS

    def validate(self, config: dict[str, Any]) -> None:
        """Requires `board` (the org's board token)."""
        raise NotImplementedError

    def fetch(self, config: dict[str, Any], ctx: Any) -> Iterator[RawPayload]:
        """Fetch the board listing, then each posting's full content.

        The listing alone lacks the requirements text, which is the entire
        point — a title tells you nothing about the hiring bar.
        """
        raise NotImplementedError

    def normalize(self, raw: RawPayload) -> Iterator[NormalizedDocument]:
        """Map to NormalizedDocument with JobFields populated.

        `external_id` comes from the posting id, which is what lets a changed
        JD be linked to its previous version via `supersedes_document_id`
        instead of appearing as a new role.
        """
        raise NotImplementedError
