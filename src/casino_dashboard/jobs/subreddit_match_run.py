"""Match a company or ticker to its subreddit, by prefix search + live metrics.

Takes free-form queries — "RKLB", "rocket lab", "Rocket Lab Corporation" — and
for each one reports the subreddits that actually belong to that company, ranked
by how alive they are, with the reasoning shown for every accept and reject.

READ-ONLY by default. `--save` writes the winners to config/ticker_subreddits.yaml
(merging, so other tickers are untouched — review the diff before committing).

No LLM anywhere in the loop, so this is safe to run in GitHub Actions.

Usage:
    python -m casino_dashboard.jobs.subreddit_match_run RKLB
    python -m casino_dashboard.jobs.subreddit_match_run "rocket lab" "ast spacemobile"
    python -m casino_dashboard.jobs.subreddit_match_run RKLB ASTS --save
    python -m casino_dashboard.jobs.subreddit_match_run --universe --json out.json

Environment equivalents (for CI): SUBREDDIT_MATCH_QUERIES (comma-separated),
SUBREDDIT_MATCH_SAVE, SUBREDDIT_MATCH_JSON.

In GitHub Actions the report is also appended to $GITHUB_STEP_SUMMARY.
"""
import argparse
import json
import logging
import os
import sys
from datetime import date

from core.social_media.reddit.subreddit_match import MatchResult, match
from core.social_media.reddit.ticker_resolver import company_name_for, resolve_ticker

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def _universe_tickers() -> set[str] | None:
    try:
        from casino_dashboard.universe import load_universe  # noqa: PLC0415

        return load_universe().all_tickers()
    except Exception as exc:  # config missing / import issue — carry on without it
        logger.warning("Could not load universe: %s", exc)
        return None


def resolve(query: str, universe: set[str] | None) -> tuple[str | None, str | None]:
    """Turn a free-form query into (ticker, company_name).

    Both directions matter: "RKLB" needs a company name so the search can find
    r/RocketLab, and "rocket lab" needs a ticker so it can find r/RKLB.
    """
    ticker = resolve_ticker(query, universe)
    looked_like_ticker = ticker is not None and query.strip().upper() == ticker
    company = None if looked_like_ticker else query.strip()
    if ticker and not company:
        company = company_name_for(ticker)
    return ticker, company


def result_lines(result: MatchResult) -> list[str]:
    header = f"### {result.query}"
    if result.ticker:
        header += f" → **{result.ticker}**"
    if result.company_name:
        header += f" ({result.company_name})"
    lines = [header, ""]

    if not result.candidates:
        lines += [f"🚩 {result.flag or 'no candidates'}", ""]
        return lines

    if result.best:
        best = result.best.metrics
        lines += [f"**Best match: [r/{best.name}](https://reddit.com/r/{best.name})** — "
                  f"{best.subscribers:,} members, {best.posts_7d}"
                  f"{'+' if best.posts_capped else ''} posts/7d, "
                  f"{best.unique_commenters}{'+' if best.comments_capped else ''} "
                  f"people commenting/7d", ""]

    lines += ["| Subreddit | Members | Posts/7d | Commenters/7d | Relevance | Verdict |",
              "|-----------|---------|----------|---------------|-----------|---------|"]
    for cand in result.candidates[:10]:
        m = cand.metrics
        verdict = "✅ " + ", ".join(cand.reasons) if cand.selected else "✖ " + ", ".join(cand.reasons)
        # Only the finalists are measured — show "—" rather than 0 for the rest,
        # so "not looked at" never reads as "dead".
        posts = f"{m.posts_7d}{'+' if m.posts_capped else ''}" if m.measured else "—"
        commenters = (f"{m.unique_commenters}{'+' if m.comments_capped else ''}"
                      if m.measured else "—")
        lines.append(
            f"| [r/{m.name}](https://reddit.com/r/{m.name}) | {m.subscribers:,} "
            f"| {posts} | {commenters} | {cand.relevance:.1f} | {verdict} |"
        )
    lines.append("")
    if result.flag:
        lines += [f"🚩 {result.flag}", ""]
    return lines


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("queries", nargs="*",
                        help="Tickers and/or company names (e.g. RKLB \"rocket lab\").")
    parser.add_argument("--universe", action="store_true",
                        help="Match every ticker in config/themes.yaml.")
    parser.add_argument("--save", action="store_true",
                        default=os.environ.get("SUBREDDIT_MATCH_SAVE", "").strip()
                        not in ("", "0", "false", "False"),
                        help="Write the best matches to config/ticker_subreddits.yaml.")
    parser.add_argument("--json", default=os.environ.get("SUBREDDIT_MATCH_JSON", "").strip() or None,
                        help="Also dump the full result (all candidates) to this JSON file.")
    parser.add_argument("--no-metrics", action="store_true",
                        help="Skip post/comment lookups — name and description only (fast).")
    parser.add_argument("--finalists", type=int, default=3,
                        help="How many candidates get live metrics (default 3).")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv if argv is not None else sys.argv[1:])
    universe = _universe_tickers()

    queries = list(args.queries)
    env_queries = os.environ.get("SUBREDDIT_MATCH_QUERIES", "").strip()
    if env_queries:
        queries += [q.strip() for q in env_queries.split(",") if q.strip()]
    if args.universe:
        queries += sorted(universe or [])
    if not queries:
        print("nothing to do — pass a ticker or company name, or --universe")
        return

    lines = ["## Subreddit match", ""]
    results: list[MatchResult] = []
    winners: dict[str, list[str]] = {}
    incomplete: list[str] = []
    for query in queries:
        ticker, company = resolve(query, universe)
        logger.info("matching %r -> ticker=%s company=%s", query, ticker, company)
        result = match(query, ticker=ticker, company_name=company,
                       with_metrics=not args.no_metrics, finalists=args.finalists)
        results.append(result)
        lines += result_lines(result)
        # Only record a ticker when the search actually completed. Writing
        # "nothing found" from a throttled run is how the previous map ended up
        # claiming CCJ had no subreddit while r/CCJ existed all along.
        if ticker and result.best and result.archive_ok:
            winners[ticker] = [c.metrics.name for c in result.candidates if c.selected]
        elif ticker and not result.archive_ok:
            incomplete.append(ticker)

    if args.json:
        with open(args.json, "w") as fh:
            json.dump([r.model_dump() for r in results], fh, indent=1, default=str)
        logger.info("wrote %s", args.json)

    if args.save and winners:
        from casino_dashboard.data.subreddit_map_loader import save_subreddit_map  # noqa: PLC0415

        save_subreddit_map(winners, updated=date.today().isoformat())
        logger.info("wrote %d ticker(s) to config/ticker_subreddits.yaml", len(winners))
        lines += [f"_Saved {len(winners)} ticker(s) to config/ticker_subreddits.yaml — "
                  "review the diff before committing._", ""]
    elif args.save:
        logger.warning("--save requested but nothing matched confidently")

    if incomplete:
        note = (f"⚠️ Archive was unreachable for {len(incomplete)} ticker(s) — "
                f"NOT saved, re-run these: {', '.join(sorted(incomplete))}")
        logger.warning(note)
        lines += [note, ""]

    report = "\n".join(lines) + "\n"
    print("\n" + report)
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a") as fh:
            fh.write(report)


if __name__ == "__main__":
    main()
