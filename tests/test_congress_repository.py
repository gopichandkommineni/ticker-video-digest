"""Tests for the congress DB repository functions."""
from datetime import date
from pathlib import Path

import pytest

from casino_dashboard.db.repository import (
    get_recent_trades_for_members,
    get_star_members,
    get_watched_members,
    upsert_congress_members,
    upsert_congress_trades,
)
from casino_dashboard.db.schema import init_db
from casino_dashboard.models import CongressTrade


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_member(bioguide, first="Alice", last="Smith", is_watched=0, is_star=0, committees=None):
    return {
        "bioguide_id": bioguide,
        "full_name": f"{first} {last}",
        "first_name": first,
        "last_name": last,
        "party": "D",
        "state": "CA",
        "chamber": "house",
        "is_watched": is_watched,
        "is_star": is_star,
        "committees": committees or [],
    }


def _make_trade(
    trade_id,
    bioguide_id="A000001",
    ticker="NVDA",
    txn_date=date(2026, 4, 1),
    disc_date=date(2026, 4, 20),
    party="D",
    chamber="house",
):
    return CongressTrade(
        trade_id=trade_id,
        bioguide_id=bioguide_id,
        full_name="Alice Smith",
        chamber=chamber,
        party=party,
        ticker=ticker,
        asset_type="Stock",
        transaction_type="buy",
        transaction_date=txn_date,
        disclosure_date=disc_date,
        amount_low=100_001.0,
        amount_high=250_000.0,
        filing_id=None,
    )


# ---------------------------------------------------------------------------
# upsert_congress_members — idempotency
# ---------------------------------------------------------------------------

def test_upsert_congress_members_idempotent(tmp_path):
    db = tmp_path / "test.db"
    init_db(db)
    member = _make_member("A000001", is_watched=1)
    upsert_congress_members([member], db)
    upsert_congress_members([member], db)  # second call must not raise
    df = get_watched_members(db)
    assert len(df) == 1


def test_upsert_congress_members_updates_on_conflict(tmp_path):
    db = tmp_path / "test.db"
    init_db(db)
    member = _make_member("A000001", is_watched=1, is_star=0)
    upsert_congress_members([member], db)
    member2 = _make_member("A000001", is_watched=1, is_star=1)
    upsert_congress_members([member2], db)
    df = get_watched_members(db)
    assert df.loc[df["bioguide_id"] == "A000001", "is_star"].iloc[0] == 1


# ---------------------------------------------------------------------------
# is_watched + is_star flags
# ---------------------------------------------------------------------------

def test_is_watched_and_is_star_both_set(tmp_path):
    """A member who appears in both lists has both flags set to 1."""
    db = tmp_path / "test.db"
    init_db(db)
    member = _make_member("A000001", is_watched=1, is_star=1)
    upsert_congress_members([member], db)

    watched_df = get_watched_members(db)
    star_df = get_star_members(db)

    assert len(watched_df) == 1
    assert len(star_df) == 1
    assert watched_df.iloc[0]["bioguide_id"] == "A000001"
    assert star_df.iloc[0]["bioguide_id"] == "A000001"


def test_is_watched_only(tmp_path):
    db = tmp_path / "test.db"
    init_db(db)
    upsert_congress_members([_make_member("A000001", is_watched=1, is_star=0)], db)
    assert len(get_watched_members(db)) == 1
    assert len(get_star_members(db)) == 0


def test_is_star_only(tmp_path):
    db = tmp_path / "test.db"
    init_db(db)
    upsert_congress_members([_make_member("A000001", is_watched=0, is_star=1)], db)
    assert len(get_watched_members(db)) == 0
    assert len(get_star_members(db)) == 1


# ---------------------------------------------------------------------------
# committee upsert
# ---------------------------------------------------------------------------

def test_committee_upserted_with_member(tmp_path):
    db = tmp_path / "test.db"
    init_db(db)
    member = _make_member("A000001", is_watched=1, committees=[
        {"committee_id": "HSAS", "committee_name": "House Armed Services",
         "title": "Chair", "rank": 1}
    ])
    upsert_congress_members([member], db)

    import sqlite3
    with sqlite3.connect(db) as conn:
        rows = conn.execute(
            "SELECT committee_id, title FROM congress_member_committees WHERE bioguide_id=?",
            ("A000001",)
        ).fetchall()
    assert len(rows) == 1
    assert rows[0] == ("HSAS", "Chair")


# ---------------------------------------------------------------------------
# upsert_congress_trades — idempotency and deduplication
# ---------------------------------------------------------------------------

def test_upsert_congress_trades_idempotent(tmp_path):
    db = tmp_path / "test.db"
    init_db(db)
    upsert_congress_members([_make_member("A000001")], db)
    trade = _make_trade("trade001")
    upsert_congress_trades([trade], db)
    upsert_congress_trades([trade], db)  # must not raise or duplicate

    df = get_recent_trades_for_members(["A000001"], days_back=365, db_path=db)
    assert len(df) == 1


# ---------------------------------------------------------------------------
# get_recent_trades_for_members — date and bioguide filtering
# ---------------------------------------------------------------------------

def test_get_recent_trades_filters_by_bioguide(tmp_path):
    db = tmp_path / "test.db"
    init_db(db)
    upsert_congress_members([
        _make_member("A000001"),
        _make_member("B000002", first="Bob", last="Jones"),
    ], db)
    upsert_congress_trades([
        _make_trade("t001", bioguide_id="A000001", ticker="NVDA"),
        _make_trade("t002", bioguide_id="B000002", ticker="LMT"),
    ], db)

    df = get_recent_trades_for_members(["A000001"], days_back=365, db_path=db)
    assert len(df) == 1
    assert df.iloc[0]["ticker"] == "NVDA"


def test_get_recent_trades_filters_by_date(tmp_path):
    db = tmp_path / "test.db"
    init_db(db)
    upsert_congress_members([_make_member("A000001")], db)
    recent_trade = _make_trade("t001", disc_date=date(2026, 4, 20))
    old_trade = _make_trade("t002", disc_date=date(2020, 1, 1), ticker="OLD")
    upsert_congress_trades([recent_trade, old_trade], db)

    # 365-day window should include recent but not 2020
    df = get_recent_trades_for_members(["A000001"], days_back=365, db_path=db)
    tickers = df["ticker"].tolist()
    assert "NVDA" in tickers
    assert "OLD" not in tickers


def test_get_recent_trades_empty_bioguide_list(tmp_path):
    db = tmp_path / "test.db"
    init_db(db)
    df = get_recent_trades_for_members([], days_back=90, db_path=db)
    assert df.empty


def test_get_recent_trades_sorted_desc(tmp_path):
    db = tmp_path / "test.db"
    init_db(db)
    upsert_congress_members([_make_member("A000001")], db)
    upsert_congress_trades([
        _make_trade("t001", disc_date=date(2026, 3, 1), ticker="NVDA"),
        _make_trade("t002", disc_date=date(2026, 4, 15), ticker="LMT"),
    ], db)

    df = get_recent_trades_for_members(["A000001"], days_back=365, db_path=db)
    assert df.iloc[0]["ticker"] == "LMT"  # more recent first


# ---------------------------------------------------------------------------
# Schema smoke test — init_db creates congress tables
# ---------------------------------------------------------------------------

def test_init_db_creates_congress_tables(tmp_path):
    db = tmp_path / "test.db"
    init_db(db)
    import sqlite3
    with sqlite3.connect(db) as conn:
        tables = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
    assert "congress_members" in tables
    assert "congress_member_committees" in tables
    assert "congress_trades" in tables
