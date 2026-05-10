"""Tests for the ETF flows fetcher module."""
import textwrap
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from casino_dashboard.data.etf_flows_fetcher import (
    ETFDailySnapshot,
    ETFFlow,
    calculate_implied_flow,
    compute_etf_flow_ratio,
    fetch_etf_snapshot_today,
    load_etf_mapping_from_yaml,
)


# ---------------------------------------------------------------------------
# calculate_implied_flow
# ---------------------------------------------------------------------------

def test_calculate_implied_flow_basic():
    # AUM went from 1000 to 1050; price return = 5% (50/1000)
    # Price appreciation = 1000 * 0.05 = 50
    # Net flow = (1050 - 1000) - 50 = 0
    result = calculate_implied_flow(
        today_aum=1050.0,
        yesterday_aum=1000.0,
        today_price=105.0,
        yesterday_price=100.0,
    )
    assert result == pytest.approx(0.0)


def test_calculate_implied_flow_positive_net_flow():
    # AUM went from 1000 to 1110; price return = 5%
    # Price appreciation = 1000 * 0.05 = 50
    # Net flow = 110 - 50 = 60
    result = calculate_implied_flow(
        today_aum=1110.0,
        yesterday_aum=1000.0,
        today_price=105.0,
        yesterday_price=100.0,
    )
    assert result == pytest.approx(60.0)


def test_calculate_implied_flow_negative_net_flow():
    # AUM went from 1000 to 940; price return = 5%
    # Price appreciation = 50; Net flow = -60 - 50 = -60
    result = calculate_implied_flow(
        today_aum=940.0,
        yesterday_aum=1000.0,
        today_price=105.0,
        yesterday_price=100.0,
    )
    assert result == pytest.approx(-110.0)


def test_calculate_implied_flow_zero_yesterday_price_returns_none():
    result = calculate_implied_flow(
        today_aum=1000.0,
        yesterday_aum=1000.0,
        today_price=50.0,
        yesterday_price=0.0,
    )
    assert result is None


def test_calculate_implied_flow_zero_yesterday_aum_returns_none():
    result = calculate_implied_flow(
        today_aum=500.0,
        yesterday_aum=0.0,
        today_price=50.0,
        yesterday_price=49.0,
    )
    assert result is None


# ---------------------------------------------------------------------------
# compute_etf_flow_ratio
# ---------------------------------------------------------------------------

def _make_flows(values: dict[date, float], etf="TEST") -> list[ETFFlow]:
    return [ETFFlow(etf_ticker=etf, date=d, net_flow_usd=v, aum_usd=None) for d, v in values.items()]


def _days_back(base: date, n: int) -> dict[date, float]:
    """Build {date: 100.0} for n days ending at base."""
    from datetime import timedelta
    return {base - timedelta(days=i): 100.0 for i in range(n)}


def test_compute_etf_flow_ratio_balanced():
    """When short-term avg equals long-term avg, ratio should be ~1.0."""
    from datetime import timedelta
    as_of = date(2026, 5, 10)
    flows = {as_of - timedelta(days=i): 100.0 for i in range(30)}
    result = compute_etf_flow_ratio(_make_flows(flows), as_of)
    assert result == pytest.approx(1.0, rel=0.01)


def test_compute_etf_flow_ratio_accelerating():
    """Recent 5-day avg > 30-day avg → ratio > 1."""
    from datetime import timedelta
    as_of = date(2026, 5, 10)
    flows = {as_of - timedelta(days=i): (200.0 if i < 5 else 100.0) for i in range(30)}
    result = compute_etf_flow_ratio(_make_flows(flows), as_of)
    assert result is not None
    assert result > 1.0


def test_compute_etf_flow_ratio_insufficient_data_returns_none():
    from datetime import timedelta
    as_of = date(2026, 5, 10)
    flows = {as_of - timedelta(days=i): 100.0 for i in range(5)}  # only 5 days
    result = compute_etf_flow_ratio(_make_flows(flows), as_of)
    assert result is None


