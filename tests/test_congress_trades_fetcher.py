"""Tests for congress_trades_fetcher.py — FMP calls are mocked throughout."""
import json
import os
import urllib.error
from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import pytest

from casino_dashboard.data.congress_trades_fetcher import (
    _make_trade_id,
    _normalize_row,
    _parse_amount,
    _parse_transaction_type,
    _should_drop_asset,
    fetch_recent_congress_trades,
)
from casino_dashboard.models import CongressTrade


# ---------------------------------------------------------------------------
# _parse_amount
# ---------------------------------------------------------------------------

def test_parse_amount_standard_range():
    low, high = _parse_amount("$1,001 - $15,000")
    assert low == 1_001.0
    assert high == 15_000.0


def test_parse_amount_large_range():
    low, high = _parse_amount("$1,000,001 - $5,000,000")
    assert low == 1_000_001.0
    assert high == 5_000_000.0


def test_parse_amount_none():
    assert _parse_amount(None) == (None, None)


def test_parse_amount_over_50m():
    low, high = _parse_amount("Over $50,000,000")
    assert low == 50_000_001.0
    assert high is None


# ---------------------------------------------------------------------------
# _parse_transaction_type
# ---------------------------------------------------------------------------

def test_parse_transaction_type_purchase():
    assert _parse_transaction_type("Purchase") == "buy"


def test_parse_transaction_type_sale_full():
    assert _parse_transaction_type("Sale (Full)") == "sell"


def test_parse_transaction_type_sale_partial():
    assert _parse_transaction_type("Sale (Partial)") == "sell"


def test_parse_transaction_type_exchange():
    assert _parse_transaction_type("Exchange") == "exchange"


def test_parse_transaction_type_unknown():
    assert _parse_transaction_type("Transfer") == "other"


# ---------------------------------------------------------------------------
# _should_drop_asset — asset-type filter
# ---------------------------------------------------------------------------

def test_should_drop_broad_market_etf_spy():
    assert _should_drop_asset("SPY", "ETF") is True


def test_should_drop_broad_market_etf_vti():
    assert _should_drop_asset("VTI", "ETF") is True


def test_should_keep_sector_etf_ita():
    assert _should_drop_asset("ITA", "ETF") is False


def test_should_keep_sector_etf_xle():
    assert _should_drop_asset("XLE", "ETF") is False


def test_should_drop_bond():
    assert _should_drop_asset("SOME_BOND", "Municipal Bond") is True


def test_should_drop_mutual_fund():
    assert _should_drop_asset("FXAIX", "Mutual Fund") is True


def test_should_drop_treasury():
    assert _should_drop_asset("T-BILL", "Treasury Note") is True


def test_should_keep_stock():
    assert _should_drop_asset("NVDA", "Stock") is False


def test_should_keep_stock_option():
    assert _should_drop_asset("NVDA", "Stock Option") is False


# ---------------------------------------------------------------------------
# _normalize_row
# ---------------------------------------------------------------------------

def _make_row(**overrides):
    base = {
        "firstName": "Nancy",
        "lastName": "Pelosi",
        "ticker": "NVDA",
        "assetType": "Stock",
        "transactionDate": "2025-12-01",
        "disclosureDate": "2026-01-10",
        "type": "Purchase",
        "amount": "$1,000,001 - $5,000,000",
        "party": "D",
    }
    base.update(overrides)
    return base


def test_normalize_row_basic():
    row = _make_row()
    trade = _normalize_row(row, "house", {})
    assert trade is not None
    assert trade.full_name == "Nancy Pelosi"
    assert trade.ticker == "NVDA"
    assert trade.transaction_type == "buy"
    assert trade.chamber == "house"
    assert trade.party == "D"
    assert trade.amount_low == 1_000_001.0
    assert trade.amount_high == 5_000_000.0


def test_normalize_row_drops_broad_etf():
    row = _make_row(ticker="SPY", assetType="ETF")
    trade = _normalize_row(row, "senate", {})
    assert trade is None


def test_normalize_row_drops_bond():
    row = _make_row(ticker="MUNI", assetType="Municipal Bond")
    trade = _normalize_row(row, "house", {})
    assert trade is None


def test_normalize_row_keeps_sector_etf():
    row = _make_row(ticker="ITA", assetType="ETF")
    trade = _normalize_row(row, "house", {})
    assert trade is not None
    assert trade.ticker == "ITA"


def test_normalize_row_missing_ticker_returns_none():
    row = _make_row(ticker="")
    trade = _normalize_row(row, "house", {})
    assert trade is None


def test_normalize_row_bad_date_returns_none():
    row = _make_row(transactionDate="not-a-date")
    trade = _normalize_row(row, "house", {})
    assert trade is None


def test_normalize_row_bioguide_matched_by_name():
    row = _make_row()
    name_to_bioguide = {"nancy pelosi": "P000197"}
    trade = _normalize_row(row, "house", name_to_bioguide)
    assert trade is not None
    assert trade.bioguide_id == "P000197"


def test_normalize_row_bioguide_none_when_no_match():
    row = _make_row()
    trade = _normalize_row(row, "house", {})
    assert trade is not None
    assert trade.bioguide_id is None


def test_normalize_row_unknown_party_becomes_I():
    row = _make_row(party="")
    trade = _normalize_row(row, "house", {})
    assert trade is not None
    assert trade.party == "I"


# ---------------------------------------------------------------------------
# _make_trade_id — deterministic deduplication key
# ---------------------------------------------------------------------------

def test_make_trade_id_is_deterministic():
    id1 = _make_trade_id("Nancy Pelosi", "2025-12-01", "NVDA", "$1,000,001 - $5,000,000")
    id2 = _make_trade_id("Nancy Pelosi", "2025-12-01", "NVDA", "$1,000,001 - $5,000,000")
    assert id1 == id2


