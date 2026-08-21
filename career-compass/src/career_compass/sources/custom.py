"""In-house career boards, driven entirely by config.

The escape hatch for companies that built their own board. Config supplies the
URL, method, a JSON path to the posting list, and a field map — so an in-house
board is still not a new Python module.

If a company genuinely cannot be expressed this way, that is a signal worth
noticing: a new platform, probably relevant to more than one company. And if
the board is JS-gated behind bot protection, the answer is not a better
scraper — it is manual.inbox (docs/08-legal-and-etiquette.md).
"""

from __future__ import annotations

from typing import Any, Iterator

from career_compass.models import NormalizedDocument, RawPayload, SourceKind


class CustomCareersAdapter:
    name = "careers.custom"
    kind = SourceKind.JOBS

    def validate(self, config: dict[str, Any]) -> None:
        """Requires `url`, `json_path`, `field_map`; `method` defaults to GET."""
        raise NotImplementedError

    def fetch(self, config: dict[str, Any], ctx: Any) -> Iterator[RawPayload]:
        raise NotImplementedError

    def normalize(self, raw: RawPayload) -> Iterator[NormalizedDocument]:
        raise NotImplementedError
