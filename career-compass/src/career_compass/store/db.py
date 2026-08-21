"""Connection and migrations."""

from __future__ import annotations

import sqlite3
from pathlib import Path

DEFAULT_DB_PATH = Path("data/career.db")


def connect(path: Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Open with foreign keys ON and WAL enabled.

    Single writer only — the scheduled job must never overlap with itself.
    The run ledger's `running` status plus the Actions concurrency group
    enforce that (ADR-0010).
    """
    raise NotImplementedError


def migrate(conn: sqlite3.Connection) -> int:
    """Apply pending forward-only migrations. Returns the resulting version."""
    raise NotImplementedError
