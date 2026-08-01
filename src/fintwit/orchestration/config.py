"""Orchestration configuration — reads from environment, never hardcoded."""

from __future__ import annotations

import json
import os

# Which provider to use by default. Override per-call or set env var.
TWEET_PROVIDER: str = os.environ.get("TWEET_PROVIDER", "getxapi").strip()

# How long (minutes) a handle can stay in backfilling/fetching before
# the orchestrator treats it as stale/retryable (silent-failure rule F2).
STALE_THRESHOLD_MINUTES: int = int(os.environ.get("STALE_THRESHOLD_MINUTES", "60"))


# ---------------------------------------------------------------------------
# Worker pool defaults (worker pool v1 spec §5.3). Every value is
# environment-overridable. Dict/list values accept a JSON env override; a
# malformed override falls back to the baked-in default rather than crashing
# ingestion.
# ---------------------------------------------------------------------------

def _json_env(name: str, default):
    raw = os.environ.get(name)
    if not raw:
        return default
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        return default


# Per-provider worker counts. twitterapi.io gets more workers than getxapi
# because it has the larger rate budget (spec §2 decision 3).
WORKER_POOL_SIZES: dict[str, int] = _json_env(
    "WORKER_POOL_SIZES", {"twitterapi": 5, "getxapi": 3}
)

# Per-provider minimum interval between HTTP calls, milliseconds (spec §3.3).
RATE_LIMITER_INTERVALS_MS: dict[str, int] = _json_env(
    "RATE_LIMITER_INTERVALS_MS", {"twitterapi": 200, "getxapi": 500}
)

# Attempts (claims) allowed per (handle, date, provider) before a row is left
# terminally failed (spec §2 decision 4 / §5.3).
MAX_ATTEMPTS: int = int(os.environ.get("MAX_ATTEMPTS", "3"))

# Backoff before the next eligible claim, indexed by attempt number. Two
# schedules (PR A): rate-limit (429) recovers fast; other transient failures
# (5xx, network) get longer waits because the upstream is unhealthy.
BACKOFF_SCHEDULE_RATE_LIMIT_SEC: list[int] = _json_env(
    "BACKOFF_SCHEDULE_RATE_LIMIT_SEC", [60, 300, 1800]      # 60s, 5min, 30min
)
BACKOFF_SCHEDULE_TRANSIENT_SEC: list[int] = _json_env(
    "BACKOFF_SCHEDULE_TRANSIENT_SEC", [300, 900, 3600]      # 5min, 15min, 1hr
)
# Back-compat alias: the worker pool v1 name referenced the single 429 schedule.
BACKOFF_SCHEDULE_SEC: list[int] = BACKOFF_SCHEDULE_RATE_LIMIT_SEC

# A row left in 'fetching' longer than this is treated as a crashed worker and
# is eligible for re-claim by the dispatch query (spec §9).
STALE_FETCHING_THRESHOLD_SEC: int = int(
    os.environ.get("STALE_FETCHING_THRESHOLD_SEC", "600")
)
