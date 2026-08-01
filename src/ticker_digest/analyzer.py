"""LLM analysis pipeline: extract_insights (per-video), synthesize_digest (cross-video)."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

import anthropic
from pydantic import BaseModel, ValidationError

from core.models import (
    DigestReport,
    Sentiment,
    Transcript,
    VideoInsights,
    VideoMetadata,
)

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


def _extract_tool_input(response: Any, tool_name: str) -> dict[str, Any]:
    for block in response.content:
        if block.type == "tool_use" and block.name == tool_name:
            return block.input  # type: ignore[return-value]
    raise ValueError(f"No {tool_name!r} tool_use block in response")


def extract_insights(transcript: Transcript, metadata: VideoMetadata) -> VideoInsights:
    client = anthropic.Anthropic()

    formatted = "\n".join(
        f"[{int(seg.start_seconds)}s] {seg.text}" for seg in transcript.segments
    )

    system = [
        {
            "type": "text",
            "text": (
                "You are a financial analyst reviewing YouTube video transcripts about stocks.\n\n"
                "Rules:\n"
                "- Only report claims explicitly stated in the transcript. Do not speculate.\n"
                "- Every catalyst, red flag, and upcoming event MUST include a citation with the "
                "exact timestamp_seconds where the claim appears.\n"
                "- The video_id for every Citation must match the video_id in the user message.\n"
                "- Stay focused on the ticker/company. Ignore off-topic discussion.\n"
                "- quote_paraphrase should be a brief paraphrase of the words spoken at that timestamp.\n"
                "- overall_sentiment reflects the speaker's net view of the stock.\n\n"
                "Call the report_video_insights tool with your findings."
            ),
            "cache_control": {"type": "ephemeral"},
        }
    ]

    tools = [
        {
            "name": "report_video_insights",
            "description": "Report structured insights extracted from the video transcript.",
            "input_schema": VideoInsights.model_json_schema(),
        }
    ]

    user_msg = (
        f"Video ID: {metadata.video_id}\n"
        f"Title: {metadata.title}\n"
        f"Channel: {metadata.channel_title}\n\n"
        f"Transcript:\n{formatted}"
    )
    messages: list[dict[str, Any]] = [{"role": "user", "content": user_msg}]

    def _call(msgs: list[dict[str, Any]]) -> Any:
        return client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            system=system,  # type: ignore[arg-type]
            messages=msgs,  # type: ignore[arg-type]
            tools=tools,  # type: ignore[arg-type]
            tool_choice={"type": "tool", "name": "report_video_insights"},
        )

    response = _call(messages)

    try:
        return VideoInsights.model_validate(_extract_tool_input(response, "report_video_insights"))
    except ValidationError as exc:
        log.warning("VideoInsights validation failed on first attempt, retrying: %s", exc)
        messages.append({"role": "assistant", "content": response.content})
        messages.append(
            {
                "role": "user",
                "content": (
                    "The previous response failed schema validation. Please fix these issues "
                    f"and call report_video_insights again:\n{exc}"
                ),
            }
        )
        response2 = _call(messages)
        return VideoInsights.model_validate(
            _extract_tool_input(response2, "report_video_insights")
        )


def synthesize_digest(
    ticker: str, company_name: str, insights: list[VideoInsights]
) -> DigestReport:
    client = anthropic.Anthropic()

    system = [
        {
            "type": "text",
            "text": (
                f"You are a financial analyst synthesizing insights from multiple YouTube video "
                f"analyses about {ticker} ({company_name}).\n\n"
                "Rules:\n"
                "- Deduplicate themes: if multiple videos mention the same catalyst, merge them "
                "into one point ranked by the number of sources.\n"
                "- Rank top_catalysts, top_red_flags, and upcoming_events by source count.\n"
                "- Note disagreements between sources explicitly in the synthesis.\n"
                "- Report only what the videos discuss — no speculation.\n"
                "- synthesis should be 2-4 paragraphs summarizing the investment picture.\n\n"
                "Call the report_digest tool with your synthesis."
            ),
            "cache_control": {"type": "ephemeral"},
        }
    ]

    tools = [
        {
            "name": "report_digest",
            "description": "Report the synthesized digest across all analyzed videos.",
            "input_schema": _DigestSynthesis.model_json_schema(),
        }
    ]

    insights_json = json.dumps(
        [ins.model_dump(mode="json") for ins in insights], indent=2
    )
    user_msg = (
        f"Ticker: {ticker}\n"
        f"Company: {company_name}\n"
        f"Videos analyzed: {len(insights)}\n\n"
        f"Per-video insights:\n{insights_json}"
    )
    messages: list[dict[str, Any]] = [{"role": "user", "content": user_msg}]

    response = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=8192,
        system=system,  # type: ignore[arg-type]
        messages=messages,  # type: ignore[arg-type]
        tools=tools,  # type: ignore[arg-type]
        tool_choice={"type": "tool", "name": "report_digest"},
    )

    synth = _DigestSynthesis.model_validate(_extract_tool_input(response, "report_digest"))

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
