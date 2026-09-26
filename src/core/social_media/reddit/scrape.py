"""Reddit post scraping — read a subreddit's feed, or search Reddit by keyword.

Two entry points, both backed by the free Arctic Shift archive (the backend
production already uses — see arctic_shift_client for its ~1–2 day lag):

- `scrape_subreddits` — every post in one or more subreddits over a window, no
  text filter. The right call for a stock's own community (r/ASTSpaceMobile),
  where every post is about the stock whether or not it repeats the ticker.
- `search_reddit` — posts matching keywords ("rocket lab", "$RKLB", "Neutron"),
  within named subreddits or across the archive. Archive hits are re-checked
  locally as whole words, so "PATH" no longer matches "Paired-Path".

Both collect the whole window (paging past the archive's 100-per-request cap),
then rank locally — `top` by score, `new` by date, `comments` by comment count —
so a 500-upvote post can't lose its slot to five newer 1-upvote posts. Either
can also pull each returned post's top comments, which is where a daily
discussion thread's content actually lives.
"""
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Literal

from pydantic import BaseModel, Field

from core.social_media.base import SocialPost
from core.social_media.reddit import arctic_shift_client as arctic

logger = logging.getLogger(__name__)

SortOrder = Literal["top", "new", "comments"]

# Searched when a keyword search names no subreddits and the archive refuses a
# Reddit-wide full-text query (it has required a subreddit or author for that).
DEFAULT_SEARCH_SUBREDDITS = ["wallstreetbets", "stocks", "investing", "options", "StockMarket"]

# Full post bodies for extraction — far above the 2,000-char cap the daily pull uses.
_MAX_BODY_CHARS = 40_000

# Posts collected per subreddit/keyword before local ranking and the final cut.
DEFAULT_SCAN_LIMIT = 500


class RedditComment(BaseModel):
    comment_id: str
    author: str
    body: str
    score: int = 0
    published_at: datetime
    url: str


class ScrapedPost(BaseModel):
    post: SocialPost
    matched_keywords: list[str] = Field(default_factory=list)
    comments: list[RedditComment] = Field(default_factory=list)


class ScrapeResult(BaseModel):
    mode: Literal["subreddit", "search"]
    targets: list[str]                      # subreddit names, or keywords
    subreddits: list[str] = Field(default_factory=list)  # searched in (search mode)
    days_back: int
    sort: SortOrder
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
    posts: list[ScrapedPost] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


# --- keyword matching --------------------------------------------------------

def _keyword_pattern(keyword: str) -> re.Pattern[str]:
    """Whole-word pattern for *keyword*.

    A ticker-shaped keyword (all capitals, optionally $-prefixed, e.g. "PATH" or
    "$RKLB") matches case-sensitively, with or without the $ — so "PATH" finds
    "$PATH" and "PATH calls" but not "Paired-Path" or "career path". Anything
    else ("rocket lab") matches case-insensitively as a whole phrase.
    """
    kw = keyword.strip()
    bare = kw.lstrip("$")
    if bare.isalpha() and bare.isupper():
        return re.compile(rf"(?<![A-Za-z0-9])\$?{re.escape(bare)}(?![A-Za-z0-9])")
    phrase = r"\s+".join(re.escape(w) for w in kw.split())
    return re.compile(rf"(?<![A-Za-z0-9]){phrase}(?![A-Za-z0-9])", re.IGNORECASE)


def matched_keywords(post: SocialPost, keywords: list[str]) -> list[str]:
    """The keywords that appear in *post*'s title or body as whole words."""
    text = f"{post.title or ''}\n{post.content}"
    return [kw for kw in keywords if _keyword_pattern(kw).search(text)]


# --- shared helpers ------------------------------------------------------------

def _clean_subreddit(name: str) -> str:
    return re.sub(r"^/?r/", "", name.strip(), flags=re.IGNORECASE).strip()


def _status_note(status: int) -> str:
    """Human wording for an archive status: 0 means the request never completed."""
    return "archive unreachable (network error)" if status == 0 else f"archive returned HTTP {status}"


def _rank(posts: list[ScrapedPost], sort: SortOrder) -> list[ScrapedPost]:
    if sort == "new":
        key = lambda s: s.post.published_at  # noqa: E731
    elif sort == "comments":
        key = lambda s: (s.post.comment_count, s.post.score)  # noqa: E731
    else:
        key = lambda s: (s.post.score, s.post.comment_count)  # noqa: E731
    return sorted(posts, key=key, reverse=True)


def _to_comment(item: dict) -> RedditComment | None:
    cid = item.get("id")
    created = item.get("created_utc")
    body = item.get("body")
    if cid is None or created is None or not body or body in ("[deleted]", "[removed]"):
        return None
    try:
        published = datetime.fromtimestamp(float(created), tz=timezone.utc)
    except (TypeError, ValueError, OSError):
        return None
    permalink = item.get("permalink") or ""
    return RedditComment(
        comment_id=str(cid),
        author=str(item.get("author") or "[unknown]"),
        body=str(body)[:_MAX_BODY_CHARS],
        score=int(item.get("score") or 0),
        published_at=published,
        url=f"https://reddit.com{permalink}" if permalink else "",
    )


