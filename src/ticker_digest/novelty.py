"""Is any of this actually new?

Most YouTube commentary about a stock repeats the same bull case week after
week. The point of a digest is the delta: what did this batch of videos say
that earlier batches didn't?

Two stages, cheap first:

1. **Deterministic.** Normalise each claim to a token set, fingerprint it, and
   compare it against every claim already stored for the ticker. An exact
   fingerprint match or a Jaccard similarity above the threshold is a
   restatement — marked ``known`` for free, no model call.
2. **LLM.** Whatever survives goes to Claude *with* the known claims as
   context, which decides between ``new`` (nobody has said this), ``developing``
   (an update to something tracked — new number, new date, new detail) and
   ``known`` (a paraphrase the token overlap missed).

With no stored history everything is ``new``, and stage 2 is skipped entirely.
"""
from __future__ import annotations

import hashlib
import logging
import re
from typing import Any

import anthropic
from pydantic import BaseModel, Field

from core.config import CLAIM_SIMILARITY_THRESHOLD, EXTRACTION_MODEL
from core.models import Claim, ClaimKind, Novelty, VideoInsights

log = logging.getLogger(__name__)

_TOKEN_RE = re.compile(r"[a-z0-9]+")

# Words that carry no distinguishing signal in a one-line stock claim. Kept
# short on purpose — over-stripping makes unrelated claims look identical.
_STOPWORDS = frozenset(
    """
    a an the and or but if of for to in on at by with from as is are was were be been
    being it its this that these those they them their he she his her we our you your
    will would can could should may might must do does did has have had not no
    about into over under than then there here so such very more most much many
    company stock shares share price
    """.split()
)

# The number of known claims shown to the model. Enough context to spot a
# paraphrase, bounded so the prompt can't grow without limit.
_MAX_KNOWN_IN_PROMPT = 60


class _Classification(BaseModel):
    index: int = Field(description="Index of the claim being classified.")
    novelty: Novelty
    reasoning: str = Field(description="One sentence on why.")
    related_claim: str | None = Field(
        default=None,
        description="The known claim this updates or repeats, if any.",
    )


class _NoveltyBatch(BaseModel):
    classifications: list[_Classification]


def tokenise(text: str) -> set[str]:
    """Normalised, stopword-free token set for *text*."""
    return {t for t in _TOKEN_RE.findall(text.lower()) if t not in _STOPWORDS}


def fingerprint(kind: str, text: str) -> str:
    """Stable id for a claim: its kind plus its sorted token set.

    Two videos wording the same fact differently only collide here when the
    words genuinely match; near-misses are caught by :func:`similarity`.
    """
    tokens = sorted(tokenise(text))
    digest = hashlib.sha1(f"{kind}:{' '.join(tokens)}".encode()).hexdigest()
    return digest[:16]


def similarity(a: set[str], b: set[str]) -> float:
    """Jaccard similarity between two token sets (0..1)."""
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def claims_from_insights(ticker: str, insights: list[VideoInsights]) -> list[Claim]:
    """Flatten per-video extractions into one list of tracked claims.

    Duplicates *within* the batch merge rather than collapse: three videos
    repeating one contract win produce one claim carrying three citations. The
    count is the point — it is what lets the thread say "four of five sources".

    ``text`` keeps the wording from the first video to make the claim. Videos
    are analysed in reliability order, so first-wins means best-source-wins;
    this function depends on that order and would give a worse paraphrase
    without it.
    """
    kinds: list[tuple[ClaimKind, str]] = [
        ("catalyst", "catalysts"),
        ("red_flag", "red_flags"),
        ("upcoming_event", "upcoming_events"),
    ]

    claims: dict[str, Claim] = {}
    for insight in insights:
        for kind, attribute in kinds:
            for citation in getattr(insight, attribute):
                text = citation.quote_paraphrase.strip()
                if not text:
                    continue
                fp = fingerprint(kind, text)
                existing = claims.get(fp)
                if existing is None:
                    claims[fp] = Claim(
                        ticker=ticker.upper(),
                        kind=kind,
                        text=text,
                        citations=[citation],
                        fingerprint=fp,
                    )
                elif citation not in existing.citations:
                    existing.citations.append(citation)
    return list(claims.values())


# Lead with what's new, then what moved, then what several people newly agreed
# on, then the rest. Ordering the thread's input is a decision the code makes,
# not the model.
_NOVELTY_RANK: dict[str, int] = {"new": 0, "developing": 1, "known": 3}


def rank_claims(claims: list[Claim]) -> list[Claim]:
    """Order claims by how much they deserve the reader's attention.

    Newest first; within a novelty band, the claim more sources made wins. A
    ``known`` claim that a new channel just repeated ranks above a plain
    ``known`` one — the claim is old, but the agreement isn't.
    """

    def key(claim: Claim) -> tuple[int, int]:
        rank = _NOVELTY_RANK.get(claim.novelty, 3)
        if claim.novelty == "known" and claim.newly_corroborated:
            rank = 2
        return (rank, -claim.source_count)

    return sorted(claims, key=key)


