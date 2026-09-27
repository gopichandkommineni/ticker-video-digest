"""Daily Reddit digest — per stock, a short brief of what Reddit is saying and a
list of concrete insights, each linked to the posts it came from.

Reads what ingestion stored in data/reddit.db, summarises with a free LLM
(Gemini, see `gemini`), writes the digest back to reddit.db for the Ticker
Detail page. See docs/specs/reddit-digest-v1.md.
"""
from core.social_media.reddit.digest.digest import (
    DigestConfig,
    DigestReport,
    build_prompt,
    run_digest,
    select_posts,
    to_digest,
)
from core.social_media.reddit.digest.gemini import (
    GeminiClient,
    GeminiError,
    GeminiFatal,
    MissingKey,
    QuotaExhausted,
)
from core.social_media.reddit.digest.store import Digest, Insight, SourcePost, load_recent

__all__ = [
    "Digest",
    "DigestConfig",
    "DigestReport",
    "GeminiClient",
    "GeminiError",
    "GeminiFatal",
    "Insight",
    "MissingKey",
    "QuotaExhausted",
    "SourcePost",
    "build_prompt",
    "load_recent",
    "run_digest",
    "select_posts",
    "to_digest",
]
