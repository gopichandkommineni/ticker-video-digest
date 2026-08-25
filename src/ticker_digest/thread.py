"""Turn judged claims into the stored deliverable: a thread of insights.

A thread is a short ordered sequence of posts, newest-and-most-important
first, each one carrying the timestamped citations it came from. It reads like
something a person would post after watching every video, which is exactly
what it replaces.

The novelty verdict drives the ordering: genuinely new claims lead, updates to
tracked claims follow, and restatements are context at the end (or omitted).
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone

from pydantic import BaseModel, Field

from core.config import SYNTHESIS_MODEL
from core.models import (
    Citation,
    Claim,
    InsightThread,
    Novelty,
    ScoredVideo,
    Sentiment,
    SourceKind,
    ThreadPost,
    VideoInsights,
)
from ticker_digest.llm import StructuredCall, ask

log = logging.getLogger(__name__)

_MAX_POSTS = 8


class _DraftPost(BaseModel):
    headline: str = Field(description="One line, under 100 characters.")
    body: str = Field(description="2-4 sentences. Plain language, no hype.")
    novelty: Novelty
    citations: list[Citation] = Field(default_factory=list)


class _ThreadDraft(BaseModel):
    """The fields Claude fills in. Ids, counts and timestamps are set here."""

    headline: str = Field(description="The thread's opening line.")
    overall_sentiment: Sentiment
    posts: list[_DraftPost]


def _thread_id(ticker: str, generated_at: datetime, source_label: str) -> str:
    seed = f"{ticker.upper()}|{generated_at.isoformat()}|{source_label}"
    return hashlib.sha1(seed.encode()).hexdigest()[:12]


def _valid_citations(
    citations: list[Citation], allowed_video_ids: set[str]
) -> list[Citation]:
    """Drop citations pointing at videos this run never read.

    A citation the reader can't click through to is worse than no citation, so
    invented video ids are removed rather than shown.
    """
    kept = []
    for citation in citations:
        if citation.video_id in allowed_video_ids:
            kept.append(citation)
        else:
            log.warning("Dropping citation to unknown video %s", citation.video_id)
    return kept


def build_thread(
    ticker: str,
    company_name: str,
    claims: list[Claim],
    insights: list[VideoInsights],
    videos: list[ScoredVideo],
    source_kind: SourceKind = "ticker_search",
    source_label: str = "",
    generated_at: datetime | None = None,
) -> InsightThread:
    """Synthesise the thread. One call to the stronger model, at the end."""
    generated_at = generated_at or datetime.now(timezone.utc)
    source_label = source_label or ticker.upper()
    allowed_video_ids = {sv.metadata.video_id for sv in videos}

    system = (
        "You write short, factual threads summarising what stock commentators "
        "said on YouTube about one company.\n\n"
        "Each claim you are given has already been judged for novelty:\n"
        "- new: nothing on record covered this before\n"
        "- developing: an update to something already tracked\n"
        "- known: a restatement of an existing claim\n\n"
        "Each claim also carries source_count (how many of this run's videos "
        "made it) and newly_corroborated (an old claim that a channel which "
        "had never said it before just repeated).\n\n"
        "Rules:\n"
        f"- At most {_MAX_POSTS} posts. Lead with the 'new' claims, then "
        "'developing'. Only include a 'known' claim when it is needed as "
        "context for a new one, or when several sources newly agreed on it.\n"
        "- If nothing is new, say so plainly in the first post. Do not "
        "manufacture significance.\n"
        "- A newly_corroborated claim earns a post even though it isn't new. "
        "Say plainly that the claim is old and the agreement is what changed.\n"
        "- Say how many sources made a claim when it is more than one. "
        "Weight agreement between independent commentators over a single "
        "confident one.\n"
        "- The claims arrive in priority order. Keep that order unless a post "
        "genuinely needs an earlier one as context.\n"
        "- One idea per post. Never merge an unrelated catalyst and red flag.\n"
        "- Every post carries the citations for the claims it covers, copied "
        "verbatim from the input. Never invent a video_id or a timestamp.\n"
        "- Report what commentators said, attributing it to them — not as "
        "your own view of the company. No price targets, no recommendations.\n"
        "- Note disagreement between sources explicitly.\n"
        "- overall_sentiment is the net view across the videos, not yours."
    )

    claims_payload = json.dumps(
        [
            {
                "kind": claim.kind,
                "text": claim.text,
                "novelty": claim.novelty,
                "novelty_reasoning": claim.novelty_reasoning,
                "related_claim": claim.related_claim,
                "source_count": claim.source_count,
                "newly_corroborated": claim.newly_corroborated,
                "citations": [c.model_dump(mode="json") for c in claim.citations],
            }
            for claim in claims
        ],
        indent=2,
    )
    sources_payload = json.dumps(
        [
            {
                "video_id": sv.metadata.video_id,
                "title": sv.metadata.title,
                "channel": sv.metadata.channel_title,
                "published_at": sv.metadata.published_at.isoformat(),
                "reliability_score": sv.reliability_score,
            }
            for sv in videos
        ],
        indent=2,
    )
    summaries_payload = json.dumps(
        [
            {
                "video_id": ins.video_id,
                "sentiment": ins.overall_sentiment,
                "summary": ins.summary,
            }
            for ins in insights
        ],
        indent=2,
    )

    new_count = sum(1 for c in claims if c.novelty == "new")
    corroborated = sum(1 for c in claims if c.newly_corroborated)
    user_msg = (
        f"Ticker: {ticker} ({company_name})\n"
        f"Source: {source_label} ({source_kind})\n"
        f"Videos analysed: {len(videos)} — {new_count} of {len(claims)} claims are new, "
        f"{corroborated} newly corroborated\n\n"
        f"Videos:\n{sources_payload}\n\n"
        f"Per-video summaries:\n{summaries_payload}\n\n"
        f"Judged claims:\n{claims_payload}"
    )

    draft = ask(
        StructuredCall(
            system=system,
            user=user_msg,
            model=SYNTHESIS_MODEL,
            response_model=_ThreadDraft,
            tool_name="report_thread",
            tool_description="Report the finished insight thread.",
            max_tokens=8192,
        )
    )

    posts = [
        ThreadPost(
            position=position,
            headline=post.headline,
            body=post.body,
            novelty=post.novelty,
            citations=_valid_citations(post.citations, allowed_video_ids),
        )
        for position, post in enumerate(draft.posts[:_MAX_POSTS], start=1)
    ]

    thread = InsightThread(
        thread_id=_thread_id(ticker, generated_at, source_label),
        ticker=ticker.upper(),
        company_name=company_name,
        source_kind=source_kind,
        source_label=source_label,
        generated_at=generated_at,
        video_count=len(videos),
        new_claim_count=new_count,
        overall_sentiment=draft.overall_sentiment,
        headline=draft.headline,
        posts=posts,
    )
    log.info(
        "Built thread %s for %s: %d posts, %d new claims",
        thread.thread_id,
        ticker,
        len(posts),
        new_count,
    )
    return thread
