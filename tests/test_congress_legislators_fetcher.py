"""Tests for congress_legislators_fetcher.py — all HTTP calls are mocked."""
import io
from unittest.mock import MagicMock, patch

import pytest
import yaml

from casino_dashboard.data.congress_legislators_fetcher import (
    _build_committee_index,
    _build_legislator_index,
    _is_subcommittee_of_whitelisted,
    _is_whitelisted,
    fetch_committee_membership,
)


# ---------------------------------------------------------------------------
# Fixtures — minimal YAML-compatible dicts
# ---------------------------------------------------------------------------

def _make_legislator(bioguide, first, last, party="D", state="CA", chamber_type="rep"):
    return {
        "id": {"bioguide": bioguide},
        "name": {"first": first, "last": last},
        "bio": {"party": party, "state": state},
        "terms": [{"type": chamber_type}],
    }


def _make_committee(thomas_id, name, subcommittees=None):
    comm = {"thomas_id": thomas_id, "name": name}
    if subcommittees:
        comm["subcommittees"] = subcommittees
    return comm


def _make_membership_entry(bioguide, title="Member", rank=None):
    entry = {"bioguide": bioguide, "title": title}
    if rank is not None:
        entry["rank"] = rank
    return entry


# ---------------------------------------------------------------------------
# _is_whitelisted
# ---------------------------------------------------------------------------

def test_is_whitelisted_house_armed_services():
    assert _is_whitelisted("House Armed Services") is True


def test_is_whitelisted_senate_armed_services():
    assert _is_whitelisted("Senate Armed Services") is True


def test_is_whitelisted_house_financial_services():
    assert _is_whitelisted("House Financial Services") is True


def test_is_whitelisted_senate_banking():
    assert _is_whitelisted("Senate Banking, Housing, and Urban Affairs") is True


def test_is_whitelisted_intelligence():
    assert _is_whitelisted("House Permanent Select Committee on Intelligence") is True
    assert _is_whitelisted("Senate Select Committee on Intelligence") is True


def test_is_whitelisted_unknown_committee():
    assert _is_whitelisted("House Agriculture") is False


# ---------------------------------------------------------------------------
# _build_legislator_index
# ---------------------------------------------------------------------------

def test_build_legislator_index_basic():
    legs = [_make_legislator("P000197", "Nancy", "Pelosi", "D", "CA", "rep")]
    idx = _build_legislator_index(legs)
    assert "P000197" in idx
    assert idx["P000197"]["full_name"] == "Nancy Pelosi"
    assert idx["P000197"]["chamber"] == "house"
    assert idx["P000197"]["party"] == "D"


def test_build_legislator_index_senator():
    legs = [_make_legislator("M001211", "Markwayne", "Mullin", "R", "OK", "sen")]
    idx = _build_legislator_index(legs)
    assert idx["M001211"]["chamber"] == "senate"


def test_build_legislator_index_skips_missing_bioguide():
    legs = [{"id": {}, "name": {"first": "No", "last": "ID"}, "bio": {}, "terms": []}]
    idx = _build_legislator_index(legs)
    assert len(idx) == 0


# ---------------------------------------------------------------------------
# _build_committee_index and _is_subcommittee_of_whitelisted
# ---------------------------------------------------------------------------

def test_build_committee_index_whitelisted_full():
    comms = [_make_committee("HSAS", "House Armed Services")]
    idx = _build_committee_index(comms)
    assert idx["HSAS"]["whitelisted"] is True


def test_build_committee_index_non_whitelisted():
    comms = [_make_committee("HSAG", "House Agriculture")]
    idx = _build_committee_index(comms)
    assert idx["HSAG"]["whitelisted"] is False


def test_build_committee_index_subcommittee_indexed():
    comms = [
        _make_committee("HSAS", "House Armed Services", subcommittees=[
            {"thomas_id": "03", "name": "Cyber Subcommittee"}
        ])
    ]
    idx = _build_committee_index(comms)
    # Subcommittee should be indexed as "HSAS03"
    assert "HSAS03" in idx


def test_is_subcommittee_of_whitelisted_true():
    comms = [_make_committee("HSAS", "House Armed Services")]
    idx = _build_committee_index(comms)
    parent = _is_subcommittee_of_whitelisted("HSAS03", idx)
    assert parent == "HSAS"


def test_is_subcommittee_of_whitelisted_non_whitelisted_parent():
    comms = [_make_committee("HSAG", "House Agriculture")]
    idx = _build_committee_index(comms)
    parent = _is_subcommittee_of_whitelisted("HSAG05", idx)
    assert parent is None


# ---------------------------------------------------------------------------
# fetch_committee_membership (integration with mocked HTTP)
# ---------------------------------------------------------------------------

def _yaml_bytes(obj):
    return yaml.dump(obj).encode()


def _mock_urlopen(legislators, committees, membership):
    urls = {
        "legislators-current": _yaml_bytes(legislators),
        "committees-current": _yaml_bytes(committees),
        "committee-membership-current": _yaml_bytes(membership),
    }

    class _FakeResp:
        def __init__(self, data):
            self._data = data

        def read(self):
            return self._data

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    def side_effect(url, timeout=30):
        for key, data in urls.items():
            if key in url:
                return _FakeResp(data)
        raise ValueError(f"Unexpected URL: {url}")

    return side_effect


