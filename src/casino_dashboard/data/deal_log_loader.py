"""
Deal log loader — reads config/deal_log.yaml into DealLogEntry dataclasses.

Validates required fields (date, sector, summary); treats missing optional
fields (amount_usd, deal_type, primary_ticker, source_url) as None rather
than crashing the daily refresh.
"""
import hashlib
import logging
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

_CONFIG_PATH = Path("config/deal_log.yaml")

_VALID_SECTORS = {
    "nuclear",
    "photonics",
    "quantum",
    "drones_defense",
    "space",
    "critical_minerals",
    "ai_infrastructure",
    "crypto_equities",
}

_VALID_DEAL_TYPES = {
    "capex_announcement",
    "contract_award",
    "funding",
    "m&a",
    "deal",
}


@dataclass
class DealLogEntry:
    deal_id: str
    date: date
    sector: str
    amount_usd: float | None
    deal_type: str | None
    primary_ticker: str | None
    source_url: str | None
    summary: str


def _make_deal_id(entry_date: date, sector: str, summary: str) -> str:
    """Stable hash of date+sector+summary for idempotent inserts."""
    raw = f"{entry_date.isoformat()}|{sector}|{summary}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _parse_entry(raw: dict, idx: int) -> DealLogEntry | None:
    """Parse one YAML entry; return None and log warning on validation failure."""
    if not isinstance(raw, dict):
        logger.warning("Deal log entry %d is not a mapping — skipping", idx)
        return None

    # Required fields
    raw_date = raw.get("date")
    sector = raw.get("sector")
    summary = raw.get("summary")

    if not raw_date:
        logger.warning("Deal log entry %d missing 'date' — skipping", idx)
        return None
    if not sector:
        logger.warning("Deal log entry %d missing 'sector' — skipping", idx)
        return None
    if not summary:
        logger.warning("Deal log entry %d missing 'summary' — skipping", idx)
        return None

    # Parse date
    try:
        if isinstance(raw_date, date):
            entry_date = raw_date
        else:
            entry_date = date.fromisoformat(str(raw_date))
    except (ValueError, TypeError):
        logger.warning("Deal log entry %d has invalid 'date' %r — skipping", idx, raw_date)
        return None

    # Validate sector
    sector = str(sector).lower()
    if sector not in _VALID_SECTORS:
        logger.warning(
            "Deal log entry %d has unknown sector %r — keeping entry but flagging",
            idx,
            sector,
        )

    # Optional fields
    amount_usd = raw.get("amount_usd")
    if amount_usd is not None:
        try:
            amount_usd = float(amount_usd)
        except (TypeError, ValueError):
            logger.warning("Deal log entry %d has non-numeric amount_usd — setting to None", idx)
            amount_usd = None

    deal_type = raw.get("deal_type")
    if deal_type is not None:
        deal_type = str(deal_type).lower()
        if deal_type not in _VALID_DEAL_TYPES:
            logger.warning(
                "Deal log entry %d has unknown deal_type %r — keeping as-is", idx, deal_type
            )

    primary_ticker = raw.get("primary_ticker")
    if primary_ticker is not None:
        primary_ticker = str(primary_ticker).upper()

    source_url = raw.get("source_url")
    if source_url is not None:
        source_url = str(source_url)

    deal_id = _make_deal_id(entry_date, sector, str(summary))

    return DealLogEntry(
        deal_id=deal_id,
        date=entry_date,
        sector=sector,
        amount_usd=amount_usd,
        deal_type=deal_type,
        primary_ticker=primary_ticker,
        source_url=source_url,
        summary=str(summary),
    )


def load_deal_log_from_yaml(path: Path = _CONFIG_PATH) -> list[DealLogEntry]:
    """Read config/deal_log.yaml and return a list of DealLogEntry instances.

    Validates required fields (date, sector, summary).
    Logs warnings for malformed entries without raising — daily refresh must not abort.
    Raises FileNotFoundError if path does not exist.
    """
    if not path.exists():
        raise FileNotFoundError(f"Deal log YAML not found: {path}")

    with path.open("r") as fh:
        raw_list = yaml.safe_load(fh)

    if raw_list is None:
        return []

    if not isinstance(raw_list, list):
        raise ValueError(f"Deal log YAML must be a list at top level, got {type(raw_list).__name__}")

    entries: list[DealLogEntry] = []
    for idx, raw in enumerate(raw_list):
        entry = _parse_entry(raw, idx)
        if entry is not None:
            entries.append(entry)

    logger.info("Loaded %d valid deal log entries from %s", len(entries), path)
    return entries
