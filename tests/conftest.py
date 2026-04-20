"""Configure test environment before any ticker_digest modules are imported."""
import os

# Prevent config.py from raising EnvironmentError during test collection.
# These are fake keys — no real API calls are made in unit tests.
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ.setdefault("YOUTUBE_API_KEY", "test-key")
