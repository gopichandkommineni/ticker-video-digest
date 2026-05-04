"""Tests for casino_dashboard.ui.loaders (DB calls mocked)."""
import pandas as pd
import pytest
from datetime import date, datetime, timezone

from casino_dashboard.models import NewsItem, TickerSnapshot
from casino_dashboard.ui.loaders import (
    load_news_for_ticker,
    load_price_history,
    load_signals_matrix,
    load_universe_for_ui,
)


def _make_snapshot(ticker: str, snap_date: date, close: float = 10.0) -> TickerSnapshot:
    return TickerSnapshot(
        ticker=ticker,
        date=snap_date,
        open=close,
        high=close,
        low=close,
        close=close,
        adj_close=close,
        volume=1_000_000,
        avg_volume_30d=800_000.0,
        news_items=[],
    )


def test_load_signals_matrix_returns_expected_shape(mocker):
    """load_signals_matrix wraps get_latest_signals_all_tickers and returns its DataFrame."""
    mock_df = pd.DataFrame(
        {"vol_ratio_30d": [1.5, 2.0], "return_1d": [0.5, -0.3]},
        index=pd.Index(["RKLB", "ASTS"], name="ticker"),
    )
    mock_df.columns.name = "signal_name"
    mocker.patch(
        "casino_dashboard.ui.loaders.get_latest_signals_all_tickers",
        return_value=mock_df,
    )
    load_signals_matrix.clear()
    result = load_signals_matrix()
    assert result.shape == (2, 2)
    assert "vol_ratio_30d" in result.columns
    assert "RKLB" in result.index


def test_load_universe_for_ui_returns_dict_with_sector_metadata():
    """load_universe_for_ui returns expected structure with all 8 sectors."""
    load_universe_for_ui.clear()
    result = load_universe_for_ui()
    assert "sectors" in result
    assert "ticker_to_sectors" in result
    assert len(result["sectors"]) == 8
    # RKLB appears in multiple sectors
    assert "RKLB" in result["ticker_to_sectors"]
    assert len(result["ticker_to_sectors"]["RKLB"]) >= 1


def test_load_price_history_with_no_data_returns_empty_df(mocker):
    """load_price_history returns an empty DataFrame when the DB has no rows."""
    mocker.patch(
        "casino_dashboard.ui.loaders.get_history",
        return_value=[],
    )
    load_price_history.clear()
    result = load_price_history("RKLB", days=60)
    assert isinstance(result, pd.DataFrame)
    assert result.empty
    assert list(result.columns) == ["date", "close", "volume"]


def test_cache_decorator_does_not_break_loaders(mocker):
    """@st.cache_data decorated loaders can be called from a non-Streamlit context."""
    snap = _make_snapshot("IONQ", date(2026, 5, 1), close=15.0)
    mocker.patch(
        "casino_dashboard.ui.loaders.get_history",
        return_value=[snap],
    )
    load_price_history.clear()
    result = load_price_history("IONQ", days=60)
    assert not result.empty
    assert "close" in result.columns
    assert float(result["close"].iloc[0]) == pytest.approx(15.0)
