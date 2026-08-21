"""ashby public job board adapter. Not yet implemented (roadmap M4)."""

from __future__ import annotations

from typing import Any, Iterator

from career_compass.models import NormalizedDocument, RawPayload, SourceKind


class AshbyAdapter:
    name = "ats.ashby"
    kind = SourceKind.JOBS

    def validate(self, config: dict[str, Any]) -> None:
        raise NotImplementedError

    def fetch(self, config: dict[str, Any], ctx: Any) -> Iterator[RawPayload]:
        raise NotImplementedError

    def normalize(self, raw: RawPayload) -> Iterator[NormalizedDocument]:
        raise NotImplementedError
