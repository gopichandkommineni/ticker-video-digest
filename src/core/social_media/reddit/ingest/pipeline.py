"""One ingestion run: resolver map → Reddit client → data/reddit.db.

For every stock:
  1. its own subreddits (from the resolver's map), every post in the window;
  2. a keyword search — the ticker and the company's short name — across the
     general list (or the big finance subreddits when that list is empty).
Then, for notable posts, their top comments. Then trim what isn't worth
keeping.

The window runs from the last good run minus an overlap (the archive fills in
posts and scores a day or two late, so the overlap re-reads them), capped so a
long outage doesn't turn into one enormous run. The first run reads a week.
"""
import logging
import math
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import ModuleType

from pydantic import BaseModel, Field

from core.social_media.reddit import scrape
from core.social_media.reddit.ingest import db
from core.social_media.reddit.scrape import DEFAULT_SEARCH_SUBREDDITS, ScrapedPost
from core.social_media.reddit.subreddit_match import _COMMON_WORD_TICKERS

logger = logging.getLogger(__name__)


class IngestConfig(BaseModel):
    """Every tunable of a run. Defaults are sized to keep reddit.db small enough
    to commit daily (see docs/specs/reddit-ingestion-v1.md)."""

    first_run_days: int = 7
    overlap_days: int = 3
    max_window_days: int = 14
    feed_scan: int = 300            # posts read per mapped subreddit per run
    search_scan: int = 200          # posts read per keyword per general subreddit
    body_chars: int = 10_000
    comment_chars: int = 2_000
    # Comments: which posts, how many, how often.
    comment_min_score: int = 20
    comment_min_comments: int = 15
    top_comments: int = 15
    comment_fresh_days: int = 3
    comment_refetch_hours: int = 20
    comment_posts_per_run: int = 100
    # Retention.
    keep_days: int = 90
    quiet_days: int = 14
    quiet_score: int = 5
    quiet_comments: int = 3
    request_delay: float = 0.3


class TickerCount(BaseModel):
    feed: int = 0
    search: int = 0


class IngestReport(BaseModel):
    run_id: int
    status: str
    window_start: datetime
    days_back: int
    tickers: int
    posts_new: int = 0
    posts_updated: int = 0
    comments_saved: int = 0
    pruned: int = 0
    per_ticker: dict[str, TickerCount] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)
    db_bytes: int = 0


# --- keywords -------------------------------------------------------------------

_LEGAL_SUFFIXES = {
    "inc", "incorporated", "corp", "corporation", "co", "company", "ltd", "limited",
    "plc", "llc", "lp", "holdings", "holding", "nv", "sa", "se", "ag", "the",
}


def short_company_name(name: str | None) -> str | None:
    """'Applied Optoelectronics, Inc.' → 'Applied Optoelectronics'.

    Legal suffixes and punctuation go; the distinctive words stay. None when
    nothing useful is left.
    """
    if not name:
        return None
    words = re.sub(r"[^\w\s&'-]", " ", name).split()
    while words and words[-1].lower() in _LEGAL_SUFFIXES:
        words.pop()
    while words and words[0].lower() == "the":
        words.pop(0)
    short = " ".join(words).strip()
    return short if len(short) >= 3 else None


def _noisy_ticker(ticker: str) -> bool:
    """Tickers that are everyday words or too short to search on their own."""
    return len(ticker) <= 2 or ticker.lower() in _COMMON_WORD_TICKERS


def ticker_keywords(ticker: str, company: str | None) -> list[str]:
    keywords = [ticker]
    short = short_company_name(company)
    if short and short.upper() != ticker:
        keywords.append(short)
    return keywords


def _search_hit_is_real(post: ScrapedPost, ticker: str, company: str | None) -> bool:
    """For a noisy ticker (PATH, AG, ON…) the bare word proves nothing — require
    $TICKER or the company name. Other tickers pass as the search matched them."""
    if not _noisy_ticker(ticker):
        return True
    text = f"{post.post.title or ''}\n{post.post.content}"
    if re.search(rf"\${re.escape(ticker)}(?![A-Za-z0-9])", text):
        return True
    short = short_company_name(company)
    return bool(short and short in post.matched_keywords)


# --- the run --------------------------------------------------------------------

def _window(conn, now: datetime, cfg: IngestConfig) -> datetime:
    last = db.last_good_run_start(conn)
    if last is None:
        return now - timedelta(days=cfg.first_run_days)
    start = last - timedelta(days=cfg.overlap_days)
    return max(start, now - timedelta(days=cfg.max_window_days))


def _archive_errors(label: str, warnings: list[str]) -> list[str]:
    """Scrape warnings that mean the archive failed (vs. a quiet subreddit)."""
    return [f"{label}: {w}" for w in warnings
            if "unreachable" in w or "HTTP" in w or "unavailable" in w]


