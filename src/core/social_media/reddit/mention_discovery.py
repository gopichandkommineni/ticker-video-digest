"""Find a stock's subreddits from where it is actually discussed.

The name-based tools ask "which subreddits are called something like RKLB?".
This asks "where do people talk about RKLB?", and lets the posts decide.

The archive refuses keyword searches across all of Reddit (it needs a
subreddit or an author), and its text search has been timing out even inside
one subreddit. So nothing here uses text search. It reads posts by subreddit
or by author — plain filters — and checks for mentions locally:

  1. Seeds: posts that mention the stock, in its mapped subreddits and in the
     general list (the big finance subreddits while that list is empty).
  2. Authors: the people who wrote most of those posts. Each one's own posts
     over the window are read, and every subreddit where they mention the stock
     becomes a candidate.
  3. Measure: each candidate's posts over the window are read once. The share
     that mention the stock decides what it is:
       stock     a real share of its posts are about this stock
       general   the stock is discussed there, among much else
       weak      too little evidence
       excluded  profile pages, NSFW or quarantined

Read-only: nothing is written. The caller decides what to keep.
"""
import logging
import re
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Literal, Protocol

from pydantic import BaseModel, Field

from core.social_media.reddit import arctic_shift_client as arctic
from core.social_media.reddit.ingest.pipeline import (
    _noisy_ticker,
    short_company_name,
    ticker_keywords,
)
from core.social_media.reddit.scrape import _keyword_pattern

logger = logging.getLogger(__name__)

Verdict = Literal["stock", "general", "weak", "excluded"]
_VERDICT_ORDER = {"stock": 0, "general": 1, "weak": 2, "excluded": 3}

# Accounts whose posts say nothing about where people discuss a stock.
_NOT_PEOPLE = {"", "[deleted]", "[unknown]", "automoderator"}


class DiscoveryConfig(BaseModel):
    """Every tunable of a discovery run."""

    days: int = 90
    listing_cap: int = 1_000       # posts read per subreddit (newest first)
    author_cap: int = 250          # posts read per author
    max_authors: int = 40          # most active seed authors followed
    max_candidates: int = 20       # subreddits measured, beyond the map and seeds
    min_mentions: int = 3          # fewer mentions than this is "weak"
    min_authors: int = 2           # one person posting alone is "weak"
    stock_share: float = 0.25      # share of posts mentioning the stock → "stock"
    named_stock_share: float = 0.05  # the same, when the name matches ticker or company


class Fetch(Protocol):
    """What discovery needs from the archive. Each returns (http_status, items)."""

    def subreddit_posts(self, subreddit: str, after: datetime, cap: int) -> tuple[int, list[dict]]: ...

    def author_posts(self, author: str, after: datetime, cap: int) -> tuple[int, list[dict]]: ...

    def subreddit_info(self, subreddit: str) -> dict | None: ...


