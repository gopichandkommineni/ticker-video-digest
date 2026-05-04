"""Tests for the sector filter pre-selection helper used by All Tickers page."""
import pytest

from casino_dashboard.ui.loaders import resolve_sector_default


ALL_SECTORS = ["nuclear", "defense", "space", "cyber", "energy", "fintech", "biotech", "industrial"]


def test_resolve_sector_default_with_query_param_returns_single_sector():
    """sector=nuclear in query params pre-selects only Nuclear."""
    result = resolve_sector_default(
        session_state={},
        query_params={"sector": "nuclear"},
        all_sector_ids=ALL_SECTORS,
    )
    assert result == ["nuclear"]


def test_resolve_sector_default_no_param_returns_all_sectors():
    """No query param and no session state returns all sectors."""
    result = resolve_sector_default(
        session_state={},
        query_params={},
        all_sector_ids=ALL_SECTORS,
    )
    assert result == ALL_SECTORS


def test_resolve_sector_default_session_state_takes_priority():
    """session_state preselect_sector takes priority over query params."""
    result = resolve_sector_default(
        session_state={"preselect_sector": "defense"},
        query_params={"sector": "nuclear"},
        all_sector_ids=ALL_SECTORS,
    )
    assert result == ["defense"]


def test_resolve_sector_default_session_state_is_consumed():
    """preselect_sector is popped from session_state after reading."""
    state = {"preselect_sector": "nuclear"}
    resolve_sector_default(
        session_state=state,
        query_params={},
        all_sector_ids=ALL_SECTORS,
    )
    assert "preselect_sector" not in state


def test_resolve_sector_default_unknown_sector_id_returns_all():
    """An unrecognized sector_id falls back to all sectors."""
    result = resolve_sector_default(
        session_state={},
        query_params={"sector": "unicorn"},
        all_sector_ids=ALL_SECTORS,
    )
    assert result == ALL_SECTORS


def test_resolve_sector_default_nuclear_maps_to_correct_display_name():
    """nuclear sector_id is in the returned list, which format_func maps to 'Nuclear'."""
    from casino_dashboard.ui.loaders import load_universe_for_ui

    load_universe_for_ui.clear()
    universe = load_universe_for_ui()
    sectors = universe["sectors"]
    all_ids = list(sectors.keys())

    result = resolve_sector_default(
        session_state={},
        query_params={"sector": "nuclear"},
        all_sector_ids=all_ids,
    )
    assert result == ["nuclear"]
    assert sectors["nuclear"].display_name == "Nuclear"
