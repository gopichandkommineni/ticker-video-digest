"""Tests for the user_added_tickers / user_added_themes repository functions."""
import sqlite3
from pathlib import Path

import pytest

from casino_dashboard.db.repository import (
    add_user_theme,
    add_user_ticker,
    get_user_added_themes,
    get_user_added_tickers,
    remove_user_ticker,
    set_user_ticker_status,
)
from casino_dashboard.db.schema import init_db


@pytest.fixture()
def db(tmp_path: Path) -> Path:
    path = tmp_path / "test.db"
    init_db(path)
    return path


# ---------------------------------------------------------------------------
# Ticker add / get
# ---------------------------------------------------------------------------


def test_add_and_get_ticker(db: Path):
    add_user_ticker("NEWTCK", "nuclear", "New Corp", "tester", db)
    df = get_user_added_tickers(db)

    assert len(df) == 1
    row = df.iloc[0]
    assert row["ticker"] == "NEWTCK"
    assert row["theme_id"] == "nuclear"
    assert row["company_name"] == "New Corp"
    assert row["status"] == "pending"
    assert row["added_by"] == "tester"


def test_add_ticker_optional_fields_none(db: Path):
    add_user_ticker("TCK2", "quantum", None, None, db)
    df = get_user_added_tickers(db)

    row = df.iloc[0]
    assert row["company_name"] is None or row["company_name"] != row["company_name"]  # None or NaN
    assert row["added_by"] is None or row["added_by"] != row["added_by"]


def test_add_duplicate_raises(db: Path):
    add_user_ticker("DUPE", "nuclear", None, None, db)
    with pytest.raises(ValueError, match="DUPE"):
        add_user_ticker("DUPE", "quantum", None, None, db)


def test_get_returns_empty_when_no_rows(db: Path):
    df = get_user_added_tickers(db)
    assert df.empty


def test_get_returns_empty_when_tables_absent(tmp_path: Path):
    """get_user_added_tickers must not crash when tables don't exist."""
    db = tmp_path / "no_tables.db"
    # Connect once to create the file but leave it empty.
    with sqlite3.connect(db) as conn:
        conn.execute("CREATE TABLE dummy (id INTEGER)")
    df = get_user_added_tickers(db)
    assert df.empty


# ---------------------------------------------------------------------------
# Status update
# ---------------------------------------------------------------------------


def test_set_status_to_complete(db: Path):
    add_user_ticker("STATUSTCK", "space", None, None, db)
    set_user_ticker_status("STATUSTCK", "complete", None, "2026-01-01T00:00:00+00:00", db)

    df = get_user_added_tickers(db)
    row = df[df["ticker"] == "STATUSTCK"].iloc[0]
    assert row["status"] == "complete"
    assert row["last_fetch_at"] == "2026-01-01T00:00:00+00:00"


def test_set_status_to_failed(db: Path):
    add_user_ticker("FAILTCK", "space", None, None, db)
    set_user_ticker_status("FAILTCK", "failed", "No data", "2026-01-01T00:00:00+00:00", db)

    df = get_user_added_tickers(db)
    row = df[df["ticker"] == "FAILTCK"].iloc[0]
    assert row["status"] == "failed"
    assert row["status_detail"] == "No data"


def test_set_status_idempotent(db: Path):
    add_user_ticker("IDEMPOTENT", "nuclear", None, None, db)
    set_user_ticker_status("IDEMPOTENT", "complete", None, "2026-01-01T00:00:00", db)
    set_user_ticker_status("IDEMPOTENT", "complete", None, "2026-01-02T00:00:00", db)

    df = get_user_added_tickers(db)
    assert len(df) == 1
    assert df.iloc[0]["last_fetch_at"] == "2026-01-02T00:00:00"


# ---------------------------------------------------------------------------
# Remove ticker
# ---------------------------------------------------------------------------


def test_remove_ticker(db: Path):
    add_user_ticker("REMOVEME", "nuclear", None, None, db)
    remove_user_ticker("REMOVEME", db)

    df = get_user_added_tickers(db)
    assert df.empty


def test_remove_nonexistent_ticker_no_error(db: Path):
    remove_user_ticker("DOESNOTEXIST", db)


# ---------------------------------------------------------------------------
# Theme add / get
# ---------------------------------------------------------------------------


def test_add_and_get_theme(db: Path):
    add_user_theme("my_sector", "My Sector", "Some description", False, "tester", db)
    df = get_user_added_themes(db)

    assert len(df) == 1
    row = df.iloc[0]
    assert row["theme_id"] == "my_sector"
    assert row["display_name"] == "My Sector"
    assert row["description"] == "Some description"
    assert row["speculative"] == 0


def test_add_duplicate_theme_raises(db: Path):
    add_user_theme("dupe_theme", "Dupe", "desc", False, None, db)
    with pytest.raises(ValueError, match="dupe_theme"):
        add_user_theme("dupe_theme", "Dupe 2", "desc2", False, None, db)


def test_get_themes_empty_when_no_rows(db: Path):
    df = get_user_added_themes(db)
    assert df.empty


def test_get_themes_returns_empty_when_tables_absent(tmp_path: Path):
    db = tmp_path / "no_tables.db"
    with sqlite3.connect(db) as conn:
        conn.execute("CREATE TABLE dummy (id INTEGER)")
    df = get_user_added_themes(db)
    assert df.empty


def test_speculative_theme_stored_correctly(db: Path):
    add_user_theme("spec_sector", "Spec Sector", "risky", True, None, db)
    df = get_user_added_themes(db)
    assert df.iloc[0]["speculative"] == 1
