"""Tests for refresh_single_ticker — mocks all network calls."""
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from casino_dashboard.db.repository import get_user_added_tickers
from casino_dashboard.db.schema import init_db
from casino_dashboard.models import TickerSnapshot


def _make_snapshots(ticker: str, n: int = 60) -> list[TickerSnapshot]:
    snaps = []
    for i in range(n):
        d = date(2024, 1, 1) + timedelta(days=i)
        snaps.append(TickerSnapshot(
            ticker=ticker,
            date=d,
            open=100.0,
            high=101.0,
            low=99.0,
            close=100.0 + i * 0.1,
            adj_close=100.0 + i * 0.1,
            volume=1_000_000,
            avg_volume_30d=None,
            news_items=[],
        ))
    return snaps


@pytest.fixture()
def db(tmp_path: Path) -> Path:
    path = tmp_path / "test.db"
    init_db(path)
    return path


# ---------------------------------------------------------------------------
# Success path
# ---------------------------------------------------------------------------


def test_refresh_single_ticker_success(db: Path):
    snapshots = _make_snapshots("TESTCK")

    mock_meta = MagicMock()
    mock_meta.ticker = "TESTCK"
    mock_meta.fifty_two_week_high = 120.0
    mock_meta.fifty_two_week_low = 80.0
    mock_meta.short_pct_of_float = None
    mock_meta.short_ratio_days = None
    mock_meta.analyst_target_mean = None
    mock_meta.analyst_target_high = None
    mock_meta.analyst_target_low = None
    mock_meta.analyst_count = None
    mock_meta.held_pct_insiders = None
    mock_meta.held_pct_institutions = None
    mock_meta.market_cap = 1e9
    mock_meta.revenue_ttm = None
    mock_meta.revenue_growth_yoy = None
    mock_meta.profit_margin = None
    mock_meta.beta = 1.2
    mock_meta.next_earnings_date = None
    mock_meta.next_earnings_time = None
    mock_meta.last_earnings_date = None

    with (
        patch(
            "casino_dashboard.jobs.refresh_sources.fetch_ticker_history",
            return_value=snapshots,
        ),
        patch(
            "casino_dashboard.jobs.refresh_sources.fetch_ticker_metadata",
            return_value=mock_meta,
        ),
    ):
        from casino_dashboard.jobs.daily_refresh import refresh_single_ticker
        success, error = refresh_single_ticker("TESTCK", db)

    assert success is True
    assert error is None

    # Verify snapshots were written.
    from casino_dashboard.db.repository import get_history
    history = get_history("TESTCK", 200, db)
    assert len(history) == 60


def test_refresh_single_ticker_writes_signals(db: Path):
    snapshots = _make_snapshots("SIGCK", n=60)

    mock_meta = MagicMock()
    mock_meta.ticker = "SIGCK"
    for attr in [
        "fifty_two_week_high", "fifty_two_week_low", "short_pct_of_float",
        "short_ratio_days", "analyst_target_mean", "analyst_target_high",
        "analyst_target_low", "analyst_count", "held_pct_insiders",
        "held_pct_institutions", "market_cap", "revenue_ttm",
        "revenue_growth_yoy", "profit_margin", "beta",
        "next_earnings_date", "next_earnings_time", "last_earnings_date",
    ]:
        setattr(mock_meta, attr, None)

    with (
        patch(
            "casino_dashboard.jobs.refresh_sources.fetch_ticker_history",
            return_value=snapshots,
        ),
        patch(
            "casino_dashboard.jobs.refresh_sources.fetch_ticker_metadata",
            return_value=mock_meta,
        ),
    ):
        from casino_dashboard.jobs.daily_refresh import refresh_single_ticker
        success, _ = refresh_single_ticker("SIGCK", db)

    assert success is True

    from casino_dashboard.db.repository import get_signals
    today = date.today()
    signals = get_signals("SIGCK", today, db)
    # At least return_1d should be present with 60 days of history.
    assert "return_1d" in signals


# ---------------------------------------------------------------------------
# Failure path
# ---------------------------------------------------------------------------


def test_refresh_single_ticker_fails_on_empty_history(db: Path):
    with patch(
        "casino_dashboard.jobs.refresh_sources.fetch_ticker_history",
        return_value=[],
    ):
        from casino_dashboard.jobs.daily_refresh import refresh_single_ticker
        success, error = refresh_single_ticker("BADCK", db)

    assert success is False
    assert error is not None
    assert "No price history" in error


def test_refresh_single_ticker_fails_on_exception(db: Path):
    with patch(
        "casino_dashboard.jobs.refresh_sources.fetch_ticker_history",
        side_effect=RuntimeError("network error"),
    ):
        from casino_dashboard.jobs.daily_refresh import refresh_single_ticker
        success, error = refresh_single_ticker("ERRCK", db)

    assert success is False
    assert error is not None
    assert "network error" in error


def test_refresh_metadata_failure_does_not_abort(db: Path):
    """Metadata failure is non-fatal; price data and signals should still be saved."""
    snapshots = _make_snapshots("METAFAIL", n=60)

    with (
        patch(
            "casino_dashboard.jobs.refresh_sources.fetch_ticker_history",
            return_value=snapshots,
        ),
        patch(
            "casino_dashboard.jobs.refresh_sources.fetch_ticker_metadata",
            side_effect=RuntimeError("meta fetch error"),
        ),
    ):
        from casino_dashboard.jobs.daily_refresh import refresh_single_ticker
        success, error = refresh_single_ticker("METAFAIL", db)

    # Should still succeed since price history was saved.
    assert success is True
    assert error is None

    from casino_dashboard.db.repository import get_history
    history = get_history("METAFAIL", 200, db)
    assert len(history) == 60
