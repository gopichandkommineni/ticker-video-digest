# Ticker Video Digest

A tool that takes a stock ticker and produces a 7-day digest of YouTube
videos about it — catalysts, red flags, upcoming trends — with citations
back to specific video timestamps.

## Usage shapes
- CLI: `python -m ticker_digest RKLB`
- Streamlit web app: ticker input → analyze button → rendered report

## Stack
- Python 3.11
- uv for dependency management (pyproject.toml, not requirements.txt)
- google-api-python-client — YouTube Data API v3
- youtube-transcript-api — caption extraction
- anthropic SDK — Claude API calls
- pydantic v2 — structured LLM output schemas
- SQLite (stdlib sqlite3) — transcript and metadata caching
- Streamlit — web UI
- pytest — tests

## File layout
src/ticker_digest/
  __init__.py
  models.py         # Pydantic models: VideoMetadata, Transcript, VideoInsights, DigestReport
  youtube_client.py # search_recent_videos, get_video_metadata
  transcripts.py    # get_transcript (with cache), fetch_captions
  cache.py          # SQLite wrapper: get/set for transcripts and metadata
  analyzer.py       # extract_insights (per-video), synthesize_digest (cross-video)
  config.py         # env var loading, constants
  cli.py            # argparse entrypoint
app.py              # Streamlit entrypoint
tests/
  test_*.py
pyproject.toml
README.md

## Analysis approach
Two-pass LLM pipeline:
1. Per-video extraction (Claude Sonnet 4.6) — transcript in, VideoInsights
   pydantic model out. Includes catalysts, red_flags, upcoming_events,
   sentiment, each with timestamp_seconds for citations.
2. Cross-video synthesis (Claude Opus 4.7) — list of VideoInsights in,
   DigestReport out. Aggregates themes, ranks by source count, preserves
   citations.

Enable prompt caching on the system prompt + schema definitions since
they're reused across the per-video pass.

## Conventions
- Type hints on every function signature
- Pydantic models for every structured data boundary
- No secrets in code — read from environment variables only
  (ANTHROPIC_API_KEY, YOUTUBE_API_KEY)
- No network calls in unit tests — use fixtures or mocks
- Log at INFO level for user-visible progress, DEBUG for diagnostics

## Quality filters (pre-transcription)
- Minimum video duration: 120 seconds
- Minimum channel subscriber count: 500
- Exclude videos where title is ALL CAPS or contains rocket/fire emoji spam
- Prefer videos published in the last 7 days, sorted by view count

## Disclaimers
The output is aggregated commentary from public YouTube videos.
It is not investment advice. The UI and CLI must surface this clearly.
