"""Tests for validate_ticker — mocks yfinance, no network calls."""
from unittest.mock import MagicMock, patch

import pytest

from casino_dashboard.data.ticker_validation import validate_ticker


def _make_mock_ticker(info: dict):
    mock = MagicMock()
    mock.info = info
    return mock


# ---------------------------------------------------------------------------
# Valid ticker
# ---------------------------------------------------------------------------


def test_valid_ticker_returns_true_and_name():
    mock_info = {
        "longName": "Palantir Technologies Inc.",
        "regularMarketPrice": 42.50,
    }
    with patch("casino_dashboard.data.ticker_validation.yf.Ticker", return_value=_make_mock_ticker(mock_info)):
        valid, name, error = validate_ticker("PLTR")

    assert valid is True
    assert name == "Palantir Technologies Inc."
    assert error is None


def test_valid_ticker_uses_shortname_fallback():
    mock_info = {
        "shortName": "RocketLab USA",
        "previousClose": 10.0,
    }
    with patch("casino_dashboard.data.ticker_validation.yf.Ticker", return_value=_make_mock_ticker(mock_info)):
        valid, name, error = validate_ticker("RKLB")

    assert valid is True
    assert name == "RocketLab USA"
    assert error is None


def test_valid_ticker_uses_current_price_fallback():
    mock_info = {
        "longName": "Some Corp",
        "currentPrice": 5.25,
    }
    with patch("casino_dashboard.data.ticker_validation.yf.Ticker", return_value=_make_mock_ticker(mock_info)):
        valid, name, _ = validate_ticker("SOME")

    assert valid is True
    assert name == "Some Corp"


# ---------------------------------------------------------------------------
# Invalid ticker
# ---------------------------------------------------------------------------


def test_invalid_ticker_no_name_returns_false():
    mock_info = {"symbol": "ZZZZQ", "trailingPegRatio": None}
    with patch("casino_dashboard.data.ticker_validation.yf.Ticker", return_value=_make_mock_ticker(mock_info)):
        valid, name, error = validate_ticker("ZZZZQ")

    assert valid is False
    assert name is None
    assert error is not None
    assert "ZZZZQ" in error


def test_invalid_ticker_name_but_no_price():
    mock_info = {"longName": "Ghost Corp", "regularMarketPrice": None}
    with patch("casino_dashboard.data.ticker_validation.yf.Ticker", return_value=_make_mock_ticker(mock_info)):
        valid, name, error = validate_ticker("GHOST")

    assert valid is False
    assert name is None
    assert error is not None


def test_yfinance_exception_returns_false():
    with patch(
        "casino_dashboard.data.ticker_validation.yf.Ticker",
        side_effect=Exception("network timeout"),
    ):
        valid, name, error = validate_ticker("BADTCK")

    assert valid is False
    assert name is None
    assert "network timeout" in (error or "")


def test_empty_info_dict_returns_false():
    with patch("casino_dashboard.data.ticker_validation.yf.Ticker", return_value=_make_mock_ticker({})):
        valid, name, error = validate_ticker("EMPTY")

    assert valid is False
    assert name is None
