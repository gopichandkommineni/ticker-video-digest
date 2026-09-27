"""The subreddit map — config/ticker_subreddits.yaml — and every read/write of it.

This file is the committable source of truth for which subreddits the Reddit
scraper reads. It is written by the resolver (the Subreddits page and
`subreddit_resolve`), by the discovery/match/catalog runners with --save, and
by hand. Hand edits are respected.

Format:
    tickers:
      RKLB:
        subreddits: [RocketLab, RKLB]
        updated: '2026-09-27'
        details:                       # optional — why each one is here
          RocketLab: {source: resolved, added: '2026-09-27', subscribers: 29000}
          RKLB: {source: manual, added: '2026-09-27'}
    general:                           # subreddits not tied to one stock
      subreddits: [wallstreetbets]
      details:
        wallstreetbets: {source: manual, added: '2026-09-27'}

`subreddits` stays a plain list so the file is easy to hand-edit; `details` is
optional and an entry without one is simply a legacy/hand-added subreddit.
Subreddit names are compared case-insensitively (Reddit treats them that way)
but stored in the case they were given.
"""
import logging
import re
from datetime import date
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel

logger = logging.getLogger(__name__)

_CONFIG_PATH = Path("config/ticker_subreddits.yaml")

_HEADER = (
    "# Per-ticker subreddit map — which subreddits the Reddit scraper reads for\n"
    "# each stock, plus a 'general' list not tied to one stock. Written by the\n"
    "# subreddit resolver (Subreddits page / subreddit_resolve) and the\n"
    "# discovery runners, and freely hand-editable: changes are respected.\n"
    "# Manually added subreddits survive a re-run of discovery for that ticker.\n"
)

Source = Literal["manual", "resolved"]

# Reddit names: letters, digits, underscore; 3–21 characters today, but a few
# old communities are shorter, so accept 2.
_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_]{1,20}$")
_PREFIX_RE = re.compile(
    r"^(?:https?://)?(?:(?:www|old|new)\.)?(?:reddit\.com)?/?r/", re.IGNORECASE
)


class SubredditEntry(BaseModel):
    """One subreddit in the map, and why it is there."""

    name: str
    ticker: str | None = None          # None = the general list
    source: Source | None = None       # None = saved before provenance was recorded, or hand-edited
    added: str | None = None
    subscribers: int | None = None
    note: str | None = None


def clean_subreddit_name(raw: str) -> str:
    """Normalise user input to a bare subreddit name, or raise ValueError.

    Accepts 'wallstreetbets', 'r/wallstreetbets', '/r/wallstreetbets' and a
    pasted URL like 'https://www.reddit.com/r/wallstreetbets/'.
    """
    name = _PREFIX_RE.sub("", raw.strip()).strip("/").split("/")[0].strip()
    if not _NAME_RE.fullmatch(name):
        raise ValueError(
            f"{raw!r} is not a valid subreddit name — use letters, digits and "
            "underscores, 2–21 characters (e.g. wallstreetbets)"
        )
    return name


# --- raw file access ---------------------------------------------------------

