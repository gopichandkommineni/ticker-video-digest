"""Tests for casino_dashboard.data.manual_notes_loader."""
import pytest

from casino_dashboard.data.manual_notes_loader import load_manual_notes_from_yaml


# ── Test 1: valid YAML → returns expected dict ────────────────────────────────

def test_valid_yaml_returns_expected_dict(tmp_path):
    yaml_file = tmp_path / "notes.yaml"
    yaml_file.write_text(
        "AAOI:\n"
        "  catalyst: 'Texas grant'\n"
        "  red_flag: null\n"
        "POET:\n"
        "  catalyst: null\n"
        "  red_flag: 'Marvell cancelled'\n"
    )
    result = load_manual_notes_from_yaml(yaml_file)
    assert result == {
        "AAOI": {"catalyst": "Texas grant", "red_flag": None},
        "POET": {"catalyst": None, "red_flag": "Marvell cancelled"},
    }


# ── Test 2: empty YAML → returns empty dict ───────────────────────────────────

def test_empty_yaml_returns_empty_dict(tmp_path):
    yaml_file = tmp_path / "notes.yaml"
    yaml_file.write_text("")
    result = load_manual_notes_from_yaml(yaml_file)
    assert result == {}


# ── Test 3: lowercase ticker key → raises ValueError ─────────────────────────

def test_lowercase_ticker_raises_value_error(tmp_path):
    yaml_file = tmp_path / "notes.yaml"
    yaml_file.write_text(
        "aaoi:\n"
        "  catalyst: null\n"
        "  red_flag: null\n"
    )
    with pytest.raises(ValueError, match="Invalid ticker key"):
        load_manual_notes_from_yaml(yaml_file)


# ── Test 4: non-string value (int) → raises ValueError ───────────────────────

def test_non_string_value_raises_value_error(tmp_path):
    yaml_file = tmp_path / "notes.yaml"
    yaml_file.write_text(
        "AAOI:\n"
        "  catalyst: 42\n"
        "  red_flag: null\n"
    )
    with pytest.raises(ValueError, match="must be str or null"):
        load_manual_notes_from_yaml(yaml_file)


# ── Test 5: missing file → raises FileNotFoundError ──────────────────────────

def test_missing_file_raises_file_not_found(tmp_path):
    missing = tmp_path / "does_not_exist.yaml"
    with pytest.raises(FileNotFoundError):
        load_manual_notes_from_yaml(missing)
