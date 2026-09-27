"""Errors any digest LLM client raises, whichever model is behind it.

The runner only needs to know how bad a failure is:
- `LLMError`: this stock's call failed; record it and carry on.
- `LLMFatal`: every further call would fail the same way (bad key, not logged
  in, retired model), so stop the run.
- `QuotaExhausted`: the daily or plan allowance is spent, so stop until it resets.
- `MissingKey`: the client can't be set up at all (no key, no CLI).
"""


class LLMError(RuntimeError):
    """The call failed (bad response, server error after retries, bad JSON)."""


class LLMFatal(LLMError):
    """A failure every further call would repeat. Stop the run rather than
    fail 64 times."""


class QuotaExhausted(LLMFatal):
    """The allowance is used up (a free tier's daily quota, a plan's usage
    limit). Stop for now; the next run picks up the skipped stocks."""


class MissingKey(LLMError):
    """The client has no way in: no API key, or no Claude Code CLI."""
