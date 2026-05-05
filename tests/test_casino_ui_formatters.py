"""Tests for casino_dashboard.ui.formatters — detail-page number formatters."""
import pytest

from casino_dashboard.ui.formatters import format_currency, format_market_cap, format_pct


# ── format_market_cap ─────────────────────────────────────────────────────────

def test_format_market_cap_billions():
    assert format_market_cap(13_970_000_000) == "$13.97B"


def test_format_market_cap_millions():
    assert format_market_cap(455_710_000) == "$455.71M"


def test_format_market_cap_small_billions():
    assert format_market_cap(1_000_000_000) == "$1.00B"


def test_format_market_cap_small_millions():
    assert format_market_cap(1_000_000) == "$1.00M"


def test_format_market_cap_sub_million():
    assert format_market_cap(999_999) == "$999,999.00"


def test_format_market_cap_none():
    assert format_market_cap(None) == "—"


def test_format_market_cap_nan():
    assert format_market_cap(float("nan")) == "—"


def test_format_market_cap_negative_billions():
    assert format_market_cap(-2_500_000_000) == "$-2.50B"


# ── format_pct ────────────────────────────────────────────────────────────────

def test_format_pct_large_positive():
    assert format_pct(0.8275) == "+82.75%"


def test_format_pct_small_negative():
    assert format_pct(-0.0839) == "-8.39%"


def test_format_pct_none():
    assert format_pct(None) == "—"


def test_format_pct_nan():
    assert format_pct(float("nan")) == "—"


def test_format_pct_zero():
    # Exact zero: sign is suppressed ('+0.00%' would be misleading)
    assert format_pct(0.0) == "0.00%"


def test_format_pct_positive_small():
    assert format_pct(0.0150) == "+1.50%"


def test_format_pct_negative_small():
    assert format_pct(-0.0036) == "-0.36%"


# ── format_currency ───────────────────────────────────────────────────────────

def test_format_currency_standard():
    assert format_currency(176.97) == "$176.97"


def test_format_currency_round():
    assert format_currency(100.0) == "$100.00"


def test_format_currency_small():
    assert format_currency(0.50) == "$0.50"


def test_format_currency_none():
    assert format_currency(None) == "—"


def test_format_currency_nan():
    assert format_currency(float("nan")) == "—"


def test_format_currency_large():
    assert format_currency(12345.67) == "$12345.67"


# ── format_pct sign-suppression for near-zero values ─────────────────────────

def test_format_pct_exact_zero_no_sign():
    """Exact zero should show '0.00%', not '+0.00%'."""
    assert format_pct(0.0) == "0.00%"


def test_format_pct_tiny_negative_rounds_to_zero():
    """Value that rounds to 0.00% at display precision must not show '-0.00%'."""
    assert format_pct(-0.0000001) == "0.00%"


def test_format_pct_tiny_positive_rounds_to_zero():
    assert format_pct(0.0000001) == "0.00%"


def test_format_pct_small_negative_does_not_round_to_zero():
    """A value large enough to show at 2dp should keep its sign."""
    assert format_pct(-0.001) == "-0.10%"


def test_format_pct_small_positive_keeps_sign():
    assert format_pct(0.001) == "+0.10%"
