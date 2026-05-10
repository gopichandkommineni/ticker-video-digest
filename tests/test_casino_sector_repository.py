"""Tests for repository functions covering the new sector-ranking tables."""
from datetime import date
from pathlib import Path

import pytest

from casino_dashboard.db.repository import (
    get_deal_log_for_sector,
    get_deal_log_latest_date_per_sector,
    get_etf_flows,
    get_sector_etf_mapping,
    get_sector_heat_latest,
    save_deal_log_entries,
    save_etf_flow,
    save_sector_etf_mapping,
    save_sector_heat,
)
from casino_dashboard.data.deal_log_loader import DealLogEntry


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def db(tmp_path) -> Path:
    return tmp_path / "test.db"


# ---------------------------------------------------------------------------
# ETF flows
# ---------------------------------------------------------------------------

def test_save_and_get_etf_flow(db):
    d = date(2026, 5, 10)
    save_etf_flow("SMH", d, net_flow_usd=1_000_000.0, aum_usd=20_000_000_000.0, price=250.0, db_path=db)
    df = get_etf_flows("SMH", days=10, db_path=db)
    assert len(df) == 1
    assert df.iloc[0]["net_flow_usd"] == pytest.approx(1_000_000.0)
    assert df.iloc[0]["aum_usd"] == pytest.approx(20_000_000_000.0)


def test_etf_flow_upsert_on_conflict(db):
    d = date(2026, 5, 10)
    save_etf_flow("SMH", d, net_flow_usd=1_000.0, aum_usd=100.0, price=10.0, db_path=db)
    save_etf_flow("SMH", d, net_flow_usd=2_000.0, aum_usd=200.0, price=20.0, db_path=db)
    df = get_etf_flows("SMH", days=10, db_path=db)
    assert len(df) == 1
    assert df.iloc[0]["net_flow_usd"] == pytest.approx(2_000.0)


def test_etf_flow_null_net_flow_allowed(db):
    d = date(2026, 5, 10)
    save_etf_flow("QTUM", d, net_flow_usd=None, aum_usd=500_000_000.0, price=45.0, db_path=db)
    df = get_etf_flows("QTUM", days=5, db_path=db)
    assert len(df) == 1
    assert df.iloc[0]["net_flow_usd"] is None


def test_get_etf_flows_empty_returns_empty_df(db):
    df = get_etf_flows("NONEXISTENT", days=30, db_path=db)
    assert df.empty
    assert list(df.columns) == ["date", "net_flow_usd", "aum_usd", "price"]


# ---------------------------------------------------------------------------
# Sector ETF mapping
# ---------------------------------------------------------------------------

def test_save_and_get_sector_etf_mapping(db):
    save_sector_etf_mapping("nuclear", "URNM", is_primary=True, db_path=db)
    save_sector_etf_mapping("nuclear", "NLR", is_primary=False, db_path=db)
    df = get_sector_etf_mapping(db_path=db)
    assert len(df) == 2
    assert set(df["etf_ticker"].tolist()) == {"URNM", "NLR"}


def test_sector_etf_mapping_upsert(db):
    save_sector_etf_mapping("nuclear", "URNM", is_primary=False, db_path=db)
    save_sector_etf_mapping("nuclear", "URNM", is_primary=True, db_path=db)
    df = get_sector_etf_mapping(db_path=db)
    assert len(df) == 1
    assert df.iloc[0]["is_primary"] == 1


# ---------------------------------------------------------------------------
# Deal log
# ---------------------------------------------------------------------------

def _make_entry(
    sector: str = "nuclear",
    amount: float | None = 1_000_000.0,
    entry_date: date = date(2026, 5, 1),
    summary: str = "Test deal",
) -> DealLogEntry:
    from casino_dashboard.data.deal_log_loader import _make_deal_id
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


def test_save_and_get_deal_log(db):
    entries = [
        _make_entry("nuclear", 1_000_000.0, date(2026, 5, 1), "Nuclear deal"),
        _make_entry("nuclear", 2_000_000.0, date(2026, 5, 3), "Another nuclear deal"),
    ]
    save_deal_log_entries(entries, db_path=db)
    df = get_deal_log_for_sector("nuclear", days=30, db_path=db)
    assert len(df) == 2


def test_deal_log_idempotent_on_duplicate_id(db):
    entry = _make_entry("ai_infrastructure", 5_000_000.0, date(2026, 5, 1), "AI deal")
    save_deal_log_entries([entry], db_path=db)
    save_deal_log_entries([entry], db_path=db)  # duplicate
    df = get_deal_log_for_sector("ai_infrastructure", days=30, db_path=db)
    assert len(df) == 1


