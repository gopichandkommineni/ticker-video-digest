"""How much does a company want a skill, right now?

    demand(C,S) = branch_weight × Σ role × level × source × weight × decay

then normalized 0-100 within the company, so a company with a verbose blog is
comparable to one with a terse one. See docs/05-gap-scoring.md.
"""

from __future__ import annotations

from datetime import datetime

from career_compass.config import ScoringConfig


def decay(published_at: datetime, now: datetime, half_life_days: int) -> float:
    """0.5 ** (age_days / half_life_days).

    Exponential rather than a cutoff window: a cliff makes scores jump
    discontinuously as documents cross it, and throws away slow-moving
    architectural signal entirely (ADR-0009).
    """
    raise NotImplementedError


def distinct_source_multiplier(count: int, cfg: ScoringConfig) -> float:
    """Halve a single-source theme until something corroborates it.

    The single most important correction in the model. Without it, whoever
    writes the longest blog post defines the industry.
    """
    raise NotImplementedError


def compute_demand(company_slug: str, cfg: ScoringConfig, now: datetime) -> dict[str, float]:
    """All skills for one company. Writes company_skill_demand.

    Recomputed wholesale each run — the table is small, and full recompute is
    simpler and far less bug-prone than incremental.
    """
    raise NotImplementedError


def compute_trend(company_slug: str, cfg: ScoringConfig, now: datetime) -> dict[str, float]:
    """Current window vs. previous.

    Often more actionable than the level: a skill rising 20 → 45 matters more
    than one flat at 60.
    """
    raise NotImplementedError
