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

# Apify managed Reddit scraper (handles Cloudflare/anti-bot). When APIFY_TOKEN is
# set, the Reddit pull uses Apify instead of the (now-blocked) direct JSON path.
APIFY_TOKEN: str = os.environ.get("APIFY_TOKEN", "").strip()
# Actor id in the API "username~actor-name" form. Override to use a different one.
APIFY_REDDIT_ACTOR: str = os.environ.get("APIFY_REDDIT_ACTOR", "trudax~reddit-scraper").strip()

# ANTHROPIC_API_KEY is deliberately *not* required at import. Two reasons: the
# SDK resolves credentials from more places than this variable (an `ant auth
# login` profile counts), and the YouTube digest can reach Claude through a
# locally installed Claude Code CLI with no key at all. Features that truly
# need a key call require_anthropic_key() instead.
if not YOUTUBE_API_KEY:
    raise EnvironmentError(
        "YOUTUBE_API_KEY is not set. Add it to .env or the environment."
    )

def require_anthropic_key(feature: str) -> str:
    """Return the API key, or explain what to do when there isn't one."""
    if ANTHROPIC_API_KEY:
        return ANTHROPIC_API_KEY
    raise EnvironmentError(
        f"{feature} needs Claude, but ANTHROPIC_API_KEY is not set. "
        "Add it to .env or the environment."
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


# ---------------------------------------------------------------------------
# YouTube digest — models, source scoring, novelty, storage
# ---------------------------------------------------------------------------

# Two-pass pipeline: a cheaper model per video, a stronger one for synthesis.
# Overridable so a run can be pinned to a different model without a code change.
EXTRACTION_MODEL: str = os.environ.get(
    "TICKER_DIGEST_EXTRACTION_MODEL", "claude-sonnet-4-6"
).strip()
SYNTHESIS_MODEL: str = os.environ.get(
    "TICKER_DIGEST_SYNTHESIS_MODEL", "claude-opus-4-7"
).strip()

# How the digest reaches Claude: "api" (the Anthropic SDK, needs credentials),
# "cli" (shell out to a logged-in Claude Code CLI, needs none), or "auto" —
# the API when a key is present, the CLI when it isn't.
LLM_BACKEND: str = os.environ.get("TICKER_DIGEST_LLM_BACKEND", "auto").strip().lower()
CLAUDE_CLI_PATH: str = os.environ.get("TICKER_DIGEST_CLAUDE_CLI", "claude").strip()
# A long transcript through a cold CLI process is not fast.
CLAUDE_CLI_TIMEOUT_SECONDS: int = int(
    os.environ.get("TICKER_DIGEST_CLAUDE_CLI_TIMEOUT", "600")
)

# Transcripts are truncated before they reach the model. A 2-hour video is
# ~90k characters; this keeps a single extraction call bounded.
MAX_TRANSCRIPT_CHARS: int = 120_000

# Reliability scoring. Each component is normalised to 0..1 and combined with
# these weights, so the total is also 0..1. Subscribers and views say "does
# anyone listen to this channel"; engagement (views per subscriber) says "did
# this particular video land"; depth rewards long-form over a 3-minute take;
# recency prefers commentary published against current facts.
RELIABILITY_WEIGHTS: dict[str, float] = {
    "subscribers": 0.30,
    "views": 0.25,
    "engagement": 0.15,
    "depth": 0.15,
    "recency": 0.15,
}

# Saturation points for the log-scaled components — a channel at or above this
# subscriber count scores 1.0 on that component.
RELIABILITY_SUBSCRIBER_SATURATION: int = 500_000
RELIABILITY_VIEW_SATURATION: int = 100_000
# Depth saturates at 20 minutes; a video this long or longer is "in depth".
RELIABILITY_DEPTH_SATURATION_SECONDS: int = 1_200

# Titles that look like engagement bait are dropped before transcription.
SPAM_TITLE_EMOJI: tuple[str, ...] = ("🚀", "🔥", "💎", "🌙", "💰")
# ALL-CAPS detection ignores the ticker itself, so "RKLB stock" is fine but
# "RKLB STOCK IS ABOUT TO EXPLODE" is not. A title is spammy when this share
# of its long words are upper-case.
SPAM_TITLE_CAPS_RATIO: float = 0.7
# More than this many spam emoji anywhere in the title is also bait.
SPAM_TITLE_MAX_EMOJI: int = 1

# Videos are ranked, then walked in order until enough of them yield a
# transcript. Plenty of otherwise-good videos have captions disabled, and
# finding that out is free — so a run backfills from the ranked remainder
# rather than analysing fewer videos than asked for. This bounds how far down
# the list it will walk: max_videos x this, so a request for 5 tries at most 15.
TRANSCRIPT_ATTEMPT_MULTIPLIER: int = 3

# Novelty detection. Claims from a new run are compared against claims stored
# from earlier runs for the same ticker within this window.
NOVELTY_LOOKBACK_DAYS: int = 90
# Jaccard similarity over normalised claim tokens. At or above this, the claim
# is a restatement and is marked "known" without spending an LLM call.
CLAIM_SIMILARITY_THRESHOLD: float = 0.72

# Where digest runs, claims and threads are stored. Separate from the
# dashboard's snapshots.db, and git-ignored (see .gitignore).
DIGEST_DB_PATH: Path = Path(
    os.environ.get("TICKER_DIGEST_DB", str(Path(__file__).parents[2] / "data" / "digests.db"))
)
