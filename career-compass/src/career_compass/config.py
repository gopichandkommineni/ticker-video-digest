"""Loading and validating everything under config/ and taxonomy/.

Configuration is data; code is generic. No module in this package should
contain the string "netflix" (ADR-0004). This module is where that rule is
enforced in practice — everything company-shaped enters the system here.

Loaders fail loudly. A skill slug in resume.yaml that does not exist in the
taxonomy is a hard error at load time, not a silently dropped row at scoring
time.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel


class ConfigError(Exception):
    """A config file is unusable. Raised at load, never swallowed."""


class CompanyConfig(BaseModel):
    slug: str
    name: str
    priority: int
    status: str
    why: str
    domains: list[str] = []


class SourceConfig(BaseModel):
    company: str
    kind: str
    adapter: str
    config: dict[str, Any] = {}
    verified: bool = False
    refresh_interval_hours: int | None = None
    note: str | None = None
    reason_no_automation: str | None = None


class ScoringConfig(BaseModel):
    """Every constant in the scoring model. See config/scoring.yaml.

    Deliberately one flat object rather than constants scattered through the
    analysis package: if a score surprises me, I want one file to read.
    """

    extractor_version: str
    schema_version: int
    taxonomy_version: int
    branch_weights: dict[str, float]
    role_weights: dict[str, float]
    target_level: str
    level_weights: dict[str, float]
    source_weights: dict[str, float]
    half_life_days: dict[str, int]
    distinct_source_guard: dict[str, float]
    demand_window_days: int
    trend_window_days: int
    supply_weights: dict[str, float]
    unevidenced_rating_cap: float
    evidence_weights: dict[str, float]
    impact_metric_multiplier: float
    evidence_saturation_k: int
    skill_recency_half_life_years: int
    closability: dict[str, float]
    closability_overrides: dict[str, float] = {}
    report: dict[str, Any] = {}


class Taxonomy(BaseModel):
    """The controlled vocabulary, loaded and indexed for lookup.

    `by_slug` and `alias_index` are built once and reused by the extractor's
    deterministic pre-pass and by validation.
    """

    version: int
    by_slug: dict[str, dict[str, Any]]
    alias_index: dict[str, str]
    branch_of: dict[str, str]

    def resolve(self, phrase: str) -> str | None:
        """Case-insensitive alias lookup. None if the phrase is unmapped."""
        raise NotImplementedError

    def branch(self, slug: str) -> str:
        """Top-level branch for a skill slug, for branch-weight lookup."""
        raise NotImplementedError


def load_companies(path: Path) -> list[CompanyConfig]:
    raise NotImplementedError


def load_sources(path: Path, companies: list[CompanyConfig]) -> list[SourceConfig]:
    """Load sources, applying `defaults:` and validating company references.

    A source naming a company that does not exist is a ConfigError. So is an
    adapter name with no registered implementation — better to fail at load
    than to silently skip a source and report "not hiring".
    """
    raise NotImplementedError


def load_scoring(path: Path) -> ScoringConfig:
    raise NotImplementedError


def load_taxonomy(path: Path) -> Taxonomy:
    """Parse taxonomy/skills.yaml and build the lookup indexes.

    Raises ConfigError on duplicate slugs or on an alias claimed by two
    different skills — an ambiguous alias silently corrupts every score
    downstream.
    """
    raise NotImplementedError


def load_overrides(path: Path) -> dict[str, Any]:
    """Load config/overrides.yaml.

    Every entry must carry a `reason`; entries without one are rejected
    (ADR-0006). Overrides adjust, they never delete.
    """
    raise NotImplementedError