def test_deal_log_filters_by_sector(db):
    entries = [
        _make_entry("nuclear", summary="Nuclear deal"),
        _make_entry("space", summary="Space deal"),
    ]
    save_deal_log_entries(entries, db_path=db)
    df = get_deal_log_for_sector("nuclear", days=30, db_path=db)
    assert len(df) == 1
    assert df.iloc[0]["sector"] == "nuclear"


def test_deal_log_filters_by_days(db):
    old_entry = _make_entry("nuclear", entry_date=date(2026, 1, 1), summary="Old deal")
    recent_entry = _make_entry("nuclear", entry_date=date(2026, 5, 9), summary="Recent deal")
    save_deal_log_entries([old_entry, recent_entry], db_path=db)
    df = get_deal_log_for_sector("nuclear", days=30, db_path=db)
    # Only the recent entry should appear in the 30-day window (as of 2026-05-10)
    assert len(df) == 1
    assert "Recent" in df.iloc[0]["summary"]


def test_get_deal_log_latest_date_per_sector(db):
    entries = [
        _make_entry("nuclear", entry_date=date(2026, 5, 1), summary="Deal 1"),
        _make_entry("nuclear", entry_date=date(2026, 5, 8), summary="Deal 2"),
        _make_entry("space", entry_date=date(2026, 4, 15), summary="Space deal"),
    ]
    save_deal_log_entries(entries, db_path=db)
    latest = get_deal_log_latest_date_per_sector(db_path=db)
    assert latest["nuclear"] == "2026-05-08"
    assert latest["space"] == "2026-04-15"


# ---------------------------------------------------------------------------
# Sector heat
# ---------------------------------------------------------------------------

def test_save_and_get_sector_heat(db):
    save_sector_heat(
        sector="ai_infrastructure",
        heat_date=date(2026, 5, 10),
        etf_flow_5d_30d_ratio=1.5,
        deal_log_30d_total_usd=80_000_000_000.0,
        deal_log_30d_count=2,
        days_since_last_deal=7,
        agg_social_velocity=2.3,
        news_heat_ratio=1.8,
        agg_return_30d=0.184,
        pct_above_sma50=0.875,
        agg_atr_pct_change_30d=0.05,
        constituent_count=8,
        db_path=db,
    )
    df = get_sector_heat_latest(db_path=db)
    assert "ai_infrastructure" in df.index
    row = df.loc["ai_infrastructure"]
    assert row["etf_flow_5d_30d_ratio"] == pytest.approx(1.5)
    assert row["constituent_count"] == 8


def test_sector_heat_upsert_updates_values(db):
    kwargs = dict(
        sector="nuclear",
        heat_date=date(2026, 5, 10),
        etf_flow_5d_30d_ratio=1.0,
        deal_log_30d_total_usd=None,
        deal_log_30d_count=0,
        days_since_last_deal=5,
        agg_social_velocity=1.1,
        news_heat_ratio=0.9,
        agg_return_30d=0.09,
        pct_above_sma50=0.6,
        agg_atr_pct_change_30d=0.01,
        constituent_count=10,
        db_path=db,
    )
    save_sector_heat(**kwargs)
    save_sector_heat(**{**kwargs, "agg_return_30d": 0.12})

    df = get_sector_heat_latest(db_path=db)
    assert df.loc["nuclear"]["agg_return_30d"] == pytest.approx(0.12)


def test_get_sector_heat_latest_empty_returns_empty_df(db):
    df = get_sector_heat_latest(db_path=db)
    assert df.empty


def test_sector_heat_null_fields_allowed(db):
    save_sector_heat(
        sector="photonics",
        heat_date=date(2026, 5, 10),
        etf_flow_5d_30d_ratio=None,  # no ETF for photonics
        deal_log_30d_total_usd=1_200_000_000.0,
        deal_log_30d_count=1,
        days_since_last_deal=4,
        agg_social_velocity=1.8,
        news_heat_ratio=2.1,
        agg_return_30d=0.142,
        pct_above_sma50=0.714,
        agg_atr_pct_change_30d=None,
        constituent_count=7,
        db_path=db,
    )
    df = get_sector_heat_latest(db_path=db)
    assert "photonics" in df.index
    assert df.loc["photonics"]["etf_flow_5d_30d_ratio"] is None
