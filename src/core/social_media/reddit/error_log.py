"""Why outside calls failed — the Reddit pipeline's error log.

Every failed call to an outside service is recorded here with the service's own
reason, not just a status code: the Reddit archive (Arctic Shift) refusing a
search, a network error, or the digest's LLM (Claude CLI / Gemini) failing for a
stock. Two ways to read it:

- in the run report: `summary_lines()` groups the run's failures by source,
  status and reason, with a count and an example of what was being asked;
- on disk: set REDDIT_ERROR_LOG to a file path and each failure is also appended
  there as one JSON line (the local `./run reddit-brief` job does this, in its
  logs folder), so reasons survive the run.

Recording never raises: observability must not break the pipeline.
"""
import json
import logging
import os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

_MAX_RECENT = 500


class ErrorRecord(BaseModel):
    at: str                                  # ISO time, UTC
    source: str                              # "arctic_shift" | "digest_llm" | …
    status: int = 0                          # HTTP status; 0 = no response / not HTTP
    reason: str = ""                         # the service's own words
    context: dict[str, str] = Field(default_factory=dict)   # what was being asked


_recent: list[ErrorRecord] = []


def record(source: str, status: int, reason: str, **context: object) -> ErrorRecord:
    """Note a failed call. Context values are stringified; None values dropped."""
    rec = ErrorRecord(
        at=datetime.now(tz=timezone.utc).isoformat(timespec="seconds"),
        source=source, status=status, reason=(reason or "").strip()[:300],
        context={k: str(v)[:200] for k, v in context.items() if v is not None and v != ""},
    )
    _recent.append(rec)
    del _recent[:-_MAX_RECENT]
    path = os.environ.get("REDDIT_ERROR_LOG", "").strip()
    if path:
        try:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            with open(path, "a", encoding="utf-8") as fh:
                fh.write(rec.model_dump_json() + "\n")
        except OSError as exc:
            logger.debug("Could not write %s: %s", path, exc)
    return rec


def recent(source: str | None = None) -> list[ErrorRecord]:
    """This process's failures, oldest first (optionally one source only)."""
    return [r for r in _recent if source is None or r.source == source]


def clear() -> None:
    _recent.clear()


def summary_lines(source: str | None = None, limit: int = 10) -> list[str]:
    """Markdown: failures grouped by (source, status, reason), most frequent
    first, each with a count and one example of what was being asked."""
    records = recent(source)
    if not records:
        return []
    groups = Counter((r.source, r.status, r.reason or "(no reason given)") for r in records)
    example = {}
    for r in records:
        example.setdefault((r.source, r.status, r.reason or "(no reason given)"), r)
    lines = [f"### Why calls failed ({len(records)})", "",
             "| Source | Status | Reason | Times | Example |", "|---|---|---|---|---|"]
    for key, n in groups.most_common(limit):
        src, status, reason = key
        ctx = ", ".join(f"{k}={v}" for k, v in example[key].context.items())
        lines.append(f"| {src} | {status or '—'} | {_cell(reason)} | {n} | {_cell(ctx)} |")
    if len(groups) > limit:
        lines.append(f"| … | | {len(groups) - limit} more kinds | | |")
    return lines


def _cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")[:160]


def read_log(path: Path, limit: int = 20) -> list[ErrorRecord]:
    """The last *limit* records from a REDDIT_ERROR_LOG file ([] if none)."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()[-limit:]
    except OSError:
        return []
    out = []
    for line in lines:
        try:
            out.append(ErrorRecord(**json.loads(line)))
        except (ValueError, TypeError):
            continue
    return out
