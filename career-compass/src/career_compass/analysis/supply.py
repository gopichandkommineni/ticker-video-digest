"""How much do I have of a skill?

    supply(S) = 100 × sat(0.35·rating + 0.50·evidence + 0.15·recency)

The decomposition is the point (ADR-0008). A scalar "I'm a 4 at this" cannot
distinguish "I don't know this" from "I know this and cannot prove it" — and
those two need completely different prep items.
"""

from __future__ import annotations

from career_compass.config import ScoringConfig
from career_compass.models import ProfileClaim


def rating_component(claim: ProfileClaim, cfg: ScoringConfig) -> float:
    """Self-rating, CAPPED at `unevidenced_rating_cap` with no evidence.

    An interview does not test what you know, it tests what you can
    demonstrate. Unevidenced confidence is not supply; it is optimism.
    """
    raise NotImplementedError


def evidence_component(claim: ProfileClaim, cfg: ScoringConfig) -> float:
    """Saturating sum over evidence, weighted by kind.

    A shipped system you owned (1.0) beats a design doc (0.9) beats a merged
    PR (0.5) beats a completed course (0.2) — an ordering that is a claim
    about what survives scrutiny. Entries with a concrete `impact_metric` get
    1.3×, because numbers are what survive an interview.
    """
    raise NotImplementedError


def recency_component(claim: ProfileClaim, cfg: ScoringConfig, now_year: int) -> float:
    """0.5 ** (years_since_last_used / 4). Skills decay."""
    raise NotImplementedError


def compute_supply(cfg: ScoringConfig, now_year: int) -> dict[str, float]:
    raise NotImplementedError


def unevidenced_claims() -> list[str]:
    """Claims rated >= 4 with zero evidence rows.

    The most useful single output of the supply side, and the reason it is
    worth building before any company is ingested (roadmap M1). These are not
    skill gaps — they are legibility gaps, and the fix is to write, not to
    build.
    """
    raise NotImplementedError
