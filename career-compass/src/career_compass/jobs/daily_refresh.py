"""Daily: ingest → normalize → extract → analyze.

`python -m career_compass.jobs.daily_refresh`

Contract:
  * Opens one run-ledger row per stage.
  * Per-source failure isolation — a broken endpoint marks itself failed and
    the job still commits its results.
  * A stage that fails ENTIRELY leaves the database untouched. A stale
    database is strictly better than a half-written one.
  * Idempotent and resumable: re-running after an interruption re-fetches only
    what is missing or stale.
"""

from __future__ import annotations


def main() -> int:
    raise NotImplementedError


if __name__ == "__main__":
    raise SystemExit(main())
