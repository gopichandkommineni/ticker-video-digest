"""Running the two extraction passes."""

from __future__ import annotations

from career_compass.models import CompanyProfile, DocumentInsights


def alias_prepass(body_text: str) -> list[tuple[str, str]]:
    """Deterministic exact-alias matching, before any LLM call.

    Two purposes: it grounds the model by showing it what is definitely there,
    and it provides a non-LLM baseline. Large divergence between the pre-pass
    and the model's output is a signal that something is wrong with the
    prompt — worth alerting on rather than trusting.
    """
    raise NotImplementedError


def extract_document(document_id: int, *, extractor_version: str) -> DocumentInsights:
    """One document in, typed insights out.

    Skips documents that already have a row for this (extractor_version,
    schema_version) — extraction is the only stage that costs money, so
    idempotency here is a budget feature, not just a correctness one.

    Records input/output tokens and cost, so "what would a full
    re-extraction cost?" is a query rather than a guess.
    """
    raise NotImplementedError


def synthesize_company(company_slug: str, window_days: int) -> CompanyProfile:
    """Many document insights for one company in, one profile out."""
    raise NotImplementedError


def review_unmapped(days: int = 30) -> list[tuple[str, int, str | None]]:
    """Frequency-ranked backlog of phrases the extractor could not place.

    Powers `career taxonomy review`. The corpus proposes; a human disposes.
    This loop is how the vocabulary tracks the industry instead of freezing at
    whatever I knew when I built this — and it is also how the system tells me
    the industry moved (ADR-0005).
    """
    raise NotImplementedError
