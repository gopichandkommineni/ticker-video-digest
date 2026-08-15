"""Catalog-first subreddit discovery: enumerate subreddits, sort by subscriber
count, cut to the stock ones, then cut to the single-stock ones.

This is the top-down counterpart to `subreddit_discovery`, which works bottom-up
(guess r/RKLB, r/RKLBstock, … for one ticker at a time and probe each guess).
Guessing only ever finds subs whose name we thought of; a catalog sweep finds
r/ASTSpaceMobile without anybody naming it first. Three stages:

1. **ENUMERATE** — every subreddit the archive will hand over above a subscriber
   floor, sorted by subscriber count descending.
2. **MARKET** — keep the stock / stock-market ones (r/stocks, r/wallstreetbets,
   r/pennystocks, …), judged from name + title + description.
3. **PER-STOCK** — of those, keep the ones that belong to ONE company and
   attribute each to a ticker (r/RKLB → RKLB, r/ASTSpaceMobile → ASTS), judged
   from name/title/description and gated on subscriber count.

Reddit's own API is not usable here (the public JSON API is Cloudflare-blocked
and new API apps are gated), so the sweep runs against **Arctic Shift**, the
free community archive — same backend the rest of the Reddit code already uses.

**No global "order by subscribers" endpoint exists**, so stage 1 cannot ask the
archive for "the top 5000 subs". It pages through subreddits by *creation time*
with a server-side subscriber floor and sorts locally; a run is therefore
complete only down to that floor and up to its request budget, both of which the
report states explicitly rather than implying full coverage.
"""
import logging
import re
import time
from collections import deque

from pydantic import BaseModel, Field

from core.social_media.reddit.subreddit_discovery import (
    _FINANCE_CONTEXT,
    SubredditInfo,
    _as_sub_field,
    _relevance,
    _valid_subreddit_name,
)

logger = logging.getLogger(__name__)

_REQUEST_DELAY = 0.35     # polite pause between sweep pages
_PAGE_SIZE = 100          # Arctic Shift caps a page at 100 items
_REDDIT_EPOCH = 1119000000  # ~2005-06-17, before the first subreddit existed

# Fallback sweep, used only when the archive rejects creation-time paging. It
# starts from single-character prefixes and deepens into the ones that come back
# full — subreddit names are letters, digits and underscores.
_PREFIX_ALPHABET = "abcdefghijklmnopqrstuvwxyz0123456789_"
_FALLBACK_PREFIXES = list("abcdefghijklmnopqrstuvwxyz0123456789")
_MAX_PREFIX_DEPTH = 3    # "abc" — deeper than this costs more than it returns

# ---------------------------------------------------------------------------
# Stage-2 vocabulary — is this subreddit about the stock market at all?
#
# Matching is on whole TOKENS, not substrings, which is what keeps r/Stockholm,
# r/marketing, r/livestock and r/supermarket out: their names are single tokens
# ('stockholm'), so the token 'stock' never matches. camelCase names do split,
# so r/StockMarket -> {stock, market}.
# ---------------------------------------------------------------------------

# Self-sufficient: one of these in the NAME is enough to call it a market sub.
_MARKET_STRONG = {
    "stock", "stocks", "stockmarket", "stockmarkets", "stonks", "stonk",
    "wallstreetbets", "wallstreet", "wsb", "investing", "investment",
    "investments", "investor", "investors", "pennystocks", "pennystock",
    "daytrading", "swingtrading", "valueinvesting", "dividends", "dividend",
    "shortsqueeze", "nasdaq", "nyse", "etf", "etfs", "spac", "spacs",
    "hedgefund", "hedgefunds", "brokerage", "shareholders", "smallcaps",
    "microcaps", "bagholders", "tickers", "premarket", "aftermarket",
}

# Suffix forms of the strong terms, so r/CanadianStocks and r/ASXInvesting land
# too. Deliberately no bare 'stock' (that would readmit r/livestock) — plural
# and verb forms only.
_MARKET_STRONG_SUFFIXES = (
    "stocks", "stockmarket", "investing", "investors", "investor",
    "wallstreetbets", "pennystocks", "stonks",
)

