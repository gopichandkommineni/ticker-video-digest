"""Orchestration configuration — reads from environment, never hardcoded."""

from __future__ import annotations

import os

# Which provider to use by default. Override per-call or set env var.
TWEET_PROVIDER: str = os.environ.get("TWEET_PROVIDER", "getxapi").strip()

# How long (minutes) a handle can stay in backfilling/fetching before
# the orchestrator treats it as stale/retryable (silent-failure rule F2).
STALE_THRESHOLD_MINUTES: int = int(os.environ.get("STALE_THRESHOLD_MINUTES", "60"))
