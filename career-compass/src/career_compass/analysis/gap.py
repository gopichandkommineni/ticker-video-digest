"""Gap and leverage.

    gap      = demand × (1 − supply/100)     "how much this hurts"
    leverage = gap × closability             "what to actually do next"

That distinction is the point of the whole system. A gap you cannot close in
the time you have is not a task, it is a fact about the world — and the honest
advice for a large domain gap is "get adjacent to it or lead with something
else", not a study plan that cannot work.
"""

from __future__ import annotations

from career_compass.config import ScoringConfig
from career_compass.models import Gap


def closability(skill_slug: str, cfg: ScoringConfig) -> float:
    """Branch prior, overridable per skill."""
    raise NotImplementedError


def compute_gaps(company_slug: str, cfg: ScoringConfig) -> list[Gap]:
    """Every gap must carry its rationale.

    `GapRationale` is non-negotiable: a career decision made on an
    unexplainable number is worse than no number.
    """
    raise NotImplementedError


def apply_overrides(gaps: list[Gap], overrides: dict) -> list[Gap]:
    """Adjust, never delete (ADR-0006).

    A suppressed row still exists and still appears under
    `--show-suppressed`, with its reason attached. A tool that lets me
    silently hide inconvenient findings converges on telling me what I want to
    hear, which is the one failure mode a career tool cannot have.
    """
    raise NotImplementedError
