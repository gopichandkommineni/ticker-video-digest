"""Catalog-first subreddit report: every subreddit by subscriber count, then the
stock ones, then the ones belonging to a single stock.

Where `subreddit_discovery_run` asks "which subreddits exist for RKLB?" and can
only find names it thought to guess, this asks "which subreddits exist at all?"
and filters down — so a community nobody guessed (r/ASTSpaceMobile) still turns
up. Backed by Arctic Shift; Reddit's own API is closed to us.

READ-ONLY by default: writes nothing to the database and commits nothing.
`--save` writes the per-stock map to config/ticker_subreddits.yaml (review the
diff before committing); `--out DIR` dumps the full CSV/JSON for offline work.

Usage:
    python -m casino_dashboard.jobs.subreddit_catalog_run
    python -m casino_dashboard.jobs.subreddit_catalog_run --min-subscribers 500 --max-requests 900
    python -m casino_dashboard.jobs.subreddit_catalog_run --out research/probes/subreddit_catalog
    python -m casino_dashboard.jobs.subreddit_catalog_run --save

Environment equivalents (for CI): SUBREDDIT_CATALOG_MIN_SUBSCRIBERS,
SUBREDDIT_CATALOG_MAX_REQUESTS, SUBREDDIT_CATALOG_TICKER_MIN_SUBSCRIBERS,
SUBREDDIT_CATALOG_OUT, SUBREDDIT_CATALOG_SAVE, SUBREDDIT_CATALOG_NO_NAMES.

In GitHub Actions the report is also appended to $GITHUB_STEP_SUMMARY.
"""
import argparse
import csv
import json
import logging
import os
import sys
from datetime import date
from pathlib import Path

import yaml