# Need corroboration — a strong term elsewhere, or finance words in the text.
# On their own these are r/tradeoffers, r/marketing, r/Options (Elder Scrolls
# mods), r/capital (photography), so they never select alone.
_MARKET_WEAK = {
    "market", "markets", "trading", "trader", "traders", "trade", "options",
    "calls", "puts", "shares", "equity", "equities", "finance", "financial",
    "portfolio", "earnings", "ipo", "bull", "bulls", "bear", "bears",
    "bullish", "bearish", "ticker", "securities", "capital", "money",
    "dd", "yolo", "valuation", "fundamentals", "technicals",
}

# Text-only route: a sub whose NAME says nothing (r/ASTSpaceMobile) still counts
# as market-related if its title/description is unmistakably financial. Two
# distinct finance words are required, at least one of them from this
# unambiguous subset — otherwise "share your portfolio of art" reads as a stock
# sub, since 'share' and 'portfolio' are everyday words on their own.
_MIN_TEXT_FINANCE_WORDS = 2
_TEXT_FINANCE_STRONG = {
    "stock", "stocks", "invest", "investing", "investor", "investors",
    "shareholder", "shareholders", "nasdaq", "nyse", "ticker", "earnings",
    "dividend", "dividends", "bullish", "bearish", "equity", "equities",
    "trading", "traders", "puts", "calls", "valuation",
}

# Stage-3 gate: attribution confidence, matching the bottom-up discovery's bar.
_MIN_TICKER_RELEVANCE = 0.6


class TickerMatch(BaseModel):
    ticker: str
    company_name: str | None = None
    relevance: float


class MarketMatch(BaseModel):
    is_market: bool
    rule: str = ""                                  # which route qualified it
    signals: list[str] = Field(default_factory=list)


class CatalogRow(BaseModel):
    info: SubredditInfo
    market: MarketMatch
    ticker: TickerMatch | None = None

    @property
    def is_per_stock(self) -> bool:
        return self.ticker is not None


class UniverseEntry(BaseModel):
    """One stock to attribute subreddits to."""
    ticker: str
    company_name: str | None = None


class CatalogReport(BaseModel):
    strategy: str                    # how stage 1 enumerated (see fetch_catalog)
    min_subscribers: int
    requests_made: int
    scanned: int                     # unique subreddits seen
    truncated: bool                  # request budget hit before the sweep ended
    rows: list[CatalogRow] = Field(default_factory=list)   # ALL, subscribers desc

    @property
    def market_rows(self) -> list[CatalogRow]:
        return [r for r in self.rows if r.market.is_market]

    @property
    def ticker_rows(self) -> list[CatalogRow]:
        return [r for r in self.rows if r.is_per_stock]

    def by_ticker(self) -> dict[str, list[str]]:
        """{TICKER: [subreddit, ...]} — subreddits per stock, biggest first."""
        out: dict[str, list[str]] = {}
        for row in self.ticker_rows:
            assert row.ticker is not None
            out.setdefault(row.ticker.ticker, []).append(row.info.name)
        return out


# ---------------------------------------------------------------------------
# Stage 1 — enumerate
# ---------------------------------------------------------------------------

def info_from_item(item: dict) -> SubredditInfo | None:
    """Build a SubredditInfo from an Arctic Shift subreddit dict (None if unusable)."""
    name = _as_sub_field(item, "display_name", "name", default="")
    if not name or not _valid_subreddit_name(str(name)):
        return None
    return SubredditInfo(
        name=str(name),
        subscribers=int(_as_sub_field(item, "subscribers", "subscriber_count", default=0) or 0),
        active_online=0,
        title=str(_as_sub_field(item, "title", default="") or ""),
        public_description=str(
            _as_sub_field(item, "public_description", "description", default="") or ""
        ),
        created_utc=float(_as_sub_field(item, "created_utc", "created", default=0.0) or 0.0),
        over18=bool(_as_sub_field(item, "over18", "nsfw", default=False)),
        quarantined=bool(_as_sub_field(item, "quarantine", default=False)),
    )