def partition(
    claims: list[Claim], known: list[Claim]
) -> tuple[list[Claim], list[Claim]]:
    """Split *claims* into ``(restatements, candidates)`` without a model call.

    Restatements are already marked ``known``; candidates still need judging.
    """
    known_fingerprints = {c.fingerprint for c in known}
    known_tokens = [(c, tokenise(c.text)) for c in known]

    restatements: list[Claim] = []
    candidates: list[Claim] = []

    for claim in claims:
        if claim.fingerprint in known_fingerprints:
            match = next(
                (c for c in known if c.fingerprint == claim.fingerprint), None
            )
            restatements.append(
                claim.model_copy(
                    update={
                        "novelty": "known",
                        "novelty_reasoning": "Identical to a claim already tracked.",
                        "related_claim": match.text if match else None,
                    }
                )
            )
            continue

        tokens = tokenise(claim.text)
        best_claim, best_score = None, 0.0
        for candidate, candidate_tokens in known_tokens:
            score = similarity(tokens, candidate_tokens)
            if score > best_score:
                best_claim, best_score = candidate, score

        if best_score >= CLAIM_SIMILARITY_THRESHOLD and best_claim is not None:
            restatements.append(
                claim.model_copy(
                    update={
                        "novelty": "known",
                        "novelty_reasoning": (
                            f"Near-duplicate of a tracked claim "
                            f"(similarity {best_score:.2f})."
                        ),
                        "related_claim": best_claim.text,
                    }
                )
            )
        else:
            candidates.append(claim)

    return restatements, candidates


def _extract_tool_input(response: Any, tool_name: str) -> dict[str, Any]:
    for block in response.content:
        if block.type == "tool_use" and block.name == tool_name:
            return block.input  # type: ignore[return-value]
    raise ValueError(f"No {tool_name!r} tool_use block in response")


def classify_novelty(
    ticker: str,
    company_name: str,
    candidates: list[Claim],
    known: list[Claim],
) -> list[Claim]:
    """Ask Claude which surviving candidates are genuinely new.

    Returns *candidates* with novelty filled in. Candidates the model fails to
    classify keep their default (``new``) — under-reporting news is worse than
    over-reporting it, and the citation is always there to check.
    """
    if not candidates:
        return []
    if not known:
        log.info("No stored history for %s — all %d claims are new", ticker, len(candidates))
        return [
            claim.model_copy(
                update={
                    "novelty": "new",
                    "novelty_reasoning": "First run for this ticker; nothing to compare against.",
                }
            )
            for claim in candidates
        ]

    client = anthropic.Anthropic()

    system = [
        {
            "type": "text",
            "text": (
                "You decide whether claims made about a stock in new YouTube videos "
                "are actually news, given claims already on record.\n\n"
                "Classify each numbered claim as exactly one of:\n"
                "- new: no claim on record covers this. A genuinely new development, "
                "number, contract, product, risk or event.\n"
                "- developing: a claim on record covers the same subject, but this "
                "adds something — a firmer date, a revised figure, a confirmation.\n"
                "- known: a restatement of something on record, in different words.\n\n"
                "Rules:\n"
                "- Judge the substance, not the wording. Two different sentences "
                "about the same contract award are the same claim.\n"
                "- A recurring thesis ('they will dominate this market') is 'known' "
                "unless the video attaches a new fact to it.\n"
                "- When genuinely unsure between new and developing, choose developing.\n"
                "- Set related_claim to the on-record claim you matched against, "
                "verbatim, for 'developing' and 'known'. Leave it null for 'new'.\n"
                "- Return exactly one classification per claim index.\n\n"
                "Call the classify_claims tool."
            ),
            "cache_control": {"type": "ephemeral"},
        }
    ]

    tools = [
        {
            "name": "classify_claims",
            "description": "Report a novelty classification for every claim.",
            "input_schema": _NoveltyBatch.model_json_schema(),
        }
    ]

    known_lines = "\n".join(
        f"- [{c.kind}] {c.text}" for c in known[:_MAX_KNOWN_IN_PROMPT]
    )
    new_lines = "\n".join(
        f"{i}. [{c.kind}] {c.text}" for i, c in enumerate(candidates)
    )
    user_msg = (
        f"Ticker: {ticker} ({company_name})\n\n"
        f"Claims already on record ({len(known)} total, showing "
        f"{min(len(known), _MAX_KNOWN_IN_PROMPT)}):\n{known_lines}\n\n"
        f"Claims from the new videos, to classify:\n{new_lines}"
    )

    response = client.messages.create(
        model=EXTRACTION_MODEL,
        max_tokens=4096,
        system=system,  # type: ignore[arg-type]
        messages=[{"role": "user", "content": user_msg}],
        tools=tools,  # type: ignore[arg-type]
        tool_choice={"type": "tool", "name": "classify_claims"},
    )

    batch = _NoveltyBatch.model_validate(
        _extract_tool_input(response, "classify_claims")
    )
    by_index = {c.index: c for c in batch.classifications}

    classified: list[Claim] = []
    for index, claim in enumerate(candidates):
        result = by_index.get(index)
        if result is None:
            log.warning("No classification returned for claim %d — treating as new", index)
            classified.append(claim)
            continue
        classified.append(
            claim.model_copy(
                update={
                    "novelty": result.novelty,
                    "novelty_reasoning": result.reasoning,
                    "related_claim": result.related_claim,
                }
            )
        )
    return classified


def assess(
    ticker: str,
    company_name: str,
    claims: list[Claim],
    known: list[Claim],
) -> list[Claim]:
    """Full novelty pass: deterministic filter, then the model on what's left.

    Order is preserved so the caller can still show catalysts before red flags.
    """
    restatements, candidates = partition(claims, known)
    log.info(
        "%s: %d claims — %d matched on record deterministically, %d sent for judging",
        ticker,
        len(claims),
        len(restatements),
        len(candidates),
    )
    judged = classify_novelty(ticker, company_name, candidates, known)

    by_fingerprint = {c.fingerprint: c for c in restatements + judged}
    return [by_fingerprint.get(c.fingerprint, c) for c in claims]


__all__ = [
    "assess",
    "claims_from_insights",
    "classify_novelty",
    "fingerprint",
    "partition",
    "rank_claims",
    "similarity",
    "tokenise",
]
