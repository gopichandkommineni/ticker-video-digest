"""
Star-traders YAML loader.

Reads config/star_traders.yaml and returns the list of hand-curated
congressional traders. If a bioguide_id does not appear in the current
legislators data, logs a warning and keeps the entry — the user owns the
YAML and should fix stale IDs.
"""
import logging
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

_CONFIG_PATH = Path("config/star_traders.yaml")


def load_star_traders(
    path: Path = _CONFIG_PATH,
    known_bioguides: set[str] | None = None,
) -> list[dict]:
    """Return the list of star-trader dicts from star_traders.yaml.

    Each dict has: bioguide_id, name, note.

    known_bioguides: if provided, warns on any entry whose bioguide_id is not
    in the set. Does not raise — the daily refresh must not abort on a stale ID.
    """
    if not path.exists():
        raise FileNotFoundError(f"star_traders.yaml not found: {path}")

    with path.open("r") as fh:
        raw = yaml.safe_load(fh)

    if raw is None:
        return []

    if not isinstance(raw, dict) or "star_traders" not in raw:
        raise ValueError(
            f"star_traders.yaml must have a top-level 'star_traders' key, got: {list(raw.keys()) if isinstance(raw, dict) else type(raw).__name__}"
        )

    entries = raw["star_traders"]
    if not isinstance(entries, list):
        raise ValueError("star_traders.yaml 'star_traders' must be a list")

    result = []
    seen_ids: dict[str, str] = {}  # bioguide_id → name of first occurrence
    for entry in entries:
        if not isinstance(entry, dict):
            logger.warning("star_traders.yaml: non-dict entry %r — skipping", entry)
            continue
        bioguide_id = entry.get("bioguide_id")
        if not bioguide_id:
            logger.warning("star_traders.yaml: entry missing bioguide_id — skipping: %r", entry)
            continue
        bioguide_id = str(bioguide_id)
        name = str(entry.get("name", ""))
        if bioguide_id in seen_ids:
            logger.warning(
                "star_traders.yaml: duplicate bioguide_id %r — already used by %r, "
                "skipping second entry for %r. Fix the YAML to use the correct IDs.",
                bioguide_id,
                seen_ids[bioguide_id],
                name,
            )
            continue
        seen_ids[bioguide_id] = name
        if known_bioguides is not None and bioguide_id not in known_bioguides:
            logger.warning(
                "star_traders.yaml: bioguide_id %r (%s) not found in current legislators — "
                "keeping entry but verify the ID is correct",
                bioguide_id,
                name,
            )
        result.append(
            {
                "bioguide_id": bioguide_id,
                "name": name,
                "note": str(entry.get("note", "")),
            }
        )

    logger.info("Loaded %d star traders from %s", len(result), path)
    return result