def _page(**kwargs) -> tuple[int, list[dict]]:
    from core.social_media.reddit import arctic_shift_client as arctic  # noqa: PLC0415

    return arctic.search_subreddits_raw(**kwargs)


def _sweep_by_created(
    min_subscribers: int,
    max_requests: int,
    server_side_floor: bool,
    sleep: bool,
    forward: bool = True,
) -> tuple[dict[str, SubredditInfo], int, bool, bool]:
    """Page through subreddits by creation time, one cursor step per request.

    *forward* walks oldest-first (`after` cursor, explicit ``sort=asc``);
    otherwise it walks newest-first (`before` cursor, archive's default order),
    which is the shape to use when the archive rejects ``sort``.

    Returns (subs_by_lowercase_name, requests_made, truncated, supported).
    *supported* is False when the archive rejected the query shape (HTTP 400) on
    the very first page, which tells the caller to try a different shape rather
    than concluding Reddit has no subreddits.
    """
    found: dict[str, SubredditInfo] = {}
    cursor = _REDDIT_EPOCH if forward else int(time.time())
    requests_made = 0
    truncated = False

    while requests_made < max_requests:
        kwargs: dict = {"limit": _PAGE_SIZE}
        if forward:
            kwargs["after"], kwargs["sort"] = cursor, "asc"
        else:
            kwargs["before"] = cursor
        if server_side_floor:
            kwargs["min_subscribers"] = min_subscribers
        status, items = _page(**kwargs)
        requests_made += 1

        if status == 400:
            # Rejected on page 1 = this query shape is unsupported, so the caller
            # should try another. Rejected later = the shape works and something
            # else went wrong mid-sweep, leaving the result incomplete.
            first_page = requests_made == 1
            return found, requests_made, not first_page, not first_page
        if status != 200 or not items:
            break

        edge = cursor
        for item in items:
            info = info_from_item(item)
            if info is None:
                continue
            created = int(info.created_utc or 0)
            if created:
                edge = max(edge, created) if forward else min(edge, created)
            if info.subscribers >= min_subscribers:
                found.setdefault(info.name.lower(), info)

        # No cursor progress (every item shares the cursor's timestamp, or the
        # archive ignored after/before) — stop rather than spin on one page.
        if (edge <= cursor) if forward else (edge >= cursor):
            break
        cursor = edge
        if sleep:
            time.sleep(_REQUEST_DELAY)
    else:
        truncated = True

    return found, requests_made, truncated, True


def _sweep_by_prefix(
    min_subscribers: int,
    max_requests: int,
    prefixes: list[str],
    sleep: bool,
    max_depth: int = _MAX_PREFIX_DEPTH,
) -> tuple[dict[str, SubredditInfo], int, bool]:
    """Fallback sweep: page the archive by subreddit-name prefix.

    The archive returns at most one capped page per prefix, so a flat a–z sweep
    would see ~100 subs per letter and stop. Instead this is adaptive and
    breadth-first: a prefix that comes back FULL is assumed to have more behind
    it and is expanded into its children ("a" → "aa", "ab", …), while a prefix
    that comes back short is exhausted and closed out. Breadth-first matters
    because the request budget usually runs out mid-sweep — this way it runs out
    having covered every prefix at depth N, not a third of the alphabet in depth.
    """
    found: dict[str, SubredditInfo] = {}
    requests_made = 0
    truncated = False
    queue: deque[str] = deque(prefixes)

    while queue:
        if requests_made >= max_requests:
            truncated = True
            break
        prefix = queue.popleft()
        status, items = _page(query=prefix, limit=_PAGE_SIZE)
        requests_made += 1
        if status != 200:
            continue
        for item in items:
            info = info_from_item(item)
            if info is not None and info.subscribers >= min_subscribers:
                found.setdefault(info.name.lower(), info)
        if len(items) >= _PAGE_SIZE and len(prefix) < max_depth:
            queue.extend(prefix + char for char in _PREFIX_ALPHABET)
        if sleep:
            time.sleep(_REQUEST_DELAY)

    return found, requests_made, truncated


