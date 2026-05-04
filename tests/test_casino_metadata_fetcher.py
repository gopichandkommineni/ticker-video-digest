"""Tests for casino_dashboard.data.yfinance_metadata — all yfinance calls mocked."""
from datetime import date, datetime, timezone, timedelta
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from casino_dashboard.data.yfinance_metadata import (
    TickerMetadata,
    _classify_earnings_time,
    fetch_metadata_for_universe,
    fetch_ticker_metadata,
)


def _make_ticker_mock(info: dict, earnings_df: pd.DataFrame | None = None) -> MagicMock:
    mock = MagicMock()
    mock.info = info
    if earnings_df is None:
        earnings_df = pd.DataFrame()
    mock.earnings_dates = earnings_df
    return mock


def _bmo_dt() -> datetime:
    """Return a datetime that falls before 9:30 AM ET."""
    from zoneinfo import ZoneInfo
    return datetime(2026, 5, 7, 8, 0, 0, tzinfo=ZoneInfo("America/New_York"))


def _amc_dt() -> datetime:
    """Return a datetime that falls after 4:00 PM ET."""
    from zoneinfo import ZoneInfo
    return datetime(2026, 5, 7, 16, 30, 0, tzinfo=ZoneInfo("America/New_York"))


def _midday_dt() -> datetime:
    """Return a datetime that is midday ET — not BMO or AMC."""
    from zoneinfo import ZoneInfo
    return datetime(2026, 5, 7, 12, 0, 0, tzinfo=ZoneInfo("America/New_York"))


def _make_earnings_df(*datetimes: datetime) -> pd.DataFrame:
    """Build a minimal earnings_dates DataFrame indexed by the given datetimes."""
    return pd.DataFrame(index=pd.DatetimeIndex(datetimes))


# ── Test 1: all fields populated → all map correctly ──────────────────────────

def test_all_fields_populated():
    info = {
        "fiftyTwoWeekHigh": 190.0,
        "fiftyTwoWeekLow": 12.5,
        "shortPercentOfFloat": 0.135,
        "shortRatio": 0.95,
        "targetMeanPrice": 111.75,
        "heldPercentInsiders": 0.0479,
        "heldPercentInstitutions": 0.6428,
        "marketCap": 13_970_000_000,
        "totalRevenue": 455_710_000,
        "revenueGrowth": 0.8275,
        "profitMargins": -0.0839,
        "beta": 3.76,
    }
    future = datetime.now(tz=timezone.utc) + timedelta(days=5)
    past = datetime.now(tz=timezone.utc) - timedelta(days=90)
    earnings_df = _make_earnings_df(future, past)
    mock_ticker = _make_ticker_mock(info, earnings_df)

    with patch("casino_dashboard.data.yfinance_metadata.yf.Ticker", return_value=mock_ticker):
        meta = fetch_ticker_metadata("AAOI")

    assert meta.ticker == "AAOI"
    assert meta.fifty_two_week_high == pytest.approx(190.0)
    assert meta.fifty_two_week_low == pytest.approx(12.5)
    assert meta.short_pct_of_float == pytest.approx(0.135)
    assert meta.short_ratio_days == pytest.approx(0.95)
    assert meta.analyst_target_mean == pytest.approx(111.75)
    assert meta.held_pct_insiders == pytest.approx(0.0479)
    assert meta.held_pct_institutions == pytest.approx(0.6428)
    assert meta.market_cap == pytest.approx(13_970_000_000)
    assert meta.revenue_ttm == pytest.approx(455_710_000)
    assert meta.revenue_growth_yoy == pytest.approx(0.8275)
    assert meta.profit_margin == pytest.approx(-0.0839)
    assert meta.beta == pytest.approx(3.76)
    assert meta.next_earnings_date is not None
    assert meta.last_earnings_date is not None


# ── Test 2: missing single field → that field is None, others ok ─────────────

def test_single_missing_field_becomes_none():
    info = {
        "fiftyTwoWeekHigh": 190.0,
        # fiftyTwoWeekLow deliberately absent
        "shortPercentOfFloat": 0.135,
        "shortRatio": 0.95,
        "targetMeanPrice": 111.75,
        "heldPercentInsiders": 0.0479,
        "heldPercentInstitutions": 0.6428,
        "marketCap": 13_970_000_000,
        "totalRevenue": 455_710_000,
        "revenueGrowth": 0.8275,
        "profitMargins": -0.0839,
        "beta": 3.76,
    }
    mock_ticker = _make_ticker_mock(info)
    with patch("casino_dashboard.data.yfinance_metadata.yf.Ticker", return_value=mock_ticker):
        meta = fetch_ticker_metadata("AAOI")

    assert meta.fifty_two_week_low is None
    assert meta.fifty_two_week_high == pytest.approx(190.0)
    assert meta.beta == pytest.approx(3.76)


# ── Test 3: all fields missing → all None, no crash ──────────────────────────

