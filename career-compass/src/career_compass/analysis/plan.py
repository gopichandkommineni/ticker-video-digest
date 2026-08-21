"""Turning gaps into things to actually do this month."""

from __future__ import annotations

from career_compass.models import Gap


def generate_prep_items(gaps: list[Gap], limit: int) -> list[dict]:
    """Target the WEAKEST COMPONENT of supply, not the skill in general.

        high rating + no evidence  → write / talk   (make existing work legible)
        low rating + closable      → build          (a project forcing the constraint)
        stale (last used > 4y)     → build + write  (refresh and re-evidence)
        domain gap, low closability→ read + talk_to (vocabulary and a person inside)

    Each item keeps its gap_id so "why is this on my list?" always has an
    answer.
    """
    raise NotImplementedError


def cross_company_themes(min_companies: int = 3) -> list[dict]:
    """Skills in demand at several targets at once.

    Industry-level signal no single company's data shows — and the highest
    ROI prep, since it pays off wherever I land (roadmap M7).
    """
    raise NotImplementedError