def test_make_trade_id_differs_on_ticker():
    id1 = _make_trade_id("Nancy Pelosi", "2025-12-01", "NVDA", "$1,000,001 - $5,000,000")
    id2 = _make_trade_id("Nancy Pelosi", "2025-12-01", "AMD", "$1,000,001 - $5,000,000")
    assert id1 != id2


# ---------------------------------------------------------------------------
# fetch_recent_congress_trades (mocked HTTP)
# ---------------------------------------------------------------------------

def _fmp_response_bytes(rows):
    return json.dumps(rows).encode()


def _make_fmp_row(chamber_suffix="", **overrides):
    base = {
        "firstName": "Nancy",
        "lastName": "Pelosi",
        "ticker": "NVDA",
        "assetType": "Stock",
        "transactionDate": "2026-04-01",
        "disclosureDate": "2026-04-20",
        "type": "Purchase",
        "amount": "$100,001 - $250,000",
        "party": "D",
    }
    base.update(overrides)
    return base


def _setup_fmp_mock(senate_rows, house_rows):
    class _FakeResp:
        def __init__(self, data):
            self._data = data

        def read(self):
            return self._data

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    def side_effect(url, timeout=30):
        if "senate" in url:
            return _FakeResp(_fmp_response_bytes(senate_rows))
        if "house" in url:
            return _FakeResp(_fmp_response_bytes(house_rows))
        raise ValueError(f"Unexpected URL: {url}")

    return side_effect


def test_fetch_returns_trade_records(monkeypatch):
    monkeypatch.setenv("FMP_API_KEY", "test-key")
    senate_row = _make_fmp_row()
    house_row = _make_fmp_row(firstName="Tommy", lastName="Tuberville", ticker="LMT", party="R")

    with patch("casino_dashboard.data.congress_trades_fetcher.urllib.request.urlopen",
               side_effect=_setup_fmp_mock([senate_row], [house_row])):
        trades = fetch_recent_congress_trades(days_back=90)

    assert len(trades) == 2
    tickers = {t.ticker for t in trades}
    assert "NVDA" in tickers
    assert "LMT" in tickers


def test_fetch_drops_broad_etf(monkeypatch):
    monkeypatch.setenv("FMP_API_KEY", "test-key")
    rows = [_make_fmp_row(ticker="SPY", assetType="ETF")]

    with patch("casino_dashboard.data.congress_trades_fetcher.urllib.request.urlopen",
               side_effect=_setup_fmp_mock(rows, [])):
        trades = fetch_recent_congress_trades(days_back=90)

    assert len(trades) == 0


def test_fetch_keeps_sector_etf(monkeypatch):
    monkeypatch.setenv("FMP_API_KEY", "test-key")
    rows = [_make_fmp_row(ticker="ITA", assetType="ETF")]

    with patch("casino_dashboard.data.congress_trades_fetcher.urllib.request.urlopen",
               side_effect=_setup_fmp_mock(rows, [])):
        trades = fetch_recent_congress_trades(days_back=90)

    assert len(trades) == 1
    assert trades[0].ticker == "ITA"


def test_fetch_dedupe_by_trade_id(monkeypatch):
    """Same row returned twice (e.g. from overlapping pages) appears once."""
    monkeypatch.setenv("FMP_API_KEY", "test-key")
    row = _make_fmp_row()

    with patch("casino_dashboard.data.congress_trades_fetcher.urllib.request.urlopen",
               side_effect=_setup_fmp_mock([row, row], [])):
        trades = fetch_recent_congress_trades(days_back=90)

    assert len(trades) == 1


def test_fetch_bioguide_none_when_unmatched(monkeypatch):
    monkeypatch.setenv("FMP_API_KEY", "test-key")
    rows = [_make_fmp_row()]

    with patch("casino_dashboard.data.congress_trades_fetcher.urllib.request.urlopen",
               side_effect=_setup_fmp_mock(rows, [])):
        trades = fetch_recent_congress_trades(days_back=90, legislators=[])

    assert trades[0].bioguide_id is None


def test_fetch_raises_on_404(monkeypatch):
    monkeypatch.setenv("FMP_API_KEY", "test-key")

    with patch("casino_dashboard.data.congress_trades_fetcher.urllib.request.urlopen",
               side_effect=urllib.error.HTTPError(None, 404, "Not Found", {}, None)):
        with pytest.raises(RuntimeError, match="404"):
            fetch_recent_congress_trades(days_back=90)


def test_fetch_raises_without_api_key(monkeypatch):
    monkeypatch.delenv("FMP_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="FMP_API_KEY"):
        fetch_recent_congress_trades(days_back=90)


def test_fetch_bioguide_filter_applied(monkeypatch):
    """Only trades matching bioguide_filter are returned after name lookup."""
    monkeypatch.setenv("FMP_API_KEY", "test-key")
    rows = [
        _make_fmp_row(firstName="Nancy", lastName="Pelosi", ticker="NVDA"),
        _make_fmp_row(firstName="Tommy", lastName="Tuberville", ticker="LMT", party="R"),
    ]
    legislators = [
        {"bioguide_id": "P000197", "full_name": "Nancy Pelosi", "last_name": "Pelosi"},
        {"bioguide_id": "T000278", "full_name": "Tommy Tuberville", "last_name": "Tuberville"},
    ]

    with patch("casino_dashboard.data.congress_trades_fetcher.urllib.request.urlopen",
               side_effect=_setup_fmp_mock(rows, [])):
        trades = fetch_recent_congress_trades(
            days_back=90,
            bioguide_filter=["P000197"],
            legislators=legislators,
        )

    assert len(trades) == 1
    assert trades[0].ticker == "NVDA"
    assert trades[0].bioguide_id == "P000197"
