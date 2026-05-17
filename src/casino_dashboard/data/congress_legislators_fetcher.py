"""
Congress legislators fetcher.

Downloads three YAML files from the unitedstates/congress-legislators
public-domain GitHub repo and returns a normalized "watched members" dict
covering the committees with meaningful policy-insider access.

Selection scope (documented here so the rule is discoverable):
  A legislator is included if ANY of the following is true:
    1. title == "Chair" on a whitelisted full committee
    2. title == "Ranking Member" on a whitelisted full committee
    3. title == "Chair" on a subcommittee of a whitelisted committee
       (subcommittee thomas_id starts with the parent's thomas_id and is
       longer than the parent's thomas_id — i.e. is a child ID)

Whitelisted committees (matched by display name, not hardcoded thomas_id
since thomas_ids can be reassigned):
  House Armed Services, Senate Armed Services,
  House Financial Services, Senate Banking Housing and Urban Affairs,
  House Energy and Commerce, Senate Energy and Natural Resources,
  House Permanent Select Committee on Intelligence,
  Senate Select Committee on Intelligence,
  House Foreign Affairs, Senate Foreign Relations,
  Senate Commerce Science and Transportation,
  House Science Space and Technology

Error handling: any HTTP error raises immediately. We do NOT fall back to a
stale cached copy — the daily refresh job must fail loudly so the operator
knows data is stale.
"""
import json
import logging
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

_LEGISLATORS_URL = (
    "https://raw.githubusercontent.com/unitedstates/congress-legislators"
    "/main/legislators-current.yaml"
)
_COMMITTEES_URL = (
    "https://raw.githubusercontent.com/unitedstates/congress-legislators"
    "/main/committees-current.yaml"
)
_MEMBERSHIP_URL = (
    "https://raw.githubusercontent.com/unitedstates/congress-legislators"
    "/main/committee-membership-current.yaml"
)

_TMP_DIR = Path("/tmp/congress_legislators_cache")

# Whitelisted committee names — partial-match, case-insensitive.
# Each tuple is (display_label, [substrings_to_try]).  A committee matches
# if ANY substring is found in its lowercased name.  We include both the
# short form ("house armed services") and the "Committee on" long form
# ("armed services") so the matcher works regardless of how the YAML
# formats the name.
_WHITELISTED_COMMITTEES: list[tuple[str, list[str]]] = [
    ("House Armed Services",       ["house armed services", "armed services committee"]),
    ("Senate Armed Services",      ["senate armed services"]),
    ("House Financial Services",   ["house financial services", "financial services committee"]),
    ("Senate Banking",             ["senate banking"]),
    ("House Energy and Commerce",  ["house energy and commerce", "energy and commerce"]),
    ("Senate Energy and Natural Resources", ["senate energy and natural resources"]),
    ("House Intelligence",         ["house permanent select committee on intelligence",
                                    "permanent select committee on intelligence"]),
    ("Senate Intelligence",        ["senate select committee on intelligence",
                                    "select committee on intelligence"]),
    ("House Foreign Affairs",      ["house foreign affairs", "foreign affairs committee"]),
    ("Senate Foreign Relations",   ["senate foreign relations", "foreign relations committee"]),
    ("Senate Commerce",            ["senate commerce, science", "commerce, science, and transportation"]),
    ("House Science",              ["house science, space", "science, space, and technology"]),
]

# Flat list of all substrings for quick _is_whitelisted checks
_WHITELISTED_COMMITTEE_SUBSTRINGS: list[str] = [
    sub for _, subs in _WHITELISTED_COMMITTEES for sub in subs
]


def _fetch_yaml(url: str, cache_path: Path) -> object:
    """Download YAML from url, cache to cache_path, return parsed object.

    Raises urllib.error.URLError / urllib.error.HTTPError on failure.
    """
    logger.info("Fetching %s …", url)
    with urllib.request.urlopen(url, timeout=30) as resp:  # noqa: S310
        raw_bytes = resp.read()
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_bytes(raw_bytes)
    return yaml.safe_load(raw_bytes)


def _is_whitelisted(committee_name: str) -> bool:
    name_lower = committee_name.lower()
    return any(sub in name_lower for sub in _WHITELISTED_COMMITTEE_SUBSTRINGS)


def _build_legislator_index(legislators: list[dict]) -> dict[str, dict]:
    """Return {bioguide_id: normalized_dict} from legislators-current.yaml."""
    index: dict[str, dict] = {}
    for leg in legislators:
        ids = leg.get("id", {})
        bioguide = ids.get("bioguide")
        if not bioguide:
            continue
        name = leg.get("name", {})
        bio = leg.get("bio", {})
        terms = leg.get("terms", [])
        chamber = "unknown"
        if terms:
            last_type = terms[-1].get("type", "")
            if last_type == "sen":
                chamber = "senate"
            elif last_type == "rep":
                chamber = "house"
        index[bioguide] = {
            "bioguide_id": bioguide,
            "full_name": f"{name.get('first', '')} {name.get('last', '')}".strip(),
            "first_name": name.get("first", ""),
            "last_name": name.get("last", ""),
            "party": bio.get("party", "I"),
            "state": bio.get("state", ""),
            "chamber": chamber,
        }
    return index


