"""Tests for the deal log YAML loader."""
import textwrap
from datetime import date
from pathlib import Path

import pytest
import yaml

from casino_dashboard.data.deal_log_loader import (
    DealLogEntry,
    _make_deal_id,
    _parse_entry,
    load_deal_log_from_yaml,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_yaml(tmp_path: Path, content: str) -> Path:
    p = tmp_path / "deal_log.yaml"
    p.write_text(textwrap.dedent(content))
    return p


# ---------------------------------------------------------------------------
# _make_deal_id
# ---------------------------------------------------------------------------

def test_deal_id_is_deterministic():
    d = date(2026, 5, 1)
    id1 = _make_deal_id(d, "nuclear", "Test summary")
    id2 = _make_deal_id(d, "nuclear", "Test summary")
    assert id1 == id2


def test_deal_id_differs_on_different_summary():
    d = date(2026, 5, 1)
    id1 = _make_deal_id(d, "nuclear", "Summary A")
    id2 = _make_deal_id(d, "nuclear", "Summary B")
    assert id1 != id2


def test_deal_id_is_16_chars():
    d = date(2026, 5, 1)
    assert len(_make_deal_id(d, "nuclear", "Test")) == 16


# ---------------------------------------------------------------------------
# _parse_entry — field validation
# ---------------------------------------------------------------------------

def test_parse_entry_valid_full():
    raw = {
        "date": "2026-05-01",
        "sector": "nuclear",
        "amount_usd": 1_500_000_000,
        "deal_type": "contract_award",
        "primary_ticker": "oklo",
        "source_url": "https://example.com",
        "summary": "OKLO DOE contract",
    }
    entry = _parse_entry(raw, 0)
    assert entry is not None
    assert entry.date == date(2026, 5, 1)
    assert entry.sector == "nuclear"
    assert entry.amount_usd == 1_500_000_000.0
    assert entry.deal_type == "contract_award"
    assert entry.primary_ticker == "OKLO"  # uppercased
    assert entry.summary == "OKLO DOE contract"


def test_parse_entry_null_amount_is_allowed():
    raw = {
        "date": "2026-05-01",
        "sector": "photonics",
        "amount_usd": None,
        "summary": "AAOI Texas grant",
    }
    entry = _parse_entry(raw, 0)
    assert entry is not None
    assert entry.amount_usd is None


def test_parse_entry_missing_date_returns_none():
    raw = {"sector": "nuclear", "summary": "Test"}
    assert _parse_entry(raw, 0) is None


def test_parse_entry_missing_sector_returns_none():
    raw = {"date": "2026-05-01", "summary": "Test"}
    assert _parse_entry(raw, 0) is None


def test_parse_entry_missing_summary_returns_none():
    raw = {"date": "2026-05-01", "sector": "nuclear"}
    assert _parse_entry(raw, 0) is None


def test_parse_entry_invalid_date_returns_none():
    raw = {"date": "not-a-date", "sector": "nuclear", "summary": "Test"}
    assert _parse_entry(raw, 0) is None


def test_parse_entry_non_dict_returns_none():
    assert _parse_entry("not a dict", 0) is None


def test_parse_entry_sector_is_lowercased():
    raw = {"date": "2026-05-01", "sector": "NUCLEAR", "summary": "Test"}
    entry = _parse_entry(raw, 0)
    assert entry is not None
    assert entry.sector == "nuclear"


def test_parse_entry_unknown_sector_still_parses():
    """Unknown sector logs a warning but doesn't reject the entry."""
    raw = {"date": "2026-05-01", "sector": "unknown_sector", "summary": "Test"}
    entry = _parse_entry(raw, 0)
    assert entry is not None
    assert entry.sector == "unknown_sector"


# ---------------------------------------------------------------------------
# load_deal_log_from_yaml
# ---------------------------------------------------------------------------

def test_load_valid_yaml(tmp_path):
    content = """
    - date: "2026-05-01"
      sector: nuclear
      amount_usd: 1500000000
      deal_type: contract_award
      primary_ticker: OKLO
      summary: "OKLO DOE contract"

    - date: "2026-04-28"
      sector: photonics
      amount_usd: null
      summary: "AAOI Texas grant"
    """
    p = _write_yaml(tmp_path, content)
    entries = load_deal_log_from_yaml(p)
    assert len(entries) == 2
    assert entries[0].sector == "nuclear"
    assert entries[1].sector == "photonics"
    assert entries[1].amount_usd is None


def test_load_skips_invalid_entries(tmp_path):
    content = """
    - date: "2026-05-01"
      sector: nuclear
      summary: "Valid entry"

    - sector: photonics
      summary: "Missing date — should be skipped"

    - date: "2026-04-28"
      sector: ai_infrastructure
      summary: "Also valid"
    """
    p = _write_yaml(tmp_path, content)
    entries = load_deal_log_from_yaml(p)
    assert len(entries) == 2


def test_load_empty_yaml_returns_empty_list(tmp_path):
    p = tmp_path / "deal_log.yaml"
    p.write_text("")
    entries = load_deal_log_from_yaml(p)
    assert entries == []


def test_load_file_not_found_raises():
    with pytest.raises(FileNotFoundError):
        load_deal_log_from_yaml(Path("/nonexistent/deal_log.yaml"))


def test_load_top_level_not_list_raises(tmp_path):
    p = tmp_path / "deal_log.yaml"
    p.write_text("sector: nuclear\n")
    with pytest.raises(ValueError, match="must be a list"):
        load_deal_log_from_yaml(p)


def test_load_deals_have_stable_ids(tmp_path):
    content = """
    - date: "2026-05-01"
      sector: nuclear
      summary: "Stable ID test"
    """
    p = _write_yaml(tmp_path, content)
    entries1 = load_deal_log_from_yaml(p)
    entries2 = load_deal_log_from_yaml(p)
    assert entries1[0].deal_id == entries2[0].deal_id


def test_load_real_deal_log_config():
    """Smoke test: the shipped config/deal_log.yaml must parse without errors."""
    config_path = Path("config/deal_log.yaml")
    if not config_path.exists():
        pytest.skip("config/deal_log.yaml not present")
    entries = load_deal_log_from_yaml(config_path)
    assert len(entries) >= 5
    for entry in entries:
        assert isinstance(entry, DealLogEntry)
        assert entry.date is not None
        assert entry.sector
        assert entry.summary
