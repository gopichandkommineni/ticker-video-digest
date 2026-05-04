"""Tests for social mention signal computers."""
import pandas as pd
import pytest

from casino_dashboard.signals.computers import (
    compute_apewisdom_velocity_24h,
    compute_mention_velocity_7d,
)


# ── compute_apewisdom_velocity_24h ────────────────────────────────────────────

def test_velocity_24h_basic():
    assert compute_apewisdom_velocity_24h(100, 50) == pytest.approx(2.0)


def test_velocity_24h_mentions_24h_ago_none_returns_none():
    assert compute_apewisdom_velocity_24h(100, None) is None


def test_velocity_24h_mentions_24h_ago_zero_returns_none():
    assert compute_apewisdom_velocity_24h(100, 0) is None


def test_velocity_24h_non_round_values():
    result = compute_apewisdom_velocity_24h(75, 50)
    assert result == pytest.approx(1.5)


# ── compute_mention_velocity_7d ───────────────────────────────────────────────

def _make_history(counts: list[int]) -> pd.DataFrame:
    """Build a newest-first DataFrame matching get_social_history output."""
    dates = [f"2026-05-{4 - i:02d}" for i in range(len(counts))]
    return pd.DataFrame(
        {"date": dates, "mention_count": counts, "mentions_24h_ago": [None] * len(counts)}
    )


def test_velocity_7d_expected_ratio():
    # today=100, prior 7 days all 50 → 100/50 = 2.0
    hist = _make_history([100, 50, 50, 50, 50, 50, 50, 50])
    result = compute_mention_velocity_7d(hist)
    assert result == pytest.approx(2.0)


def test_velocity_7d_fewer_than_8_rows_returns_none():
    hist = _make_history([100, 50, 50, 50, 50, 50, 50])  # only 7 rows
    assert compute_mention_velocity_7d(hist) is None


def test_velocity_7d_empty_returns_none():
    assert compute_mention_velocity_7d(pd.DataFrame(columns=["date", "mention_count", "mentions_24h_ago"])) is None


def test_velocity_7d_nan_values_handled():
    import math
    counts = [100, float("nan"), 50, 50, 50, 50, 50, 50]
    hist = _make_history(counts)
    hist["mention_count"] = pd.to_numeric(hist["mention_count"], errors="coerce")
    result = compute_mention_velocity_7d(hist)
    # NaN in prior dropped; mean of remaining 6 values (all 50) = 50 → 100/50=2.0
    assert result is not None
    assert result == pytest.approx(2.0)
