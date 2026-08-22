"""Does today's code still agree with the production database?

`data/snapshots.db` is committed, and it was written by whatever version of this
code was live at the time. That makes it a free oracle: if the current code
disagrees with it, the current code changed something.

Two questions get asked here:

1. **Schema** — does `init_db()` on an empty file produce the same tables,
   columns and indexes that production actually has?
2. **Signals** — recomputing the stored signals from the stored inputs, does the
   current code produce the same numbers the old code did?

Marked `parity` and excluded from the default run because (2) takes ~20s.
Run them with `./run verify`.
"""
from __future__ import annotations

import shutil
import sqlite3
from datetime import date
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
PRODUCTION_DB = REPO_ROOT / "data" / "snapshots.db"

pytestmark = [
    pytest.mark.parity,
    pytest.mark.skipif(
        not PRODUCTION_DB.exists(),
        reason="data/snapshots.db not present — nothing to compare against",
    ),
]


def _schema_of(db_path: Path) -> tuple[dict, dict]:
    """(objects, columns) for a database, in a comparable shape."""
    conn = sqlite3.connect(db_path)
    objects = {
        (row[0], row[1]): row[2]
        for row in conn.execute(
            "SELECT type, name, tbl_name FROM sqlite_master "
            "WHERE name NOT LIKE 'sqlite_%' ORDER BY type, name"
        )
    }
    columns = {
        table: sorted((c[1], c[2]) for c in conn.execute(f"PRAGMA table_info({table})"))
        for kind, table in objects
        if kind == "table"
    }
    conn.close()
    return objects, columns


def test_init_db_matches_production_schema(tmp_path: Path) -> None:
    """A database created from scratch must match the one in production."""
    from casino_dashboard.db.schema import init_db

    fresh = tmp_path / "fresh.db"
    init_db(fresh)

    fresh_objects, fresh_columns = _schema_of(fresh)
    prod_objects, prod_columns = _schema_of(PRODUCTION_DB)

    missing = sorted(set(prod_objects) - set(fresh_objects))
    assert not missing, (
        f"production has objects init_db() would not create: {missing}. "
        f"Someone changed the database without changing schema.py."
    )

    for table in sorted(set(prod_columns) & set(fresh_columns)):
        assert fresh_columns[table] == prod_columns[table], (
            f"{table} columns differ.\n"
            f"  production: {prod_columns[table]}\n"
            f"  init_db()  : {fresh_columns[table]}"
        )


def test_signals_recompute_to_the_same_numbers(tmp_path: Path) -> None:
    """Recomputing production's signals from production's inputs reproduces them.

    Only valid while the newest snapshot and the newest signal row share a date.
    If prices have moved on since signals were last written, a difference is
    expected rather than a regression, so the test skips instead of lying.
    """
    from casino_dashboard.signals.orchestrator import compute_and_save_all_signals
    from casino_dashboard.universe import load_universe

    conn = sqlite3.connect(PRODUCTION_DB)
    latest_signal_date = conn.execute("SELECT MAX(date) FROM signals").fetchone()[0]
    latest_snapshot_date = conn.execute(
        "SELECT MAX(date) FROM ticker_snapshots"
    ).fetchone()[0]
    stored = {
        (ticker, name): value
        for ticker, name, value in conn.execute(
            "SELECT ticker, signal_name, value FROM signals WHERE date = ?",
            (latest_signal_date,),
        )
    }
    conn.close()

    if latest_snapshot_date != latest_signal_date:
        pytest.skip(
            f"snapshots run to {latest_snapshot_date} but signals only to "
            f"{latest_signal_date}; recomputing would legitimately differ"
        )
    assert stored, "production has no signals to compare against"

    working = tmp_path / "copy.db"
    shutil.copy(PRODUCTION_DB, working)
    compute_and_save_all_signals(load_universe(db_path=working), working)

    conn = sqlite3.connect(working)
    recomputed = {
        (ticker, name): value
        for ticker, name, value in conn.execute(
            "SELECT ticker, signal_name, value FROM signals WHERE date = ?",
            (date.today().isoformat(),),
        )
    }
    conn.close()

    shared = set(stored) & set(recomputed)
    assert len(shared) >= len(stored) * 0.95, (
        f"only {len(shared)} of {len(stored)} production signals were recomputed "
        f"at all — a signal was renamed or dropped"
    )

    mismatches = []
    for key in sorted(shared):
        was, now = stored[key], recomputed[key]
        if was is None and now is None:
            continue
        if (was is None) != (now is None) or abs(was - now) > 1e-9:
            mismatches.append(f"{key[0]}/{key[1]}: production={was} now={now}")

    assert not mismatches, (
        f"{len(mismatches)} of {len(shared)} signals changed value:\n  "
        + "\n  ".join(mismatches[:10])
    )
