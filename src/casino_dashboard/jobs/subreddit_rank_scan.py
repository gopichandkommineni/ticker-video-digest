"""Reverse subreddit discovery: rank subreddits by subscriber count, filter to
our universe.

Two complementary passes, merged per ticker:

  * GLOBAL sweep — pull subreddits from Arctic Shift sorted by subscribers
    DESCENDING, from the largest down to a floor, and test each against every
    universe ticker with the same relevance scorer discovery uses. One pass
    catches big communities whose exact names we'd never guess. Only subs above
    the subscriber floor are reachable this way (below it there are millions).

  * PER-TICKER search — run the existing discover() for each ticker (prefix
    search + candidate generation + scoring). Catches small or dormant NAMED
    subs (r/SNDK_Stock at 22 members, r/CCJ at 183) that sit below the global
    floor.

Per-sub post counts are fetched ONLY for subreddits that match the universe, so
the global sweep stays cheap (metadata pages, not a post query per sub).

READ-ONLY by default — writes nothing, commits nothing. Pass --save (or
SUBREDDIT_SCAN_SAVE=1) to write selected subs to config/ticker_subreddits.yaml.

Usage:
    # full universe, both passes, floor 1000
    python -m casino_dashboard.jobs.subreddit_rank_scan
    # tune the global floor / cap and restrict to a few tickers
    SUBREDDIT_SCAN_MIN_SUBS=5000 SUBREDDIT_SCAN_TICKERS="RKLB,IONQ,COIN" \
        python -m casino_dashboard.jobs.subreddit_rank_scan --mode global
"""
import logging
import os
import sys
import time

from core.social_media.reddit import arctic_shift_client as arctic
from core.social_media.reddit.subreddit_discovery import (
    _MIN_RELEVANCE_SELECT,
    ScoredSubreddit,
    SubredditInfo,
    _relevance,
    count_recent_posts,
    discover,
    score_subreddit,
)
from core.social_media.reddit.ticker_resolver import company_name_for

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

_REQUEST_DELAY = 0.5
_DEFAULT_MIN_SUBS = 1000
_DEFAULT_MAX_COUNT = 50_000


def _info_from_dict(item: dict) -> SubredditInfo | None:
    name = arctic._first(item, "display_name", "name")
    if not name:
        return None
    return SubredditInfo(
        name=str(name),
        subscribers=int(arctic._first(item, "subscribers", "subscriber_count", default=0) or 0),
        active_online=0,
        title=str(arctic._first(item, "title", default="") or ""),
        public_description=str(
            arctic._first(item, "public_description", "description", default="") or ""
        ),
        created_utc=float(arctic._first(item, "created_utc", "created", default=0.0) or 0.0),
        over18=bool(arctic._first(item, "over18", "nsfw", default=False)),
        quarantined=bool(arctic._first(item, "quarantine", default=False)),
    )


def build_universe(tickers: list[str] | None = None) -> dict[str, str | None]:
    """Map each universe ticker to a company name (best-effort, for name-form
    matching). Restrict to *tickers* when given, else load the full universe."""
    if not tickers:
        from casino_dashboard.universe import load_universe  # noqa: PLC0415

        tickers = sorted(load_universe().all_tickers())
    universe: dict[str, str | None] = {}
    for tkr in tickers:
        try:
            universe[tkr] = company_name_for(tkr)
        except Exception as exc:  # resolver/network hiccup — match on ticker alone
            logger.warning("No company name for %s: %s", tkr, exc)
            universe[tkr] = None
    return universe


def _tickers_matching(info: SubredditInfo, universe: dict[str, str | None]) -> list[str]:
    """Universe tickers whose relevance to this subreddit clears the select floor.

    Usually 0 or 1 — the scorer already suppresses cross-ticker collisions."""
    return [
        tkr
        for tkr, company in universe.items()
        if _relevance(info, tkr, company) >= _MIN_RELEVANCE_SELECT
    ]


def global_sweep(
    universe: dict[str, str | None],
    min_subscribers: int = _DEFAULT_MIN_SUBS,
    max_count: int = _DEFAULT_MAX_COUNT,
    sleep: bool = True,
) -> dict[str, dict[str, SubredditInfo]]:
    """Scan subreddits ranked by subscribers desc; return {ticker: {name: info}}
    for every sub that matches a universe ticker. No post counts yet."""
    hits: dict[str, dict[str, SubredditInfo]] = {}
    scanned = 0
    for item in arctic.iter_subreddits_by_subscribers(
        min_subscribers=min_subscribers,
        max_count=max_count,
        sleep=_REQUEST_DELAY if sleep else 0.0,
    ):
        scanned += 1
        info = _info_from_dict(item)
        if info is None:
            continue
        for tkr in _tickers_matching(info, universe):
            hits.setdefault(tkr, {})[info.name.lower()] = info
    logger.info(
        "Global sweep: scanned %d subs (>= %d subscribers), matched %d ticker(s)",
        scanned, min_subscribers, len(hits),
    )
    return hits


