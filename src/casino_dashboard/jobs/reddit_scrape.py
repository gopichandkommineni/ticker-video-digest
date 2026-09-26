"""Scrape Reddit posts on demand — a subreddit's feed, or a keyword search.

Two modes:

    subreddit   every post in the named subreddits over the window (no text filter)
    search      posts matching keywords, in named subreddits or across the archive

Examples:
    python -m casino_dashboard.jobs.reddit_scrape subreddit RKLB ASTSpaceMobile
    python -m casino_dashboard.jobs.reddit_scrape subreddit wallstreetbets --days 1 --sort comments
    python -m casino_dashboard.jobs.reddit_scrape search "rocket lab" RKLB Neutron
    python -m casino_dashboard.jobs.reddit_scrape search '$ASTS' --subreddits wallstreetbets,stocks --comments 5
    python -m casino_dashboard.jobs.reddit_scrape search IREN --json out/iren.json

Options:
    --days N          window, in days (default 7)
    --limit N         posts returned after ranking (default 25)
    --sort S          top (score, default) | new | comments
    --comments N      also pull each post's top N comments (default 0)
    --subreddits A,B  search mode: where to search (default: all of Reddit,
                      falling back to the big finance subs if the archive refuses)
    --json PATH       write the full result (full post bodies + comments) as JSON
    --save --ticker T store the posts in data/snapshots.db's reddit_posts table
                      under ticker T

Backed by the free Arctic Shift archive (~1–2 day lag), so it runs anywhere,
GitHub Actions included. READ-ONLY unless --save; with --save it writes the
production database, which CLAUDE.md says is committed only by the daily
refresh — review before committing a local run.

In GitHub Actions the report is also appended to $GITHUB_STEP_SUMMARY.
"""
import argparse
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from core.social_media.reddit.scrape import (
    ScrapeResult,
    scrape_subreddits,
    search_reddit,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

_DEFAULT_DB = Path("data/snapshots.db")
_SNIPPET_CHARS = 280


def _split_csv(values: list[str]) -> list[str]:
    """Accept both `A B C` and `A,B,C` (the workflow passes one comma list)."""
    return [v.strip() for raw in values for v in raw.split(",") if v.strip()]


def _parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="python -m casino_dashboard.jobs.reddit_scrape",
        description="Scrape Reddit posts: a subreddit's feed, or a keyword search.",
    )
    p.add_argument("mode", choices=["subreddit", "search"])
    p.add_argument("targets", nargs="+", help="subreddit names, or search keywords")
    p.add_argument("--days", type=int, default=7)
    p.add_argument("--limit", type=int, default=25)
    p.add_argument("--sort", choices=["top", "new", "comments"], default="top")
    p.add_argument("--comments", type=int, default=0)
    p.add_argument("--subreddits", default="", help="search mode: comma-separated")
    p.add_argument("--json", dest="json_path", default="")
    p.add_argument("--save", action="store_true")
    p.add_argument("--ticker", default="")
    args = p.parse_args(argv)
    if args.save and not args.ticker:
        p.error("--save needs --ticker (reddit_posts rows are keyed by ticker)")
    if args.mode == "subreddit" and args.subreddits:
        p.error("--subreddits is for search mode; in subreddit mode list them as targets")
    return args


def run(args: argparse.Namespace) -> ScrapeResult:
    targets = _split_csv(args.targets)
    ticker = args.ticker.strip().upper()
    if args.mode == "subreddit":
        return scrape_subreddits(
            targets, days_back=args.days, limit=args.limit, sort=args.sort,
            comments_per_post=args.comments, ticker=ticker,
        )
    return search_reddit(
        targets, subreddits=_split_csv([args.subreddits]) or None, days_back=args.days,
        limit=args.limit, sort=args.sort, comments_per_post=args.comments, ticker=ticker,
    )


def _age(published: datetime, now: datetime) -> str:
    hours = (now - published).total_seconds() / 3600
    return f"{hours:.0f}h" if hours < 48 else f"{hours / 24:.0f}d"


def _one_line(text: str, limit: int = _SNIPPET_CHARS) -> str:
    flat = " ".join(text.split()).replace("|", "\\|")
    return flat if len(flat) <= limit else flat[: limit - 1] + "…"


def render_report(result: ScrapeResult) -> list[str]:
    """Markdown report lines: a summary table, then each post with its body
    snippet and top comments."""
    now = result.fetched_at
    if result.mode == "subreddit":
        what = ", ".join(f"r/{t}" for t in result.targets)
        heading = f"## Reddit scrape — {what}"
    else:
        heading = f"## Reddit search — {', '.join(repr(t) for t in result.targets)}"
    lines = [
        heading,
        "",
        f"Last **{result.days_back}d** · sorted by **{result.sort}** · "
        f"**{len(result.posts)}** posts",
    ]
    if result.mode == "search":
        lines.append(f"Searched: {', '.join(result.subreddits)}")
    lines.append("")
    for w in result.warnings:
        lines.append(f"> ⚠️ {w}")
    if result.warnings:
        lines.append("")
    if not result.posts:
        lines.append("_No posts found._")
        return lines

    lines += ["| # | Score | Comments | Age | Subreddit | Title |", "|---|---|---|---|---|---|"]
    for i, sp in enumerate(result.posts, 1):
        p = sp.post
        lines.append(
            f"| {i} | {p.score} | {p.comment_count} | {_age(p.published_at, now)} | "
            f"r/{p.subreddit} | [{_one_line(p.title or '(untitled)', 100)}]({p.url}) |"
        )

    lines.append("")
    for i, sp in enumerate(result.posts, 1):
        p = sp.post
        lines.append(f"### {i}. {_one_line(p.title or '(untitled)', 150)}")
        meta = f"r/{p.subreddit} · u/{p.author} · {p.score} pts · {p.comment_count} comments"
        if sp.matched_keywords:
            meta += f" · matched: {', '.join(sp.matched_keywords)}"
        lines += [meta, ""]
        if p.content.strip():
            lines += [f"> {_one_line(p.content)}", ""]
        for c in sp.comments:
            lines.append(f"- **{c.score}** u/{c.author}: {_one_line(c.body, 200)}")
        if sp.comments:
            lines.append("")
    return lines


def _write_json(result: ScrapeResult, path: str) -> None:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(result.model_dump_json(indent=2), encoding="utf-8")
    logger.info("Wrote %s", out)


def _save(result: ScrapeResult, db_path: Path = _DEFAULT_DB) -> int:
    from casino_dashboard.db.repository import save_reddit_posts  # noqa: PLC0415

    return save_reddit_posts([sp.post for sp in result.posts], db_path)


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    result = run(args)

    report = "\n".join(render_report(result))
    print(report)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write(report + "\n")

    if args.json_path:
        _write_json(result, args.json_path)
    if args.save:
        saved = _save(result)
        logger.info(
            "Saved %d posts to reddit_posts under %s (%s)",
            saved, args.ticker.upper(), datetime.now(tz=timezone.utc).isoformat(timespec="seconds"),
        )


if __name__ == "__main__":
    main()
