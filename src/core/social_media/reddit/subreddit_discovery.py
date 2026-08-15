"""Discover which subreddits belong to a given stock and rank them by community
metrics, so per-ticker post-pulling can target real communities and drop noise.

Public Reddit JSON API only — no credentials required. Two discovery paths are
combined: (1) a pattern generator that guesses common naming conventions from
the ticker and company name (r/RKLB, r/RKLBstock, r/RKLB_investors, r/RocketLab,
r/Rocket_Lab, …), and (2) Reddit's own /subreddits/search endpoint to catch
communities the patterns miss. Each surviving candidate is scored from the
metrics we CAN see publicly.

Important limitation: true traffic stats (unique visitors / pageviews per
day/week) live at /r/{sub}/about/traffic.json and are **moderator-only** — not
available for subs we do not moderate. Ranking therefore uses subscriber count,
currently-online count, measured recent-post volume, and name/description
relevance, not visitor counts.
"""
import logging
import math
import re
import time
from datetime import datetime, timedelta, timezone

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

_REQUEST_DELAY = 0.5   # polite pause between metric calls
_MAX_CANDIDATES = 40   # hard cap on subs probed per ticker (bounds request volume)

# Corporate suffixes stripped before turning a company name into subreddit-name
# guesses ("Rocket Lab USA, Inc." -> "RocketLab" / "Rocket_Lab").
_COMPANY_SUFFIXES = {
    "inc", "incorporated", "corp", "corporation", "co", "company", "ltd",
    "limited", "plc", "llc", "lp", "holdings", "holding", "group", "sa", "nv",
    "ag", "se", "technologies", "technology", "tech", "systems", "usa",
    "international", "industries", "the",
}

# Selection thresholds — tune here.
_MIN_SUBS_SELECT = 100        # below this, treat as too small to matter …
_BIG_SUB = 2000               # … unless it is clearly a large community
_MIN_POSTS_SELECT = 1         # at least one post in the last 7 days
_NOISE_SUBS = 25              # under this AND no recent posts => noise


class SubredditInfo(BaseModel):
    name: str
    subscribers: int = 0
    active_online: int = 0
    title: str = ""
    public_description: str = ""
    created_utc: float = 0.0
    over18: bool = False
    quarantined: bool = False
    # Posts seen in the last 7 days. A LOWER BOUND: we read at most ~100 recent
    # posts, so a very active sub whose latest 100 posts all fall inside the
    # window reports 100 (the floor), not its true weekly total.
    posts_7d: int = 0


class ScoredSubreddit(BaseModel):
    info: SubredditInfo
    relevance: float          # 0..1 — does name/title/description match the stock?
    score: float
    selected: bool
    reasons: list[str] = Field(default_factory=list)


class DiscoveryResult(BaseModel):
    ticker: str
    company_name: str | None = None
    candidates_checked: int = 0
    subreddits: list[ScoredSubreddit] = Field(default_factory=list)  # ranked desc
    flag: str | None = None   # human-readable note when nothing solid was found

    @property
    def found(self) -> bool:
        return any(s.selected for s in self.subreddits)

    @property
    def selected(self) -> list[ScoredSubreddit]:
        return [s for s in self.subreddits if s.selected]


# ---------------------------------------------------------------------------
# Candidate generation
# ---------------------------------------------------------------------------

def _valid_subreddit_name(name: str) -> bool:
    """Reddit subreddit names: 3–21 chars, letters/digits/underscore."""
    return bool(re.fullmatch(r"[A-Za-z0-9_]{3,21}", name))


def _company_tokens(company_name: str) -> list[str]:
    """Meaningful words in a company name, corporate suffixes removed."""
    words = re.split(r"[^A-Za-z0-9]+", company_name)
    return [w for w in words if w and w.lower() not in _COMPANY_SUFFIXES]


def generate_candidates(
    ticker: str,
    company_name: str | None = None,
    extra_seeds: list[str] | None = None,
) -> list[str]:
    """Guess likely subreddit names for a stock from common naming patterns.

    Deterministic and offline — no network. Returns a de-duplicated, order-stable
    list of syntactically valid subreddit names (case preserved for the /r/ path,
    which is case-insensitive on Reddit's side).
    """
    t = ticker.strip().upper()
    cands: list[str] = []

    def add(name: str) -> None:
        if _valid_subreddit_name(name) and name not in cands:
            cands.append(name)

    # Ticker-based patterns
    add(t)
    add(t.lower())
    for suffix in ("stock", "stocks", "_stock", "_stocks", "investors",
                   "_investors", "Investors", "trading", "_trading", "trader"):
        add(f"{t}{suffix}")

    # Company-name-based patterns (catches r/RocketLab, r/Rocket_Lab)
    if company_name:
        toks = _company_tokens(company_name)
        if toks:
            add("".join(toks))            # RocketLab
            add("_".join(toks))           # Rocket_Lab
            add("".join(toks).lower())    # rocketlab
            if len(toks) == 1:
                add(toks[0])

    for seed in extra_seeds or []:
        add(seed.strip())

    return cands[:_MAX_CANDIDATES]


# ---------------------------------------------------------------------------
# Metric fetchers — backed by Arctic Shift (free archive API, not reddit.com,
# so not subject to Reddit's Cloudflare/IP block).
# ---------------------------------------------------------------------------

def _as_sub_field(item: dict, *keys, default=None):
    for k in keys:
        if item.get(k) is not None:
            return item[k]
    return default


