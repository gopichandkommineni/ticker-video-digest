"""Post-pool cross-provider reconciliation (worker pool v1 spec §3.6).

After the worker pool finishes, every (handle, date, provider) row carries a
single-provider outcome: complete / exhausted / failed. Reconciliation collapses
the per-provider view into the cross-provider verdict the rest of the system
already understands:

  - both providers terminal (complete/exhausted) AND counts agree → 'ok'
  - both providers terminal AND counts disagree                   → 'mismatch'
  - any provider still failed / pending / fetching                → skipped
    (the failed row must retry first)

This preserves the pre-pool semantics: 'ok'/'mismatch' stay the cross-provider
verdict; 'complete'/'exhausted' are the single-provider outcomes that feed it.
The count-agreement threshold is the same one the sequential path uses.
"""

from __future__ import annotations

import logging
import sqlite3
from collections import Counter

from .day_fetcher import MISMATCH_THRESHOLD

logger = logging.getLogger(__name__)

# Single-provider terminal states that are ready to be reconciled (spec §3.6).
_TERMINAL = frozenset({"complete", "exhausted"})


def _verdict(counts: list[int]) -> str:
    """'ok' if the provider counts agree within MISMATCH_THRESHOLD, else 'mismatch'.

    Mirrors day_fetcher._verify_and_mark: diff as a fraction of the larger count.
    """
    hi = max(counts) if counts else 0
    lo = min(counts) if counts else 0
    denom = max(hi, 1)
    diff_frac = (hi - lo) / denom
    return "ok" if diff_frac <= MISMATCH_THRESHOLD else "mismatch"


def reconcile_completed_days(conn: sqlite3.Connection) -> dict:
    """Collapse terminal single-provider rows into ok/mismatch (spec §3.6).

    Idempotent: rows already reconciled to ok/mismatch are not terminal and are
    skipped. Returns a summary dict: {'ok', 'mismatch', 'skipped'}.
    """
    rows = conn.execute(
        "SELECT handle, date, provider, status, tweets_fetched "
        "FROM day_fetch_log"
    ).fetchall()

    groups: dict[tuple[str, str], dict[str, tuple[str, int | None]]] = {}
    for r in rows:
        groups.setdefault((r["handle"], r["date"]), {})[r["provider"]] = (
            r["status"], r["tweets_fetched"],
        )

    summary: Counter = Counter()
    for (handle, date), provs in groups.items():
        statuses = {s for (s, _) in provs.values()}
        # Reconcile only when BOTH providers reached a terminal single-provider
        # status. A failed/pending/fetching row (or a lone provider) → skip.
        if len(provs) < 2 or not statuses.issubset(_TERMINAL):
            summary["skipped"] += 1
            continue

        counts = [(c or 0) for (_, c) in provs.values()]
        verdict = _verdict(counts)
        with conn:
            conn.execute(
                "UPDATE day_fetch_log SET status = ? "
                "WHERE handle = ? AND date = ? AND status IN ('complete', 'exhausted')",
                (verdict, handle, date),
            )
        summary[verdict] += 1
        if verdict == "mismatch":
            logger.warning("reconcile %s %s — mismatch: counts=%s", handle, date, counts)

    result = {"ok": summary["ok"], "mismatch": summary["mismatch"],
              "skipped": summary["skipped"]}
    logger.info("reconcile_completed_days: %s", result)
    return result
