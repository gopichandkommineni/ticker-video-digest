"""robots.txt, rate limiting, and identification.

Enforced centrally so a new adapter cannot forget. There is deliberately no
override flag: a block is an answer, and the answer is respected
(docs/08-legal-and-etiquette.md).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PolitenessPolicy:
    requests_per_second_per_host: float = 1.0
    jitter_seconds: float = 0.3
    max_retries: int = 3
    user_agent: str = "career-compass/0.1 (personal research; +contact@example.com)"


class RobotsCache:
    """Per-host robots.txt, fetched once and cached for the run."""

    def allowed(self, url: str, user_agent: str) -> bool:
        raise NotImplementedError


class HostRateLimiter:
    """Token bucket per host, with jitter.

    The dataset is small and there is no deadline. There is never a reason to
    be fast.
    """

    def acquire(self, host: str) -> None:
        raise NotImplementedError