def fetch_about(name: str) -> SubredditInfo | None:
    """Look up a subreddit's metadata via Arctic Shift. None if not found.

    Note: Arctic Shift exposes subscriber counts + description, but not a live
    "users online" figure and not moderator-only traffic (visitors/day), so
    active_online stays 0 and ranking leans on subscribers + post volume.
    """
    from core.social_media.reddit import arctic_shift_client as arctic  # noqa: PLC0415

    items = arctic.search_subreddits(subreddit=name, limit=5)
    match = None
    for it in items:
        disp = str(_as_sub_field(it, "display_name", "name", default=""))
        if disp.lower() == name.lower():
            match = it
            break
    if match is None:
        return None
    return SubredditInfo(
        name=str(_as_sub_field(match, "display_name", "name", default=name)),
        subscribers=int(_as_sub_field(match, "subscribers", "subscriber_count", default=0) or 0),
        active_online=0,
        title=str(_as_sub_field(match, "title", default="") or ""),
        public_description=str(_as_sub_field(match, "public_description", "description", default="") or ""),
        created_utc=float(_as_sub_field(match, "created_utc", "created", default=0.0) or 0.0),
        over18=bool(_as_sub_field(match, "over18", "nsfw", default=False)),
        quarantined=bool(_as_sub_field(match, "quarantine", default=False)),
    )


def count_recent_posts(name: str, days: int = 7) -> int:
    """Count a subreddit's posts in the last *days* days via Arctic Shift
    (lower bound — capped at the 100 returned per query)."""
    from core.social_media.reddit import arctic_shift_client as arctic  # noqa: PLC0415

    return arctic.count_posts_in_window(name, days)


def search_subreddits(query: str, limit: int = 10) -> list[str]:
    """Find subreddits matching *query* via Arctic Shift's subreddit search."""
    from core.social_media.reddit import arctic_shift_client as arctic  # noqa: PLC0415

    names: list[str] = []
    for it in arctic.search_subreddits(query=query, limit=limit):
        name = _as_sub_field(it, "display_name", "name")
        if name and _valid_subreddit_name(name) and name not in names:
            names.append(name)
    return names


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def _relevance(info: SubredditInfo, ticker: str, company_name: str | None) -> float:
    hay = f"{info.name} {info.title} {info.public_description}".lower()
    score = 0.0
    if ticker.lower() in re.split(r"[^a-z0-9]+", hay):
        score += 0.6
    elif ticker.lower() in hay:
        score += 0.4
    if company_name:
        toks = [t.lower() for t in _company_tokens(company_name) if len(t) >= 3]
        if toks and any(t in hay for t in toks):
            score += 0.6
    return min(score, 1.0)


def score_subreddit(
    info: SubredditInfo, ticker: str, company_name: str | None
) -> ScoredSubreddit:
    relevance = _relevance(info, ticker, company_name)
    reasons: list[str] = []

    # Transparent, explainable score: size (log) + recent activity + relevance.
    score = round(
        math.log10(info.subscribers + 1) * 10
        + info.posts_7d * 2
        + relevance * 20,
        2,
    )

    is_noise = info.subscribers < _NOISE_SUBS and info.posts_7d == 0
    selected = (
        relevance > 0
        and not info.quarantined
        and not is_noise
        and info.subscribers >= _MIN_SUBS_SELECT
        and (info.posts_7d >= _MIN_POSTS_SELECT or info.subscribers >= _BIG_SUB)
    )

    if relevance == 0:
        reasons.append("name/description does not reference the stock")
    if info.subscribers < _MIN_SUBS_SELECT and info.subscribers < _BIG_SUB:
        reasons.append(f"only {info.subscribers} subscribers")
    if info.posts_7d == 0:
        reasons.append("no posts in last 7d")
    if info.quarantined:
        reasons.append("quarantined")
    if selected:
        reasons = ["selected"]

    return ScoredSubreddit(
        info=info, relevance=relevance, score=score, selected=selected, reasons=reasons
    )


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def discover(
    ticker: str,
    company_name: str | None = None,
    extra_seeds: list[str] | None = None,
    include_search: bool = True,
    sleep: bool = True,
) -> DiscoveryResult:
    """Find and rank subreddits for *ticker*.

    Combines the pattern generator with a Reddit subreddit search, probes each
    unique candidate's metrics, scores them, and flags the case where nothing
    solid turns up.
    """
    ticker = ticker.strip().upper()
    candidates = generate_candidates(ticker, company_name, extra_seeds)

    if include_search:
        for q in filter(None, [ticker, company_name]):
            for name in search_subreddits(q):
                if name not in candidates and _valid_subreddit_name(name):
                    candidates.append(name)
                    if sleep:
                        time.sleep(_REQUEST_DELAY)
    candidates = candidates[:_MAX_CANDIDATES]

    scored: list[ScoredSubreddit] = []
    checked = 0
    seen_names: set[str] = set()
    for name in candidates:
        checked += 1
        info = fetch_about(name)
        if sleep:
            time.sleep(_REQUEST_DELAY)
        if info is None:
            continue
        # Reddit's /r/ path is case-insensitive; dedupe on the canonical name.
        key = info.name.lower()
        if key in seen_names:
            continue
        seen_names.add(key)
        info.posts_7d = count_recent_posts(info.name)
        if sleep:
            time.sleep(_REQUEST_DELAY)
        scored.append(score_subreddit(info, ticker, company_name))

    scored.sort(key=lambda s: s.score, reverse=True)

    flag: str | None = None
    if not scored:
        flag = "no matching subreddit found"
    elif not any(s.selected for s in scored):
        flag = f"{len(scored)} subreddit(s) exist but none cleared the noise threshold"

    return DiscoveryResult(
        ticker=ticker,
        company_name=company_name,
        candidates_checked=checked,
        subreddits=scored,
        flag=flag,
    )
