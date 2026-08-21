"""`career` — the command surface.

Design phase: every command is declared and documented, none implemented.
The list is itself a design artifact — if a command is hard to name, the
underlying model is probably wrong.
"""

from __future__ import annotations

import argparse

COMMANDS = {
    # ── setup and health ──────────────────────────────────────────────────
    "init":             "Create data/career.db, apply migrations, sync config.",
    "sources verify":   "Fetch each source once and show what came back. The ONLY "
                        "way `verified` becomes true — a human looks and decides.",
    "sources status":   "Per-source last-ok, consecutive failures, disabled state.",
    "doctor":           "Config, taxonomy, and profile validation in one pass.",

    # ── pipeline ──────────────────────────────────────────────────────────
    "ingest":           "Fetch due sources. --company, --source, --manual, --force.",
    "normalize":        "Raw → documents. --all replays the entire raw store offline.",
    "extract":          "Run the LLM passes. --version to A/B a new prompt.",
    "analyze":          "Recompute demand, supply, gaps, and the prep plan.",
    "refresh":          "ingest + normalize + extract + analyze. What the cron runs.",

    # ── reading ───────────────────────────────────────────────────────────
    "brief":            "The one-pager for a company. `career brief netflix`.",
    "gaps":             "Ranked gaps. --company, --by leverage|gap, --show-suppressed.",
    "plan":             "This cycle's prep items, targeting the weakest supply component.",
    "diff":             "What changed. --since 7d.",
    "themes":           "What a company has been writing about, quote-backed.",
    "docs":             "List ingested documents. --company, --kind, --since.",
    "jobs":             "Open postings. --company, --level, --include-closed.",
    "cross":            "Skills in demand at 3+ targets at once. The highest-ROI prep.",

    # ── me ────────────────────────────────────────────────────────────────
    "profile show":     "Claims and evidence, flagging every claim with none.",
    "profile validate": "Check every skill slug in resume.yaml against the taxonomy.",

    # ── manual intervention ───────────────────────────────────────────────
    "note":             "Attach a note to any entity. --pin to force it into briefs.",
    "taxonomy review":  "Frequency-ranked unmapped phrases. The monthly 10-minute loop "
                        "that keeps the vocabulary from freezing.",
    "taxonomy validate":"Check for duplicate slugs and ambiguous aliases.",
}


def build_parser() -> argparse.ArgumentParser:
    raise NotImplementedError


def main(argv: list[str] | None = None) -> int:
    raise NotImplementedError
