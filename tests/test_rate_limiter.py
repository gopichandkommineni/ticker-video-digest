"""RateLimiter tests (worker pool v1 spec §3.3, §8).

Deterministic: a fake monotonic clock and a record-only sleep make these tests
non-flaky (no real wall-clock waiting).
"""

from __future__ import annotations

import pytest

from fintwit.orchestration.rate_limiter import RateLimiter, from_interval_ms


class FakeClock:
    """A controllable monotonic clock; sleep() advances it and is recorded."""

    def __init__(self) -> None:
        # Start at a large value so the first wait() sees a huge elapsed gap and
        # does not sleep — matching real time.monotonic() (never near zero).
        self.t = 1000.0
        self.sleeps: list[float] = []

    def monotonic(self) -> float:
        return self.t

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.t += seconds


def test_min_interval_enforced():
    clock = FakeClock()
    rl = RateLimiter(0.2, _monotonic=clock.monotonic, _sleep=clock.sleep)

    # First call: no prior call, no sleep.
    rl.wait()
    assert clock.sleeps == []

    # Immediate second call: must sleep the full interval.
    rl.wait()
    assert clock.sleeps == [0.2]

    # Advance time partway, then call: sleeps only the remainder.
    clock.t += 0.05
    rl.wait()
    assert clock.sleeps[-1] == pytest.approx(0.15)

    # Advance well past the interval: no sleep.
    clock.t += 10.0
    rl.wait()
    assert len(clock.sleeps) == 2  # unchanged — no new sleep added


def test_independent_per_provider():
    clock_a = FakeClock()
    clock_b = FakeClock()
    a = RateLimiter(0.2, _monotonic=clock_a.monotonic, _sleep=clock_a.sleep)
    b = RateLimiter(0.5, _monotonic=clock_b.monotonic, _sleep=clock_b.sleep)

    # Hammering limiter A does not make limiter B wait.
    a.wait()
    a.wait()
    a.wait()
    assert clock_a.sleeps == [0.2, 0.2]
    assert clock_b.sleeps == []  # B untouched

    b.wait()
    b.wait()
    assert clock_b.sleeps == [0.5]


def test_from_interval_ms():
    rl = from_interval_ms(250)
    assert rl.min_interval == 0.25
