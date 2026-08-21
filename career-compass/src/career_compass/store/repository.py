"""Typed data access. The only module that writes SQL.

Grouped by the four zones in docs/02-data-model.md. The invariant worth
protecting: only the DERIVED zone is disposable, and deleting it plus a re-run
must reproduce identical state with zero network calls (ADR-0002). There is a
test for that.
"""

from __future__ import annotations

from career_compass.models import Gap, NormalizedDocument


class Repository:
    # ── provenance ────────────────────────────────────────────────────────
    def start_run(self, job_name: str) -> int: ...
    def finish_run(self, run_id: int, status: str, stats: dict) -> None: ...
    def sync_sources(self, sources: list) -> None:
        """Upsert from config, preserving runtime state (last_ok_at, failures)."""
        ...

    # ── canonical ─────────────────────────────────────────────────────────
    def insert_raw(self, source_id: int, content_hash: str, **kw) -> int | None:
        """INSERT OR IGNORE on content_hash. None means already seen."""
        ...

    def upsert_document(self, doc: NormalizedDocument, raw_id: int) -> int: ...
    def touch_last_seen(self, document_ids: list[int]) -> None:
        """Absence across runs is how closure is inferred; this records presence."""
        ...

    def sync_skills(self, taxonomy) -> None: ...
    def add_annotation(self, entity_type: str, entity_id: int, body: str, pinned: bool) -> int: ...
    def pinned_annotations(self, entity_type: str, entity_id: int) -> list[str]:
        """Returned VERBATIM to the brief. Never LLM-summarized (ADR-0006)."""
        ...

    # ── derived ───────────────────────────────────────────────────────────
    def insert_extraction(self, document_id: int, version: str, payload: dict, **kw) -> int: ...
    def replace_demand(self, company_id: int, rows: list[dict]) -> None: ...
    def replace_gaps(self, company_id: int, gaps: list[Gap]) -> None: ...

    # ── me ────────────────────────────────────────────────────────────────
    def sync_profile(self, claims: list) -> None:
        """Materialize profile/resume.yaml. The YAML is the source of truth;
        nothing ever writes back to it (ADR-0008)."""
        ...
