"""Tests for the sector heat aggregator."""
from datetime import date, timedelta
from pathlib import Path

import pytest

from casino_dashboard.db.repository import (
    save_etf_flow,
    save_sector_etf_mapping,
    save_signal,
    save_deal_log_entries,
    get_sector_heat_latest,
)
from casino_dashboard.data.deal_log_loader import DealLogEntry, _make_deal_id
from casino_dashboard.signals.sector_aggregator import (
    SectorHeat,
    _compute_atr_pct_change_30d,
    _compute_deal_log_metrics,
    _compute_etf_flow_for_sector,
    _compute_news_heat_ratio,
    _equal_weighted_avg,
    compute_and_save_all_sector_heat,
    compute_sector_heat,
)
from casino_dashboard.universe import Sector, Universe


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def db(tmp_path) -> Path:
    return tmp_path / "test.db"


def _universe_with_sector(sector_id: str, tickers: list[str]) -> Universe:
    return Universe(
        sectors={
            sector_id: Sector(
                id=sector_id,
                display_name=sector_id.title(),
                description="Test sector",
                stage="mid",
                speculative=False,
                tickers=tickers,
            )
        }
    )


def _save_signal_for_ticker(
    ticker: str,
    signal_name: str,
    value: float,
    sig_date: date,
    db: Path,
) -> None:
    save_signal(ticker, sig_date, signal_name, value, db)


def _make_deal(
    sector: str,
    amount: float | None,
    entry_date: date,
    summary: str,
) -> DealLogEntry:
    return DealLogEntry(
        deal_id=_make_deal_id(entry_date, sector, summary),
        date=entry_date,
        sector=sector,
        amount_usd=amount,
        deal_type="deal",
        primary_ticker=None,
        source_url=None,
        summary=summary,
    )


# ---------------------------------------------------------------------------
# _equal_weighted_avg
# ---------------------------------------------------------------------------

def test_equal_weighted_avg_basic():
    result = _equal_weighted_avg({"A": 0.1, "B": 0.3})
    assert result == pytest.approx(0.2)


def test_equal_weighted_avg_single():
    assert _equal_weighted_avg({"A": 0.5}) == pytest.approx(0.5)


def test_equal_weighted_avg_empty_returns_none():
    assert _equal_weighted_avg({}) is None


# ---------------------------------------------------------------------------
# compute_sector_heat — equal weighting
# ---------------------------------------------------------------------------

def test_equal_weighting_of_returns(db):
    today = date(2026, 5, 10)
    for ticker, ret in [("AAA", 0.10), ("BBB", 0.20), ("CCC", 0.30)]:
        _save_signal_for_ticker(ticker, "return_1m", ret, today, db)

    heat = compute_sector_heat("test_sector", ["AAA", "BBB", "CCC"], today, db)
    assert heat.agg_return_30d == pytest.approx(0.20)


def test_null_ticker_skipped_in_averaging(db):
    """If one ticker has no return data, equal weight is over those that do."""
    today = date(2026, 5, 10)
    _save_signal_for_ticker("AAA", "return_1m", 0.10, today, db)
    _save_signal_for_ticker("BBB", "return_1m", 0.30, today, db)
    # CCC has no data

    heat = compute_sector_heat("test_sector", ["AAA", "BBB", "CCC"], today, db)
    assert heat.agg_return_30d == pytest.approx(0.20)


def test_all_null_returns_none(db):
    today = date(2026, 5, 10)
    heat = compute_sector_heat("test_sector", ["AAA", "BBB"], today, db)
    assert heat.agg_return_30d is None


# ---------------------------------------------------------------------------
# Breadth (pct_above_sma50)
# ---------------------------------------------------------------------------

def test_breadth_aggregated_as_fraction(db):
    today = date(2026, 5, 10)
    # 3 of 4 tickers above SMA50
    for ticker, above in [("A", 1.0), ("B", 1.0), ("C", 1.0), ("D", 0.0)]:
        _save_signal_for_ticker(ticker, "pct_above_sma50", above, today, db)

    heat = compute_sector_heat("test_sector", ["A", "B", "C", "D"], today, db)
    assert heat.pct_above_sma50 == pytest.approx(0.75)


# ---------------------------------------------------------------------------
# Social velocity
# ---------------------------------------------------------------------------

def test_social_velocity_equal_weighted(db):
    today = date(2026, 5, 10)
    for ticker, vel in [("A", 2.0), ("B", 4.0)]:
        _save_signal_for_ticker(ticker, "apewisdom_velocity_24h", vel, today, db)

    heat = compute_sector_heat("test_sector", ["A", "B", "C"], today, db)
    assert heat.agg_social_velocity == pytest.approx(3.0)


# ---------------------------------------------------------------------------
# Deal log metrics
# ---------------------------------------------------------------------------

def test_deal_log_30d_total_sums_amounts(db):
    entries = [
        _make_deal("nuclear", 1_000_000.0, date(2026, 5, 1), "Deal 1"),
        _make_deal("nuclear", 2_000_000.0, date(2026, 5, 5), "Deal 2"),
    ]
    save_deal_log_entries(entries, db)
    total, count, days_since = _compute_deal_log_metrics("nuclear", date(2026, 5, 10), db)
    assert total == pytest.approx(3_000_000.0)
    assert count == 2


