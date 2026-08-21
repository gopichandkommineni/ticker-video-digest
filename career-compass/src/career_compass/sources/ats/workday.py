"""Workday-hosted job boards.

Workday boards are POST-based JSON search against a tenant + site path, with
offset pagination and a facet payload copied from the careers page's own
request. Awkward but stable, and widely used by large hardware and enterprise
companies.
"""

from __future__ import annotations

from typing import Any, Iterator

from career_compass.models import NormalizedDocument, RawPayload, SourceKind


class WorkdayAdapter:
    name = "ats.workday"
    kind = SourceKind.JOBS

    def validate(self, config: dict[str, Any]) -> None:
        """Requires `tenant` and `site`."""
        raise NotImplementedError

    def fetch(self, config: dict[str, Any], ctx: Any) -> Iterator[RawPayload]:
        """Paginate the search endpoint, then fetch each posting detail.

        Pagination must be bounded: a filter that fails open returns the
        company's entire global req list, which is both rude and useless.
        """
        raise NotImplementedError

    def normalize(self, raw: RawPayload) -> Iterator[NormalizedDocument]:
        raise NotImplementedError
