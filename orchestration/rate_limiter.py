"""Per-provider rate limiter for the ingestion worker pool (spec §3.3).

One instance per provider, shared across that provider's worker threads. It
enforces a minimum wall-clock interval between successive HTTP calls. The
limiter is passed in via dependency injection (never a module global) so tests
can construct isolated instances.
"""

from __future__ import annotations

import threading
import time
from typing import Callable


class RateLimiter:
    """Serialize calls so they are at least ``min_interval_s`` seconds apart.

    Thread-safe: the lock is held across the sleep so concurrent callers queue
    up and are spaced by the interval rather than all firing at once.

    ``_monotonic`` / ``_sleep`` are injectable purely for deterministic tests;
    they default to the real clock.
    """

    def __init__(
        self,
        min_interval_s: float,
        *,
        _monotonic: Callable[[], float] = time.monotonic,
        _sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.min_interval = min_interval_s
        self.last_call = 0.0
        self.lock = threading.Lock()
        self._monotonic = _monotonic
        self._sleep = _sleep

    def wait(self) -> None:
        """Block until at least ``min_interval`` has elapsed since the last call."""
        with self.lock:
            elapsed = self._monotonic() - self.last_call
            if elapsed < self.min_interval:
                self._sleep(self.min_interval - elapsed)
            self.last_call = self._monotonic()


def from_interval_ms(interval_ms: float) -> RateLimiter:
    """Build a RateLimiter from a millisecond interval (config units, spec §5.3)."""
    return RateLimiter(interval_ms / 1000.0)
