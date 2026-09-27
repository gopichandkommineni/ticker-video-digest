"""Find each stock's subreddits from where it is actually discussed — read-only.

Follows the people who mention a stock to the subreddits where they talk about
it, then ranks those by the share of their posts that mention it. See
core/social_media/reddit/mention_discovery.py for how, and
docs/runbooks/reddit-local-runbook.md §4c for reading the result.

Usage:
    python -m casino_dashboard.jobs.subreddit_find RKLB PATH AG ON
    python -m casino_dashboard.jobs.subreddit_find RKLB --days 30
    python -m casino_dashboard.jobs.subreddit_find RKLB --json out.json

Writes NOTHING: the report compares what it found with
config/ticker_subreddits.yaml, and you decide what to change. Needs no
credentials; reads the Arctic Shift archive, so it runs locally or in Actions.
Expect a few minutes per stock.
"""
import argparse
import json
import logging
import sys

from core.social_media.reddit.mention_discovery import (
    ArcticFetch,
    Discovery,
    DiscoveryConfig,
    discover,
)
from core.social_media.reddit.resolver import load_general_subreddits, load_subreddit_map
from core.social_media.reddit.scrape import DEFAULT_SEARCH_SUBREDDITS
from casino_dashboard.jobs.subreddit_catalog_run import load_company_names

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

_MARK = {"stock": "✅ stock", "general": "• general", "weak": "· weak", "excluded": "✗ excluded"}


def render(d: Discovery) -> list[str]:
    who = f"{d.ticker} ({d.company})" if d.company else d.ticker
    lines = [
        f"## {who}",
        "",
        f"Keywords: {', '.join(d.keywords)} · last {d.days} days · "
        f"{d.seed_mentions} mentions in {len(d.seed_subreddits)} starting subreddits · "
        f"{d.authors_followed} authors followed",
        "",
        "| Subreddit | Verdict | Mentions / posts read | Share | Authors | Last mention "
        "| Subscribers | Found via | In map |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for c in d.candidates:
        read = f"{c.mentions} / {c.posts}"
        if c.posts and c.days_covered < d.days:
            read += f" (newest {c.days_covered:g}d)"
        last = f"{c.last_mention:%Y-%m-%d}" if c.last_mention else "—"
        lines.append(
            f"| r/{c.subreddit} | {_MARK[c.verdict]} | {read} | {c.share:.1%} | {c.authors} "
            f"| {last} | {c.subscribers:,} | {', '.join(c.found_via)} "
            f"| {'✓' if c.mapped else 'new'} |")
    new = [c.subreddit for c in d.candidates if c.verdict == "stock" and not c.mapped]
    unsupported = [c for c in d.candidates if c.mapped and c.verdict != "stock"]
    lines.append("")
    if new:
        lines.append(f"**Not in the map yet:** {', '.join('r/' + s for s in new)}")
    if unsupported:
        lines.append("**In the map, but the posts don't back it:** "
                     + ", ".join(f"r/{c.subreddit} ({c.reason})" for c in unsupported))
    if d.warnings:
        lines += ["", f"_{len(d.warnings)} read(s) failed:_ " + "; ".join(d.warnings[:10])]
    return lines


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="subreddit_find", description=__doc__.splitlines()[0])
    ap.add_argument("tickers", nargs="+", help="stocks to look up, e.g. RKLB PATH")
    ap.add_argument("--days", type=int, default=DiscoveryConfig().days,
                    help="window in days (default: %(default)s)")
    ap.add_argument("--json", metavar="FILE", help="also save the full result as JSON")
    args = ap.parse_args(sys.argv[1:] if argv is None else argv)

    cfg = DiscoveryConfig(days=args.days)
    subreddit_map = load_subreddit_map()
    search = load_general_subreddits() or list(DEFAULT_SEARCH_SUBREDDITS)
    names = load_company_names()
    fetch = ArcticFetch()
    results = []
    for ticker in (t.strip().upper() for t in args.tickers if t.strip()):
        d = discover(ticker, names.get(ticker), subreddit_map.get(ticker, []), search,
                     fetch=fetch, cfg=cfg)
        results.append(d)
        print("\n".join(render(d)) + "\n", flush=True)
    print(f"_{fetch.reads} archive reads. Nothing was written._")
    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump([d.model_dump(mode="json") for d in results], fh, indent=2)
    return 0 if any(d.candidates for d in results) else 1


if __name__ == "__main__":
    sys.exit(main())
