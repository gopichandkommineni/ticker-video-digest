"""Tests for casino_dashboard.ui.formatting helpers."""
import math

import pytest

from casino_dashboard.ui.formatting import (
    color_for_return,
    format_money,
    format_pct,
    format_ratio,
)


def test_format_pct_positive():
    assert format_pct(12.3) == "+12.3%"


def test_format_pct_negative():
    assert format_pct(-3.1) == "-3.1%"


def test_format_pct_none_and_nan():
    assert format_pct(None) == "—"
    assert format_pct(float("nan")) == "—"


def test_format_pct_zero():
    assert format_pct(0.0) == "0.0%"


def test_format_ratio_gt1_and_lt1():
    assert format_ratio(1.52) == "1.52x"
    assert format_ratio(0.75) == "0.75x"


def test_format_ratio_none():
    assert format_ratio(None) == "—"


def test_format_money_gt1000():
    assert format_money(1234.56) == "$1,234.56"


def test_format_money_lt1():
    assert format_money(0.75) == "$0.75"


def test_format_money_none():
    assert format_money(None) == "—"
