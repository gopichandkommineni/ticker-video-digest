"""Load and persist the per-ticker subreddit map (config/ticker_subreddits.yaml).

This file is the committable source of truth for which subreddits the Reddit
scraper pulls per ticker. Subreddit discovery writes it (run with --save); it is
also hand-editable — add or remove subreddits by hand and they are respected.

Format:
    tickers:
      RKLB:
        subreddits: [RocketLab, RKLB]
        updated: "2026-08-13"
      ASTS:
        subreddits: [ASTSpaceMobile]
"""
import logging
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

_CONFIG_PATH = Path("config/ticker_subreddits.yaml")

_HEADER = (
    "# Per-ticker subreddit map — which subreddits the Reddit scraper pulls\n"
    "# for each stock. Written by `subreddit_discovery_run --save`, and freely\n"
    "# hand-editable: add/remove subreddits and they are respected on the next\n"
    "# run (re-running discovery for a ticker overwrites only that ticker).\n"
)


def load_subreddit_map(path: Path = _CONFIG_PATH) -> dict[str, list[str]]:
    """Return {TICKER: [subreddit, ...]}. Missing file or empty map -> {}.

    Tickers are upper-cased; subreddit lists are de-duplicated in order. Malformed
    entries are skipped with a warning rather than raising, so a hand-edit typo
    never breaks the refresh pipeline.
    """
    if not path.exists():
        return {}

    with path.open("r") as fh:
        raw = yaml.safe_load(fh)

    if not isinstance(raw, dict):
        return {}
    tickers = raw.get("tickers")
    if not isinstance(tickers, dict):
        return {}

    result: dict[str, list[str]] = {}
    for key, value in tickers.items():
        if not isinstance(key, str):
            logger.warning("Skipping non-string ticker key %r in subreddit map", key)
            continue
        subs_raw = value.get("subreddits") if isinstance(value, dict) else value
        if not isinstance(subs_raw, list):
            logger.warning("Skipping %r: 'subreddits' must be a list", key)
            continue
        seen: set[str] = set()
        subs: list[str] = []
        for s in subs_raw:
            if isinstance(s, str) and s and s not in seen:
                seen.add(s)
                subs.append(s)
        result[key.upper()] = subs
    return result


def save_subreddit_map(
    mapping: dict[str, list[str]],
    updated: str,
    path: Path = _CONFIG_PATH,
    merge: bool = True,
) -> None:
    """Write *mapping* ({TICKER: [subreddit, ...]}) to the YAML file.

    When *merge* is True (default) the existing file is loaded first and only the
    tickers in *mapping* are replaced — other tickers' entries (including manual
    ones) are preserved. *updated* is stamped on each written ticker; pass a date
    string (the runtime forbids Date.now-style calls, so callers supply it).
    """
    existing: dict[str, dict] = {}
    if merge and path.exists():
        with path.open("r") as fh:
            raw = yaml.safe_load(fh) or {}
        if isinstance(raw, dict) and isinstance(raw.get("tickers"), dict):
            existing = dict(raw["tickers"])

    for ticker, subs in mapping.items():
        existing[ticker.upper()] = {"subreddits": list(subs), "updated": updated}

    path.parent.mkdir(parents=True, exist_ok=True)
    ordered = {t: existing[t] for t in sorted(existing)}
    with path.open("w") as fh:
        fh.write(_HEADER)
        yaml.safe_dump({"tickers": ordered}, fh, sort_keys=False, default_flow_style=False)
