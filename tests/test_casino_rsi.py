"""Tests for compute_rsi_14."""
from datetime import date, timedelta

import pytest

from casino_dashboard.models import TickerSnapshot
from casino_dashboard.signals.computers import compute_rsi_14


def _snap(d: date, close: float) -> TickerSnapshot:
    return TickerSnapshot(
        ticker="TEST",
        date=d,
        open=close,
        high=close,
        low=close,
        close=close,
        adj_close=close,
        volume=1_000_000,
        avg_volume_30d=None,
        news_items=[],
    )


def _build(closes: list[float]) -> list[TickerSnapshot]:
    today = date.today()
    n = len(closes)
    return [_snap(today - timedelta(days=n - 1 - i), c) for i, c in enumerate(closes)]


# ── Test 1: monotonically rising series → RSI approaches 100 ─────────────────

def test_monotonically_rising_approaches_100():
    closes = [float(i) for i in range(1, 31)]  # 30 days, 1..30
    history = _build(closes)
    rsi = compute_rsi_14(history)
    assert rsi is not None
    assert rsi > 80.0


# ── Test 2: monotonically falling series → RSI approaches 0 ──────────────────

def test_monotonically_falling_approaches_0():
    closes = [float(30 - i) for i in range(30)]  # 30..1
    history = _build(closes)
    rsi = compute_rsi_14(history)
    assert rsi is not None
    assert rsi < 20.0


# ── Test 3: alternating (flat-ish) series → RSI near 50 ─────────────────────

def test_alternating_series_near_50():
    closes = []
    for i in range(30):
        closes.append(100.0 + (1 if i % 2 == 0 else -1))
    history = _build(closes)
    rsi = compute_rsi_14(history)
    assert rsi is not None
    assert 30.0 <= rsi <= 70.0


# ── Test 4: all gains → RSI = 100 ────────────────────────────────────────────

def test_all_gains_returns_100():
    closes = [float(i) for i in range(1, 20)]  # strictly increasing
    history = _build(closes)
    rsi = compute_rsi_14(history)
    assert rsi == pytest.approx(100.0)


# ── Test 5: all losses → RSI = 0 ─────────────────────────────────────────────

def test_all_losses_returns_0():
    closes = [float(20 - i) for i in range(20)]  # strictly decreasing
    history = _build(closes)
    rsi = compute_rsi_14(history)
    assert rsi == pytest.approx(0.0)


# ── Test 6: fewer than 15 days of history → None ─────────────────────────────

def test_fewer_than_15_days_returns_none():
    closes = [100.0, 101.0, 102.0, 103.0]
    history = _build(closes)
    assert compute_rsi_14(history) is None
