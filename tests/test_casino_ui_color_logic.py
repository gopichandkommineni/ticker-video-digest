"""Tests for casino_dashboard.ui.components.colors — color classification functions."""
import pytest

from casino_dashboard.ui.components.colors import (
    color_for_analyst_upside,
    color_for_earnings_days,
    color_for_profit_margin,
    color_for_returns,
    color_for_revenue_growth,
    color_for_rsi,
    color_for_setup,
    color_for_short_pct,
    color_for_volume_ratio,
    color_to_hex,
)


# ── color_for_returns ─────────────────────────────────────────────────────────

def test_color_for_returns_positive():
    assert color_for_returns(0.05) == "green"


def test_color_for_returns_negative():
    assert color_for_returns(-0.05) == "red"


def test_color_for_returns_zero():
    assert color_for_returns(0.0) == "gray"


def test_color_for_returns_none():
    assert color_for_returns(None) == "gray"


def test_color_for_returns_nan():
    assert color_for_returns(float("nan")) == "gray"


# ── color_for_setup ───────────────────────────────────────────────────────────

def test_color_for_setup_breakout():
    assert color_for_setup(1.0, 0.0) == "green"


def test_color_for_setup_breakdown():
    assert color_for_setup(0.0, 1.0) == "red"


def test_color_for_setup_neutral():
    assert color_for_setup(0.0, 0.0) == "gray"


def test_color_for_setup_none():
    assert color_for_setup(None, None) == "gray"


# ── color_for_volume_ratio ────────────────────────────────────────────────────

def test_color_for_volume_ratio_high():
    assert color_for_volume_ratio(2.0) == "green"


def test_color_for_volume_ratio_at_threshold():
    # Exactly 1.5x is NOT >1.5, so should be gray
    assert color_for_volume_ratio(1.5) == "gray"


def test_color_for_volume_ratio_above_threshold():
    assert color_for_volume_ratio(1.51) == "green"


def test_color_for_volume_ratio_low():
    assert color_for_volume_ratio(0.4) == "red"


def test_color_for_volume_ratio_at_low_threshold():
    # Exactly 0.5 is NOT <0.5, so gray
    assert color_for_volume_ratio(0.5) == "gray"


def test_color_for_volume_ratio_normal():
    assert color_for_volume_ratio(1.0) == "gray"


def test_color_for_volume_ratio_none():
    assert color_for_volume_ratio(None) == "gray"


# ── color_for_rsi ─────────────────────────────────────────────────────────────

def test_color_for_rsi_overbought():
    assert color_for_rsi(75) == "yellow"


def test_color_for_rsi_at_70():
    assert color_for_rsi(70) == "yellow"


def test_color_for_rsi_approaching():
    assert color_for_rsi(65) == "yellow"


def test_color_for_rsi_at_60():
    assert color_for_rsi(60) == "yellow"


def test_color_for_rsi_neutral_above_30():
    assert color_for_rsi(50) == "gray"


def test_color_for_rsi_oversold():
    assert color_for_rsi(25) == "green"


def test_color_for_rsi_at_30():
    # Exactly 30 is NOT <30, so neutral
    assert color_for_rsi(30) == "gray"


def test_color_for_rsi_none():
    assert color_for_rsi(None) == "gray"


# ── color_for_short_pct ───────────────────────────────────────────────────────

def test_color_for_short_pct_high():
    assert color_for_short_pct(0.20) == "yellow"


def test_color_for_short_pct_at_threshold():
    # Exactly 0.15 is NOT >0.15, so gray
    assert color_for_short_pct(0.15) == "gray"


def test_color_for_short_pct_above_threshold():
    assert color_for_short_pct(0.16) == "yellow"


def test_color_for_short_pct_low():
    assert color_for_short_pct(0.05) == "gray"


def test_color_for_short_pct_none():
    assert color_for_short_pct(None) == "gray"


def test_color_for_short_pct_zero():
    assert color_for_short_pct(0.0) == "gray"


# ── color_for_earnings_days ───────────────────────────────────────────────────

def test_color_for_earnings_days_imminent():
    assert color_for_earnings_days(3) == "yellow"


def test_color_for_earnings_days_at_threshold():
    # Exactly 7 is NOT <7, so gray
    assert color_for_earnings_days(7) == "gray"


def test_color_for_earnings_days_far():
    assert color_for_earnings_days(30) == "gray"


def test_color_for_earnings_days_zero():
    assert color_for_earnings_days(0) == "yellow"


def test_color_for_earnings_days_none():
    assert color_for_earnings_days(None) == "gray"


# ── color_for_analyst_upside ──────────────────────────────────────────────────

def test_color_for_analyst_upside_positive():
    assert color_for_analyst_upside(0.20) == "green"


def test_color_for_analyst_upside_negative():
    assert color_for_analyst_upside(-0.10) == "red"


def test_color_for_analyst_upside_zero():
    assert color_for_analyst_upside(0.0) == "gray"


def test_color_for_analyst_upside_none():
    assert color_for_analyst_upside(None) == "gray"


# ── color_for_revenue_growth ──────────────────────────────────────────────────

def test_color_for_revenue_growth_positive():
    assert color_for_revenue_growth(0.15) == "green"


def test_color_for_revenue_growth_negative():
    assert color_for_revenue_growth(-0.05) == "red"


def test_color_for_revenue_growth_none():
    assert color_for_revenue_growth(None) == "gray"


# ── color_for_profit_margin ───────────────────────────────────────────────────

def test_color_for_profit_margin_positive():
    assert color_for_profit_margin(0.10) == "green"


def test_color_for_profit_margin_negative():
    assert color_for_profit_margin(-0.08) == "red"


def test_color_for_profit_margin_none():
    assert color_for_profit_margin(None) == "gray"


# ── color_to_hex ──────────────────────────────────────────────────────────────

def test_color_to_hex_green():
    assert color_to_hex("green") == "#16a34a"


def test_color_to_hex_red():
    assert color_to_hex("red") == "#dc2626"


def test_color_to_hex_yellow():
    assert color_to_hex("yellow") == "#ca8a04"


def test_color_to_hex_gray():
    assert color_to_hex("gray") == "#6b7280"


def test_color_to_hex_none_returns_gray_hex():
    assert color_to_hex(None) == "#6b7280"
