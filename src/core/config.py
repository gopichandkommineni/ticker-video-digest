"""Environment variable loading and constants."""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parents[2] / ".env")

ANTHROPIC_API_KEY: str = os.environ.get("ANTHROPIC_API_KEY", "").strip()
YOUTUBE_API_KEY: str = os.environ.get("YOUTUBE_API_KEY", "").strip()
# Optional — market dashboard degrades gracefully when missing.
FRED_API_KEY: str = os.environ.get("FRED_API_KEY", "").strip()

# ---------------------------------------------------------------------------
# Social media credentials (all optional — scrapers degrade gracefully)
# ---------------------------------------------------------------------------
# Reddit: PRAW OAuth app credentials. Reddit now 403-blocks the unauthenticated
# public JSON API for most IPs, so these are effectively required for Reddit to
# return data. CLIENT_ID/SECRET alone -> read-only app-only OAuth; add
# USERNAME/PASSWORD for a "script" app's full user (password) grant.
REDDIT_CLIENT_ID: str = os.environ.get("REDDIT_CLIENT_ID", "").strip()
REDDIT_CLIENT_SECRET: str = os.environ.get("REDDIT_CLIENT_SECRET", "").strip()
REDDIT_USERNAME: str = os.environ.get("REDDIT_USERNAME", "").strip()
REDDIT_PASSWORD: str = os.environ.get("REDDIT_PASSWORD", "").strip()
# X (Twitter): API v2 bearer token for the recent-search endpoint.
X_BEARER_TOKEN: str = os.environ.get("X_BEARER_TOKEN", "").strip()

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


# ---------------------------------------------------------------------------
# Market dashboard configuration
# ---------------------------------------------------------------------------

# Per-indicator cache TTL (seconds). Intraday-quoted series (VIX) refresh
# fastest; daily series sit at ~6h; weekly/monthly FRED series at ~24h.
INDICATOR_TTLS: dict[str, int] = {
    # Stock-market & sentiment
    "VIX": 3600,
    "BUFFETT": 86400,
    "CAPE": 86400,
    "AAII": 86400,
    "MARGIN_DEBT": 86400,
    "PUT_CALL": 21600,
    "MAG7_CONCENTRATION": 21600,
    "BREADTH_RSP_SPY": 21600,
    # Real-economy
    "T10Y2Y": 86400,
    "INDPRO": 86400,
    "UNRATE": 86400,
    "ICSA": 86400,
    "CORE_CPI_YOY": 86400,
    "REAL_RETAIL_SALES": 86400,
    "M2_YOY": 86400,
}

# Sign in the composite. +1 means "high reading pushes Reality Score up
# (decoupling)"; -1 means "high reading pushes Reality Score down (alignment)".
# VIX is excluded from the composite and shown separately as context.
INDICATOR_SIGNS: dict[str, int] = {
    # market bucket — high readings = market hot
    "BUFFETT": +1,
    "CAPE": +1,
    "AAII": +1,
    "MARGIN_DEBT": +1,
    "MAG7_CONCENTRATION": +1,
    "PUT_CALL": -1,           # low P/C = greed → flip
    "BREADTH_RSP_SPY": -1,    # rising RSP/SPY = healthy breadth → flip
    # economy bucket — high readings = economy weak
    "T10Y2Y": -1,             # negative spread (inversion) = weakness → flip
    "INDPRO": -1,             # high industrial production = strong → flip
    "UNRATE": +1,
    "ICSA": +1,
    "CORE_CPI_YOY": +1,       # sticky inflation = pressure
    "REAL_RETAIL_SALES": -1,  # strong retail = aligned → flip
    "M2_YOY": -1,             # liquidity tide supports market → flip
}

INDICATOR_BUCKETS: dict[str, str] = {
    "BUFFETT": "market",
    "CAPE": "market",
    "AAII": "market",
    "MARGIN_DEBT": "market",
    "PUT_CALL": "market",
    "MAG7_CONCENTRATION": "market",
    "BREADTH_RSP_SPY": "market",
    "T10Y2Y": "economy",
    "INDPRO": "economy",
    "UNRATE": "economy",
    "ICSA": "economy",
    "CORE_CPI_YOY": "economy",
    "REAL_RETAIL_SALES": "economy",
    "M2_YOY": "economy",
    "VIX": "context",
}

# Reality Score = MARKET_BUCKET_WEIGHT * mean(market z's) + ECONOMY_BUCKET_WEIGHT * mean(economy z's)
REALITY_SCORE_WEIGHTS: dict[str, float] = {
    "market": 0.5,
    "economy": 0.5,
}