def _build_committee_index(committees: list[dict]) -> dict[str, dict]:
    """Return {thomas_id: {thomas_id, name, whitelisted}} from committees-current.yaml."""
    index: dict[str, dict] = {}
    for comm in committees:
        thomas_id = comm.get("thomas_id") or comm.get("id")
        if not thomas_id:
            continue
        name = comm.get("name", "")
        index[thomas_id] = {
            "thomas_id": thomas_id,
            "name": name,
            "whitelisted": _is_whitelisted(name),
        }
        # Index subcommittees too
        for sub in comm.get("subcommittees", []):
            sub_thomas_id = sub.get("thomas_id")
            if not sub_thomas_id:
                continue
            # Subcommittee thomas_id in the source file is relative (e.g. "03"),
            # but in membership-current it is stored as parent+sub (e.g. "HSAS03").
            # Store both relative and absolute form.
            full_sub_id = thomas_id + sub_thomas_id
            sub_name = sub.get("name", f"{name} Subcommittee")
            index[full_sub_id] = {
                "thomas_id": full_sub_id,
                "name": sub_name,
                "parent_thomas_id": thomas_id,
                "whitelisted": False,  # subcommittees inherit parent whitelisting contextually
            }
    return index


def _is_subcommittee_of_whitelisted(thomas_id: str, committee_index: dict[str, dict]) -> str | None:
    """Return the parent thomas_id if thomas_id is a subcommittee of a whitelisted committee."""
    entry = committee_index.get(thomas_id)
    if not entry:
        # Try prefix matching: find a whitelisted committee whose thomas_id is a
        # proper prefix of this thomas_id.
        for cid, comm in committee_index.items():
            if comm.get("whitelisted") and thomas_id.startswith(cid) and thomas_id != cid:
                return cid
        return None
    parent_id = entry.get("parent_thomas_id")
    if parent_id and committee_index.get(parent_id, {}).get("whitelisted"):
        return parent_id
    return None


def fetch_committee_membership() -> dict:
    """Return normalized watched-members dict from unitedstates/congress-legislators.

    Selection rules:
      - title == "Chair" on a whitelisted full committee
      - title == "Ranking Member" on a whitelisted full committee
      - title == "Chair" on a subcommittee of a whitelisted full committee

    The three raw YAML files are cached to /tmp for this run only (re-fetched
    on each daily-refresh call). They are NOT committed to the repo.

    Raises on any HTTP failure — do NOT fall back to stale data.
    """
    legislators_raw = _fetch_yaml(_LEGISLATORS_URL, _TMP_DIR / "legislators-current.yaml")
    committees_raw = _fetch_yaml(_COMMITTEES_URL, _TMP_DIR / "committees-current.yaml")
    membership_raw = _fetch_yaml(_MEMBERSHIP_URL, _TMP_DIR / "committee-membership-current.yaml")

    if not isinstance(legislators_raw, list):
        raise ValueError("legislators-current.yaml is not a list")
    if not isinstance(committees_raw, list):
        raise ValueError("committees-current.yaml is not a list")
    if not isinstance(membership_raw, dict):
        raise ValueError("committee-membership-current.yaml is not a dict")

    legislator_index = _build_legislator_index(legislators_raw)
    committee_index = _build_committee_index(committees_raw)

    # Diagnostic: log which whitelisted committees were found in the YAML
    whitelisted_found = {cid: info["name"] for cid, info in committee_index.items() if info.get("whitelisted")}
    logger.info(
        "Committee index: %d total committees, %d whitelisted: %s",
        len(committee_index),
        len(whitelisted_found),
        ", ".join(f"{cid}={name}" for cid, name in sorted(whitelisted_found.items())),
    )
    if not whitelisted_found:
        # Dump a sample of committee names to help diagnose name-matching issues
        sample = list(committee_index.items())[:10]
        logger.warning(
            "No whitelisted committees matched! Sample committee names from YAML: %s",
            ", ".join(f'{cid}={info["name"]!r}' for cid, info in sample),
        )

    # {bioguide_id: {member_info, committees: [...]}}
    watched: dict[str, dict] = {}

    for thomas_id, members in membership_raw.items():
        comm_info = committee_index.get(thomas_id)
        is_full_committee_whitelisted = comm_info and comm_info.get("whitelisted", False)
        parent_id = _is_subcommittee_of_whitelisted(thomas_id, committee_index)
        is_sub_of_whitelisted = parent_id is not None and not is_full_committee_whitelisted

        if not isinstance(members, list):
            continue

        for member in members:
            bioguide = member.get("bioguide") or member.get("bioguide_id")
            if not bioguide:
                continue

            title = member.get("title", "")
            rank = member.get("rank")

            qualifies = False
            if is_full_committee_whitelisted and title in ("Chair", "Ranking Member"):
                qualifies = True
            elif is_sub_of_whitelisted and title == "Chair":
                qualifies = True

            if not qualifies:
                continue

            leg = legislator_index.get(bioguide)
            if leg is None:
                logger.warning(
                    "bioguide %s found in membership but not in legislators-current — skipping",
                    bioguide,
                )
                continue

            if bioguide not in watched:
                watched[bioguide] = {**leg, "committees": []}

            comm_name = comm_info["name"] if comm_info else thomas_id
            watched[bioguide]["committees"].append(
                {
                    "committee_id": thomas_id,
                    "committee_name": comm_name,
                    "title": title,
                    "rank": rank,
                }
            )

    fetched_at = datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    logger.info("fetch_committee_membership: %d watched members identified", len(watched))
    return {
        "watched_members": list(watched.values()),
        "all_bioguide_ids": list(legislator_index.keys()),
        "fetched_at": fetched_at,
    }