def test_compute_etf_flow_ratio_empty_returns_none():
    result = compute_etf_flow_ratio([], date(2026, 5, 10))
    assert result is None


def test_compute_etf_flow_ratio_zero_avg_returns_none():
    from datetime import timedelta
    as_of = date(2026, 5, 10)
    flows = {as_of - timedelta(days=i): 0.0 for i in range(30)}
    result = compute_etf_flow_ratio(_make_flows(flows), as_of)
    assert result is None


# ---------------------------------------------------------------------------
# fetch_etf_snapshot_today — mocked yfinance
# ---------------------------------------------------------------------------

def test_fetch_etf_snapshot_today_success():
    mock_hist = pd.DataFrame(
        {"Close": [150.0]},
        index=pd.to_datetime(["2026-05-10"]),
    )
    mock_ticker = MagicMock()
    mock_ticker.history.return_value = mock_hist
    mock_ticker.info = {"totalAssets": 5_000_000_000}

    with patch("casino_dashboard.data.etf_flows_fetcher.yf.Ticker", return_value=mock_ticker):
        result = fetch_etf_snapshot_today("SMH")

    assert result is not None
    assert result.etf_ticker == "SMH"
    assert result.price == pytest.approx(150.0)
    assert result.aum_usd == pytest.approx(5_000_000_000)


def test_fetch_etf_snapshot_today_no_aum_still_returns_snapshot():
    mock_hist = pd.DataFrame(
        {"Close": [50.0]},
        index=pd.to_datetime(["2026-05-10"]),
    )
    mock_ticker = MagicMock()
    mock_ticker.history.return_value = mock_hist
    mock_ticker.info = {}  # no totalAssets

    with patch("casino_dashboard.data.etf_flows_fetcher.yf.Ticker", return_value=mock_ticker):
        result = fetch_etf_snapshot_today("QTUM")

    assert result is not None
    assert result.aum_usd is None


def test_fetch_etf_snapshot_today_empty_history_returns_none():
    mock_ticker = MagicMock()
    mock_ticker.history.return_value = pd.DataFrame()
    mock_ticker.info = {}

    with patch("casino_dashboard.data.etf_flows_fetcher.yf.Ticker", return_value=mock_ticker):
        result = fetch_etf_snapshot_today("FAKE")

    assert result is None


def test_fetch_etf_snapshot_today_exception_returns_none():
    with patch(
        "casino_dashboard.data.etf_flows_fetcher.yf.Ticker",
        side_effect=Exception("network error"),
    ):
        result = fetch_etf_snapshot_today("SMH")

    assert result is None


# ---------------------------------------------------------------------------
# load_etf_mapping_from_yaml
# ---------------------------------------------------------------------------

def test_load_etf_mapping_parses_tickers(tmp_path):
    content = textwrap.dedent("""
    nuclear:
      - ticker: URNM
        is_primary: true
      - ticker: NLR
        is_primary: false
    photonics:
    """)
    p = tmp_path / "etf_mapping.yaml"
    p.write_text(content)
    mapping = load_etf_mapping_from_yaml(p)
    assert mapping["nuclear"] == ["URNM", "NLR"]
    assert mapping["photonics"] == []  # null → empty list


def test_load_etf_mapping_file_not_found_raises():
    with pytest.raises(FileNotFoundError):
        load_etf_mapping_from_yaml(Path("/nonexistent/etf_mapping.yaml"))


def test_load_etf_mapping_real_config():
    """Smoke test: the shipped config/etf_mapping.yaml must parse without error."""
    config_path = Path("config/etf_mapping.yaml")
    if not config_path.exists():
        pytest.skip("config/etf_mapping.yaml not present")
    mapping = load_etf_mapping_from_yaml(config_path)
    assert "ai_infrastructure" in mapping
    assert "SMH" in mapping["ai_infrastructure"]
    assert mapping.get("photonics") == []  # photonics has no ETFs
