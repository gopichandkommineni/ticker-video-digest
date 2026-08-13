"""Read-only live smoke test for the Reddit scraper.

Hits Reddit for real (PRAW when REDDIT_CLIENT_ID/SECRET are set, otherwise the
public JSON API — no credentials needed) and prints what it found. Writes
NOTHING to the database and commits NOTHING, so it is safe to run on demand to
confirm live Reddit access works from a given environment.

Usage:
    python -m casino_dashboard.jobs.reddit_smoke_test RKLB ASTS COIN
    REDDIT_SMOKE_TICKERS="RKLB,ASTS" python -m casino_dashboard.jobs.reddit_smoke_test

In GitHub Actions the summary table is also written to $GITHUB_STEP_SUMMARY.
"""
import logging
import os
import sys

from core.social_media.reddit.client import RedditScraper

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

_DEFAULT_TICKERS = ["RKLB", "ASTS", "COIN"]


def _resolve_tickers(argv: list[str]) -> list[str]:
    if argv:
        return [t.strip().upper() for t in argv if t.strip()]
    env = os.environ.get("REDDIT_SMOKE_TICKERS", "").strip()
    if env:
        return [t.strip().upper() for t in env.split(",") if t.strip()]
    return _DEFAULT_TICKERS


def run(tickers: list[str]) -> list[str]:
    """Fetch each ticker and return markdown report lines (also printed to stdout)."""
    scraper = RedditScraper()
    using_praw = scraper._praw_reddit is not None
    logger.info(
        "Reddit smoke test — %d tickers via %s",
        len(tickers),
        "PRAW (authenticated)" if using_praw else "public JSON API (no auth)",
    )

    lines: list[str] = [
        "## Reddit smoke test",
        "",
        f"Auth mode: **{'PRAW (authenticated)' if using_praw else 'public JSON API (no credentials)'}**",
        "",
        "| Ticker | Posts | Avg score | Top post |",
        "|--------|-------|-----------|----------|",
    ]

    for ticker in tickers:
        try:
            signals = scraper.search_ticker(ticker, days_back=7, max_posts=25)
        except Exception as exc:  # surface, don't crash the whole run
            logger.warning("Fetch failed for %s: %s", ticker, exc)
            lines.append(f"| {ticker} | — | — | ✗ error: {exc} |")
            continue

        n = signals.total_posts
        avg = f"{signals.avg_score:.0f}" if n else "—"
        if signals.top_posts:
            top = signals.top_posts[0]
            title = (top.title or top.content or "")[:60].replace("|", "\\|")
            top_cell = f"[{title}]({top.url}) · {top.score}↑ / {top.comment_count}💬"
        else:
            top_cell = "_no posts in last 7d_"
        lines.append(f"| {ticker} | {n} | {avg} | {top_cell} |")
        logger.info("%s: %d posts (avg score %s)", ticker, n, avg)

    return lines


def main() -> None:
    tickers = _resolve_tickers(sys.argv[1:])
    lines = run(tickers)
    report = "\n".join(lines) + "\n"
    print("\n" + report)

    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a") as f:
            f.write(report)


if __name__ == "__main__":
    main()