def test_fetch_committee_membership_chair_included():
    """A full-committee Chair on a whitelisted committee is included."""
    legislators = [_make_legislator("A000001", "Alice", "Smith", "D", "CA", "rep")]
    committees = [_make_committee("HSAS", "House Armed Services")]
    membership = {"HSAS": [_make_membership_entry("A000001", "Chair", rank=1)]}

    with patch("casino_dashboard.data.congress_legislators_fetcher.urllib.request.urlopen",
               side_effect=_mock_urlopen(legislators, committees, membership)):
        result = fetch_committee_membership()

    assert len(result["watched_members"]) == 1
    member = result["watched_members"][0]
    assert member["bioguide_id"] == "A000001"
    assert member["committees"][0]["title"] == "Chair"


def test_fetch_committee_membership_ranking_member_included():
    """A Ranking Member on a whitelisted committee is included."""
    legislators = [_make_legislator("B000002", "Bob", "Jones", "R", "TX", "rep")]
    committees = [_make_committee("HSAS", "House Armed Services")]
    membership = {"HSAS": [_make_membership_entry("B000002", "Ranking Member", rank=2)]}

    with patch("casino_dashboard.data.congress_legislators_fetcher.urllib.request.urlopen",
               side_effect=_mock_urlopen(legislators, committees, membership)):
        result = fetch_committee_membership()

    assert len(result["watched_members"]) == 1
    assert result["watched_members"][0]["bioguide_id"] == "B000002"


def test_fetch_committee_membership_regular_member_excluded():
    """A regular Member on a whitelisted full committee is NOT included."""
    legislators = [_make_legislator("C000003", "Carol", "White", "D", "NY", "rep")]
    committees = [_make_committee("HSAS", "House Armed Services")]
    membership = {"HSAS": [_make_membership_entry("C000003", "Member")]}

    with patch("casino_dashboard.data.congress_legislators_fetcher.urllib.request.urlopen",
               side_effect=_mock_urlopen(legislators, committees, membership)):
        result = fetch_committee_membership()

    assert len(result["watched_members"]) == 0


def test_fetch_committee_membership_subcommittee_chair_included():
    """A Chair on a subcommittee of a whitelisted committee is included."""
    legislators = [_make_legislator("D000004", "Dan", "Brown", "R", "FL", "rep")]
    committees = [_make_committee("HSAS", "House Armed Services")]
    # HSAS01 is a subcommittee of HSAS
    membership = {
        "HSAS": [_make_membership_entry("D000004", "Member")],
        "HSAS01": [_make_membership_entry("D000004", "Chair", rank=1)],
    }

    with patch("casino_dashboard.data.congress_legislators_fetcher.urllib.request.urlopen",
               side_effect=_mock_urlopen(legislators, committees, membership)):
        result = fetch_committee_membership()

    assert len(result["watched_members"]) == 1
    assert result["watched_members"][0]["bioguide_id"] == "D000004"


def test_fetch_committee_membership_subcommittee_chair_non_whitelisted_excluded():
    """A Chair on a subcommittee of a NON-whitelisted committee is excluded."""
    legislators = [_make_legislator("E000005", "Eve", "Green", "D", "WA", "rep")]
    committees = [_make_committee("HSAG", "House Agriculture")]
    membership = {
        "HSAG01": [_make_membership_entry("E000005", "Chair", rank=1)],
    }

    with patch("casino_dashboard.data.congress_legislators_fetcher.urllib.request.urlopen",
               side_effect=_mock_urlopen(legislators, committees, membership)):
        result = fetch_committee_membership()

    assert len(result["watched_members"]) == 0


def test_fetch_committee_membership_member_on_two_committees_appears_once():
    """A member who chairs two whitelisted committees appears once with both committee entries."""
    legislators = [_make_legislator("F000006", "Frank", "Lee", "R", "OH", "rep")]
    committees = [
        _make_committee("HSAS", "House Armed Services"),
        _make_committee("HIFS", "House Financial Services"),
    ]
    membership = {
        "HSAS": [_make_membership_entry("F000006", "Chair", rank=1)],
        "HIFS": [_make_membership_entry("F000006", "Chair", rank=1)],
    }

    with patch("casino_dashboard.data.congress_legislators_fetcher.urllib.request.urlopen",
               side_effect=_mock_urlopen(legislators, committees, membership)):
        result = fetch_committee_membership()

    assert len(result["watched_members"]) == 1
    member = result["watched_members"][0]
    assert len(member["committees"]) == 2
    committee_ids = {c["committee_id"] for c in member["committees"]}
    assert "HSAS" in committee_ids
    assert "HIFS" in committee_ids


def test_fetch_committee_membership_returns_fetched_at():
    legislators = [_make_legislator("A000001", "Alice", "Smith")]
    committees = [_make_committee("HSAS", "House Armed Services")]
    membership = {"HSAS": [_make_membership_entry("A000001", "Chair")]}

    with patch("casino_dashboard.data.congress_legislators_fetcher.urllib.request.urlopen",
               side_effect=_mock_urlopen(legislators, committees, membership)):
        result = fetch_committee_membership()

    assert "fetched_at" in result
    assert result["fetched_at"].endswith("Z")


def test_fetch_committee_membership_raises_on_http_error():
    import urllib.error

    with patch("casino_dashboard.data.congress_legislators_fetcher.urllib.request.urlopen",
               side_effect=urllib.error.HTTPError(None, 500, "Server Error", {}, None)):
        with pytest.raises(urllib.error.HTTPError):
            fetch_committee_membership()
