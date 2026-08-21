"""The "what do I say in the room" one-pager.

The single most valuable output. Everything else exists to make this
trustworthy.
"""

from __future__ import annotations


def company_brief(company_slug: str) -> str:
    """Render a brief for one company.

    Sections:
      1. What they're building        — themes ranked by DISTINCT sources
      2. Their design vocabulary      — the words to use in the room
      3. Open roles                   — with time-to-close where known
      4. Requirement drift            — what changed in their JDs recently
      5. My matching stories          — from profile stories[], matched on slug
      6. My gaps, ranked by leverage  — with the quotes that caused them
      7. Pinned notes                 — VERBATIM. Never summarized (ADR-0006).

    Every claim links to document ids. If I cannot check it, I should not act
    on it.
    """
    raise NotImplementedError


def weekly_diff(days: int = 7) -> str:
    """What changed: new and closed postings, moving demand, new themes.

    The output I actually want to read on a Monday. If this stops being worth
    reading, the system is not earning its keep and should be cut down rather
    than propped up.
    """
    raise NotImplementedError