class ArcticFetch:
    """The real archive. Subreddit listings are cached, so a subreddit shared by
    several stocks (r/wallstreetbets) is read once per run."""

    def __init__(self) -> None:
        self.reads = 0
        self._listings: dict[tuple[str, int, int], tuple[int, list[dict]]] = {}

    def subreddit_posts(self, subreddit: str, after: datetime, cap: int) -> tuple[int, list[dict]]:
        key = (subreddit.lower(), int(after.timestamp()) // 3600, cap)
        if key not in self._listings:
            self.reads += 1
            self._listings[key] = arctic.search_posts_paged(
                subreddit=subreddit, after=after, max_items=cap)
        return self._listings[key]

    def author_posts(self, author: str, after: datetime, cap: int) -> tuple[int, list[dict]]:
        self.reads += 1
        return arctic.search_posts_paged(author=author, after=after, max_items=cap)

    def subreddit_info(self, subreddit: str) -> dict | None:
        self.reads += 1
        items = arctic.search_subreddits(subreddit=subreddit, limit=1)
        return items[0] if items else None


class Candidate(BaseModel):
    subreddit: str
    verdict: Verdict = "weak"
    reason: str = ""
    mentions: int = 0              # posts in the window that mention the stock
    posts: int = 0                 # posts read in the window
    share: float = 0.0
    authors: int = 0               # distinct authors of those mentions
    last_mention: datetime | None = None
    days_covered: float = 0.0      # less than the window when the listing hit its cap
    subscribers: int = 0
    name_match: bool = False
    mapped: bool = False           # already in config/ticker_subreddits.yaml
    via_authors: int = 0           # seed authors who mention the stock there
    found_via: list[str] = Field(default_factory=list)   # map, seed, authors


class Discovery(BaseModel):
    ticker: str
    company: str | None = None
    keywords: list[str]
    days: int
    seed_subreddits: list[str]
    seed_mentions: int = 0
    authors_followed: int = 0
    candidates: list[Candidate] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


# --- matching ---------------------------------------------------------------------

def _text(item: dict) -> str:
    return f"{item.get('title') or ''}\n{item.get('selftext') or item.get('body') or ''}"


def mentions_stock(item: dict, ticker: str, company: str | None) -> bool:
    """Does this post name the stock? Whole words, as the ingest search does.
    A ticker that is an everyday word (PATH, ON, AG) needs $TICKER or the company."""
    text = _text(item)
    if _noisy_ticker(ticker):
        if re.search(rf"\${re.escape(ticker)}(?![A-Za-z0-9])", text):
            return True
        short = short_company_name(company)
        return bool(short and _keyword_pattern(short).search(text))
    return any(_keyword_pattern(k).search(text) for k in ticker_keywords(ticker, company))


def _norm(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


def name_matches(subreddit: str, ticker: str, company: str | None) -> bool:
    """r/RKLBInvestors, r/RocketLab_de: the name carries the ticker or the company.
    Everyday-word tickers only count through the company name."""
    name = _norm(subreddit)
    if not _noisy_ticker(ticker) and ticker.lower() in name:
        return True
    short = _norm(short_company_name(company) or "")
    return len(short) >= 4 and short in name


def classify(c: Candidate, info: dict | None, cfg: DiscoveryConfig) -> tuple[Verdict, str]:
    if c.subreddit.lower().startswith("u_"):
        return "excluded", "a user's profile page"
    if info and (info.get("over18") or info.get("over_18")):
        return "excluded", "NSFW"
    if info and info.get("quarantine"):
        return "excluded", "quarantined"
    if c.posts == 0:
        return "weak", "no posts read in the window"
    if c.mentions < cfg.min_mentions or c.authors < cfg.min_authors:
        return "weak", f"{c.mentions} mention(s) by {c.authors} author(s)"
    needed = cfg.named_stock_share if c.name_match else cfg.stock_share
    if c.share >= needed:
        return "stock", f"{c.share:.0%} of posts mention it"
    return "general", f"discussed, but only {c.share:.1%} of posts"


# --- the run ----------------------------------------------------------------------

def _created(item: dict) -> datetime | None:
    try:
        return datetime.fromtimestamp(float(item.get("created_utc")), tz=timezone.utc)
    except (TypeError, ValueError, OSError):
        return None


def _measure(name: str, items: list[dict], ticker: str, company: str | None,
             now: datetime, cfg: DiscoveryConfig) -> Candidate:
    hits = [it for it in items if mentions_stock(it, ticker, company)]
    times = [t for t in map(_created, items) if t]
    hit_times = [t for t in map(_created, hits) if t]
    covered = cfg.days
    if len(items) >= cfg.listing_cap and times:
        covered = (now - min(times)).total_seconds() / 86_400
    return Candidate(
        subreddit=name,
        mentions=len(hits),
        posts=len(items),
        share=len(hits) / len(items) if items else 0.0,
        authors=len({str(it.get("author") or "") for it in hits} - {""}),
        last_mention=max(hit_times) if hit_times else None,
        days_covered=round(covered, 1),
    )


def discover(
    ticker: str,
    company: str | None,
    mapped: list[str],
    search_subreddits: list[str],
    fetch: Fetch | None = None,
    cfg: DiscoveryConfig | None = None,
    now: datetime | None = None,
) -> Discovery:
    """Rank the subreddits where *ticker* is discussed. See the module docstring."""
    cfg = cfg or DiscoveryConfig()
    fetch = fetch or ArcticFetch()
    now = now or datetime.now(tz=timezone.utc)
    ticker = ticker.upper()
    after = now - timedelta(days=cfg.days)
    seeds = list(dict.fromkeys(mapped + search_subreddits))
    result = Discovery(ticker=ticker, company=company, days=cfg.days,
                       keywords=ticker_keywords(ticker, company), seed_subreddits=seeds)

    listings: dict[str, list[dict] | None] = {}   # lower name → posts; None = read failed

    def listing(name: str) -> list[dict] | None:
        if name.lower() not in listings:
            status, items = fetch.subreddit_posts(name, after, cfg.listing_cap)
            if status != 200:
                result.warnings.append(f"r/{name}: couldn't read its posts "
                                       f"({arctic.last_error or f'HTTP {status}'})")
            listings[name.lower()] = items if status == 200 else None
        return listings[name.lower()]

    # 1. Seeds: who mentions the stock where we already look.
    author_counts: Counter[str] = Counter()
    for sub in seeds:
        for item in listing(sub) or []:
            if mentions_stock(item, ticker, company):
                result.seed_mentions += 1
                author_counts[str(item.get("author") or "")] += 1

    # 2. Follow the most active authors to wherever else they mention it.
    via: dict[str, set[str]] = {}
    names: dict[str, str] = {}
    authors = [a for a, _ in author_counts.most_common()
               if a.lower() not in _NOT_PEOPLE][: cfg.max_authors]
    for author in authors:
        status, items = fetch.author_posts(author, after, cfg.author_cap)
        if status != 200:
            result.warnings.append(f"u/{author}: couldn't read their posts "
                                   f"({arctic.last_error or f'HTTP {status}'})")
            continue
        result.authors_followed += 1
        for item in items:
            sub = str(item.get("subreddit") or "")
            if sub and mentions_stock(item, ticker, company):
                via.setdefault(sub.lower(), set()).add(author)
                names.setdefault(sub.lower(), sub)

    # 3. Measure the map, the seeds, and the busiest subreddits the authors led to.
    found: dict[str, list[str]] = {}
    for sub in mapped:
        found.setdefault(sub.lower(), []).append("map")
        names.setdefault(sub.lower(), sub)
    for sub in search_subreddits:
        found.setdefault(sub.lower(), []).append("seed")
        names.setdefault(sub.lower(), sub)
    by_authors = sorted(via, key=lambda k: (-len(via[k]), k))
    for key in by_authors[: cfg.max_candidates]:
        found.setdefault(key, []).append("authors")

    mapped_keys = {s.lower() for s in mapped}
    for key, how in found.items():
        name = names[key]
        profile = key.startswith("u_")
        items = [] if profile else listing(name)
        c = _measure(name, items or [], ticker, company, now, cfg)
        info = None if profile else fetch.subreddit_info(name)
        c.subscribers = int((info or {}).get("subscribers") or 0)
        c.name_match = name_matches(name, ticker, company)
        c.mapped = key in mapped_keys
        c.via_authors = len(via.get(key, ()))
        c.found_via = how
        c.verdict, c.reason = classify(c, info, cfg)
        result.candidates.append(c)

    result.candidates.sort(key=lambda c: (_VERDICT_ORDER[c.verdict], -c.mentions, c.subreddit.lower()))
    logger.info("%s: %d seed mentions, %d authors followed, %d subreddits measured",
                ticker, result.seed_mentions, result.authors_followed, len(result.candidates))
    return result
