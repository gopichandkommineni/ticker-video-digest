"""Subreddit resolver — which subreddits belong to which stock.

Two inputs, one output:

- a company name (or ticker) → `resolve_company` searches the Reddit archive and
  returns ranked candidates; `save_resolved` stores the ones you pick;
- a subreddit name → `add_subreddit` stores it directly, for one stock or on the
  general list.

The output is the subreddit map, config/ticker_subreddits.yaml (`store`), which
the Reddit scraper reads.
"""
from core.social_media.reddit.resolver.resolve import (
    add_subreddit,
    resolve_company,
    resolve_query,
    save_resolved,
)
from core.social_media.reddit.resolver.store import (
    SubredditEntry,
    add_entries,
    clean_subreddit_name,
    load_entries,
    load_general_subreddits,
    load_subreddit_map,
    remove_entry,
    save_subreddit_map,
)

__all__ = [
    "SubredditEntry",
    "add_entries",
    "add_subreddit",
    "clean_subreddit_name",
    "load_entries",
    "load_general_subreddits",
    "load_subreddit_map",
    "remove_entry",
    "resolve_company",
    "resolve_query",
    "save_resolved",
    "save_subreddit_map",
]
