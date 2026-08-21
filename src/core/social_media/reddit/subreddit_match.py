"""Find the subreddit that belongs to a company, by prefix search + metrics.

Where `subreddit_discovery` GUESSES names ("RKLB" -> try r/RKLB, r/RKLBstock, …)
and can only find what it thought to guess, this ASKS the archive which
subreddits actually start with a given prefix. That difference is not cosmetic:
guessing never found r/RocketLab (29k members) because "RocketLab" was not on
the guess list for RKLB, and one prefix query returns full metadata for every
hit, replacing ~40 per-name lookups with 2 requests.

Everything here is deterministic — no LLM — so it can run in CI.

Design rules, each one paid for by a false positive found in testing:

  * PREFIX QUERIES USE SEVERAL STEMS. Prefix matching is literal on the display
    name, so "nuscalepower" finds nothing while "nuscale" finds r/NuSCALE_POWER.
    We query the ticker, the first company word, and the joined company name.
  * limit=500, NOT the default. r/BBstock is invisible at limit=50 because a
    two-letter prefix has thousands of matches and the response is truncated.
  * NAME MATCHING IS WHOLE-WORD ONLY, never a bare substring. Substring matching
    maps MU -> r/Microneedling, INTU -> r/intuitiveeating, MRVL -> r/MarvelLegends.
  * THE DESCRIPTION MUST CORROBORATE. A name match alone cannot select: r/PATH,
    r/Poet, r/avav and r/sndk all have names identical to their ticker and
    nothing to do with the company. The description has to name the ticker or
    the company.
  * CIRCULAR EVIDENCE DOES NOT COUNT. r/QuantumComputing is named after the
    words in "Quantum Computing Inc." and its description repeats them, which
    says nothing about the stock — so a company-phrase name needs the ticker or
    finance vocabulary too. Size cannot make this call: r/ASTSpaceMobile is 18x
    bigger than r/ASTS and is genuine, r/QuantumComputing is 51x bigger than
    r/qubt_stock and is not.
"""
import logging
import re
import time
from datetime import datetime, timedelta, timezone

from pydantic import BaseModel, Field

from core.social_media.reddit import arctic_shift_client as arctic
from core.social_media.reddit.subreddit_discovery import (
    _COMPANY_SUFFIXES,
    _NAME_SUFFIXES,
    _norm,
)

logger = logging.getLogger(__name__)

_PREFIX_LIMIT = 500       # short prefixes truncate badly below this
_PAGE = 100               # the archive's hard per-request ceiling
_REQUEST_DELAY = 0.4
_RETRIES = 5              # the endpoint 422s intermittently under load
_COMMENT_PAGES = 3        # bounded sample for finalists only
_FINALISTS = 3
_MIN_SUBS = 10
_MAX_PREFIX = 21          # Reddit caps subreddit names at 21 characters, and the
                          # archive rejects a longer prefix outright with HTTP 400

# Tickers that are also everyday English words. For these a bare mention in a
# description proves nothing — r/PathofExileTrades says "path" constantly — so
# only the unambiguous $TICKER form counts as description evidence.
_COMMON_WORD_TICKERS = frozenset({
    "path", "poet", "coin", "hut", "net", "app", "cake", "eat", "open", "run",
    "lite",   # r/Liteaccess is Lite Access Technologies (LTE.V), not Lumentum
    "car", "all", "key", "gold", "cash", "play", "love", "fire", "real", "air",
    "well", "fun", "live", "nice", "best", "free", "step", "form", "site",
    "arm", "on", "it", "up", "so", "by", "we", "me", "go", "big", "new",
})

# Finance vocabulary. Deliberately EXCLUDES "share"/"shares": "a community to
# share and discuss news" is ordinary English, and counting it as finance
# context scored r/dellxps13 a perfect relevance for DELL.
_FINANCE_CONTEXT = frozenset({
    "stock", "stocks", "invest", "investing", "investor", "investors",
    "trading", "trader", "traders", "shareholder", "shareholders", "ticker",
    "nasdaq", "nyse", "amex", "earnings", "dividend", "dividends", "bullish",
    "bearish", "options", "equity", "equities", "dd", "calls", "puts",
    "portfolio", "valuation", "float", "premarket", "holders",
})