def test_all_fields_missing_returns_all_none():
    mock_ticker = _make_ticker_mock({})
    with patch("casino_dashboard.data.yfinance_metadata.yf.Ticker", return_value=mock_ticker):
        meta = fetch_ticker_metadata("AAOI")

    assert meta.ticker == "AAOI"
    assert meta.fifty_two_week_high is None
    assert meta.fifty_two_week_low is None
    assert meta.short_pct_of_float is None
    assert meta.short_ratio_days is None
    assert meta.analyst_target_mean is None
    assert meta.held_pct_insiders is None
    assert meta.held_pct_institutions is None
    assert meta.market_cap is None
    assert meta.revenue_ttm is None
    assert meta.revenue_growth_yoy is None
    assert meta.profit_margin is None
    assert meta.beta is None
    assert meta.next_earnings_date is None
    assert meta.next_earnings_time is None
    assert meta.last_earnings_date is None


# ── Test 4: BMO timestamp → next_earnings_time = 'BMO' ───────────────────────

def test_earnings_bmo_classification():
    future_bmo = _bmo_dt() + timedelta(days=5)
    earnings_df = _make_earnings_df(future_bmo)
    mock_ticker = _make_ticker_mock({}, earnings_df)
    with patch("casino_dashboard.data.yfinance_metadata.yf.Ticker", return_value=mock_ticker):
        meta = fetch_ticker_metadata("AAOI")

    assert meta.next_earnings_time == "BMO"


# ── Test 5: AMC timestamp → next_earnings_time = 'AMC' ───────────────────────

def test_earnings_amc_classification():
    future_amc = _amc_dt() + timedelta(days=5)
    earnings_df = _make_earnings_df(future_amc)
    mock_ticker = _make_ticker_mock({}, earnings_df)
    with patch("casino_dashboard.data.yfinance_metadata.yf.Ticker", return_value=mock_ticker):
        meta = fetch_ticker_metadata("AAOI")

    assert meta.next_earnings_time == "AMC"


# ── Test 6: midday timestamp → next_earnings_time = None ─────────────────────

def test_earnings_midday_classification_is_none():
    future_midday = _midday_dt() + timedelta(days=5)
    earnings_df = _make_earnings_df(future_midday)
    mock_ticker = _make_ticker_mock({}, earnings_df)
    with patch("casino_dashboard.data.yfinance_metadata.yf.Ticker", return_value=mock_ticker):
        meta = fetch_ticker_metadata("AAOI")

    assert meta.next_earnings_time is None


# ── Test 7: earnings_dates empty → both dates None ────────────────────────────

def test_empty_earnings_dates():
    mock_ticker = _make_ticker_mock({}, pd.DataFrame())
    with patch("casino_dashboard.data.yfinance_metadata.yf.Ticker", return_value=mock_ticker):
        meta = fetch_ticker_metadata("AAOI")

    assert meta.next_earnings_date is None
    assert meta.last_earnings_date is None
    assert meta.next_earnings_time is None


# ── Test 8: only past dates → next is None, last is set ──────────────────────

def test_only_past_earnings_dates():
    past1 = datetime.now(tz=timezone.utc) - timedelta(days=90)
    past2 = datetime.now(tz=timezone.utc) - timedelta(days=180)
    earnings_df = _make_earnings_df(past1, past2)
    mock_ticker = _make_ticker_mock({}, earnings_df)
    with patch("casino_dashboard.data.yfinance_metadata.yf.Ticker", return_value=mock_ticker):
        meta = fetch_ticker_metadata("AAOI")

    assert meta.next_earnings_date is None
    assert meta.last_earnings_date == past1.date()


# ── Test 9: only future dates → next is set, last is None ────────────────────

def test_only_future_earnings_dates():
    future1 = datetime.now(tz=timezone.utc) + timedelta(days=10)
    future2 = datetime.now(tz=timezone.utc) + timedelta(days=100)
    earnings_df = _make_earnings_df(future1, future2)
    mock_ticker = _make_ticker_mock({}, earnings_df)
    with patch("casino_dashboard.data.yfinance_metadata.yf.Ticker", return_value=mock_ticker):
        meta = fetch_ticker_metadata("AAOI")

    assert meta.next_earnings_date == future1.date()
    assert meta.last_earnings_date is None


# ── Test 10: universe fetch handles per-ticker exceptions gracefully ──────────

def test_universe_fetch_handles_exceptions():
    def _side_effect(ticker: str):
        mock = MagicMock()
        if ticker == "BAD":
            mock.info = None
            mock.earnings_dates = pd.DataFrame()
        else:
            mock.info = {"beta": 1.5}
            mock.earnings_dates = pd.DataFrame()
        return mock

    with patch("casino_dashboard.data.yfinance_metadata.yf.Ticker", side_effect=_side_effect):
        with patch("casino_dashboard.data.yfinance_metadata.time.sleep"):
            results = fetch_metadata_for_universe(["AAOI", "BAD", "POET"])

    assert len(results) == 3
    aaoi = next(r for r in results if r.ticker == "AAOI")
    assert aaoi.beta == pytest.approx(1.5)
    bad = next(r for r in results if r.ticker == "BAD")
    assert bad.beta is None