def _read_raw(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open("r") as fh:
        raw = yaml.safe_load(fh)
    return raw if isinstance(raw, dict) else {}


def _write_raw(raw: dict, path: Path) -> None:
    tickers = raw.get("tickers") if isinstance(raw.get("tickers"), dict) else {}
    out: dict = {"tickers": {t: tickers[t] for t in sorted(tickers)}}
    general = raw.get("general")
    if isinstance(general, dict) and general.get("subreddits"):
        out["general"] = general
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as fh:
        fh.write(_HEADER)
        yaml.safe_dump(out, fh, sort_keys=False, default_flow_style=False)


def _clean_list(value: object, label: str) -> list[str] | None:
    """The de-duplicated subreddit list of one block, or None if malformed."""
    subs_raw = value.get("subreddits") if isinstance(value, dict) else value
    if not isinstance(subs_raw, list):
        logger.warning("Skipping %r: 'subreddits' must be a list", label)
        return None
    seen: set[str] = set()
    subs: list[str] = []
    for s in subs_raw:
        if isinstance(s, str) and s and s.lower() not in seen:
            seen.add(s.lower())
            subs.append(s)
    return subs


def _details(block: object) -> dict[str, dict]:
    details = block.get("details") if isinstance(block, dict) else None
    if not isinstance(details, dict):
        return {}
    return {str(k).lower(): v for k, v in details.items() if isinstance(v, dict)}


# --- reads -------------------------------------------------------------------

def load_subreddit_map(path: Path = _CONFIG_PATH) -> dict[str, list[str]]:
    """Return {TICKER: [subreddit, ...]}. Missing file or empty map -> {}.

    Tickers are upper-cased; subreddit lists are de-duplicated in order. Malformed
    entries are skipped with a warning rather than raising, so a hand-edit typo
    never breaks the refresh pipeline. The general list is not included — see
    `load_general_subreddits`.
    """
    tickers = _read_raw(path).get("tickers")
    if not isinstance(tickers, dict):
        return {}

    result: dict[str, list[str]] = {}
    for key, value in tickers.items():
        if not isinstance(key, str):
            logger.warning("Skipping non-string ticker key %r in subreddit map", key)
            continue
        subs = _clean_list(value, key)
        if subs is not None:
            result[key.upper()] = subs
    return result


def load_general_subreddits(path: Path = _CONFIG_PATH) -> list[str]:
    """The subreddits on the general list (not tied to one stock)."""
    general = _read_raw(path).get("general")
    if general is None:
        return []
    return _clean_list(general, "general") or []


def load_entries(path: Path = _CONFIG_PATH) -> list[SubredditEntry]:
    """Every subreddit in the map with its details, per-ticker entries first."""
    raw = _read_raw(path)
    entries: list[SubredditEntry] = []
    tickers = raw.get("tickers") if isinstance(raw.get("tickers"), dict) else {}
    blocks: list[tuple[str | None, object]] = [
        (str(t).upper(), v) for t, v in sorted(tickers.items(), key=lambda kv: str(kv[0]))
    ]
    if "general" in raw:
        blocks.append((None, raw["general"]))
    for ticker, block in blocks:
        details = _details(block)
        for name in _clean_list(block, ticker or "general") or []:
            info = details.get(name.lower(), {})
            source = info.get("source")
            entries.append(SubredditEntry(
                name=name,
                ticker=ticker,
                source=source if source in ("manual", "resolved") else None,
                added=str(info["added"]) if info.get("added") else None,
                subscribers=info.get("subscribers") if isinstance(info.get("subscribers"), int) else None,
                note=info.get("note"),
            ))
    return entries


# --- writes ------------------------------------------------------------------

def _entry_details(entry: SubredditEntry) -> dict:
    info: dict = {}
    if entry.source:
        info["source"] = entry.source
    if entry.added:
        info["added"] = entry.added
    if entry.subscribers is not None:
        info["subscribers"] = entry.subscribers
    if entry.note:
        info["note"] = entry.note
    return info


def _block(raw: dict, ticker: str | None) -> dict:
    """The (created-if-missing) block for *ticker*, or the general block."""
    if ticker is None:
        general = raw.get("general")
        if not isinstance(general, dict):
            general = {"subreddits": list(general) if isinstance(general, list) else []}
            raw["general"] = general
        return general
    tickers = raw.setdefault("tickers", {})
    if not isinstance(tickers, dict):
        tickers = raw["tickers"] = {}
    block = tickers.get(ticker)
    if not isinstance(block, dict):
        block = {"subreddits": list(block) if isinstance(block, list) else []}
        tickers[ticker] = block
    return block


def add_entries(
    entries: list[SubredditEntry],
    path: Path = _CONFIG_PATH,
) -> list[SubredditEntry]:
    """Append *entries* to the map, keeping everything already there.

    A subreddit already listed under the same ticker (or on the general list)
    is skipped. Returns the entries actually added.
    """
    raw = _read_raw(path)
    added: list[SubredditEntry] = []
    for entry in entries:
        ticker = entry.ticker.upper() if entry.ticker else None
        block = _block(raw, ticker)
        subs = _clean_list(block, ticker or "general") or []
        if entry.name.lower() in {s.lower() for s in subs}:
            continue
        block["subreddits"] = subs + [entry.name]
        info = _entry_details(entry)
        if info:
            details = block.get("details") if isinstance(block.get("details"), dict) else {}
            details[entry.name] = info
            block["details"] = details
        if ticker is not None and entry.added:
            block["updated"] = entry.added
        added.append(entry.model_copy(update={"ticker": ticker}))
    if added:
        _write_raw(raw, path)
    return added


def remove_entry(name: str, ticker: str | None, path: Path = _CONFIG_PATH) -> bool:
    """Remove *name* from *ticker*'s list (or the general list). True if removed.

    A ticker left with no subreddits is dropped from the file entirely, so the
    scraper falls back to its default subreddits for it.
    """
    raw = _read_raw(path)
    ticker = ticker.upper() if ticker else None
    tickers = raw.get("tickers") if isinstance(raw.get("tickers"), dict) else {}
    block = raw.get("general") if ticker is None else tickers.get(ticker)
    if block is None:
        return False
    subs = _clean_list(block, ticker or "general") or []
    kept = [s for s in subs if s.lower() != name.lower()]
    if len(kept) == len(subs):
        return False

    if not isinstance(block, dict):
        block = {"subreddits": kept}
    block["subreddits"] = kept
    if isinstance(block.get("details"), dict):
        block["details"] = {k: v for k, v in block["details"].items() if str(k).lower() != name.lower()}
        if not block["details"]:
            del block["details"]

    if ticker is None:
        raw["general"] = block
    elif kept:
        tickers[ticker] = block
    else:
        del tickers[ticker]
    _write_raw(raw, path)
    return True


def save_subreddit_map(
    mapping: dict[str, list[str]],
    updated: str,
    path: Path = _CONFIG_PATH,
    merge: bool = True,
) -> None:
    """Replace each ticker's list in *mapping* ({TICKER: [subreddit, ...]}).

    Used by the discovery/match/catalog runners' --save. When *merge* is True
    (default) other tickers are untouched. Within a replaced ticker, subreddits
    someone added by hand (source: manual) are kept after the new list, so a
    discovery re-run never silently drops a deliberate choice. *updated* is
    stamped on each written ticker.
    """
    raw = _read_raw(path) if merge else {}
    tickers = raw.get("tickers") if isinstance(raw.get("tickers"), dict) else {}

    for ticker, subs in mapping.items():
        ticker = ticker.upper()
        old = tickers.get(ticker)
        old_details = _details(old)
        manual = [
            s for s in ((_clean_list(old, ticker) or []) if old is not None else [])
            if old_details.get(s.lower(), {}).get("source") == "manual"
        ]
        new_subs = _clean_list(list(subs), ticker) or []
        lowered = {s.lower() for s in new_subs}
        final = new_subs + [s for s in manual if s.lower() not in lowered]
        block: dict = {"subreddits": final, "updated": updated}
        kept_details = {s: old_details[s.lower()] for s in final if s.lower() in old_details}
        if kept_details:
            block["details"] = kept_details
        tickers[ticker] = block

    raw["tickers"] = tickers
    _write_raw(raw, path)


def today() -> str:
    return date.today().isoformat()