from core.social_media.reddit.subreddit_catalog import (
    CatalogReport,
    SubredditInfo,
    UniverseEntry,
    build_report,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# How many rows of the raw (unfiltered) catalog the Markdown report shows. The
# full sweep is tens of thousands of subs — the CSV/JSON dump carries all of it.
_TOP_N_ALL = 100
_TOP_N_MARKET = 250


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    try:
        return int(raw) if raw else default
    except ValueError:
        logger.warning("%s=%r is not an integer — using %d", name, raw, default)
        return default


def _env_flag(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() not in ("", "0", "false", "no")


_NAMES_CACHE = Path("config/ticker_company_names.yaml")

_NAMES_HEADER = (
    "# Ticker -> company name, resolved from yfinance and cached here because\n"
    "# that lookup is the slowest part of a catalog run (one network round-trip\n"
    "# per ticker, minutes for the universe) and the answer almost never changes.\n"
    "# Delete a line to re-resolve it, or run with --refresh-names.\n"
)


def load_company_names(path: Path = _NAMES_CACHE) -> dict[str, str]:
    """Read the cached ticker -> company-name map ({} when absent/unreadable)."""
    if not path.exists():
        return {}
    try:
        with path.open() as fh:
            raw = yaml.safe_load(fh) or {}
    except Exception as exc:  # a hand-edit typo must not break the run
        logger.warning("Could not read %s: %s", path, exc)
        return {}
    names = raw.get("names") if isinstance(raw, dict) else None
    if not isinstance(names, dict):
        return {}
    return {str(k).upper(): str(v) for k, v in names.items() if v}


def save_company_names(names: dict[str, str], path: Path = _NAMES_CACHE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as fh:
        fh.write(_NAMES_HEADER)
        yaml.safe_dump({"names": dict(sorted(names.items()))}, fh, sort_keys=False)


def universe_entries(
    with_company_names: bool = True, refresh_names: bool = False
) -> list[UniverseEntry]:
    """Our tickers, each with a company name when one can be resolved.

    The name is what catches company-named subs (r/RocketLab for RKLB), so it is
    worth resolving — but yfinance charges a network round-trip per ticker and
    dominates the wall-clock of an otherwise fast job. Resolved names are cached
    in config/ticker_company_names.yaml, so only tickers new since the last run
    cost anything. A failed lookup degrades to ticker-only matching rather than
    dropping the stock.
    """
    from casino_dashboard.universe import load_universe  # noqa: PLC0415

    tickers = sorted(load_universe().all_tickers())
    if not with_company_names:
        return [UniverseEntry(ticker=t) for t in tickers]

    cached = {} if refresh_names else load_company_names(_NAMES_CACHE)
    missing = [t for t in tickers if t not in cached]
    if missing:
        from core.social_media.reddit.ticker_resolver import company_name_for  # noqa: PLC0415

        logger.info(
            "Resolving company names for %d ticker(s) (%d already cached) …",
            len(missing), len(tickers) - len(missing),
        )
        for ticker in missing:
            try:
                name = company_name_for(ticker)
            except Exception as exc:  # yfinance flakiness must not sink the sweep
                logger.warning("Company-name lookup failed for %s: %s", ticker, exc)
                name = None
            if name:
                cached[ticker] = name
        save_company_names(cached, _NAMES_CACHE)
        logger.info("Cached %d company names in %s", len(cached), _NAMES_CACHE)

    entries = [UniverseEntry(ticker=t, company_name=cached.get(t)) for t in tickers]
    resolved = sum(1 for e in entries if e.company_name)
    logger.info("Universe: %d tickers, %d with company names", len(entries), resolved)
    return entries


def _row_link(name: str) -> str:
    return f"[r/{name}](https://reddit.com/r/{name})"


def _truncate(text: str, limit: int = 70) -> str:
    clean = " ".join((text or "").split())
    return clean[: limit - 1] + "…" if len(clean) > limit else (clean or "—")


def report_lines(
    report: CatalogReport, expected_tickers: set[str] | None = None
) -> list[str]:
    """Render the three stages as Markdown, each table subscriber-sorted.

    *expected_tickers* drives the "no subreddit found for …" flag — the stocks a
    sweep turned up nothing for are the actionable part of the result.
    """
    market = report.market_rows
    per_stock = report.ticker_rows
    coverage = (
        f"Swept **{report.scanned:,}** subreddits with **{report.min_subscribers:,}+** "
        f"subscribers via `{report.strategy}` ({report.requests_made} requests)."
    )

    lines = [
        "## Subreddit catalog (Arctic Shift)",
        "",
        coverage,
        "",
        f"- Stage 1 — all subreddits: **{report.scanned:,}**",
        f"- Stage 2 — stock / stock-market: **{len(market):,}**",
        f"- Stage 3 — belonging to one stock in our universe: **{len(per_stock):,}**",
        "",
    ]
    if report.truncated:
        lines += [
            (
                "> ⚠️ **Incomplete sweep** — the request budget ran out before the "
                "archive did. Counts are a lower bound; raise `--max-requests` for "
                "full coverage."
            ),
            "",
        ]
    if report.strategy == "prefix":
        lines += [
            (
                "> ⚠️ **Fallback strategy** — creation-time paging was rejected, so "
                "this ran a prefix sweep, which sees roughly one page per prefix. "
                "Treat the catalog as a sample, not a census."
            ),
            "",
        ]

    # Stage 3 first — it is the one that feeds config/ticker_subreddits.yaml.
    lines += [
        f"### Stage 3 — per-stock subreddits ({len(per_stock)})",
        "",
        "| Subreddit | Subscribers | Ticker | Relevance | Title |",
        "|-----------|-------------|--------|-----------|-------|",
    ]
    for row in per_stock:
        assert row.ticker is not None
        lines.append(
            f"| {_row_link(row.info.name)} | {row.info.subscribers:,} "
            f"| **{row.ticker.ticker}** | {row.ticker.relevance:.2f} "
            f"| {_truncate(row.info.title or row.info.public_description)} |"
        )
    if not per_stock:
        lines.append("| _none_ | — | — | — | — |")
    lines.append("")

    covered = report.by_ticker()
    missing = sorted((expected_tickers or set()) - covered.keys())
    if missing:
        lines += [
            f"🚩 **No subreddit found for {len(missing)} ticker(s):** "
            + ", ".join(missing),
            "",
        ]

    shown = market[:_TOP_N_MARKET]
    lines += [
        f"### Stage 2 — stock / stock-market subreddits (top {len(shown)} of {len(market)})",
        "",
        "| Subreddit | Subscribers | Matched by | Signals | Title |",
        "|-----------|-------------|------------|---------|-------|",
    ]
    for row in shown:
        lines.append(
            f"| {_row_link(row.info.name)} | {row.info.subscribers:,} "
            f"| {row.market.rule} | {_truncate(', '.join(row.market.signals), 40)} "
            f"| {_truncate(row.info.title or row.info.public_description, 50)} |"
        )
    if not market:
        lines.append("| _none_ | — | — | — | — |")
    lines.append("")

    top_all = report.rows[:_TOP_N_ALL]
    lines += [
        f"### Stage 1 — all subreddits by subscribers (top {len(top_all)} of {report.scanned:,})",
        "",
        "| # | Subreddit | Subscribers | Stock? | Title |",
        "|---|-----------|-------------|--------|-------|",
    ]
    for i, row in enumerate(top_all, 1):
        mark = "✅" if row.market.is_market else "—"
        lines.append(
            f"| {i} | {_row_link(row.info.name)} | {row.info.subscribers:,} | {mark} "
            f"| {_truncate(row.info.title or row.info.public_description, 50)} |"
        )
    lines += [
        "",
        (
            "_Subscriber counts come from the Arctic Shift archive and lag live "
            "Reddit by ~1–2 days. Live 'users online' and moderator-only traffic "
            "stats are not available from any public source._"
        ),
        "",
    ]
    return lines


def write_artifacts(report: CatalogReport, out_dir: Path, stamp: str) -> list[Path]:
    """Dump the full catalog (all stages) as CSV + the per-stock map as JSON."""
    target = out_dir / stamp
    target.mkdir(parents=True, exist_ok=True)

    csv_path = target / "catalog.csv"
    with csv_path.open("w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(
            ["subreddit", "subscribers", "is_market", "market_rule", "market_signals",
             "ticker", "relevance", "title", "description", "over18", "quarantined"]
        )
        for row in report.rows:
            writer.writerow([
                row.info.name, row.info.subscribers, int(row.market.is_market),
                row.market.rule, "|".join(row.market.signals),
                row.ticker.ticker if row.ticker else "",
                f"{row.ticker.relevance:.2f}" if row.ticker else "",
                " ".join((row.info.title or "").split()),
                " ".join((row.info.public_description or "").split()),
                int(row.info.over18), int(row.info.quarantined),
            ])

    json_path = target / "per_stock.json"
    payload = {
        "generated": stamp,
        "strategy": report.strategy,
        "min_subscribers": report.min_subscribers,
        "requests_made": report.requests_made,
        "scanned": report.scanned,
        "truncated": report.truncated,
        "tickers": report.by_ticker(),
    }
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    logger.info("Wrote %s and %s", csv_path, json_path)
    return [csv_path, json_path]


def fetch_only(
    out_dir: Path,
    stamp: str,
    min_subscribers: int,
    max_requests: int,
    sleep: bool = True,
) -> tuple[Path, int, int]:
    """PHASE 1 — dump every subreddit and its subscriber count, nothing else.

    Deliberately does no filtering and resolves no company names: fetching is the
    slow, rate-limited, failure-prone half, and filtering is the half worth
    re-running. Keeping them apart means one fetch feeds any number of filter
    passes (`--from-catalog`), and a change of heart about thresholds costs
    nothing.

    Rows stream to disk as they arrive rather than being held in memory to the
    end, so a walk that times out, gets rate-limited, or is cancelled still
    leaves behind everything it had already seen.

    Returns (csv_path, rows_written, smallest_subscriber_count_reached).
    """
    from core.social_media.reddit import arctic_shift_client as arctic  # noqa: PLC0415
    from core.social_media.reddit.subreddit_catalog import (  # noqa: PLC0415
        _RANKED_MAX_COUNT,
        _RANKED_PAGE_SIZE,
        _REQUEST_DELAY,
        info_from_item,
    )

    target = out_dir / stamp
    target.mkdir(parents=True, exist_ok=True)
    csv_path = target / "catalog.csv"

    max_count = min(_RANKED_MAX_COUNT, max(max_requests, 1) * _RANKED_PAGE_SIZE)
    rows = 0
    floor_reached = 0

    with csv_path.open("w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(
            ["subreddit", "subscribers", "title", "description", "over18", "quarantined"]
        )
        for item in arctic.iter_subreddits_by_subscribers(
            min_subscribers=min_subscribers,
            max_count=max_count,
            page_size=_RANKED_PAGE_SIZE,
            sleep=_REQUEST_DELAY if sleep else 0,
        ):
            info = info_from_item(item)
            if info is None or info.subscribers < min_subscribers:
                continue
            writer.writerow([
                info.name, info.subscribers,
                " ".join((info.title or "").split()),
                " ".join((info.public_description or "").split()),
                int(info.over18), int(info.quarantined),
            ])
            rows += 1
            floor_reached = info.subscribers
            if rows % 5_000 == 0:
                fh.flush()
                logger.info("… %d subreddits written (down to %d subscribers)",
                            rows, floor_reached)

    logger.info(
        "Fetched %d subreddits to %s (largest first, down to %d subscribers)",
        rows, csv_path, floor_reached,
    )
    return csv_path, rows, floor_reached


def fill_gaps_with_discovery(
    report: CatalogReport, entries: list[UniverseEntry], sleep: bool = True
) -> dict[str, list[str]]:
    """Run bottom-up `discover()` for the stocks the sweep found nothing for.

    The two approaches fail in opposite directions, which is why it is worth
    running both. A ranked sweep cannot see below its subscriber floor, and real
    ticker communities live down there — r/SNDK_Stock had 22 members, r/CCJ 183.
    Guessing names finds those, because a named sub is findable by name however
    small it is. So the sweep goes first and this cleans up after it, one
    discover() per still-missing ticker rather than for the whole universe.
    """
    from core.social_media.reddit.subreddit_discovery import discover  # noqa: PLC0415

    gaps = [e for e in entries if e.ticker not in report.by_ticker()]
    if not gaps:
        return {}

    logger.info("Filling %d gap(s) with per-ticker discovery …", len(gaps))
    filled: dict[str, list[str]] = {}
    for entry in gaps:
        try:
            result = discover(entry.ticker, company_name=entry.company_name, sleep=sleep)
        except Exception as exc:  # one bad ticker must not sink the rest
            logger.warning("Discovery failed for %s: %s", entry.ticker, exc)
            continue
        names = [s.info.name for s in result.selected]
        if names:
            filled[entry.ticker] = names
    logger.info("Per-ticker pass found subreddits for %d more ticker(s)", len(filled))
    return filled


def load_catalog_csv(path: Path) -> list[SubredditInfo]:
    """Read a catalog.csv written by `write_artifacts` back into SubredditInfo.

    The sweep is the expensive half and the filters are the half worth iterating
    on, so a saved catalog can be re-filtered — new keywords, a different
    attribution floor, `--save` — without touching the network again.
    """
    infos: list[SubredditInfo] = []
    with path.open(newline="") as fh:
        for row in csv.DictReader(fh):
            name = (row.get("subreddit") or "").strip()
            if not name:
                continue
            try:
                subscribers = int(row.get("subscribers") or 0)
            except ValueError:
                subscribers = 0
            infos.append(SubredditInfo(
                name=name,
                subscribers=subscribers,
                title=row.get("title") or "",
                public_description=row.get("description") or "",
                over18=row.get("over18") == "1",
                quarantined=row.get("quarantined") == "1",
            ))
    logger.info("Loaded %d subreddits from %s", len(infos), path)
    return infos


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument(
        "--min-subscribers", type=int,
        default=_env_int("SUBREDDIT_CATALOG_MIN_SUBSCRIBERS", 1000),
        help="Subscriber floor for the sweep (lower = far more requests).",
    )
    parser.add_argument(
        "--ticker-min-subscribers", type=int,
        default=_env_int("SUBREDDIT_CATALOG_TICKER_MIN_SUBSCRIBERS", 50),
        help="Subscriber floor for attributing a sub to a stock.",
    )
    parser.add_argument(
        "--max-requests", type=int,
        default=_env_int("SUBREDDIT_CATALOG_MAX_REQUESTS", 600),
        help="Hard cap on archive requests (bounds runtime).",
    )
    parser.add_argument(
        "--out", default=os.environ.get("SUBREDDIT_CATALOG_OUT", "").strip() or None,
        help="Directory to write catalog.csv + per_stock.json into.",
    )
    parser.add_argument(
        "--from-catalog",
        default=os.environ.get("SUBREDDIT_CATALOG_FROM", "").strip() or None,
        help="Re-filter a saved catalog.csv offline instead of sweeping again.",
    )
    parser.add_argument(
        "--newest-first", action="store_true",
        default=_env_flag("SUBREDDIT_CATALOG_NEWEST_FIRST"),
        help="Sweep from today backwards. Use when the budget cannot cover the "
             "whole archive: ticker subs are recent, so a partial oldest-first "
             "sweep misses them entirely.",
    )
    parser.add_argument(
        "--save", action="store_true", default=_env_flag("SUBREDDIT_CATALOG_SAVE"),
        help="Write the per-stock map to config/ticker_subreddits.yaml.",
    )
    parser.add_argument(
        "--no-company-names", action="store_true",
        default=_env_flag("SUBREDDIT_CATALOG_NO_NAMES"),
        help="Skip yfinance name lookups (ticker-symbol matching only).",
    )
    parser.add_argument(
        "--fetch-only", action="store_true", default=_env_flag("SUBREDDIT_CATALOG_FETCH_ONLY"),
        help="Phase 1 only: dump every subreddit + subscriber count to --out and "
             "stop. No filtering, no company-name lookups.",
    )
    parser.add_argument(
        "--refresh-names", action="store_true",
        default=_env_flag("SUBREDDIT_CATALOG_REFRESH_NAMES"),
        help="Re-resolve company names instead of using the cached ones.",
    )
    parser.add_argument(
        "--with-per-ticker", action="store_true",
        default=_env_flag("SUBREDDIT_CATALOG_PER_TICKER"),
        help="After the sweep, run bottom-up discovery for tickers it found "
             "nothing for — catches named subs below the subscriber floor.",
    )
    parser.add_argument("--no-sleep", action="store_true", help="Skip polite delays (tests).")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv if argv is not None else sys.argv[1:])
    stamp = date.today().isoformat()

    if args.fetch_only:
        out = Path(args.out or "research/probes/subreddit_catalog")
        csv_path, rows, floor = fetch_only(
            out, stamp, args.min_subscribers, args.max_requests, sleep=not args.no_sleep
        )
        summary = (
            f"## Subreddit catalog — phase 1 (fetch)\n\n"
            f"Fetched **{rows:,}** subreddits, largest first, down to "
            f"**{floor:,}** subscribers → `{csv_path}`\n\n"
            f"Filter it with:\n\n"
            f"```bash\npython -m casino_dashboard.jobs.subreddit_catalog_run "
            f"--from-catalog {csv_path}\n```\n"
        )
        print("\n" + summary)
        summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
        if summary_path:
            with open(summary_path, "a") as f:
                f.write(summary)
        return

    entries = universe_entries(
        with_company_names=not args.no_company_names, refresh_names=args.refresh_names
    )

    cached = load_catalog_csv(Path(args.from_catalog)) if args.from_catalog else None
    report = build_report(
        entries,
        min_subscribers=args.min_subscribers,
        ticker_min_subscribers=args.ticker_min_subscribers,
        max_requests=args.max_requests,
        sleep=not args.no_sleep,
        infos=cached,
        newest_first=args.newest_first,
    )
    if cached is not None:
        report.strategy = f"re-filtered {Path(args.from_catalog).name}"

    lines = report_lines(report, expected_tickers={e.ticker for e in entries})

    filled: dict[str, list[str]] = {}
    if args.with_per_ticker:
        filled = fill_gaps_with_discovery(report, entries, sleep=not args.no_sleep)
        if filled:
            lines += [
                f"### Per-ticker pass — {len(filled)} stock(s) the sweep missed",
                "",
                "| Ticker | Subreddits |",
                "|--------|------------|",
                *(f"| **{t}** | {', '.join('r/' + n for n in names)} |"
                  for t, names in sorted(filled.items())),
                "",
            ]

    if args.out:
        write_artifacts(report, Path(args.out), stamp)

    if args.save:
        mapping = {**report.by_ticker(), **filled}
        if mapping:
            from casino_dashboard.data.subreddit_map_loader import save_subreddit_map  # noqa: PLC0415

            save_subreddit_map(mapping, updated=stamp)
            logger.info("Wrote %d tickers to config/ticker_subreddits.yaml", len(mapping))
            lines += [
                (
                    f"_Saved {len(mapping)} ticker(s) to "
                    "config/ticker_subreddits.yaml — review and commit._"
                ),
                "",
            ]
        else:
            logger.warning("--save requested but no per-stock subreddits were found")

    report_text = "\n".join(lines) + "\n"
    print("\n" + report_text)

    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a") as f:
            f.write(report_text)


if __name__ == "__main__":
    main()
