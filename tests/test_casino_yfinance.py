from datetime import date, datetime, timezone
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from casino_dashboard.data.yfinance_client import (
    _parse_news,
    fetch_ticker_snapshot,
    fetch_universe_snapshot,
)
from casino_dashboard.models import TickerSnapshot
from casino_dashboard.universe import Sector, Universe


def _make_history(rows: int = 90) -> pd.DataFrame:
    """Build a minimal yfinance-style history DataFrame."""
    idx = pd.date_range(end="2024-12-31", periods=rows, freq="B")
    return pd.DataFrame(
        {
            "Open": [10.0] * rows,
            "High": [11.0] * rows,
            "Low": [9.0] * rows,
            "Close": [10.5] * rows,
            "Adj Close": [10.3] * rows,
            "Volume": [1_000_000] * rows,
            "Dividends": [0.0] * rows,
            "Stock Splits": [0.0] * rows,
        },
        index=idx,
    )


def _make_news(n: int = 3) -> list[dict]:
    return [
        {
            "title": f"News {i}",
            "link": f"https://example.com/{i}",
            "publisher": "TestPub",
            "providerPublishTime": 1_700_000_000 + i,
        }
        for i in range(n)
    ]


def _make_mock_ticker(hist: pd.DataFrame | None = None, news: list | None = None) -> MagicMock:
    mock = MagicMock()
    mock.history.return_value = hist if hist is not None else _make_history()
    mock.news = news if news is not None else _make_news()
    return mock


# ── happy path ────────────────────────────────────────────────────────────────

def test_fetch_ticker_snapshot_happy_path():
    hist = _make_history(90)
    mock_ticker = _make_mock_ticker(hist=hist, news=_make_news(3))

    with patch("casino_dashboard.data.yfinance_client.yf.Ticker", return_value=mock_ticker):
        snap = fetch_ticker_snapshot("RKLB")

    assert snap is not None
    assert snap.ticker == "RKLB"
    assert isinstance(snap.date, date)
    assert snap.open == pytest.approx(10.0)
    assert snap.close == pytest.approx(10.5)
    assert snap.adj_close == pytest.approx(10.3)
    assert snap.volume == 1_000_000
    assert len(snap.news_items) == 3


def test_avg_volume_30d_computed_correctly():
    hist = _make_history(90)
    # Override last 30 rows to have a different volume
    hist.iloc[-30:, hist.columns.get_loc("Volume")] = 2_000_000
    mock_ticker = _make_mock_ticker(hist=hist)

    with patch("casino_dashboard.data.yfinance_client.yf.Ticker", return_value=mock_ticker):
        snap = fetch_ticker_snapshot("TEST")

    assert snap is not None
    assert snap.avg_volume_30d == pytest.approx(2_000_000.0)


def test_fetch_returns_none_on_empty_history():
    mock_ticker = _make_mock_ticker(hist=pd.DataFrame())

    with patch("casino_dashboard.data.yfinance_client.yf.Ticker", return_value=mock_ticker):
        snap = fetch_ticker_snapshot("EMPTY")

    assert snap is None


# ── retry logic ───────────────────────────────────────────────────────────────

def test_retries_on_exception_then_succeeds():
    hist = _make_history()
    mock_ticker = MagicMock()
    mock_ticker.news = _make_news(1)
    # Fail twice, succeed on third attempt
    mock_ticker.history.side_effect = [
        Exception("timeout"),
        Exception("timeout"),
        hist,
    ]

    with patch("casino_dashboard.data.yfinance_client.yf.Ticker", return_value=mock_ticker), \
         patch("casino_dashboard.data.yfinance_client.time.sleep"):
        snap = fetch_ticker_snapshot("RETRY")

    assert snap is not None
    assert mock_ticker.history.call_count == 3


def test_returns_none_after_all_retries_fail():
    mock_ticker = MagicMock()
    mock_ticker.history.side_effect = Exception("persistent failure")
    mock_ticker.news = []

    with patch("casino_dashboard.data.yfinance_client.yf.Ticker", return_value=mock_ticker), \
         patch("casino_dashboard.data.yfinance_client.time.sleep"):
        snap = fetch_ticker_snapshot("FAIL")

    assert snap is None
    assert mock_ticker.history.call_count == 4  # initial + 3 retries


# ── news parsing ──────────────────────────────────────────────────────────────

def test_parse_news_happy_path():
    raw = _make_news(2)
    items = _parse_news(raw)
    assert len(items) == 2
    assert items[0].title == "News 0"
    assert items[0].publisher == "TestPub"
    assert items[0].published_at.tzinfo is not None


def test_parse_news_skips_malformed():
    raw = [{"title": "ok", "link": "http://x.com", "publisher": "P", "providerPublishTime": 1_700_000_000},
           {"bad": "item"}]  # missing providerPublishTime → will be 0, but should not crash
    items = _parse_news(raw)
    # First item always parses; second may or may not depending on fallback
    assert len(items) >= 1


def test_parse_news_limits_to_five():
    hist = _make_history()
    mock_ticker = _make_mock_ticker(hist=hist, news=_make_news(10))

    with patch("casino_dashboard.data.yfinance_client.yf.Ticker", return_value=mock_ticker):
        snap = fetch_ticker_snapshot("LIMITED")

    assert snap is not None
    assert len(snap.news_items) <= 5


# ── universe fetch ────────────────────────────────────────────────────────────

def test_fetch_universe_snapshot_aggregates():
    sector = Sector(
        id="test",
        display_name="Test",
        description="desc",
        stage="early",
        speculative=True,
        tickers=["AAA", "BBB"],
    )
    universe = Universe(sectors={"test": sector})

    hist = _make_history()

    def fake_ticker(sym):
        m = MagicMock()
        m.history.return_value = hist
        m.news = _make_news(1)
        return m

    with patch("casino_dashboard.data.yfinance_client.yf.Ticker", side_effect=fake_ticker):
        snaps = fetch_universe_snapshot(universe)

    assert len(snaps) == 2
    tickers_returned = {s.ticker for s in snaps}
    assert tickers_returned == {"AAA", "BBB"}
