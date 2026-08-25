"""LLM analysis: extract_insights (per-video), synthesize_digest (cross-video).

Both go through :mod:`ticker_digest.llm`, so they work the same whether Claude
is reached through the API or through a locally installed Claude Code CLI.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from pydantic import BaseModel

from core.config import EXTRACTION_MODEL, MAX_TRANSCRIPT_CHARS, SYNTHESIS_MODEL
from core.models import (
    DigestReport,
    Sentiment,
    Transcript,
    VideoInsights,
    VideoMetadata,
)
from ticker_digest.llm import StructuredCall, ask

log = logging.getLogger(__name__)


class _DigestSynthesis(BaseModel):
    """Fields Claude fills in during cross-video synthesis.

    Omits ticker, video_count, generated_at, and video_insights — those are
    set programmatically in synthesize_digest, not by the model.
    """

    company_name: str
    top_catalysts: list[str]
    top_red_flags: list[str]
    upcoming_events: list[str]
    overall_sentiment: Sentiment
    synthesis: str


def extract_insights(transcript: Transcript, metadata: VideoMetadata) -> VideoInsights:
    formatted = "\n".join(
        f"[{int(seg.start_seconds)}s] {seg.text}" for seg in transcript.segments
    )
    if len(formatted) > MAX_TRANSCRIPT_CHARS:
        log.info(
            "Truncating transcript for %s: %d chars -> %d",
            metadata.video_id,
            len(formatted),
            MAX_TRANSCRIPT_CHARS,
        )
        formatted = formatted[:MAX_TRANSCRIPT_CHARS] + "\n[transcript truncated]"

    system = (
        "You are a financial analyst reviewing YouTube video transcripts about stocks.\n\n"
        "Rules:\n"
        "- Only report claims explicitly stated in the transcript. Do not speculate.\n"
        "- Every catalyst, red flag, and upcoming event MUST include a citation with the "
        "exact timestamp_seconds where the claim appears.\n"
        "- The video_id for every Citation must match the video_id in the user message.\n"
        "- Stay focused on the ticker/company. Ignore off-topic discussion.\n"
        "- quote_paraphrase should be a brief paraphrase of the words spoken at that timestamp.\n"
        "- overall_sentiment reflects the speaker's net view of the stock."
    )
    user = (
        f"Video ID: {metadata.video_id}\n"
        f"Title: {metadata.title}\n"
        f"Channel: {metadata.channel_title}\n\n"
        f"Transcript:\n{formatted}"
    )

    return ask(
        StructuredCall(
            system=system,
            user=user,
            model=EXTRACTION_MODEL,
            response_model=VideoInsights,
            tool_name="report_video_insights",
            tool_description="Report structured insights extracted from the video transcript.",
            max_tokens=4096,
        )
    )


def synthesize_digest(
    ticker: str, company_name: str, insights: list[VideoInsights]
) -> DigestReport:
    system = (
        f"You are a financial analyst synthesizing insights from multiple YouTube video "
        f"analyses about {ticker} ({company_name}).\n\n"
        "Rules:\n"
        "- Deduplicate themes: if multiple videos mention the same catalyst, merge them "
        "into one point ranked by the number of sources.\n"
        "- Rank top_catalysts, top_red_flags, and upcoming_events by source count.\n"
        "- Note disagreements between sources explicitly in the synthesis.\n"
        "- Report only what the videos discuss — no speculation.\n"
        "- synthesis should be 2-4 paragraphs summarizing the investment picture."
    )
    insights_json = json.dumps([ins.model_dump(mode="json") for ins in insights], indent=2)
    user = (
        f"Ticker: {ticker}\n"
        f"Company: {company_name}\n"
        f"Videos analyzed: {len(insights)}\n\n"
        f"Per-video insights:\n{insights_json}"
    )

    synth = ask(
        StructuredCall(
            system=system,
            user=user,
            model=SYNTHESIS_MODEL,
            response_model=_DigestSynthesis,
            tool_name="report_digest",
            tool_description="Report the synthesized digest across all analyzed videos.",
            max_tokens=8192,
        )
    )

    return DigestReport(
        ticker=ticker,
        company_name=synth.company_name,
        generated_at=datetime.now(timezone.utc),
        video_count=len(insights),
        top_catalysts=synth.top_catalysts,
        top_red_flags=synth.top_red_flags,
        upcoming_events=synth.upcoming_events,
        overall_sentiment=synth.overall_sentiment,
        synthesis=synth.synthesis,
        video_insights=insights,
    )
