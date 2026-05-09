"""Pure-function tests for the Reality Score composite."""
from datetime import datetime, timezone

import pytest

from ticker_digest.market.reality_score import compute_reality_score
from ticker_digest.models import MarketIndicator, MarketSnapshot


def _ind(series_id: str, bucket: str, z: float | None) -> MarketIndicator:
    return MarketIndicator(
        name=series_id,
        series_id=series_id,
        source="computed",
        bucket=bucket,  # type: ignore[arg-type]
        value=0.0 if z is None else float(z),
        z_score=z,
        as_of=datetime(2026, 5, 1, tzinfo=timezone.utc),
    )


def _snap(indicators: dict[str, MarketIndicator]) -> MarketSnapshot:
    return MarketSnapshot(generated_at=datetime(2026, 5, 1, tzinfo=timezone.utc), indicators=indicators)


SIGNS = {"A": +1, "B": -1, "C": +1, "D": -1}
BUCKETS = {"A": "market", "B": "market", "C": "economy", "D": "economy"}
WEIGHTS = {"market": 0.5, "economy": 0.5}


def test_aligned_when_all_zero():
    snap = _snap({k: _ind(k, BUCKETS[k], 0.0) for k in BUCKETS})
    score = compute_reality_score(snap, weights=WEIGHTS, signs=SIGNS, buckets=BUCKETS)
    assert score.score == 0.0
    assert score.band == "aligned"
    assert score.market_z == 0.0 and score.economy_z == 0.0
    assert set(score.used_indicators) == {"A", "B", "C", "D"}


def test_severe_decoupling_when_market_hot_and_economy_weak():
    # A=+2 (sign +1 → +2), B=-2 (sign -1 → +2)  -> market_z = +2
    # C=+2 (sign +1 → +2), D=-2 (sign -1 → +2)  -> economy_z = +2
    indicators = {
        "A": _ind("A", "market", 2.0),
        "B": _ind("B", "market", -2.0),
        "C": _ind("C", "economy", 2.0),
        "D": _ind("D", "economy", -2.0),
    }
    score = compute_reality_score(_snap(indicators), weights=WEIGHTS, signs=SIGNS, buckets=BUCKETS)
    assert score.market_z == 2.0
    assert score.economy_z == 2.0
    assert score.score == pytest.approx(2.0)
    assert score.band == "severe_decoupling"


def test_negative_score_when_market_cold_economy_strong():
    indicators = {
        "A": _ind("A", "market", -1.5),
        "B": _ind("B", "market", 1.5),
        "C": _ind("C", "economy", -1.5),
        "D": _ind("D", "economy", 1.5),
    }
    score = compute_reality_score(_snap(indicators), weights=WEIGHTS, signs=SIGNS, buckets=BUCKETS)
    assert score.score == pytest.approx(-1.5)
    assert score.band == "market_discounting_weakness"


def test_skips_none_z_and_context_bucket():
    buckets = dict(BUCKETS, V="context")
    signs = dict(SIGNS, V=+1)
    indicators = {
        "A": _ind("A", "market", 1.0),
        "B": _ind("B", "market", None),  # missing z → skipped
        "C": _ind("C", "economy", 0.0),
        "D": _ind("D", "economy", 0.0),
        "V": _ind("V", "context", 5.0),  # context → skipped
    }
    score = compute_reality_score(_snap(indicators), weights=WEIGHTS, signs=signs, buckets=buckets)
    # Only A contributes to market: +1.0; C and D both 0 to economy.
    assert score.market_z == 1.0
    assert score.economy_z == 0.0
    assert score.score == pytest.approx(0.5)
    assert "B" in score.skipped_indicators
    assert "V" in score.skipped_indicators
    assert "A" in score.used_indicators


def test_single_bucket_normalization():
    # No economy data — score should reflect market_z scaled, not halved.
    indicators = {
        "A": _ind("A", "market", 2.0),
        "B": _ind("B", "market", -2.0),  # sign -1 → +2
    }
    score = compute_reality_score(_snap(indicators), weights=WEIGHTS, signs=SIGNS, buckets=BUCKETS)
    assert score.market_z == 2.0
    assert score.economy_z is None
    assert score.score == pytest.approx(2.0)


def test_empty_snapshot_returns_aligned_zero():
    score = compute_reality_score(_snap({}))
    assert score.score == 0.0
    assert score.band == "aligned"
    assert score.market_z is None and score.economy_z is None


def test_band_boundaries():
    cases = [
        (1.6, "severe_decoupling"),
        (1.5, "severe_decoupling"),
        (0.5, "stretched"),
        (0.4, "aligned"),
        (-0.4, "aligned"),
        (-0.5, "market_discounting_weakness"),
        (-2.0, "market_discounting_weakness"),
    ]
    for z, expected_band in cases:
        indicators = {"A": _ind("A", "market", z), "C": _ind("C", "economy", z)}
        # signs +1, +1 → score = z
        score = compute_reality_score(
            _snap(indicators),
            weights=WEIGHTS,
            signs={"A": +1, "C": +1},
            buckets={"A": "market", "C": "economy"},
        )
        assert score.band == expected_band, f"z={z}"