def fetch_top_comments(post_id: str, limit: int = 10) -> list[RedditComment]:
    """The *limit* highest-scoring comments on a post (any depth)."""
    if limit <= 0:
        return []
    comments = [c for c in map(_to_comment, arctic.search_comments(post_id)) if c]
    comments.sort(key=lambda c: c.score, reverse=True)
    return comments[:limit]


def _attach_comments(posts: list[ScrapedPost], per_post: int) -> None:
    if per_post <= 0:
        return
    for sp in posts:
        try:
            sp.comments = fetch_top_comments(sp.post.post_id, per_post)
        except Exception as exc:  # one bad thread must not sink the scrape
            logger.warning("Comments failed for %s (continuing): %s", sp.post.post_id, exc)


# --- entry points --------------------------------------------------------------

def scrape_subreddits(
    subreddits: list[str],
    days_back: int = 7,
    limit: int = 25,
    sort: SortOrder = "top",
    comments_per_post: int = 0,
    ticker: str = "",
    scan_limit: int = DEFAULT_SCAN_LIMIT,
) -> ScrapeResult:
    """Every post in *subreddits* over the last *days_back* days, ranked by
    *sort*, top *limit* returned. No text filter. *ticker* is stamped on each
    post so the result can be stored against a stock.
    """
    subs = [_clean_subreddit(s) for s in subreddits if s.strip()]
    result = ScrapeResult(
        mode="subreddit", targets=subs, subreddits=subs, days_back=days_back, sort=sort
    )
    after = datetime.now(tz=timezone.utc) - timedelta(days=days_back)
    found: dict[str, ScrapedPost] = {}
    for sub in subs:
        status, items = arctic.search_posts_paged(subreddit=sub, after=after, max_items=scan_limit)
        if status != 200:
            result.warnings.append(f"r/{sub}: {_status_note(status)}")
            continue
        if not items:
            result.warnings.append(f"r/{sub}: no posts in the last {days_back} days")
        for item in items:
            post = arctic._to_post(item, ticker, max_chars=_MAX_BODY_CHARS)
            if post is not None:
                found.setdefault(post.post_id, ScrapedPost(post=post))
        logger.info("r/%s: %d posts in window", sub, len(items))

    result.posts = _rank(list(found.values()), sort)[:limit]
    _attach_comments(result.posts, comments_per_post)
    return result


def search_reddit(
    keywords: list[str],
    subreddits: list[str] | None = None,
    days_back: int = 7,
    limit: int = 25,
    sort: SortOrder = "top",
    comments_per_post: int = 0,
    ticker: str = "",
    scan_limit: int = DEFAULT_SCAN_LIMIT,
) -> ScrapeResult:
    """Posts matching any of *keywords* over the last *days_back* days.

    With *subreddits*, searches each of them. Without, tries a Reddit-wide
    archive search first; if the archive refuses one (it has required a
    subreddit or author for full-text queries), falls back to
    DEFAULT_SEARCH_SUBREDDITS and says so in `warnings`. Every archive hit is
    re-checked as a whole-word match (see `_keyword_pattern`); hits that only
    matched as a substring are dropped.
    """
    kws = [k.strip() for k in keywords if k.strip()]
    subs = [_clean_subreddit(s) for s in (subreddits or []) if s.strip()]
    result = ScrapeResult(mode="search", targets=kws, days_back=days_back, sort=sort)
    after = datetime.now(tz=timezone.utc) - timedelta(days=days_back)

    scopes: list[str | None] = list(subs) if subs else [None]
    raw: list[dict] = []
    dropped = 0
    for kw in kws:
        # The archive's text search ignores "$", so query the bare word.
        query = kw.lstrip("$")
        kw_scopes = list(scopes)
        while kw_scopes:
            scope = kw_scopes.pop(0)
            status, items = arctic.search_posts_paged(
                subreddit=scope, query=query, after=after, max_items=scan_limit
            )
            if scope is None and status != 200:
                note = (
                    f"Reddit-wide search unavailable ({_status_note(status)}); searched "
                    f"{', '.join('r/' + s for s in DEFAULT_SEARCH_SUBREDDITS)} instead"
                )
                if note not in result.warnings:
                    result.warnings.append(note)
                scopes = list(DEFAULT_SEARCH_SUBREDDITS)
                kw_scopes = list(DEFAULT_SEARCH_SUBREDDITS)
                continue
            if status != 200:
                result.warnings.append(f"'{kw}' in r/{scope}: {_status_note(status)}")
                continue
            raw.extend(items)

    result.subreddits = [s for s in scopes if s] or ["(all of Reddit)"]

    found: dict[str, ScrapedPost] = {}
    for item in raw:
        post = arctic._to_post(item, ticker, max_chars=_MAX_BODY_CHARS)
        if post is None or post.post_id in found:
            continue
        hits = matched_keywords(post, kws)
        if not hits:
            dropped += 1
            continue
        found[post.post_id] = ScrapedPost(post=post, matched_keywords=hits)

    if dropped:
        logger.info("Dropped %d archive hits that matched only as a substring", dropped)
    result.posts = _rank(list(found.values()), sort)[:limit]
    _attach_comments(result.posts, comments_per_post)
    return result