def fetch_catalog(
    min_subscribers: int = 1000,
    max_requests: int = 600,
    sleep: bool = True,
    prefixes: list[str] | None = None,
) -> tuple[list[SubredditInfo], str, int, bool]:
    """Enumerate subreddits with at least *min_subscribers* members.

    Returns (infos_sorted_by_subscribers_desc, strategy, requests_made, truncated).

    Query shapes are tried in order until one returns rows, because Arctic Shift
    is a community service whose accepted params drift and a rejected param
    comes back as HTTP 400 rather than a warning:

    1. ``created+min_subscribers`` — oldest-first creation-time paging with the
       subscriber floor applied server-side. Cheapest: every row is a keeper.
    2. ``created`` — same paging, floor applied locally (more pages, same yield).
    3. ``created-desc+min_subscribers`` / 4. ``created-desc`` — newest-first
       paging, which drops the explicit ``sort`` param for archives that reject it.
    5. ``prefix`` — adaptive name-prefix sweep, deepening into prefixes that come
       back full. Thinner coverage than creation-time paging; a floor to land on,
       not an equivalent.

    The shape that ran is returned so the report can state what the numbers
    actually cover.
    """
    shapes = [
        ("created+min_subscribers", {"server_side_floor": True, "forward": True}),
        ("created", {"server_side_floor": False, "forward": True}),
        ("created-desc+min_subscribers", {"server_side_floor": True, "forward": False}),
        ("created-desc", {"server_side_floor": False, "forward": False}),
    ]

    found: dict[str, SubredditInfo] = {}
    strategy, reqs, truncated = "", 0, False
    for label, kwargs in shapes:
        remaining = max_requests - reqs
        if remaining <= 0:
            truncated = True
            break
        found, sweep_reqs, truncated, _ = _sweep_by_created(
            min_subscribers, remaining, sleep=sleep, **kwargs
        )
        reqs += sweep_reqs
        strategy = label
        if found:
            break
        logger.info("Catalog: '%s' returned nothing — trying the next query shape", label)

    if not found and max_requests - reqs > 0:
        logger.info("Catalog: creation-time paging unavailable — falling back to prefix sweep")
        found, prefix_reqs, truncated = _sweep_by_prefix(
            min_subscribers, max_requests - reqs, prefixes or _FALLBACK_PREFIXES, sleep=sleep
        )
        strategy = "prefix"
        reqs += prefix_reqs

    infos = sorted(found.values(), key=lambda i: i.subscribers, reverse=True)
    logger.info(
        "Catalog: %d subreddits >= %d subscribers via %s (%d requests%s)",
        len(infos), min_subscribers, strategy, reqs, ", budget exhausted" if truncated else "",
    )
    return infos, strategy, reqs, truncated


# ---------------------------------------------------------------------------
# Stage 2 — is it about the stock market?
# ---------------------------------------------------------------------------

def _split_tokens(text: str) -> list[str]:
    """Lowercase word tokens, splitting punctuation AND camelCase humps.

    'StockMarket' -> ['stock', 'market']; 'wallstreetbets' -> ['wallstreetbets'];
    'ASTSpaceMobile' -> ['ast', 'space', 'mobile'].
    """
    parts = re.split(r"[^A-Za-z0-9]+", text)
    tokens: list[str] = []
    for part in parts:
        if not part:
            continue
        for piece in re.findall(r"[A-Z]+(?![a-z])|[A-Z][a-z0-9]*|[a-z0-9]+", part):
            tokens.append(piece.lower())
    return tokens


def _strong_hits(tokens: list[str]) -> list[str]:
    hits = []
    for tok in tokens:
        if tok in _MARKET_STRONG or (
            len(tok) > 6 and tok.endswith(_MARKET_STRONG_SUFFIXES)
        ):
            hits.append(tok)
    return hits