class SubredditMetrics(BaseModel):
    """What a subreddit looks like right now."""

    name: str
    subscribers: int = 0
    title: str = ""
    public_description: str = ""
    lang: str | None = None
    over18: bool = False
    created_utc: float | None = None
    posts_7d: int = 0
    posts_capped: bool = False
    comments_sampled: int = 0
    unique_commenters: int = 0
    comments_capped: bool = False
    # False until live metrics were actually fetched. Only the finalists are
    # measured, so without this an unmeasured candidate is indistinguishable
    # from a genuinely dead one — both would read as "0 posts, 0 commenters".
    measured: bool = False


class MatchCandidate(BaseModel):
    """A scored candidate with the reasoning that produced the score."""

    metrics: SubredditMetrics
    relevance: float = Field(ge=0.0, le=1.0)
    activity: int = 0
    score: float = 0.0
    selected: bool = False
    reasons: list[str] = Field(default_factory=list)


class MatchResult(BaseModel):
    query: str
    ticker: str | None = None
    company_name: str | None = None
    prefixes: list[str] = Field(default_factory=list)
    candidates: list[MatchCandidate] = Field(default_factory=list)
    best: MatchCandidate | None = None
    flag: str | None = None
    # False when any prefix query failed outright. A caller must not read
    # "no match" from an incomplete search — that is how bad data gets saved.
    archive_ok: bool = True


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------

def _tokens(text: str) -> set[str]:
    return {t for t in re.split(r"[^a-z0-9$]+", (text or "").lower()) if t}


def company_words(company: str | None) -> list[str]:
    """Meaningful words of a company name, legal suffixes removed."""
    if not company:
        return []
    words = [w.strip(".,").lower() for w in company.replace(",", " ").split()]
    return [w for w in words if w and w not in _COMPANY_SUFFIXES and len(w) >= 3]


def name_is_about(name: str, base: str) -> bool:
    """True when a subreddit NAME is *base*, or *base* + a finance suffix.

    Never a bare substring — that is what makes r/Microneedling look like MU.
    """
    if not base or len(base) < 2:
        return False
    nm = _norm(name)
    if nm == base:
        return True
    return nm.startswith(base) and nm[len(base):] in _NAME_SUFFIXES


def prefix_stems(ticker: str | None, company: str | None) -> list[str]:
    """Prefixes to ask the archive for.

    Several stems, because prefix matching is literal: r/NuSCALE_POWER is found
    by "nuscale" but not by the joined "nuscalepower".
    """
    stems: list[str] = []
    if ticker:
        stems.append(ticker.lower())
    words = company_words(company)
    if words:
        stems.append(_norm(words[0]))
        joined = _norm("".join(words))
        if joined and joined not in stems:
            stems.append(joined)
    seen: set[str] = set()
    return [s for s in stems
            if s and len(s) <= _MAX_PREFIX and not (s in seen or seen.add(s))]


# ---------------------------------------------------------------------------
# Archive access
# ---------------------------------------------------------------------------

def _request(path: str, params: dict) -> tuple[int, list[dict]]:
    """GET with bounded retry. The archive 422s ("Timeout, maybe slow down")
    under load, and a failed call must never be mistaken for an empty result."""
    url = f"{arctic._BASE}/api/{path}"
    status = 0
    for attempt in range(_RETRIES):
        status, items = arctic.request(url, params)
        if status == 200:
            return status, items
        if status == 400:
            # A rejected query is permanent — retrying wastes five round-trips
            # and then misreports a malformed request as an unreachable archive.
            logger.warning("archive rejected %s %s", path, params)
            return status, []
        time.sleep(1.0 * (attempt + 1))
    logger.warning("archive unreachable for %s %s (last status %s)", path, params, status)
    return status, []


