import math
from datetime import date, datetime, timezone
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from casino_dashboard.data.yfinance_client import (
    _parse_news,
    fetch_ticker_history,
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

def test_fetch_ticker_history_returns_list():
    hist = _make_history(90)
    mock_ticker = _make_mock_ticker(hist=hist, news=_make_news(3))

    with patch("casino_dashboard.data.yfinance_client.yf.Ticker", return_value=mock_ticker):
        snaps = fetch_ticker_history("RKLB")

    assert isinstance(snaps, list)
    assert len(snaps) == 90
    last = snaps[-1]
    assert last.ticker == "RKLB"
    assert isinstance(last.date, date)
    assert last.open == pytest.approx(10.0)
    assert last.close == pytest.approx(10.5)
    assert last.adj_close == pytest.approx(10.3)
    assert last.volume == 1_000_000
    # News only on the last snapshot
    assert len(last.news_items) == 3
    for snap in snaps[:-1]:
        assert snap.news_items == []


def test_500_trading_days_yield_roughly_500_snapshots():
    hist = _make_history(500)
    mock_ticker = _make_mock_ticker(hist=hist)

    with patch("casino_dashboard.data.yfinance_client.yf.Ticker", return_value=mock_ticker):
        snaps = fetch_ticker_history("RKLB")

    # 2y of business-day history (~500 rows) → exactly 500 snapshots
    assert len(snaps) == 500


def test_avg_volume_30d_computed_correctly():
    hist = _make_history(90)
    mock_ticker = _make_mock_ticker(hist=hist)

    with patch("casino_dashboard.data.yfinance_client.yf.Ticker", return_value=mock_ticker):
        snaps = fetch_ticker_history("TEST")

    assert snaps
    # Uniform volume of 1_000_000 — rolling mean should equal that for all
    # rows after the first (row 0 has NaN → None since no prior window)
    assert snaps[0].avg_volume_30d is None
    assert snaps[-1].avg_volume_30d == pytest.approx(1_000_000.0)


def test_avg_volume_30d_rolling_window():
    hist = _make_history(36)
    # Give each row a distinct volume: row i → (i+1) * 1000
    for i in range(36):
        hist.iloc[i, hist.columns.get_loc("Volume")] = (i + 1) * 1000

    mock_ticker = _make_mock_ticker(hist=hist)

    with patch("casino_dashboard.data.yfinance_client.yf.Ticker", return_value=mock_ticker):
        snaps = fetch_ticker_history("TEST")

    # Row 5 avg = mean of rows 0-4 volumes = mean(1000,2000,3000,4000,5000) = 3000
    assert snaps[5].avg_volume_30d == pytest.approx(3000.0)
    # Row 35 avg = mean of rows 5-34 volumes = mean(6000,...,35000) = 20500
    assert snaps[35].avg_volume_30d == pytest.approx(20500.0)


def test_fetch_returns_empty_list_on_empty_history():
    mock_ticker = _make_mock_ticker(hist=pd.DataFrame())

    with patch("casino_dashboard.data.yfinance_client.yf.Ticker", return_value=mock_ticker):
        snaps = fetch_ticker_history("EMPTY")

    assert snaps == []


# ── NaN price rows ──────────────────────────────────────────────────────────────

def test_skips_rows_with_nan_close():
    """yfinance NaN bars must be dropped: sqlite3 stores NaN as NULL, which
    would otherwise trip the NOT NULL constraint on ticker_snapshots.close."""
    hist = _make_history(10)
    # Punch a NaN into the Close of row 5 (e.g. a halted/partial session).
    hist.iloc[5, hist.columns.get_loc("Close")] = float("nan")

    mock_ticker = _make_mock_ticker(hist=hist)

    with patch("casino_dashboard.data.yfinance_client.yf.Ticker", return_value=mock_ticker):
        snaps = fetch_ticker_history("NANROW")

    assert len(snaps) == 9
    assert all(not math.isnan(s.close) for s in snaps)


def test_no_nan_in_any_price_field():
    hist = _make_history(8)
    hist.iloc[2, hist.columns.get_loc("Open")] = float("nan")
    hist.iloc[4, hist.columns.get_loc("Volume")] = float("nan")

    mock_ticker = _make_mock_ticker(hist=hist)

    with patch("casino_dashboard.data.yfinance_client.yf.Ticker", return_value=mock_ticker):
        snaps = fetch_ticker_history("NANROW2")

    assert len(snaps) == 6


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
        snaps = fetch_ticker_history("RETRY")

    assert snaps
    assert mock_ticker.history.call_count == 3


def test_returns_empty_list_after_all_retries_fail():
    mock_ticker = MagicMock()
    mock_ticker.history.side_effect = Exception("persistent failure")
    mock_ticker.news = []

    with patch("casino_dashboard.data.yfinance_client.yf.Ticker", return_value=mock_ticker), \
         patch("casino_dashboard.data.yfinance_client.time.sleep"):
        snaps = fetch_ticker_history("FAIL")

    assert snaps == []
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
        snaps = fetch_ticker_history("LIMITED")

    assert snaps
    assert len(snaps[-1].news_items) <= 5


def _make_news_new_format(n: int = 3) -> list[dict]:
    """Build news items in the yfinance 2025+ nested format."""
    return [
        {
            "id": f"id-{i}",
            "content": {
                "title": f"New Format News {i}",
                "pubDate": f"2026-05-0{i + 1}T12:00:00Z",
                "provider": {"displayName": f"Publisher{i}"},
                "canonicalUrl": {"url": f"https://example.com/new/{i}"},
                "clickThroughUrl": {"url": f"https://example.com/click/{i}"},
            },
        }
        for i in range(n)
    ]


def test_parse_news_new_format_happy_path():
    raw = _make_news_new_format(2)
    items = _parse_news(raw)
    assert len(items) == 2
    assert items[0].title == "New Format News 0"
    assert items[0].publisher == "Publisher0"
    assert items[0].link == "https://example.com/new/0"
    assert items[0].published_at.year == 2026
    assert items[0].published_at.tzinfo is not None


def test_parse_news_legacy_format_happy_path():
    raw = _make_news(2)
    items = _parse_news(raw)
    assert len(items) == 2
    assert items[0].title == "News 0"
    assert items[0].publisher == "TestPub"
    assert items[0].link == "https://example.com/0"
    assert items[0].published_at.tzinfo is not None


def test_parse_news_empty_list():
    items = _parse_news([])
    assert items == []


def test_parse_news_skips_missing_title():
    raw = [
        {
            "content": {
                "pubDate": "2026-05-01T12:00:00Z",
                "provider": {"displayName": "Pub"},
                "canonicalUrl": {"url": "https://example.com/1"},
            }
        }
    ]
    items = _parse_news(raw)
    assert items == []


def test_parse_news_skips_empty_title():
    raw = [
        {
            "content": {
                "title": "",
                "pubDate": "2026-05-01T12:00:00Z",
                "provider": {"displayName": "Pub"},
                "canonicalUrl": {"url": "https://example.com/1"},
            }
        }
    ]
    items = _parse_news(raw)
    assert items == []


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
        result = fetch_universe_snapshot(universe)

    assert isinstance(result, dict)
    assert set(result.keys()) == {"AAA", "BBB"}
    for ticker, snaps in result.items():
        assert isinstance(snaps, list)
        assert len(snaps) > 0
