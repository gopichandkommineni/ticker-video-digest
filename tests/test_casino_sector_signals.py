"""Tests for sector-level signal computations: atr14, atr14_pct, pct_above_sma50."""
from datetime import date, timedelta

import pytest

from casino_dashboard.models import TickerSnapshot
from casino_dashboard.signals.computers import (
    compute_atr14,
    compute_atr14_pct,
    compute_pct_above_sma50,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_history(n: int, close: float = 100.0, high_offset: float = 2.0, low_offset: float = 2.0) -> list[TickerSnapshot]:
    """Generate a synthetic price history of length n."""
    base = date(2026, 1, 1)
    return [
        TickerSnapshot(
            ticker="TEST",
            date=base + timedelta(days=i),
            open=close,
            high=close + high_offset,
            low=close - low_offset,
            close=close,
            adj_close=close,
            volume=1_000_000,
            avg_volume_30d=1_000_000.0,
            news_items=[],
        )
        for i in range(n)
    ]


def _make_history_custom(closes: list[float]) -> list[TickerSnapshot]:
    base = date(2026, 1, 1)
    snaps = []
    for i, c in enumerate(closes):
        snaps.append(
            TickerSnapshot(
                ticker="TEST",
                date=base + timedelta(days=i),
                open=c,
                high=c + 1.0,
                low=c - 1.0,
                close=c,
                adj_close=c,
                volume=1_000_000,
                avg_volume_30d=1_000_000.0,
                news_items=[],
            )
        )
    return snaps


# ---------------------------------------------------------------------------
# compute_atr14
# ---------------------------------------------------------------------------

def test_atr14_returns_none_for_insufficient_history():
    history = _make_history(14)
    assert compute_atr14(history) is None


def test_atr14_returns_float_with_15_days():
    history = _make_history(15, close=100.0, high_offset=2.0, low_offset=2.0)
    result = compute_atr14(history)
    # True Range = max(4.0, |102-100|, |98-100|) = 4.0 per day
    assert result == pytest.approx(4.0)


def test_atr14_uses_last_14_changes():
    """With 30 days of history, ATR14 should still use only last 15 rows."""
    history = _make_history(30, close=100.0, high_offset=3.0, low_offset=3.0)
    result = compute_atr14(history)
    assert result == pytest.approx(6.0)  # TR = max(6, 3, 3) = 6 per bar


def test_atr14_gap_day_increases_true_range():
    """A large gap (today open >> yesterday close) should register in TR."""
    history = _make_history(14, close=100.0)
    # Add a gap day: prev close=100, today high=120, low=110, close=115
    gap_day = TickerSnapshot(
        ticker="TEST",
        date=history[-1].date + timedelta(days=1),
        open=110.0,
        high=120.0,
        low=110.0,
        close=115.0,
        adj_close=115.0,
        volume=1_000_000,
        avg_volume_30d=1_000_000.0,
        news_items=[],
    )
    history.append(gap_day)
    result = compute_atr14(history)
    assert result is not None
    # True range for the gap day = max(10, |120-100|, |110-100|) = 20
    # This exceeds the normal TR so ATR should be > normal 4.0
    assert result > 4.0


# ---------------------------------------------------------------------------
# compute_atr14_pct
# ---------------------------------------------------------------------------

def test_atr14_pct_returns_none_for_insufficient_history():
    history = _make_history(14)
    assert compute_atr14_pct(history) is None


def test_atr14_pct_normalizes_by_close():
    history = _make_history(15, close=100.0, high_offset=2.0, low_offset=2.0)
    result = compute_atr14_pct(history)
    # ATR = 4.0, close = 100 → atr14_pct = 0.04
    assert result == pytest.approx(0.04)


def test_atr14_pct_zero_close_returns_none():
    history = _make_history(15, close=0.0)
    assert compute_atr14_pct(history) is None


def test_atr14_pct_higher_price_gives_lower_pct():
    hist_100 = _make_history(15, close=100.0, high_offset=2.0, low_offset=2.0)
    hist_200 = _make_history(15, close=200.0, high_offset=2.0, low_offset=2.0)
    pct_100 = compute_atr14_pct(hist_100)
    pct_200 = compute_atr14_pct(hist_200)
    assert pct_100 is not None
    assert pct_200 is not None
    assert pct_100 > pct_200


# ---------------------------------------------------------------------------
# compute_pct_above_sma50
# ---------------------------------------------------------------------------

def test_pct_above_sma50_returns_none_insufficient_history():
    history = _make_history(49)
    assert compute_pct_above_sma50(history) is None


def test_pct_above_sma50_returns_1_when_above():
    # Last close = 120, SMA50 of stable 100s = 100 → above
    history = _make_history(50, close=100.0)
    history[-1] = TickerSnapshot(
        ticker="TEST",
        date=history[-1].date,
        open=120.0,
        high=122.0,
        low=118.0,
        close=120.0,
        adj_close=120.0,
        volume=1_000_000,
        avg_volume_30d=1_000_000.0,
        news_items=[],
    )
    result = compute_pct_above_sma50(history)
    assert result == 1.0


def test_pct_above_sma50_returns_0_when_below():
    history = _make_history(50, close=100.0)
    history[-1] = TickerSnapshot(
        ticker="TEST",
        date=history[-1].date,
        open=80.0,
        high=82.0,
        low=78.0,
        close=80.0,
        adj_close=80.0,
        volume=1_000_000,
        avg_volume_30d=1_000_000.0,
        news_items=[],
    )
    result = compute_pct_above_sma50(history)
    assert result == 0.0


def test_pct_above_sma50_equal_to_sma_returns_0():
    """Close exactly at SMA50 → not above → 0.0."""
    history = _make_history(50, close=100.0)
    result = compute_pct_above_sma50(history)
    # All closes = 100, SMA50 = 100, close = 100 → not above (strict)
    assert result == 0.0