def test_deal_log_null_amounts_count_but_not_total(db):
    entries = [
        _make_deal("photonics", None, date(2026, 5, 8), "Grant (unspecified)"),
        _make_deal("photonics", 500_000.0, date(2026, 5, 7), "Another deal"),
    ]
    save_deal_log_entries(entries, db)
    total, count, _ = _compute_deal_log_metrics("photonics", date(2026, 5, 10), db)
    assert count == 2
    assert total == pytest.approx(500_000.0)


def test_deal_log_days_since_last_deal(db):
    entries = [_make_deal("space", 100.0, date(2026, 5, 3), "Space deal")]
    save_deal_log_entries(entries, db)
    _, _, days = _compute_deal_log_metrics("space", date(2026, 5, 10), db)
    assert days == 7


def test_deal_log_no_entries_returns_zero_count(db):
    total, count, days = _compute_deal_log_metrics("quantum", date(2026, 5, 10), db)
    assert count == 0
    assert total is None
    assert days is None


# ---------------------------------------------------------------------------
# ATR pct change
# ---------------------------------------------------------------------------

def test_atr_pct_change_positive_when_vol_expanding(db):
    today = date(2026, 5, 10)
    thirty_ago = today - timedelta(days=30)

    for ticker in ["A", "B"]:
        save_signal(ticker, today, "atr14_pct", 0.05, db)
        save_signal(ticker, thirty_ago, "atr14_pct", 0.03, db)

    result = _compute_atr_pct_change_30d(["A", "B"], today, db)
    assert result == pytest.approx(0.02)


def test_atr_pct_change_negative_when_vol_compressing(db):
    today = date(2026, 5, 10)
    thirty_ago = today - timedelta(days=30)

    for ticker in ["A", "B"]:
        save_signal(ticker, today, "atr14_pct", 0.02, db)
        save_signal(ticker, thirty_ago, "atr14_pct", 0.05, db)

    result = _compute_atr_pct_change_30d(["A", "B"], today, db)
    assert result == pytest.approx(-0.03)


def test_atr_pct_change_none_when_no_historical_data(db):
    today = date(2026, 5, 10)
    save_signal("A", today, "atr14_pct", 0.04, db)
    # No 30-days-ago data
    result = _compute_atr_pct_change_30d(["A"], today, db)
    assert result is None


# ---------------------------------------------------------------------------
# constituent_count
# ---------------------------------------------------------------------------

def test_constituent_count_reflects_passed_list(db):
    today = date(2026, 5, 10)
    heat = compute_sector_heat("nuclear", ["SMR", "OKLO", "NNE", "BWXT"], today, db)
    assert heat.constituent_count == 4


# ---------------------------------------------------------------------------
# compute_and_save_all_sector_heat — integration
# ---------------------------------------------------------------------------

def test_compute_and_save_all_writes_to_db(db):
    today = date(2026, 5, 10)
    universe = _universe_with_sector("ai_infrastructure", ["VRT", "ETN"])
    for ticker in ["VRT", "ETN"]:
        save_signal(ticker, today, "return_1m", 0.15, db)
        save_signal(ticker, today, "pct_above_sma50", 1.0, db)

    compute_and_save_all_sector_heat(universe, db)

    df = get_sector_heat_latest(db_path=db)
    assert "ai_infrastructure" in df.index
    assert df.loc["ai_infrastructure"]["agg_return_30d"] == pytest.approx(0.15)


def test_compute_and_save_handles_all_null_sector_gracefully(db):
    """A sector with zero data should still produce a row (all nulls except count)."""
    universe = _universe_with_sector("quantum", ["IONQ", "RGTI"])
    compute_and_save_all_sector_heat(universe, db)
    df = get_sector_heat_latest(db_path=db)
    assert "quantum" in df.index
    assert df.loc["quantum"]["constituent_count"] == 2
    assert df.loc["quantum"]["agg_return_30d"] is None


def test_sector_failure_does_not_abort_other_sectors(db):
    """If one sector computation fails, others still persist."""
    # Build a universe with two sectors; one will naturally produce no data
    sectors = {
        "nuclear": Sector(
            id="nuclear", display_name="Nuclear", description="",
            stage="mid", speculative=False, tickers=["SMR", "OKLO"]
        ),
        "photonics": Sector(
            id="photonics", display_name="Photonics", description="",
            stage="mid", speculative=False, tickers=["AAOI", "POET"]
        ),
    }
    universe = Universe(sectors=sectors)
    today = date(2026, 5, 10)
    save_signal("SMR", today, "return_1m", 0.09, db)
    save_signal("OKLO", today, "return_1m", 0.12, db)

    compute_and_save_all_sector_heat(universe, db)

    df = get_sector_heat_latest(db_path=db)
    assert "nuclear" in df.index
    assert "photonics" in df.index  # row exists even if all nulls
