"""Tests for casino_dashboard.ui.indicators — pure functions, no I/O."""
import math

import pandas as pd
import pytest

from casino_dashboard.ui.indicators import compute_bollinger, compute_rsi, compute_sma


# ── SMA ───────────────────────────────────────────────────────────────────────

def test_sma_known_values():
    prices = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
    result = compute_sma(prices, window=3)
    assert math.isnan(result.iloc[0])
    assert math.isnan(result.iloc[1])
    assert result.iloc[2] == pytest.approx(2.0)
    assert result.iloc[3] == pytest.approx(3.0)
    assert result.iloc[4] == pytest.approx(4.0)


def test_sma_window_larger_than_series_returns_all_nan():
    prices = pd.Series([10.0, 20.0, 30.0])
    result = compute_sma(prices, window=10)
    assert result.isna().all()


def test_sma_window_equals_length():
    prices = pd.Series([2.0, 4.0, 6.0])
    result = compute_sma(prices, window=3)
    assert math.isnan(result.iloc[0])
    assert math.isnan(result.iloc[1])
    assert result.iloc[2] == pytest.approx(4.0)


def test_sma_returns_same_length_as_input():
    prices = pd.Series(range(50), dtype=float)
    assert len(compute_sma(prices, window=20)) == 50


# ── RSI ───────────────────────────────────────────────────────────────────────

def test_rsi_monotonically_rising_approaches_100():
    prices = pd.Series([float(i) for i in range(1, 51)])
    result = compute_rsi(prices, window=14)
    valid = result.dropna()
    assert len(valid) > 0
    assert (valid > 90).all(), f"Expected RSI > 90 for monotonically rising, got {valid.tolist()}"


def test_rsi_monotonically_falling_approaches_0():
    prices = pd.Series([float(50 - i) for i in range(50)])
    result = compute_rsi(prices, window=14)
    valid = result.dropna()
    assert len(valid) > 0
    assert (valid < 10).all(), f"Expected RSI < 10 for monotonically falling, got {valid.tolist()}"


def test_rsi_flat_series_returns_nan():
    prices = pd.Series([100.0] * 30)
    result = compute_rsi(prices, window=14)
    valid = result.dropna()
    # Flat → zero gain and zero loss → RS undefined → NaN
    assert valid.empty or valid.isna().all()


def test_rsi_first_window_values_are_nan():
    prices = pd.Series([float(i) for i in range(1, 31)])
    result = compute_rsi(prices, window=14)
    # First 14 values should be NaN
    assert result.iloc[:14].isna().all()


def test_rsi_returns_same_length_as_input():
    prices = pd.Series(range(50), dtype=float)
    assert len(compute_rsi(prices, window=14)) == 50


# ── Bollinger Bands ───────────────────────────────────────────────────────────

def test_bollinger_returns_three_series_of_same_length():
    prices = pd.Series(range(50), dtype=float)
    middle, upper, lower = compute_bollinger(prices, window=20)
    assert len(middle) == len(upper) == len(lower) == 50


def test_bollinger_middle_band_equals_sma():
    prices = pd.Series([float(i) for i in range(1, 41)])
    middle, _, _ = compute_bollinger(prices, window=20)
    expected = compute_sma(prices, window=20)
    pd.testing.assert_series_equal(middle, expected)


def test_bollinger_upper_minus_middle_equals_two_std():
    prices = pd.Series([float(i % 10) for i in range(40)])
    middle, upper, lower = compute_bollinger(prices, window=20, num_std=2.0)
    rolling_std = prices.rolling(window=20, min_periods=20).std()
    expected_width = 2.0 * rolling_std
    diff = (upper - middle).dropna()
    expected_diff = expected_width.dropna()
    pd.testing.assert_series_equal(diff, expected_diff, check_names=False)


def test_bollinger_lower_symmetric_around_middle():
    prices = pd.Series([float(i % 7) for i in range(40)])
    middle, upper, lower = compute_bollinger(prices, window=20)
    # upper - middle == middle - lower at every non-NaN point
    width_up = (upper - middle).dropna()
    width_down = (middle - lower).dropna()
    pd.testing.assert_series_equal(width_up, width_down, check_names=False)
