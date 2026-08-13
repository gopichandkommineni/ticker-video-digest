"""Unit tests for ticker resolution — yfinance search is mocked."""
from unittest.mock import patch

from core.social_media.reddit.ticker_resolver import (
    company_name_for,
    looks_like_ticker,
    resolve_ticker,
)


def test_looks_like_ticker():
    assert looks_like_ticker("RKLB")
    assert looks_like_ticker("rklb")
    assert looks_like_ticker("BRK.B")
    assert not looks_like_ticker("Rocket Lab")
    assert not looks_like_ticker("coinbase global")  # has space
    assert not looks_like_ticker("VeryLongName")      # too long


def test_resolve_ticker_passthrough_for_symbol():
    assert resolve_ticker("rklb") == "RKLB"
    # returned even if outside a provided universe
    assert resolve_ticker("TSLA", universe={"RKLB"}) == "TSLA"


def test_resolve_name_via_search():
    quotes = [{"symbol": "RKLB", "quoteType": "EQUITY", "longname": "Rocket Lab USA, Inc."}]
    with patch("core.social_media.reddit.ticker_resolver._yf_search", return_value=quotes):
        assert resolve_ticker("Rocket Lab") == "RKLB"


def test_resolve_name_skips_non_equity():
    quotes = [
        {"symbol": "BTC-USD", "quoteType": "CRYPTOCURRENCY"},
        {"symbol": "RKLB", "quoteType": "EQUITY"},
    ]
    with patch("core.social_media.reddit.ticker_resolver._yf_search", return_value=quotes):
        assert resolve_ticker("rocket lab crypto") == "RKLB"


def test_resolve_name_unresolved_returns_none():
    with patch("core.social_media.reddit.ticker_resolver._yf_search", return_value=[]):
        assert resolve_ticker("some nonexistent company xyz") is None


def test_company_name_for_matches_symbol():
    quotes = [
        {"symbol": "OTHER", "longname": "Wrong Co"},
        {"symbol": "RKLB", "longname": "Rocket Lab USA, Inc."},
    ]
    with patch("core.social_media.reddit.ticker_resolver._yf_search", return_value=quotes):
        assert company_name_for("RKLB") == "Rocket Lab USA, Inc."


def test_company_name_for_none_when_no_match():
    with patch("core.social_media.reddit.ticker_resolver._yf_search", return_value=[]):
        assert company_name_for("RKLB") is None
