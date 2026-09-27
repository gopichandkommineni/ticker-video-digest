"""The resolver's two ways in.

1. By company: `resolve_company("Rocket Lab")` works out the ticker and company
   name, then runs the prefix-search matcher (`subreddit_match.match`) and
   returns every candidate with its evidence. Nothing is saved until the caller
   picks names and calls `save_resolved` — the matcher is good, not perfect.
2. By name: `add_subreddit("wallstreetbets", ticker=None)` puts a subreddit
   straight into the map, optionally tied to a stock. No network call.

Both write to the subreddit map (see `store`), which is what the scraper reads.
"""
import logging
from pathlib import Path

from core.social_media.reddit.resolver.store import (
    _CONFIG_PATH,
    SubredditEntry,
    add_entries,
    clean_subreddit_name,
    today,
)
from core.social_media.reddit.subreddit_match import MatchCandidate, MatchResult, match
from core.social_media.reddit.ticker_resolver import company_name_for, resolve_ticker

logger = logging.getLogger(__name__)


def resolve_query(query: str, universe: set[str] | None = None) -> tuple[str | None, str | None]:
    """Turn a free-form query into (ticker, company_name).

    Both directions matter: "RKLB" needs a company name so the search can find
    r/RocketLab, and "rocket lab" needs a ticker so it can find r/RKLB.
    """
    ticker = resolve_ticker(query, universe)
    looked_like_ticker = ticker is not None and query.strip().upper() == ticker
    company = None if looked_like_ticker else query.strip()
    if ticker and not company:
        company = company_name_for(ticker)
    return ticker, company


def resolve_company(
    query: str,
    universe: set[str] | None = None,
    ticker: str | None = None,
    with_metrics: bool = True,
) -> MatchResult:
    """Find the subreddits that belong to a company (or ticker).

    *ticker* overrides the lookup — use it when the name can't be resolved to a
    ticker automatically. The result lists every plausible candidate, best
    first; `candidate.selected` marks the ones the matcher is confident about.
    """
    query = query.strip()
    if not query:
        raise ValueError("enter a company name or ticker")
    found_ticker, company = resolve_query(query, universe)
    if ticker:
        ticker = ticker.strip().upper()
        if company is None:
            company = company_name_for(ticker)
    else:
        ticker = found_ticker
    logger.info("resolving %r -> ticker=%s company=%s", query, ticker, company)
    return match(query, ticker=ticker, company_name=company, with_metrics=with_metrics)


def _entry_from_candidate(candidate: MatchCandidate, ticker: str, added: str) -> SubredditEntry:
    metrics = candidate.metrics
    return SubredditEntry(
        name=metrics.name,
        ticker=ticker,
        source="resolved",
        added=added,
        subscribers=metrics.subscribers,
        note="; ".join(candidate.reasons) or None,
    )


def save_resolved(
    result: MatchResult,
    names: list[str],
    ticker: str | None = None,
    path: Path = _CONFIG_PATH,
    added: str | None = None,
) -> list[SubredditEntry]:
    """Save the candidates named in *names* from a `resolve_company` result.

    They are stored under *ticker*, else the ticker the result resolved to.
    Returns the entries actually added (already-saved ones are skipped).
    """
    target = (ticker or result.ticker or "").strip().upper()
    if not target:
        raise ValueError(
            f"couldn't work out a ticker for {result.query!r} — enter one to save under"
        )
    wanted = {n.lower() for n in names}
    by_name = {c.metrics.name.lower(): c for c in result.candidates}
    unknown = sorted(wanted - set(by_name))
    if unknown:
        raise ValueError(f"not among the candidates: {', '.join(unknown)}")
    stamp = added or today()
    entries = [_entry_from_candidate(by_name[n], target, stamp) for n in by_name if n in wanted]
    return add_entries(entries, path)


def add_subreddit(
    name: str,
    ticker: str | None = None,
    path: Path = _CONFIG_PATH,
    added: str | None = None,
) -> SubredditEntry | None:
    """Add a subreddit straight to the map, no lookup.

    *ticker* ties it to one stock; leave it None for the general list. Returns
    the new entry, or None if it was already there. Raises ValueError for a
    name Reddit could not have.
    """
    entry = SubredditEntry(
        name=clean_subreddit_name(name),
        ticker=ticker.strip().upper() if ticker and ticker.strip() else None,
        source="manual",
        added=added or today(),
    )
    saved = add_entries([entry], path)
    return saved[0] if saved else None
