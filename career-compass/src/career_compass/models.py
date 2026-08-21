"""Core domain types.

Every boundary in this system is a pydantic model, so a malformed payload
fails at the boundary rather than three stages later. These types are the
vocabulary the rest of the code speaks; see docs/02-data-model.md.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, HttpUrl


class SourceKind(StrEnum):
    JOBS = "jobs"
    BLOG = "blog"
    TALK = "talk"
    OSS = "oss"
    NEWS = "news"
    MANUAL = "manual"


class DocumentKind(StrEnum):
    JOB_POSTING = "job_posting"
    BLOG_POST = "blog_post"
    TALK = "talk"
    REPO = "repo"
    NOTE = "note"


class MentionRole(StrEnum):
    """Why a skill appeared in a document.

    The distinction is load-bearing: "we run Cassandra" and "you must have
    designed a Cassandra-scale store" are different claims, and only the
    second is a hiring bar. See docs/05-gap-scoring.md.
    """

    REQUIREMENT = "requirement"
    NICE_TO_HAVE = "nice_to_have"
    DESCRIBED_SYSTEM = "described_system"
    ASPIRATION = "aspiration"


class Level(StrEnum):
    JUNIOR = "junior"
    MID = "mid"
    SENIOR = "senior"
    STAFF = "staff"
    PRINCIPAL = "principal"
    UNKNOWN = "unknown"


class EvidenceKind(StrEnum):
    SYSTEM = "system"
    DESIGN_DOC = "design_doc"
    INCIDENT = "incident"
    WRITING = "writing"
    TALK = "talk"
    PR = "pr"
    COURSE = "course"


class RawPayload(BaseModel):
    """Bytes as fetched, before anything interprets them.

    Adapters yield these from `fetch`. The ingest job hashes the content,
    writes it to `data/raw/`, and inserts a `raw_document` row. Adapters never
    touch storage themselves (ADR-0002).
    """

    content: bytes
    url: str | None = None
    content_type: str = "application/octet-stream"
    fetched_at: datetime
    http_status: int | None = None
    meta: dict[str, Any] = Field(default_factory=dict)


class NormalizedDocument(BaseModel):
    """The common shape every source normalizes into.

    Produced by a *pure* function of RawPayload — no network, no clock, no
    randomness — which is what makes replay over the whole raw store safe.
    """

    company_slug: str
    kind: DocumentKind
    external_id: str | None = None
    title: str
    url: HttpUrl | None = None
    author: str | None = None
    published_at: datetime | None = None
    body_text: str
    lang: str = "en"
    # Populated only for DocumentKind.JOB_POSTING.
    job: JobFields | None = None
    meta: dict[str, Any] = Field(default_factory=dict)


class JobFields(BaseModel):
    req_id: str | None = None
    team: str | None = None
    location: str | None = None
    remote_ok: bool | None = None
    level_hint: Level = Level.UNKNOWN
    employment_type: str | None = None
    posted_at: datetime | None = None


class SkillMention(BaseModel):
    """One skill, found in one document, with the quote that justifies it.

    `context_quote` is non-optional by design: every number this system
    produces must decompose back to text a human can read.
    """

    skill_slug: str
    role: MentionRole
    weight: float = Field(ge=0.0, le=1.0)
    context_quote: str


class UnmappedPhrase(BaseModel):
    """A phrase the extractor could not place in the taxonomy.

    The backlog these form is the mechanism by which the vocabulary tracks the
    industry instead of freezing (ADR-0005). Never auto-promoted.
    """

    phrase: str
    context_quote: str
    suggested_parent: str | None = None


class DocumentInsights(BaseModel):
    """Output of the per-document extraction pass."""

    summary: str
    themes: list[str]
    named_systems: list[str] = Field(default_factory=list)
    level_signal: Level = Level.UNKNOWN
    mentions: list[SkillMention]
    unmapped: list[UnmappedPhrase] = Field(default_factory=list)


class CompanyProfile(BaseModel):
    """Output of the cross-document synthesis pass, per company."""

    company_slug: str
    recurring_themes: list[ThemeSummary]
    design_vocabulary: list[str]
    open_problems: list[str]
    window_days: int


class ThemeSummary(BaseModel):
    theme: str
    distinct_source_count: int
    document_ids: list[int]
    representative_quote: str


class ProfileClaim(BaseModel):
    skill_slug: str
    self_rating: int = Field(ge=1, le=5)
    last_used_year: int | None = None
    notes: str | None = None
    evidence: list[Evidence] = Field(default_factory=list)


class Evidence(BaseModel):
    kind: EvidenceKind
    title: str
    description: str | None = None
    impact_metric: str | None = None
    url: HttpUrl | None = None
    date: date | None = None
    confidence: str = "medium"


class Gap(BaseModel):
    company_slug: str
    skill_slug: str
    demand_score: float
    supply_score: float
    gap_score: float
    leverage: float
    rationale: GapRationale


class GapRationale(BaseModel):
    """Why this row exists, in enough detail to argue with.

    A career decision made on an unexplainable number is worse than no number
    (docs/05-gap-scoring.md).
    """

    top_document_ids: list[int]
    top_quotes: list[str]
    supply_explanation: str
    overrides_applied: list[str] = Field(default_factory=list)
