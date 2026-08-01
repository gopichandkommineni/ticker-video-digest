"""Unit tests for analyzer — Anthropic client is mocked, no real API calls."""
from datetime import datetime, timezone
from unittest.mock import MagicMock

from ticker_digest.analyzer import extract_insights, synthesize_digest
from core.models import (
    Citation,
    DigestReport,
    Transcript,
    TranscriptSegment,
    VideoInsights,
    VideoMetadata,
)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _make_transcript(video_id: str = "vid001") -> Transcript:
    return Transcript(
        video_id=video_id,
        segments=[
            TranscriptSegment(text="Company announced a new contract.", start_seconds=10.0, duration_seconds=3.0),
            TranscriptSegment(text="Revenue guidance raised for next quarter.", start_seconds=45.0, duration_seconds=2.5),
        ],
        language="en",
    )


def _make_metadata(video_id: str = "vid001") -> VideoMetadata:
    return VideoMetadata(
        video_id=video_id,
        title="RKLB Stock Analysis",
        channel_id="chan_A",
        channel_title="Space Investing",
        channel_subscriber_count=50000,
        published_at=datetime(2026, 4, 15, tzinfo=timezone.utc),
        duration_seconds=600,
        view_count=15000,
    )


def _make_video_insights(video_id: str = "vid001") -> VideoInsights:
    return VideoInsights(
        video_id=video_id,
        catalysts=[Citation(video_id=video_id, timestamp_seconds=10, quote_paraphrase="New contract announced")],
        red_flags=[],
        upcoming_events=[Citation(video_id=video_id, timestamp_seconds=45, quote_paraphrase="Earnings call next week")],
        overall_sentiment="bullish",
        sentiment_reasoning="Speaker was positive throughout.",
        summary="Bullish on contract wins and raised guidance.",
    )


def _make_tool_response(tool_name: str, input_dict: dict) -> MagicMock:
    """Build a mock Anthropic Message with a single tool_use content block."""
    block = MagicMock()
    block.type = "tool_use"
    block.name = tool_name
    block.input = input_dict

    response = MagicMock()
    response.content = [block]
    return response


# ---------------------------------------------------------------------------
# extract_insights — happy path
# ---------------------------------------------------------------------------


def test_extract_insights_happy_path(mocker) -> None:
    valid_input = {
        "video_id": "vid001",
        "catalysts": [
            {"video_id": "vid001", "timestamp_seconds": 10, "quote_paraphrase": "New contract announced"}
        ],
        "red_flags": [],
        "upcoming_events": [],
        "overall_sentiment": "bullish",
        "sentiment_reasoning": "Speaker was consistently positive.",
        "summary": "Analyst is bullish on contract momentum.",
    }

    mock_client = MagicMock()
    mock_client.messages.create.return_value = _make_tool_response("report_video_insights", valid_input)

    mocker.patch("ticker_digest.analyzer.anthropic.Anthropic", return_value=mock_client)

    result = extract_insights(_make_transcript("vid001"), _make_metadata("vid001"))

    assert isinstance(result, VideoInsights)
    assert result.video_id == "vid001"
    assert result.overall_sentiment == "bullish"
    assert len(result.catalysts) == 1
    # Verify the computed Citation URL format
    assert result.catalysts[0].url == "https://youtube.com/watch?v=vid001&t=10s"
    mock_client.messages.create.assert_called_once()


# ---------------------------------------------------------------------------
# extract_insights — retry on validation error
# ---------------------------------------------------------------------------


def test_extract_insights_retries_on_validation_error(mocker) -> None:
    # First response is missing required fields — will trigger ValidationError
    bad_input = {
        "video_id": "vid001",
        "catalysts": [],
        "red_flags": [],
        "upcoming_events": [],
        # missing: overall_sentiment, sentiment_reasoning, summary
    }

    valid_input = {
        "video_id": "vid001",
        "catalysts": [],
        "red_flags": [],
        "upcoming_events": [],
        "overall_sentiment": "neutral",
        "sentiment_reasoning": "No strong signals detected.",
        "summary": "Neutral outlook with no major catalysts.",
    }

    mock_client = MagicMock()
    mock_client.messages.create.side_effect = [
        _make_tool_response("report_video_insights", bad_input),
        _make_tool_response("report_video_insights", valid_input),
    ]

    mocker.patch("ticker_digest.analyzer.anthropic.Anthropic", return_value=mock_client)

    result = extract_insights(_make_transcript("vid001"), _make_metadata("vid001"))

    assert isinstance(result, VideoInsights)
    assert result.overall_sentiment == "neutral"
    assert mock_client.messages.create.call_count == 2


# ---------------------------------------------------------------------------
# synthesize_digest — three insights
# ---------------------------------------------------------------------------


def test_synthesize_digest_with_three_insights(mocker) -> None:
    insights = [
        _make_video_insights("vid001"),
        _make_video_insights("vid002"),
        _make_video_insights("vid003"),
    ]

    synthesis_input = {
        "company_name": "Rocket Lab Holdings",
        "top_catalysts": ["New contract wins (3/3 videos)", "Raised revenue guidance (2/3 videos)"],
        "top_red_flags": [],
        "upcoming_events": ["Earnings call next week"],
        "overall_sentiment": "bullish",
        "synthesis": (
            "All three analysts agree on a bullish outlook for RKLB driven by contract momentum.\n\n"
            "Revenue guidance was raised in two of three videos, reinforcing the positive tone.\n\n"
            "No meaningful red flags were identified across the video set."
        ),
    }

    mock_client = MagicMock()
    mock_client.messages.create.return_value = _make_tool_response("report_digest", synthesis_input)

    mocker.patch("ticker_digest.analyzer.anthropic.Anthropic", return_value=mock_client)

    result = synthesize_digest("RKLB", "Rocket Lab Holdings", insights)

    assert isinstance(result, DigestReport)
    assert result.ticker == "RKLB"
    assert result.video_count == 3
    assert len(result.video_insights) == 3
    assert result.overall_sentiment == "bullish"
    assert isinstance(result.generated_at, datetime)
    mock_client.messages.create.assert_called_once()


# ---------------------------------------------------------------------------
# synthesize_digest — empty insights list
# ---------------------------------------------------------------------------


def test_synthesize_digest_empty_insights(mocker) -> None:
    synthesis_input = {
        "company_name": "Rocket Lab Holdings",
        "top_catalysts": [],
        "top_red_flags": [],
        "upcoming_events": [],
        "overall_sentiment": "neutral",
        "synthesis": "No video data was available for this ticker in the requested period.",
    }

    mock_client = MagicMock()
    mock_client.messages.create.return_value = _make_tool_response("report_digest", synthesis_input)

    mocker.patch("ticker_digest.analyzer.anthropic.Anthropic", return_value=mock_client)

    result = synthesize_digest("RKLB", "Rocket Lab Holdings", [])

    assert isinstance(result, DigestReport)
    assert result.ticker == "RKLB"
    assert result.video_count == 0
    assert result.video_insights == []
    assert result.overall_sentiment == "neutral"
