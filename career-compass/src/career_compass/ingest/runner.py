"""The ingest job: select due sources, fetch, store, record."""

from __future__ import annotations

from career_compass.config import SourceConfig


def select_due_sources(now_iso: str) -> list[SourceConfig]:
    """Sources whose refresh_interval has elapsed.

    Staleness drives work, not cron. The scheduler is a heartbeat that asks
    "what is due?", which is why adding a source never touches a workflow file
    (ADR-0010).
    """
    raise NotImplementedError


def ingest_source(source: SourceConfig) -> dict[str, object]:
    """Fetch and store one source. Never raises.

    Failure is per-source and always isolated: one 500 from one endpoint marks
    that source failed in the ledger and the run continues. A career tool that
    goes dark because one careers page changed its markup is worse than
    useless.

    Returns an outcome dict for the run ledger — one of ok / not_modified /
    empty / http_error / parse_error / blocked. Three consecutive non-ok runs
    auto-disable the source and pin an annotation on the company, so it
    surfaces in the next brief. Silent decay is what actually kills tools like
    this.
    """
    raise NotImplementedError
