"""Read-only subreddit discovery report.

Takes one or more queries — each a ticker (RKLB) OR a company name (Rocket Lab).
For a name it resolves the ticker first, then generates candidate subreddit
names, searches Reddit, ranks the matches by community metrics, and prints a
report flagging any query where nothing solid was found.

Writes NOTHING to the database and commits NOTHING — safe to run on demand to
eyeball match quality before we persist a per-ticker subreddit map.

Usage:
    python -m casino_dashboard.jobs.subreddit_discovery_run RKLB "Rocket Lab" ASTS
    SUBREDDIT_DISCOVERY_QUERIES="RKLB,ASTS,IONQ" python -m casino_dashboard.jobs.subreddit_discovery_run

In GitHub Actions the report is also appended to $GITHUB_STEP_SUMMARY.
"""
import logging
import os
import sys

from core.social_media.reddit.subreddit_discovery import DiscoveryResult, discover
from core.social_media.reddit.ticker_resolver import company_name_for, resolve_ticker
from casino_dashboard.data.subreddit_map_loader import save_subreddit_map

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# Small default subset to start with (mix of likely-real and likely-noise).
_DEFAULT_QUERIES = ["RKLB", "ASTS", "IONQ", "OKLO", "COIN"]


def _resolve_queries(argv: list[str]) -> list[str]:
    if argv:
        return [a for a in argv if a.strip()]
    env = os.environ.get("SUBREDDIT_DISCOVERY_QUERIES", "").strip()
    if env:
        return [q.strip() for q in env.split(",") if q.strip()]
    return _DEFAULT_QUERIES


def _universe_tickers() -> set[str] | None:
    try:
        from casino_dashboard.universe import load_universe  # noqa: PLC0415

        return load_universe().all_tickers()
    except Exception as exc:  # config missing / import issue — resolve without it
        logger.warning("Could not load universe for validation: %s", exc)
        return None


def _result_lines(query: str, result: DiscoveryResult | None, ticker: str | None) -> list[str]:
    if ticker is None:
        return [f"### ⚠️ `{query}` — could not resolve to a ticker", ""]

    name = result.company_name if result else None
    header = f"### {ticker}" + (f" — {name}" if name else "")
    lines = [header, ""]
    if result is None or not result.subreddits:
        lines.append(f"🚩 **No matching subreddit found** (checked "
                     f"{result.candidates_checked if result else 0} candidates)")
        lines.append("")
        return lines

    lines.append("| Subreddit | Subs | Online | Posts/7d | Score | Verdict |")
    lines.append("|-----------|------|--------|----------|-------|---------|")
    for s in result.subreddits:
        verdict = "✅ selected" if s.selected else f"✖ {', '.join(s.reasons)}"
        lines.append(
            f"| [r/{s.info.name}](https://reddit.com/r/{s.info.name}) "
            f"| {s.info.subscribers:,} | {s.info.active_online:,} "
            f"| {s.info.posts_7d} | {s.score} | {verdict} |"
        )
    if result.flag:
        lines.append("")
        lines.append(f"🚩 {result.flag}")
    lines.append("")
    return lines


def run(queries: list[str], sleep: bool = True, save: bool = False) -> list[str]:
    universe = _universe_tickers()
    lines: list[str] = ["## Subreddit discovery", ""]
    discovered: dict[str, list[str]] = {}

    # Resolve + de-duplicate by ticker first, so passing both "RKLB" and
    # "Rocket Lab" produces one RKLB section (keeping a company name if any
    # query supplied one).
    order: list[str] = []
    company_by_ticker: dict[str, str | None] = {}
    for query in queries:
        ticker = resolve_ticker(query, universe)
        if ticker is None:
            logger.warning("Could not resolve %r to a ticker", query)
            lines += _result_lines(query, None, None)
            continue
        company = None if ticker == query.strip().upper() else query
        if ticker not in company_by_ticker:
            order.append(ticker)
            company_by_ticker[ticker] = company
        elif company and not company_by_ticker[ticker]:
            company_by_ticker[ticker] = company  # upgrade with a name

    for ticker in order:
        # Use the supplied company name, else look one up so candidate generation
        # can catch name-based subs (r/RocketLab).
        company = company_by_ticker[ticker] or company_name_for(ticker)
        logger.info("Discovering subreddits for %s (%s) …", ticker, company or "no name")
        result = discover(ticker, company_name=company, sleep=sleep)
        lines += _result_lines(ticker, result, ticker)
        # Record the selected subreddits (may be empty — a deliberate "found
        # nothing" record so the map shows the ticker was checked).
        discovered[ticker] = [s.info.name for s in result.selected]

    if save and discovered:
        from datetime import date  # noqa: PLC0415

        save_subreddit_map(discovered, updated=date.today().isoformat())
        saved_note = (
            f"_Saved {len(discovered)} ticker(s) to config/ticker_subreddits.yaml — "
            "review and commit._"
        )
        logger.info("Wrote %d tickers to config/ticker_subreddits.yaml", len(discovered))
        lines += ["", saved_note, ""]

    return lines


def main() -> None:
    argv = sys.argv[1:]
    save = "--save" in argv or os.environ.get("SUBREDDIT_DISCOVERY_SAVE", "").strip() not in ("", "0", "false", "False")
    queries = _resolve_queries([a for a in argv if a != "--save"])
    lines = run(queries, save=save)
    report = "\n".join(lines) + "\n"
    print("\n" + report)

    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a") as f:
            f.write(report)


if __name__ == "__main__":
    main()
