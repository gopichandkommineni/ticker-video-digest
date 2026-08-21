"""Replayable normalization over the raw store."""

from __future__ import annotations


def normalize_all(only_unnormalized: bool = True) -> dict[str, int]:
    """Run each raw_document through its adapter's `normalize`.

    With `only_unnormalized=False` this re-derives every document from stored
    bytes — the operation a parser fix needs, and the one the whole raw/derived
    split exists to make cheap.
    """
    raise NotImplementedError


def apply_filters(doc, filters: dict) -> bool:
    """Title include/exclude and level floor from config/sources.yaml.

    Applied at normalize rather than fetch so the filter can be changed and
    replayed without re-crawling.
    """
    raise NotImplementedError


def link_supersession(doc) -> int | None:
    """Find the previous version of this document, if any.

    Matches on (company, kind, external_id). An edited JD becomes a NEW row
    pointing back at the old one, so requirement drift stays queryable —
    "they added 'distributed systems design' to the requirements in March" is
    among the strongest signals this system can surface.
    """
    raise NotImplementedError


def infer_closures(source_id: int) -> list[int]:
    """Mark postings absent from two consecutive successful runs as closed.

    Two runs, not one: a single flaky fetch must never close a hiring req.

    Nothing ever tells us a posting closed — closure is inferred from absence
    in repeated snapshots. Time-to-close is itself signal: reqs that close in
    nine days are the roles they are desperate for.
    """
    raise NotImplementedError
