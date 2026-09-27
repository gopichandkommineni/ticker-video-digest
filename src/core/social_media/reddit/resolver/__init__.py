"""Subreddit resolver — which subreddits belong to which stock.

Two inputs, one output:

- a company name (or ticker) → `resolve_company` searches the Reddit archive and
  returns ranked candidates; `save_resolved` stores the ones you pick;
- a subreddit name → `add_subreddit_auto` works out which stock it belongs to
  and stores it there, or on the general list when no single stock matches
  (`add_subreddit` stores it where you say, no lookup).

The output is the subreddit map, config/ticker_subreddits.yaml (`store`), which
the Reddit scraper reads.
"""
from core.social_media.reddit.resolver.resolve import (
    SubredditAttribution,
    add_subreddit,
    add_subreddit_auto,
    attribute_subreddit,
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
    "SubredditAttribution",
    "SubredditEntry",
    "add_entries",
    "add_subreddit",
    "add_subreddit_auto",
    "attribute_subreddit",
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