def _store(conn, sp: ScrapedPost, cfg: IngestConfig, now: datetime) -> bool:
    p = sp.post
    return db.upsert_post(
        conn, post_id=p.post_id, subreddit=p.subreddit or "", author=p.author,
        title=p.title or "", body=p.content[: cfg.body_chars], url=p.url,
        created_at=p.published_at, score=p.score, num_comments=p.comment_count, now=now,
    )


def run_ingest(
    tickers: list[str],
    subreddit_map: dict[str, list[str]],
    general: list[str],
    company_names: dict[str, str],
    db_path: Path | None = None,
    cfg: IngestConfig | None = None,
    now: datetime | None = None,
    client: ModuleType = scrape,
) -> IngestReport:
    """Ingest Reddit for *tickers*. *client* supplies scrape_subreddits,
    search_reddit and fetch_top_comments (the real `scrape` module by default)."""
    cfg = cfg or IngestConfig()
    now = now or datetime.now(tz=timezone.utc)
    path = db_path or db.default_db_path()
    conn = db.connect(path)
    since = _window(conn, now, cfg)
    days_back = max(1, math.ceil((now - since).total_seconds() / 86400))
    run_id = db.start_run(conn, since, len(tickers), now)
    report = IngestReport(run_id=run_id, status="running", window_start=since,
                          days_back=days_back, tickers=len(tickers))
    search_subs = list(general) or list(DEFAULT_SEARCH_SUBREDDITS)
    logger.info("Reddit ingest: %d tickers, %d days back, search in %s",
                len(tickers), days_back, ", ".join(search_subs))

    for ticker in tickers:
        ticker = ticker.upper()
        counts = report.per_ticker.setdefault(ticker, TickerCount())
        company = company_names.get(ticker)
        try:
            subs = subreddit_map.get(ticker, [])
            if subs:
                feed = client.scrape_subreddits(
                    subs, days_back=days_back, limit=cfg.feed_scan, sort="new",
                    ticker=ticker, scan_limit=cfg.feed_scan,
                )
                report.errors += _archive_errors(f"{ticker} feed", feed.warnings)
                for sp in feed.posts:
                    new = _store(conn, sp, cfg, now)
                    db.link_ticker(conn, sp.post.post_id, ticker, "subreddit", sp.post.subreddit or "")
                    report.posts_new += new
                    report.posts_updated += not new
                    counts.feed += 1

            found = client.search_reddit(
                ticker_keywords(ticker, company), subreddits=search_subs,
                days_back=days_back, limit=cfg.search_scan, sort="new",
                ticker=ticker, scan_limit=cfg.search_scan,
            )
            report.errors += _archive_errors(f"{ticker} search", found.warnings)
            for sp in found.posts:
                if not _search_hit_is_real(sp, ticker, company):
                    continue
                new = _store(conn, sp, cfg, now)
                db.link_ticker(conn, sp.post.post_id, ticker, "search",
                               ", ".join(sp.matched_keywords))
                report.posts_new += new
                report.posts_updated += not new
                counts.search += 1
            conn.commit()
        except Exception as exc:  # one stock failing must not sink the run
            conn.rollback()
            logger.warning("Reddit ingest failed for %s (continuing): %s", ticker, exc)
            report.errors.append(f"{ticker}: {exc}")
        if cfg.request_delay:
            time.sleep(cfg.request_delay)

    for post_id in db.posts_needing_comments(
        conn, now=now, min_score=cfg.comment_min_score, min_comments=cfg.comment_min_comments,
        fresh_days=cfg.comment_fresh_days, refetch_hours=cfg.comment_refetch_hours,
        limit=cfg.comment_posts_per_run,
    ):
        try:
            comments = client.fetch_top_comments(post_id, cfg.top_comments)
            report.comments_saved += db.save_comments(conn, post_id, [
                {"comment_id": c.comment_id, "parent_id": c.parent_id, "author": c.author,
                 "body": c.body[: cfg.comment_chars], "score": c.score,
                 "created_at": db.iso(c.published_at)}
                for c in comments
            ], now)
            conn.commit()
        except Exception as exc:
            conn.rollback()
            report.errors.append(f"comments {post_id}: {exc}")
        if cfg.request_delay:
            time.sleep(cfg.request_delay)

    report.pruned = db.prune(
        conn, now=now, keep_days=cfg.keep_days, quiet_days=cfg.quiet_days,
        quiet_score=cfg.quiet_score, quiet_comments=cfg.quiet_comments,
    )
    stored = report.posts_new + report.posts_updated
    if not report.errors:
        report.status = "ok"
    elif stored or report.comments_saved:
        report.status = "partial"
    else:
        report.status = "failed"
    db.finish_run(conn, run_id, report.status, datetime.now(tz=timezone.utc),
                  report.posts_new, report.posts_updated, report.comments_saved,
                  report.pruned, report.errors)
    conn.execute("VACUUM")
    conn.close()
    report.db_bytes = path.stat().st_size
    return report