def search_by_prefix(prefix: str, limit: int = _PREFIX_LIMIT) -> tuple[list[dict], bool]:
    """Every subreddit whose display name starts with *prefix*.

    Returns (hits, reachable). The second value matters: an unreachable archive
    and a genuinely empty result both yield [], and conflating them is exactly
    how a throttled run came to record "no subreddit exists" for tickers that
    have one — r/CCJ was lost that way.
    """
    if not prefix:
        return [], True
    status, items = _request("subreddits/search", {"subreddit_prefix": prefix, "limit": limit})
    # A 400 means this prefix was unusable, not that the archive is down — the
    # other stems for the same ticker may well have succeeded.
    return items, status in (200, 400)


def count_posts(subreddit: str, days: int = 7, max_pages: int = 10) -> tuple[int, bool]:
    """Exact post count over the window by paging a descending cursor.

    The archive caps every response at 100 regardless of the limit asked for, so
    a single call cannot distinguish "100 posts" from "thousands".
    Returns (count, hit_page_cap).
    """
    after = int((datetime.now(tz=timezone.utc) - timedelta(days=days)).timestamp())
    seen: set[str] = set()
    cursor: int | None = None
    for _ in range(max_pages):
        params = {"subreddit": subreddit, "limit": _PAGE, "after": after, "sort": "desc"}
        if cursor is not None:
            params["before"] = cursor
        status, items = _request("posts/search", params)
        if status != 200:
            return len(seen), True
        fresh = [i for i in items if i.get("id") not in seen]
        if not fresh:
            return len(seen), False
        seen.update(str(i.get("id")) for i in fresh)
        if len(items) < _PAGE:
            return len(seen), False
        cursor = min(int(i["created_utc"]) for i in fresh)
        time.sleep(_REQUEST_DELAY)
    return len(seen), True


def sample_commenters(subreddit: str, days: int = 7,
                      pages: int = _COMMENT_PAGES) -> tuple[int, int, bool]:
    """Bounded comment sample -> (comments_seen, unique_commenters, hit_cap).

    Unique COMMENTERS is the best available proxy for "how many people are
    actually here" — r/RKLB has ~30 people posting a week but ~490 commenting.
    Deliberately capped: a full week of comments for one busy sub is 20+ pages
    and several minutes, which is far too slow to do for every candidate.
    """
    after = int((datetime.now(tz=timezone.utc) - timedelta(days=days)).timestamp())
    seen: set[str] = set()
    authors: set[str] = set()
    cursor: int | None = None
    for _ in range(pages):
        params = {"subreddit": subreddit, "limit": _PAGE, "after": after, "sort": "desc"}
        if cursor is not None:
            params["before"] = cursor
        status, items = _request("comments/search", params)
        if status != 200:
            return len(seen), len(authors), True
        fresh = [i for i in items if i.get("id") not in seen]
        if not fresh:
            return len(seen), len(authors), False
        seen.update(str(i.get("id")) for i in fresh)
        authors.update(str(i.get("author")) for i in fresh
                       if i.get("author") not in (None, "[deleted]"))
        if len(items) < _PAGE:
            return len(seen), len(authors), False
        cursor = min(int(i["created_utc"]) for i in fresh)
        time.sleep(_REQUEST_DELAY)
    return len(seen), len(authors), True


