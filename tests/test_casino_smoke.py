"""
Integration test — hits real yfinance API.
Run with: pytest tests/test_casino_smoke.py -v -m integration
Skipped in unit-only runs (-m "not integration").
"""
import pytest

from casino_dashboard.data.yfinance_client import fetch_ticker_snapshot


@pytest.mark.integration
def test_rklb_real_snapshot():
    snap = fetch_ticker_snapshot("RKLB", lookback_days=90)

    assert snap is not None, "fetch_ticker_snapshot returned None for RKLB"
    assert snap.ticker == "RKLB"

    # yfinance history(period="3mo") should yield ~60 trading days
    # We only get a single TickerSnapshot (latest day), but avg_volume_30d
    # is computed from the full 3-month history; assert it looks sane.
    assert snap.open > 0
    assert snap.high >= snap.low
    assert snap.close > 0
    assert snap.volume > 0
    assert snap.avg_volume_30d is not None and snap.avg_volume_30d > 0

    # News: yfinance usually returns at least a few items for an active ticker
    assert len(snap.news_items) > 0, "Expected at least one news item for RKLB"
