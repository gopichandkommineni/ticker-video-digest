"""Eightfold-backed career sites.

Believed to back jobs.netflix.com — unverified, like every endpoint in
config/sources.yaml, and it stays excluded from analysis until a human
confirms real data came back (ADR-0004).
"""

from __future__ import annotations

from typing import Any, Iterator

from career_compass.models import NormalizedDocument, RawPayload, SourceKind


class EightfoldAdapter:
    name = "ats.eightfold"
    kind = SourceKind.JOBS

    def validate(self, config: dict[str, Any]) -> None:
        """Requires `host`."""
        raise NotImplementedError

    def fetch(self, config: dict[str, Any], ctx: Any) -> Iterator[RawPayload]:
        raise NotImplementedError

    def normalize(self, raw: RawPayload) -> Iterator[NormalizedDocument]:
        raise NotImplementedError