def metrics_from_item(item: dict) -> SubredditMetrics | None:
    name = item.get("display_name") or item.get("name")
    if not name:
        return None
    return SubredditMetrics(
        name=str(name),
        subscribers=int(item.get("subscribers") or 0),
        title=" ".join(str(item.get("title") or "").split()),
        public_description=" ".join(str(item.get("public_description") or "").split()),
        lang=item.get("lang"),
        over18=bool(item.get("over18")),
        created_utc=item.get("created_utc"),
    )


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def relevance(metrics: SubredditMetrics, ticker: str | None,
              company: str | None) -> tuple[float, list[str]]:
    """0..1 that this subreddit is the company's, plus the reasons why.

    Name evidence and description evidence are scored separately and BOTH are
    needed for a confident match, because each alone produces known failures:
    a bare name match gives r/PATH (the train) and r/Poet (poetry), while a bare
    description mention gives any sub that happens to say the word.
    """
    why: list[str] = []
    # The description haystack deliberately EXCLUDES the subreddit's own name.
    # Including it lets every name match corroborate itself — which scored
    # r/PATH (the train) and r/sndk (Russian) a perfect 1.0 for their tickers.
    haystack = f"{metrics.title} {metrics.public_description}"
    tokens = _tokens(haystack)
    words = company_words(company)
    tkr = (ticker or "").lower()

    name_hit = name_is_ticker = False
    ticker_name_match = (_norm(metrics.name) == tkr if tkr in _COMMON_WORD_TICKERS
                         else name_is_about(metrics.name, tkr))
    if tkr and ticker_name_match:
        name_hit = name_is_ticker = True
        why.append("name is the ticker")
    elif words and name_is_about(metrics.name, _norm("".join(words))):
        name_hit = True
        why.append("name is the company")

    # Each kind of evidence is judged independently — an if/elif chain records
    # only the first and would make "Rocket Lab (RKLB)" look like a bare ticker
    # echo, since the company half never gets examined.
    # Word-boundary, NOT substring: "$pl" occurs inside "$PLTR" and "$mu"
    # inside "$MULN", which handed PL Palantir's sub and MU Mullen's.
    dollar_evidence = bool(tkr and re.search(rf"\${re.escape(tkr)}\b", haystack, re.I))
    ticker_token_evidence = bool(tkr and tkr in tokens and tkr not in _COMMON_WORD_TICKERS)
    # When the company name reduces to the ticker itself ("POET Technologies"
    # -> "poet"), naming the company IS the ticker echo, not a second fact.
    company_evidence = bool(words and all(w in tokens for w in words)
                            and not (len(words) == 1 and words[0] == tkr))
    if dollar_evidence:
        why.append("$TICKER in description")
    if ticker_token_evidence:
        why.append("ticker named in description")
    if company_evidence:
        why.append("company named in description")
    ticker_evidence = dollar_evidence or ticker_token_evidence
    desc_hit = ticker_evidence or company_evidence

    finance = bool(tokens & _FINANCE_CONTEXT)
    if finance:
        why.append("finance vocabulary")

    # CIRCULARITY GUARD. A sub named after the company phrase whose description
    # merely repeats that phrase has supplied no independent evidence:
    # r/QuantumComputing is named "quantum computing" and says "quantum
    # computing", which tells us nothing about Quantum Computing Inc. the stock.
    # A TICKER-named sub describing the company is different — r/CCJ saying
    # "Cameco" links two independent facts — as is a company-named sub that
    # names the ticker, e.g. r/ASTSpaceMobile's "NASDAQ: ASTS".
    if name_hit and not name_is_ticker and not ticker_evidence and not finance:
        why.append("description only repeats the company name")
        return 0.4, why

    # The same circularity applies to a TICKER-named sub. r/Poet is called
    # "poet" and titled "poet"; r/avav is called "avav" and described
    # "avavavavavav". Echoing the ticker adds nothing — the description has to
    # supply the company or finance context, as r/CCJ's "uranium company,
    # Cameco" and r/RKLB's "Rocket Lab (RKLB)" both do.
    if name_is_ticker and not company_evidence and not finance:
        why.append("description only repeats the ticker")
        return 0.4, why

    # A description in another language cannot be corroborating this company
    # unless it names it outright: r/sndk ("Сундучный сабреддит") is not SanDisk.
    if (metrics.lang or "en").lower()[:2] != "en" and not (company_evidence or dollar_evidence):
        why.append(f"non-English community ({metrics.lang})")
        return 0.4, why

    if name_hit and desc_hit:
        return 1.0, why
    if name_hit and finance:
        return 0.7, why
    if desc_hit and finance:
        return 0.6, why
    if name_hit or desc_hit:
        return 0.4, why
    return 0.0, why


