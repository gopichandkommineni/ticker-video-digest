"""Tests for star_traders_loader.py."""
import textwrap
from pathlib import Path

import pytest

from casino_dashboard.data.star_traders_loader import load_star_traders


def _write_yaml(tmp_path: Path, content: str) -> Path:
    p = tmp_path / "star_traders.yaml"
    p.write_text(textwrap.dedent(content))
    return p


# ---------------------------------------------------------------------------
# Successful parse
# ---------------------------------------------------------------------------

def test_load_star_traders_basic(tmp_path):
    content = """
    star_traders:
      - bioguide_id: P000197
        name: "Nancy Pelosi"
        note: "Frequent tech trader"
      - bioguide_id: T000278
        name: "Tommy Tuberville"
        note: "Agriculture/defense"
    """
    p = _write_yaml(tmp_path, content)
    result = load_star_traders(p)
    assert len(result) == 2
    assert result[0]["bioguide_id"] == "P000197"
    assert result[0]["name"] == "Nancy Pelosi"
    assert result[1]["bioguide_id"] == "T000278"


def test_load_star_traders_returns_list_of_dicts(tmp_path):
    content = """
    star_traders:
      - bioguide_id: P000197
        name: "Nancy Pelosi"
        note: "Test"
    """
    p = _write_yaml(tmp_path, content)
    result = load_star_traders(p)
    assert isinstance(result, list)
    for entry in result:
        assert isinstance(entry, dict)
        assert "bioguide_id" in entry
        assert "name" in entry
        assert "note" in entry


def test_load_star_traders_empty_file(tmp_path):
    p = tmp_path / "star_traders.yaml"
    p.write_text("")
    result = load_star_traders(p)
    assert result == []


def test_load_star_traders_empty_list(tmp_path):
    content = "star_traders: []\n"
    p = _write_yaml(tmp_path, content)
    result = load_star_traders(p)
    assert result == []


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------

def test_load_star_traders_file_not_found():
    with pytest.raises(FileNotFoundError):
        load_star_traders(Path("/nonexistent/star_traders.yaml"))


def test_load_star_traders_missing_key_raises(tmp_path):
    p = tmp_path / "star_traders.yaml"
    p.write_text("some_key: []\n")
    with pytest.raises(ValueError, match="star_traders"):
        load_star_traders(p)


# ---------------------------------------------------------------------------
# Bioguide validation (warning, not exception)
# ---------------------------------------------------------------------------

def test_load_star_traders_warns_on_unknown_bioguide(tmp_path, caplog):
    """A bioguide_id not in known_bioguides emits a warning but does NOT raise."""
    content = """
    star_traders:
      - bioguide_id: XXXXX
        name: "Unknown Person"
        note: "Invalid ID"
    """
    p = _write_yaml(tmp_path, content)
    import logging
    with caplog.at_level(logging.WARNING):
        result = load_star_traders(p, known_bioguides={"P000197"})

    # Entry is kept despite unknown bioguide
    assert len(result) == 1
    assert result[0]["bioguide_id"] == "XXXXX"
    # Warning was logged
    assert any("XXXXX" in msg for msg in caplog.messages)


def test_load_star_traders_no_warning_for_known_bioguide(tmp_path, caplog):
    content = """
    star_traders:
      - bioguide_id: P000197
        name: "Nancy Pelosi"
        note: "Known"
    """
    p = _write_yaml(tmp_path, content)
    import logging
    with caplog.at_level(logging.WARNING):
        result = load_star_traders(p, known_bioguides={"P000197"})

    assert len(result) == 1
    # No warning about P000197
    assert not any("P000197" in msg and "not found" in msg for msg in caplog.messages)


def test_load_star_traders_skips_missing_bioguide_id(tmp_path, caplog):
    """Entry without bioguide_id is skipped (logged, not raised)."""
    content = """
    star_traders:
      - name: "No ID Person"
        note: "Missing bioguide_id"
      - bioguide_id: P000197
        name: "Nancy Pelosi"
        note: "Valid"
    """
    p = _write_yaml(tmp_path, content)
    result = load_star_traders(p)
    assert len(result) == 1
    assert result[0]["bioguide_id"] == "P000197"


def test_load_star_traders_warns_and_skips_duplicate_bioguide_id(tmp_path, caplog):
    """Duplicate bioguide_id: keep first, skip second, emit a warning."""
    content = """
    star_traders:
      - bioguide_id: G000596
        name: "Marjorie Taylor Greene"
        note: "First entry"
      - bioguide_id: P000197
        name: "Nancy Pelosi"
        note: "Should be kept"
      - bioguide_id: G000596
        name: "Mark Green"
        note: "Duplicate — should be skipped"
    """
    p = _write_yaml(tmp_path, content)
    import logging
    with caplog.at_level(logging.WARNING):
        result = load_star_traders(p)

    # Only 2 of 3 entries should survive (first G000596 wins)
    assert len(result) == 2
    names = [r["name"] for r in result]
    assert "Marjorie Taylor Greene" in names
    assert "Nancy Pelosi" in names
    assert "Mark Green" not in names
    # Warning logged about the duplicate
    assert any("duplicate" in msg.lower() and "G000596" in msg for msg in caplog.messages)


# ---------------------------------------------------------------------------
# Smoke test against real config
# ---------------------------------------------------------------------------

def test_load_star_traders_real_config():
    """Smoke test: config/star_traders.yaml must parse without errors."""
    config_path = Path("config/star_traders.yaml")
    if not config_path.exists():
        pytest.skip("config/star_traders.yaml not present")
    result = load_star_traders(config_path)
    assert len(result) >= 10
    for entry in result:
        assert entry["bioguide_id"]
        assert entry["name"]
