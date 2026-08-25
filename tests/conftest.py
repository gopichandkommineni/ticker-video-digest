"""Configure test environment before any ticker_digest modules are imported."""
import os

import pytest

# Prevent config.py from raising EnvironmentError during test collection.
# These are fake keys — no real API calls are made in unit tests.
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ.setdefault("YOUTUBE_API_KEY", "test-key")


@pytest.fixture(autouse=True)
def _reset_llm_backend():
    """The digest resolves its Claude backend once per process.

    That cache is deliberate — it is how a rejected API key is remembered — but
    it must not survive from one test into the next.
    """
    from ticker_digest import llm

    llm.reset_backend()
    yield
    llm.reset_backend()
