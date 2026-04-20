"""Environment variable loading and constants."""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parents[2] / ".env")

ANTHROPIC_API_KEY: str = os.environ.get("ANTHROPIC_API_KEY", "").strip()
YOUTUBE_API_KEY: str = os.environ.get("YOUTUBE_API_KEY", "").strip()

if not ANTHROPIC_API_KEY:
    raise EnvironmentError(
        "ANTHROPIC_API_KEY is not set. Add it to .env or the environment."
    )
if not YOUTUBE_API_KEY:
    raise EnvironmentError(
        "YOUTUBE_API_KEY is not set. Add it to .env or the environment."
    )

MIN_VIDEO_DURATION_SECONDS: int = 120
MIN_SUBSCRIBER_COUNT: int = 500
MAX_VIDEO_AGE_DAYS: int = 7
MAX_RESULTS: int = 10
