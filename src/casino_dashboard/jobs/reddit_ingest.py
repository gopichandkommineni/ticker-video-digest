"""Daily Reddit ingestion — posts and top comments for every stock into
data/reddit.db. Run by `reddit_ingest.yml`; safe to run by hand.

For each stock it reads the subreddits the resolver mapped to it, and searches
the general list for the ticker and company name. See
docs/specs/reddit-ingestion-v1.md.

Usage:
    python -m casino_dashboard.jobs.reddit_ingest                 # whole universe
    python -m casino_dashboard.jobs.reddit_ingest RKLB ASTS       # these stocks only
    python -m casino_dashboard.jobs.reddit_ingest --days 7 RKLB   # exactly the last 7 days
    REDDIT_DB_PATH=/tmp/reddit.db python -m casino_dashboard.jobs.reddit_ingest RKLB

Writes data/reddit.db (or REDDIT_DB_PATH). That file is production data,
committed by the workflow — don't commit a copy from a local run.

In GitHub Actions the report is also appended to $GITHUB_STEP_SUMMARY.
Exit code 1 only when the run got nothing done at all.
"""
import argparse
import logging
import os
import sys

from core.social_media.reddit import error_log
from core.social_media.reddit.ingest import IngestConfig, IngestReport, run_ingest
from core.social_media.reddit.resolver import load_general_subreddits, load_subreddit_map
from casino_dashboard.jobs.subreddit_catalog_run import load_company_names

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def _tickers(argv: list[str]) -> list[str]:
    if argv:
        return [a.strip().upper() for a in argv if a.strip()]
    env = os.environ.get("REDDIT_INGEST_TICKERS", "").strip()
    if env:
        return [t.strip().upper() for t in env.split(",") if t.strip()]
    from casino_dashboard.universe import load_universe  # noqa: PLC0415

    return sorted(load_universe().all_tickers())


def render(report: IngestReport, mapped: set[str]) -> list[str]:
    icon = {"ok": "✅", "partial": "⚠️", "failed": "❌"}.get(report.status, "•")
    lines = [
        f"## Reddit ingest — {icon} {report.status}",
        "",
        f"Window: last **{report.days_back}d** (from {report.window_start:%Y-%m-%d %H:%M} UTC) · "
        f"**{report.tickers}** stocks",
        "",
        f"- Posts: **{report.posts_new}** new, {report.posts_updated} re-seen",
        f"- Comments saved: **{report.comments_saved}**",
        f"- Pruned: {report.pruned} old or quiet posts",
        f"- reddit.db: {report.db_bytes / 1_000_000:.1f} MB",
        "",
        "| Stock | Own subreddits | Search hits |",
        "|---|---|---|",
    ]
    for ticker, c in sorted(report.per_ticker.items()):
        own = str(c.feed) if ticker in mapped else "— (none mapped)"
        lines.append(f"| {ticker} | {own} | {c.search} |")
    if report.errors:
        lines += ["", f"### Problems ({len(report.errors)})", ""]
        lines += [f"- {e}" for e in report.errors[:50]]
        if len(report.errors) > 50:
            lines.append(f"- … and {len(report.errors) - 50} more")
    reasons = error_log.summary_lines("arctic_shift")
    if reasons:
        lines += ["", *reasons, "",
                  "_A refused keyword search is retried one day at a time, then by reading "
                  "the subreddit's recent posts; only what still failed is under Problems._"]
    return lines


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="reddit_ingest", description="Reddit ingestion.")
    ap.add_argument("tickers", nargs="*", help="stocks to ingest (default: whole universe)")
    ap.add_argument("--days", type=int, default=None,
                    help="read exactly the last N days (default: since the last run)")
    args = ap.parse_args(sys.argv[1:] if argv is None else argv)
    tickers = _tickers(args.tickers)
    subreddit_map = load_subreddit_map()
    report = run_ingest(
        tickers, subreddit_map, load_general_subreddits(), load_company_names(),
        cfg=IngestConfig(window_days=args.days) if args.days else None,
    )
    text = "\n".join(render(report, set(subreddit_map)))
    print(text)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write(text + "\n")
    return 1 if report.status == "failed" else 0


if __name__ == "__main__":
    sys.exit(main())
