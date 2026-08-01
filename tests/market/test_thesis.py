"""Tests for the thesis generator. The Anthropic client is mocked."""
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from core.market import thesis as thesis_module
from core.models import (
    MarketIndicator,
    MarketSnapshot,
    MarketThesis,
    RealityScore,
)


@pytest.fixture
def tmp_cache_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("TICKER_DIGEST_CACHE_DIR", str(tmp_path))
    return tmp_path


def _snapshot() -> MarketSnapshot:
    return MarketSnapshot(
        generated_at=datetime(2026, 5, 1, tzinfo=timezone.utc),
        indicators={
            "T10Y2Y": MarketIndicator(
                name="10Y-2Y",
                series_id="T10Y2Y",
                source="fred",
                bucket="economy",
                value=-0.45,
                z_score=-1.8,
                as_of=datetime(2026, 4, 30, tzinfo=timezone.utc),
            ),
            "BUFFETT": MarketIndicator(
                name="Buffett",
                series_id="BUFFETT",
                source="computed",
                bucket="market",
                value=2.1,
                z_score=2.4,
                as_of=datetime(2026, 3, 31, tzinfo=timezone.utc),
            ),
        },
    )


def _score() -> RealityScore:
    return RealityScore(
        score=2.1,
        band="severe_decoupling",
        market_z=2.4,
        economy_z=1.8,
        contributions={"BUFFETT": 2.4, "T10Y2Y": 1.8},
        used_indicators=["BUFFETT", "T10Y2Y"],
        skipped_indicators=[],
    )


def _make_tool_response(input_dict: dict) -> MagicMock:
    block = MagicMock()
    block.type = "tool_use"
    block.name = "report_market_thesis"
    block.input = input_dict
    response = MagicMock()
    response.content = [block]
    return response


def test_generate_thesis_happy_path(tmp_cache_dir, mocker):
    payload = {
        "narrative": "Markets look stretched while real economy softens.",
        "bull_case": ["a", "b", "c"],
        "bear_case": ["x", "y", "z"],
        "key_watch_items": ["NFP", "CPI", "FOMC"],
        "regime": "fragile",
    }
    mock_client = MagicMock()
    mock_client.messages.create.return_value = _make_tool_response(payload)
    mocker.patch("core.market.thesis.anthropic.Anthropic", return_value=mock_client)

    result = thesis_module.generate_thesis(_snapshot(), _score())
    assert isinstance(result, MarketThesis)
    assert result.regime == "fragile"
    assert len(result.bull_case) == 3
    mock_client.messages.create.assert_called_once()
    # Verify tool-use forced + correct model
    kwargs = mock_client.messages.create.call_args.kwargs
    assert kwargs["model"] == "claude-sonnet-4-6"
    assert kwargs["tool_choice"] == {"type": "tool", "name": "report_market_thesis"}
    # Cache control was set on the system prompt
    assert kwargs["system"][0]["cache_control"] == {"type": "ephemeral"}


def test_generate_thesis_uses_cache(tmp_cache_dir, mocker):
    payload = {
        "narrative": "n",
        "bull_case": ["b"],
        "bear_case": ["x"],
        "key_watch_items": ["w"],
        "regime": "neutral",
    }
    mock_client = MagicMock()
    mock_client.messages.create.return_value = _make_tool_response(payload)
    mocker.patch("core.market.thesis.anthropic.Anthropic", return_value=mock_client)

    snap, scr = _snapshot(), _score()
    first = thesis_module.generate_thesis(snap, scr)
    second = thesis_module.generate_thesis(snap, scr)

    assert first.narrative == second.narrative
    # Only one network call across two invocations because the second hit the cache.
    mock_client.messages.create.assert_called_once()


def test_snapshot_hash_stable_across_dict_order():
    s1 = _snapshot()
    # Reorder indicators dict by reconstructing in opposite key order
    s2 = MarketSnapshot(
        generated_at=s1.generated_at,
        indicators={k: s1.indicators[k] for k in reversed(list(s1.indicators))},
    )
    assert thesis_module._snapshot_hash(s1, _score()) == thesis_module._snapshot_hash(s2, _score())


def test_snapshot_hash_changes_with_value():
    s1 = _snapshot()
    s2 = s1.model_copy(deep=True)
    s2.indicators["BUFFETT"].value = 99.9
    assert thesis_module._snapshot_hash(s1, _score()) != thesis_module._snapshot_hash(s2, _score())