def score(candidate_metrics: SubredditMetrics, ticker: str | None, company: str | None,
          peers: list[SubredditMetrics]) -> MatchCandidate:
    rel, why = relevance(candidate_metrics, ticker, company)
    activity = (candidate_metrics.unique_commenters * 3
                + candidate_metrics.posts_7d
                + candidate_metrics.subscribers // 100)

    reasons: list[str] = []
    if rel < 0.6:
        reasons.append(f"description does not confirm the company (relevance {rel:.1f})")
    if candidate_metrics.subscribers < _MIN_SUBS and candidate_metrics.posts_7d == 0:
        # Word this honestly: an unmeasured candidate has posts_7d == 0 because
        # nobody looked, not because the sub is dead.
        reasons.append(
            f"only {candidate_metrics.subscribers} members and no recent posts"
            if candidate_metrics.measured
            else f"only {candidate_metrics.subscribers} members (activity not measured)"
        )
    if candidate_metrics.over18:
        reasons.append("NSFW")

    selected = not reasons
    return MatchCandidate(
        metrics=candidate_metrics,
        relevance=rel,
        activity=activity,
        score=round(rel * activity, 2),
        selected=selected,
        reasons=(why if selected else reasons),
    )


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def match(query: str, ticker: str | None = None, company_name: str | None = None,
          with_metrics: bool = True, finalists: int = _FINALISTS) -> MatchResult:
    """Find the subreddit that belongs to *query* (a ticker OR a company name).

    Cheap evidence first: one prefix query per stem yields every candidate with
    its metadata, and the text gates discard most of them. Only the surviving
    finalists are worth spending post/comment requests on.
    """
    result = MatchResult(query=query, ticker=ticker, company_name=company_name)
    result.prefixes = prefix_stems(ticker, company_name)
    if not result.prefixes:
        result.flag = "nothing to search for — no ticker or company name"
        return result

    found: dict[str, SubredditMetrics] = {}
    for stem in result.prefixes:
        items, reachable = search_by_prefix(stem)
        if not reachable:
            result.archive_ok = False
        for item in items:
            metrics = metrics_from_item(item)
            if metrics and metrics.name.lower() not in found:
                found[metrics.name.lower()] = metrics
        time.sleep(_REQUEST_DELAY)
    logger.info("%s: %d candidate(s) from prefixes %s", query, len(found), result.prefixes)
    if not found:
        result.flag = ("archive unreachable — search incomplete, result unknown"
                       if not result.archive_ok
                       else "no subreddit found with these prefixes")
        return result

    # Text gate first — it is free, and it removes the overwhelming majority.
    peers = list(found.values())
    plausible = [m for m in peers if relevance(m, ticker, company_name)[0] >= 0.6]
    plausible.sort(key=lambda m: -m.subscribers)

    if with_metrics:
        for metrics in plausible[:finalists]:
            metrics.posts_7d, metrics.posts_capped = count_posts(metrics.name)
            (metrics.comments_sampled, metrics.unique_commenters,
             metrics.comments_capped) = sample_commenters(metrics.name)
            metrics.measured = True
            logger.info("  r/%s: %d subs, %d posts/7d, %d commenters",
                        metrics.name, metrics.subscribers, metrics.posts_7d,
                        metrics.unique_commenters)

    scored = [score(m, ticker, company_name, plausible) for m in plausible]
    scored.sort(key=lambda c: (c.selected, c.score), reverse=True)
    result.candidates = scored
    result.best = next((c for c in scored if c.selected), None)
    if result.best is None:
        result.flag = (f"no confident match among {len(found)} candidate(s) — "
                       "nothing had both a matching name and a confirming description")
        if not result.archive_ok:
            result.flag += " (and the search was incomplete — archive unreachable)"
    return result
