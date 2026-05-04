"""Tests for compute_return_1m, compute_return_ytd, compute_return_1y."""
from datetime import date, timedelta
from unittest.mock import patch

import pytest

from casino_dashboard.models import TickerSnapshot
from casino_dashboard.signals.computers import (
    compute_return_1m,
    compute_return_1y,
    compute_return_ytd,
)


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


def _history(n_days: int, start_close: float = 100.0, end_close: float | None = None) -> list[TickerSnapshot]:
    """Build n_days of history ending today, linearly interpolated."""
    today = date.today()
    if end_close is None:
        end_close = start_close
    result = []
    for i in range(n_days - 1, -1, -1):
        d = today - timedelta(days=i)
        frac = (n_days - 1 - i) / max(n_days - 1, 1)
        close = start_close + frac * (end_close - start_close)
        result.append(_snap(d, close))
    return result


# ── Test 1: return_1m with 21 days history → expected ratio ──────────────────

def test_return_1m_21_days():
    history = _history(22, start_close=100.0, end_close=121.0)
    result = compute_return_1m(history)
    assert result is not None
    assert result == pytest.approx((121.0 - 100.0) / 100.0, rel=0.01)


# ── Test 2: return_1m with <21 days → None ───────────────────────────────────

def test_return_1m_insufficient_history():
    history = _history(20, start_close=100.0, end_close=110.0)
    assert compute_return_1m(history) is None


# ── Test 3: return_ytd with history spanning Jan 1 → expected ratio ───────────

def test_return_ytd_spans_jan1():
    today = date.today()
    jan1 = date(today.year, 1, 1)
    # Build history from 30 days before Jan 1 (prior year) through today.
    # Prices in prior year: 80.0. Prices on/after Jan 1: 100.0 (flat).
    history = []
    d = jan1 - timedelta(days=30)
    while d <= today:
        close = 80.0 if d < jan1 else 100.0
        history.append(_snap(d, close))
        d += timedelta(days=1)

    result = compute_return_ytd(history)
    assert result is not None
    # (100 - 100) / 100 = 0 if flat all year, but first snap of year is 100.0
    # and latest is also 100.0 → return = 0.0
    assert result == pytest.approx(0.0)


# ── Test 4: return_ytd with history not reaching Jan 1 → None ────────────────

def test_return_ytd_no_jan1_data():
    today = date.today()
    jan1 = date(today.year, 1, 1)
    if (today - jan1).days < 10:
        pytest.skip("Too close to Jan 1 for this test to be meaningful")
    # Build history starting mid-year (all dates in current year, no pre-Jan-1 data).
    history = []
    start = today - timedelta(days=9)
    d = start
    while d <= today:
        history.append(_snap(d, 100.0))
        d += timedelta(days=1)
    # history[0].date is >= jan1, so compute_return_ytd must return None
    assert compute_return_ytd(history) is None


# ── Test 5: return_1y with 252 days history → expected ratio ─────────────────

def test_return_1y_252_days():
    history = _history(253, start_close=50.0, end_close=100.0)
    result = compute_return_1y(history)
    assert result is not None
    assert result == pytest.approx((100.0 - 50.0) / 50.0, rel=0.01)