def classify_market(info: SubredditInfo, ticker: TickerMatch | None = None) -> MarketMatch:
    """Decide whether *info* is a stock / stock-market subreddit.

    Four routes, in confidence order:
      * ``ticker`` — it was attributed to a specific stock, so it is a stock sub
        by construction (r/RocketLab says nothing financial in its name).
      * ``name-strong`` — the name carries an unambiguous market term.
      * ``name-weak+context`` — an ambiguous name term (r/…Trading) plus a
        strong term or finance words in the text.
      * ``text`` — the name says nothing but the title/description is
        unmistakably financial (two or more distinct finance words).
    """
    if ticker is not None:
        return MarketMatch(is_market=True, rule="ticker", signals=[ticker.ticker])

    name_tokens = _split_tokens(info.name)
    text = f"{info.title} {info.public_description}"
    text_tokens = _split_tokens(text)

    name_strong = _strong_hits(name_tokens)
    if name_strong:
        return MarketMatch(is_market=True, rule="name-strong", signals=sorted(set(name_strong)))

    name_weak = sorted({t for t in name_tokens if t in _MARKET_WEAK})
    text_finance = sorted({t for t in text_tokens if t in _FINANCE_CONTEXT})
    text_strong = _strong_hits(text_tokens)

    if name_weak and (text_strong or text_finance):
        return MarketMatch(
            is_market=True,
            rule="name-weak+context",
            signals=name_weak + sorted(set(text_strong or text_finance)),
        )

    if len(text_finance) >= _MIN_TEXT_FINANCE_WORDS and (
        text_strong or set(text_finance) & _TEXT_FINANCE_STRONG
    ):
        return MarketMatch(is_market=True, rule="text", signals=text_finance)

    return MarketMatch(is_market=False, signals=name_weak)


# ---------------------------------------------------------------------------
# Stage 3 — does it belong to ONE stock?
# ---------------------------------------------------------------------------

def attribute_ticker(
    info: SubredditInfo,
    entries: list[UniverseEntry],
    min_subscribers: int = 0,
    min_relevance: float = _MIN_TICKER_RELEVANCE,
) -> TickerMatch | None:
    """Attribute *info* to the single stock it belongs to, or None.

    Scoring is `subreddit_discovery._relevance` — one shared definition of "this
    sub is about this stock" for both the top-down and bottom-up paths, so the
    two agree on r/cake (baking, not CAKE) and r/playstation (not PL).

    A tie between two tickers is left unattributed rather than guessed: an
    ambiguous sub in the per-stock map would silently poison that stock's feed.
    """
    if info.subscribers < min_subscribers:
        return None

    best: list[TickerMatch] = []
    best_score = 0.0
    for entry in entries:
        score = _relevance(info, entry.ticker, entry.company_name)
        if score < min_relevance or score < best_score:
            continue
        match = TickerMatch(
            ticker=entry.ticker.upper(), company_name=entry.company_name, relevance=score
        )
        if score > best_score:
            best_score, best = score, [match]
        else:
            best.append(match)

    if len(best) != 1:
        if len(best) > 1:
            logger.debug(
                "r/%s matches %s equally — left unattributed",
                info.name, ", ".join(m.ticker for m in best),
            )
        return None
    return best[0]


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def build_report(
    entries: list[UniverseEntry],
    min_subscribers: int = 1000,
    ticker_min_subscribers: int = 50,
    max_requests: int = 600,
    sleep: bool = True,
    infos: list[SubredditInfo] | None = None,
) -> CatalogReport:
    """Run all three stages and return the ranked report.

    Pass *infos* to classify an already-fetched catalog (tests, or a re-filter of
    a saved sweep) instead of hitting the network again.
    """
    if infos is None:
        infos, strategy, requests_made, truncated = fetch_catalog(
            min_subscribers=min_subscribers, max_requests=max_requests, sleep=sleep
        )
    else:
        infos = sorted(infos, key=lambda i: i.subscribers, reverse=True)
        strategy, requests_made, truncated = "supplied", 0, False

    rows: list[CatalogRow] = []
    for info in infos:
        ticker = attribute_ticker(info, entries, min_subscribers=ticker_min_subscribers)
        rows.append(CatalogRow(info=info, market=classify_market(info, ticker), ticker=ticker))

    return CatalogReport(
        strategy=strategy,
        min_subscribers=min_subscribers,
        requests_made=requests_made,
        scanned=len(rows),
        truncated=truncated,
        rows=rows,
    )
