"""Tests for the universe YAML ∪ database merge in load_universe."""
import sqlite3
from pathlib import Path

import pytest

from casino_dashboard.db.schema import init_db
from casino_dashboard.universe import Sector, load_universe

_YAML_PATH = Path(__file__).parent.parent / "config" / "themes.yaml"


def _yaml_only_universe():
    return load_universe(_YAML_PATH, db_path=Path("/nonexistent/path/no.db"))


def _init_user_tables(db: Path) -> None:
    init_db(db)


def _add_theme(db: Path, theme_id: str, display_name: str, description: str, speculative: int = 0) -> None:
    with sqlite3.connect(db) as conn:
        conn.execute(
            "INSERT INTO user_added_themes (theme_id, display_name, description, speculative, created_at) "
            "VALUES (?, ?, ?, ?, '2026-01-01T00:00:00+00:00')",
            (theme_id, display_name, description, speculative),
        )


def _add_ticker(db: Path, ticker: str, theme_id: str, status: str = "complete") -> None:
    with sqlite3.connect(db) as conn:
        conn.execute(
            "INSERT INTO user_added_tickers (ticker, theme_id, status, added_at) "
            "VALUES (?, ?, ?, '2026-01-01T00:00:00+00:00')",
            (ticker, theme_id, status),
        )


# ---------------------------------------------------------------------------
# Core invariants
# ---------------------------------------------------------------------------


def test_empty_tables_same_as_yaml_only(tmp_path: Path):
    db = tmp_path / "test.db"
    _init_user_tables(db)

    merged = load_universe(_YAML_PATH, db)
    baseline = _yaml_only_universe()

    assert set(merged.sectors.keys()) == set(baseline.sectors.keys())
    for sid in baseline.sectors:
        assert set(merged.sectors[sid].tickers) == set(baseline.sectors[sid].tickers)


def test_fresh_db_no_crash(tmp_path: Path):
    """load_universe with a non-existent DB must not crash."""
    universe = load_universe(_YAML_PATH, tmp_path / "no_such.db")
    assert len(universe.sectors) > 0


def test_tables_absent_no_crash(tmp_path: Path):
    """An existing DB without the user tables must not crash."""
    db = tmp_path / "test.db"
    # Create DB without calling init_db (no user tables).
    with sqlite3.connect(db) as conn:
        conn.execute("CREATE TABLE dummy (id INTEGER PRIMARY KEY)")

    universe = load_universe(_YAML_PATH, db)
    assert len(universe.sectors) > 0


# ---------------------------------------------------------------------------
# User ticker on a YAML theme
# ---------------------------------------------------------------------------


def test_user_ticker_on_yaml_theme(tmp_path: Path):
    db = tmp_path / "test.db"
    _init_user_tables(db)
    _add_ticker(db, "NEWTICKER", "nuclear", status="complete")

    universe = load_universe(_YAML_PATH, db)
    assert "NEWTICKER" in universe.sectors["nuclear"].tickers


def test_user_ticker_pending_is_included(tmp_path: Path):
    db = tmp_path / "test.db"
    _init_user_tables(db)
    _add_ticker(db, "PENDINGTCK", "nuclear", status="pending")

    universe = load_universe(_YAML_PATH, db)
    assert "PENDINGTCK" in universe.sectors["nuclear"].tickers


def test_user_ticker_failed_is_excluded(tmp_path: Path):
    db = tmp_path / "test.db"
    _init_user_tables(db)
    _add_ticker(db, "FAILEDTCK", "nuclear", status="failed")

    universe = load_universe(_YAML_PATH, db)
    assert "FAILEDTCK" not in universe.sectors["nuclear"].tickers
    assert "FAILEDTCK" not in universe.all_tickers()


# ---------------------------------------------------------------------------
# User ticker on a user-added theme
# ---------------------------------------------------------------------------


def test_user_ticker_on_user_added_theme(tmp_path: Path):
    db = tmp_path / "test.db"
    _init_user_tables(db)
    _add_theme(db, "my_theme", "My Theme", "A custom test theme")
    _add_ticker(db, "MYTCK", "my_theme", status="complete")

    universe = load_universe(_YAML_PATH, db)
    assert "my_theme" in universe.sectors
    assert "MYTCK" in universe.sectors["my_theme"].tickers


def test_user_added_theme_attributes(tmp_path: Path):
    db = tmp_path / "test.db"
    _init_user_tables(db)
    _add_theme(db, "spec_theme", "Speculative Theme", "Very risky stuff", speculative=1)

    universe = load_universe(_YAML_PATH, db)
    sector = universe.sectors["spec_theme"]
    assert sector.display_name == "Speculative Theme"
    assert sector.speculative is True
    assert sector.stage == "user-added"


# ---------------------------------------------------------------------------
# Orphan theme_id
# ---------------------------------------------------------------------------


def test_orphan_theme_id_skipped_no_crash(tmp_path: Path, caplog):
    db = tmp_path / "test.db"
    _init_user_tables(db)
    _add_ticker(db, "ORPHANTCK", "no_such_theme", status="complete")

    import logging
    with caplog.at_level(logging.WARNING, logger="casino_dashboard.universe"):
        universe = load_universe(_YAML_PATH, db)

    assert "ORPHANTCK" not in universe.all_tickers()
    assert any("no_such_theme" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# Type / attribute consistency
# ---------------------------------------------------------------------------


def test_merged_sectors_same_type_as_yaml(tmp_path: Path):
    db = tmp_path / "test.db"
    _init_user_tables(db)
    _add_theme(db, "new_sector", "New Sector", "desc")
    _add_ticker(db, "NEWTCK", "new_sector", status="complete")
    _add_ticker(db, "YAMLTCK", "nuclear", status="complete")

    universe = load_universe(_YAML_PATH, db)

    for sid, sector in universe.sectors.items():
        assert isinstance(sector, Sector), f"Sector {sid!r} is not a Sector instance"
        assert isinstance(sector.id, str)
        assert isinstance(sector.display_name, str)
        assert isinstance(sector.description, str)
        assert isinstance(sector.stage, str)
        assert isinstance(sector.speculative, bool)
        assert isinstance(sector.tickers, list)


def test_all_tickers_includes_user_tickers(tmp_path: Path):
    db = tmp_path / "test.db"
    _init_user_tables(db)
    _add_ticker(db, "USERTCK1", "nuclear", status="complete")
    _add_ticker(db, "USERTCK2", "quantum", status="pending")

    universe = load_universe(_YAML_PATH, db)
    all_t = universe.all_tickers()
    assert "USERTCK1" in all_t
    assert "USERTCK2" in all_t


def test_sectors_for_returns_correct_sector(tmp_path: Path):
    db = tmp_path / "test.db"
    _init_user_tables(db)
    _add_ticker(db, "SECTORTCK", "nuclear", status="complete")

    universe = load_universe(_YAML_PATH, db)
    assert "nuclear" in universe.sectors_for("SECTORTCK")
