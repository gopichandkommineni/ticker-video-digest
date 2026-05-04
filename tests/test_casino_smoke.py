"""
Integration test — hits real yfinance API.
Run with: pytest tests/test_casino_smoke.py -v -m integration
Skipped in unit-only runs (-m "not integration").
"""
import pytest

from casino_dashboard.data.yfinance_client import fetch_ticker_history
from casino_dashboard.models import TickerSnapshot


@pytest.mark.integration
def test_rklb_real_snapshot():
    result = fetch_ticker_history("RKLB", lookback_days=90)

    assert len(result) > 0, "fetch_ticker_history returned no snapshots for RKLB"
    # result[0] is the oldest entry; use the latest for avg_volume_30d (needs 30 prior days)
    first = result[0]
    latest = result[-1]
    assert isinstance(first, TickerSnapshot)
    assert first.ticker == "RKLB"
    assert first.open > 0
    assert first.high >= first.low
    assert first.close > 0
    assert first.volume > 0
    assert latest.avg_volume_30d is not None and latest.avg_volume_30d > 0
