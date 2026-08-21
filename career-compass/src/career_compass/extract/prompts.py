"""Prompt construction.

The system prompt and the serialized taxonomy are identical across every call
in a pass, which makes them a large constant prefix — put prompt caching on
exactly that block. At a few thousand documents the caching is the difference
between a cheap re-extraction and a decision not to re-extract.
"""

from __future__ import annotations

from career_compass.config import Taxonomy

DOCUMENT_SYSTEM_PROMPT = """\
(Design phase — not written yet.)

Non-negotiable constraints for whatever goes here:

  * The model may ONLY emit skill slugs present in the supplied taxonomy.
    Anything it cannot place goes to `unmapped[]` with a quote and a suggested
    parent. It never invents a slug. This is what keeps the vocabulary stable
    enough for month-over-month comparison (ADR-0005).

  * Every mention carries a VERBATIM quote from the document. Every number
    this system produces must decompose back to text a human can read.

  * `role` must distinguish a hiring bar ("you must have designed...") from a
    description of what they run ("we use..."). Conflating them is the most
    likely way for demand scores to become quietly wrong.

  * Report `level_signal` from the posting's own language, not from the title.
    Titles are marketing; requirements are not.
"""

SYNTHESIS_SYSTEM_PROMPT = """\
(Design phase — not written yet.)

Ranks themes by DISTINCT SOURCE COUNT, never by mention count. A theme
appearing twelve times in one long blog post is one data point, not twelve —
the same correction the scoring layer applies, enforced here too so the
qualitative summary and the quantitative score cannot disagree.
"""


def build_taxonomy_block(taxonomy: Taxonomy) -> str:
    """Serialize slugs + aliases for the cached prompt prefix."""
    raise NotImplementedError


def build_document_prompt(document_text: str, kind: str) -> str:
    raise NotImplementedError
