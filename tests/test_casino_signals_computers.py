from datetime import date, timedelta

import pytest

from casino_dashboard.models import TickerSnapshot
from casino_dashboard.signals.computers import (
    compute_dist_from_extreme,
    compute_return,
    compute_vol_ratio_30d,
)


def _snap(i: int, close: float = 100.0, volume: int = 1_000_000) -> TickerSnapshot:
    return TickerSnapshot(
        ticker="TEST",
        date=date(2024, 1, 1) + timedelta(days=i),
        open=close,
        high=close + 1,
        low=close - 1,
        close=close,
        adj_close=close,
        volume=volume,
        avg_volume_30d=None,
        news_items=[],
    )


def _make_history(n: int, close: float = 100.0, volume: int = 1_000_000) -> list[TickerSnapshot]:
    return [_snap(i, close=close, volume=volume) for i in range(n)]


# --- vol_ratio_30d ---

def test_vol_ratio_30d_happy_path():
    history = [_snap(i, volume=1_000_000) for i in range(32)]
    history[-1] = _snap(31, volume=2_000_000)
    result = compute_vol_ratio_30d(history)
    assert result == pytest.approx(2.0)


def test_vol_ratio_30d_exact_10_prior_days():
    history = [_snap(i, volume=500_000) for i in range(11)]
    history[-1] = _snap(10, volume=1_000_000)
    result = compute_vol_ratio_30d(history)
    assert result == pytest.approx(2.0)


def test_vol_ratio_30d_insufficient_history_returns_none():
    history = [_snap(i) for i in range(9)]  # only 8 prior days available
    assert compute_vol_ratio_30d(history) is None


def test_vol_ratio_30d_only_one_day_returns_none():
    history = [_snap(0)]
    assert compute_vol_ratio_30d(history) is None


def test_vol_ratio_30d_division_by_zero_returns_none():
    history = [_snap(i, volume=0) for i in range(15)]
    assert compute_vol_ratio_30d(history) is None


def test_vol_ratio_30d_uses_only_last_30_prior():
    # Build 62-day history: first 31 days volume=9M, then 30 days volume=1M, last day volume=2M
    history = (
        [_snap(i, volume=9_000_000) for i in range(31)]
        + [_snap(31 + i, volume=1_000_000) for i in range(30)]
        + [_snap(61, volume=2_000_000)]
    )
    result = compute_vol_ratio_30d(history)
    assert result == pytest.approx(2.0)


# --- compute_return ---

def test_compute_return_1d():
    history = [_snap(0, close=100.0), _snap(1, close=105.0)]
    assert compute_return(history, 1) == pytest.approx(0.05)


def test_compute_return_5d():
    history = [_snap(i, close=100.0 + i) for i in range(6)]
    # latest close = 105, 5 days ago = 100 → return = 0.05
    assert compute_return(history, 5) == pytest.approx(0.05)


def test_compute_return_20d():
    history = [_snap(i, close=100.0) for i in range(20)] + [_snap(20, close=120.0)]
    assert compute_return(history, 20) == pytest.approx(0.20)


def test_compute_return_insufficient_history_returns_none():
    history = [_snap(0, close=100.0), _snap(1, close=110.0)]
    assert compute_return(history, 5) is None


def test_compute_return_negative():
    history = [_snap(0, close=100.0), _snap(1, close=90.0)]
    assert compute_return(history, 1) == pytest.approx(-0.10)


def test_compute_return_zero_prior_close_returns_none():
    history = [_snap(0, close=0.0), _snap(1, close=10.0)]
    assert compute_return(history, 1) is None


# --- compute_dist_from_extreme ---

def test_dist_from_high_at_the_high_returns_zero():
    # Latest day (i=29) has the highest close → dist = 0.0
    history = [_snap(i, close=100.0 + i) for i in range(30)]
    result = compute_dist_from_extreme(history, 30, "high")
    assert result == pytest.approx(0.0)


def test_dist_from_high_below_the_high():
    history = [_snap(i, close=100.0) for i in range(29)] + [_snap(29, close=90.0)]
    result = compute_dist_from_extreme(history, 30, "high")
    assert result == pytest.approx(-0.10)


def test_dist_from_low_at_the_low_returns_zero():
    # Latest day (i=29) has the lowest close → dist = 0.0
    history = [_snap(i, close=100.0 - i) for i in range(30)]
    result = compute_dist_from_extreme(history, 30, "low")
    assert result == pytest.approx(0.0)


def test_dist_from_low_above_the_low():
    history = [_snap(i, close=100.0) for i in range(29)] + [_snap(29, close=110.0)]
    result = compute_dist_from_extreme(history, 30, "low")
    assert result == pytest.approx(0.10)


def test_dist_from_extreme_insufficient_history_returns_none():
    history = [_snap(i) for i in range(5)]
    assert compute_dist_from_extreme(history, 30, "high") is None
    assert compute_dist_from_extreme(history, 30, "low") is None


def test_dist_from_extreme_invalid_kind_raises():
    history = [_snap(i) for i in range(30)]
    with pytest.raises(ValueError):
        compute_dist_from_extreme(history, 30, "median")
