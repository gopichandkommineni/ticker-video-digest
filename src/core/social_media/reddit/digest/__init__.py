"""Daily Reddit digest — per stock, a short brief of what Reddit is saying and a
list of concrete insights, each linked to the posts it came from.

Reads what ingestion stored in data/reddit.db, summarises with an LLM — the
Claude Code CLI on a Claude subscription (`claude_cli`) or Gemini's free tier
(`gemini`) — writes the digest back to reddit.db for the Ticker
Detail page. See docs/specs/reddit-digest-v1.md.
"""
from core.social_media.reddit.digest.claude_cli import ClaudeCliClient
from core.social_media.reddit.digest.digest import (
    DigestConfig,
    DigestReport,
    build_prompt,
    run_digest,
    select_posts,
    to_digest,
)
from core.social_media.reddit.digest.errors import LLMError, LLMFatal, MissingKey, QuotaExhausted
from core.social_media.reddit.digest.gemini import GeminiClient, GeminiError, GeminiFatal
from core.social_media.reddit.digest.store import Digest, Insight, SourcePost, load_recent

__all__ = [
    "ClaudeCliClient",
    "Digest",
    "DigestConfig",
    "DigestReport",
    "GeminiClient",
    "GeminiError",
    "GeminiFatal",
    "Insight",
    "LLMError",
    "LLMFatal",
    "MissingKey",
    "QuotaExhausted",
    "SourcePost",
    "build_prompt",
    "load_recent",
    "run_digest",
    "select_posts",
    "to_digest",
]
