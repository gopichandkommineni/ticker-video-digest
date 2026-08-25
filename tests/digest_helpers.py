"""Shared builders for the YouTube insight-thread tests. No network, no LLM."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from core.models import Citation, VideoInsights, VideoMetadata

NOW = datetime(2026, 4, 20, 12, 0, tzinfo=timezone.utc)


def make_metadata(
    video_id: str = "vid001",
    *,
    title: str = "Rocket Lab deep dive",
    channel_id: str = "chan_A",
    channel_title: str = "Space Investing",
    subscribers: int = 50_000,
    views: int = 15_000,
    duration: int = 900,
    age_days: float = 1.0,
) -> VideoMetadata:
    return VideoMetadata(
        video_id=video_id,
        title=title,
        channel_id=channel_id,
        channel_title=channel_title,
        channel_subscriber_count=subscribers,
        published_at=NOW - timedelta(days=age_days),
        duration_seconds=duration,
        view_count=views,
    )


def make_insights(
    video_id: str = "vid001",
    *,
    catalysts: list[str] | None = None,
    red_flags: list[str] | None = None,
    upcoming_events: list[str] | None = None,
    sentiment: str = "bullish",
) -> VideoInsights:
    def _cites(texts: list[str] | None, start: int) -> list[Citation]:
        return [
            Citation(
                video_id=video_id,
                timestamp_seconds=start + index * 10,
                quote_paraphrase=text,
            )
            for index, text in enumerate(texts or [])
        ]

    return VideoInsights(
        video_id=video_id,
        catalysts=_cites(catalysts, 10),
        red_flags=_cites(red_flags, 100),
        upcoming_events=_cites(upcoming_events, 200),
        overall_sentiment=sentiment,
        sentiment_reasoning="Tone was consistent.",
        summary="Summary of the video.",
    )


def tool_response(tool_name: str, payload: dict) -> MagicMock:
    """A mock Anthropic Message carrying one tool_use block."""
    block = MagicMock()
    block.type = "tool_use"
    block.name = tool_name
    block.input = payload

    response = MagicMock()
    response.content = [block]
    return response