def _merge_ticker(
    ticker: str,
    company: str | None,
    per_ticker: list[ScoredSubreddit],
    sweep_infos: dict[str, SubredditInfo],
    sleep: bool = True,
) -> list[ScoredSubreddit]:
    """Merge per-ticker discover() results with global-sweep matches for one
    ticker, deduped by name and ranked by subscriber count descending."""
    by_name: dict[str, ScoredSubreddit] = {s.info.name.lower(): s for s in per_ticker}
    for key, info in sweep_infos.items():
        if key in by_name:
            continue  # discover() already scored it (and has its post count)
        info.posts_7d = count_recent_posts(info.name)
        if sleep:
            time.sleep(_REQUEST_DELAY)
        by_name[key] = score_subreddit(info, ticker, company)
    merged = list(by_name.values())
    merged.sort(key=lambda s: (s.info.subscribers, s.score), reverse=True)
    return merged


def _render(ticker: str, company: str | None, rows: list[ScoredSubreddit]) -> list[str]:
    header = f"### {ticker}" + (f" — {company}" if company else "")
    lines = [header, ""]
    if not rows:
        return lines + ["🚩 no subreddits matched", ""]
    lines.append("| Subreddit | Subs | Posts/7d | Score | Verdict |")
    lines.append("|-----------|------|----------|-------|---------|")
    for s in rows:
        verdict = "✅ selected" if s.selected else f"✖ {', '.join(s.reasons)}"
        lines.append(
            f"| [r/{s.info.name}](https://reddit.com/r/{s.info.name}) "
            f"| {s.info.subscribers:,} | {s.info.posts_7d} | {s.score} | {verdict} |"
        )
    lines.append("")
    return lines


def run(
    tickers: list[str] | None = None,
    mode: str = "both",
    min_subscribers: int = _DEFAULT_MIN_SUBS,
    max_count: int = _DEFAULT_MAX_COUNT,
    sleep: bool = True,
    save: bool = False,
) -> list[str]:
    universe = build_universe(tickers)

    sweep: dict[str, dict[str, SubredditInfo]] = {}
    if mode in ("both", "global"):
        sweep = global_sweep(universe, min_subscribers, max_count, sleep=sleep)

    lines: list[str] = [
        "## Subreddit rank scan",
        "",
        f"_mode=`{mode}` · global floor=`{min_subscribers:,}` subscribers · "
        f"{len(universe)} tickers_",
        "",
    ]
    selected_map: dict[str, list[str]] = {}
    for ticker in sorted(universe):
        company = universe[ticker]
        per_ticker: list[ScoredSubreddit] = []
        if mode in ("both", "perticker"):
            per_ticker = discover(ticker, company_name=company, sleep=sleep).subreddits
        rows = _merge_ticker(ticker, company, per_ticker, sweep.get(ticker, {}), sleep=sleep)
        lines += _render(ticker, company, rows)
        selected_map[ticker] = [s.info.name for s in rows if s.selected]

    if save:
        from datetime import date  # noqa: PLC0415

        from casino_dashboard.data.subreddit_map_loader import save_subreddit_map  # noqa: PLC0415

        save_subreddit_map(selected_map, updated=date.today().isoformat())
        n = sum(1 for v in selected_map.values() if v)
        lines += ["", f"_Saved {n} ticker(s) with selections to "
                  "config/ticker_subreddits.yaml — review and commit._", ""]

    return lines


def _int_env(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    try:
        return int(raw) if raw else default
    except ValueError:
        return default


def main() -> None:
    argv = sys.argv[1:]
    save = "--save" in argv or os.environ.get("SUBREDDIT_SCAN_SAVE", "").strip() not in ("", "0", "false", "False")

    mode = "both"
    if "--mode" in argv:
        i = argv.index("--mode")
        if i + 1 < len(argv):
            mode = argv[i + 1]
    mode = os.environ.get("SUBREDDIT_SCAN_MODE", mode).strip() or "both"
    if mode not in ("both", "global", "perticker"):
        logger.error("Unknown mode %r (use both|global|perticker)", mode)
        sys.exit(1)

    tickers_env = os.environ.get("SUBREDDIT_SCAN_TICKERS", "").strip()
    tickers = [t.strip().upper() for t in tickers_env.split(",") if t.strip()] or None

    lines = run(
        tickers=tickers,
        mode=mode,
        min_subscribers=_int_env("SUBREDDIT_SCAN_MIN_SUBS", _DEFAULT_MIN_SUBS),
        max_count=_int_env("SUBREDDIT_SCAN_MAX_COUNT", _DEFAULT_MAX_COUNT),
        save=save,
    )
    report = "\n".join(lines) + "\n"
    print("\n" + report)

    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a") as f:
            f.write(report)


if __name__ == "__main__":
    main()
