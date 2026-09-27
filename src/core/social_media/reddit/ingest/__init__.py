"""Reddit ingestion — collect posts and comment threads for every stock into
data/reddit.db, for analysis (LLM digests, dashboard panels).

Reads the resolver's subreddit map, calls the Reddit client (`scrape`), stores
what it finds. `run_ingest` is one run; `db` is the store.
"""
from core.social_media.reddit.ingest.db import connect, default_db_path
from core.social_media.reddit.ingest.pipeline import (
    IngestConfig,
    IngestReport,
    run_ingest,
    short_company_name,
    ticker_keywords,
)

__all__ = [
    "IngestConfig",
    "IngestReport",
    "connect",
    "default_db_path",
    "run_ingest",
    "short_company_name",
    "ticker_keywords",
]
