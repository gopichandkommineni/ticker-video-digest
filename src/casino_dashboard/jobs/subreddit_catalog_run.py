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


def universe_entries(with_company_names: bool = True) -> list[UniverseEntry]:
    """Our tickers, each with a company name when one can be resolved.

    The name is what catches company-named subs (r/RocketLab for RKLB), so it is
    worth a yfinance lookup per ticker; a failed lookup degrades to ticker-only
    matching rather than dropping the stock.
    """
    from casino_dashboard.universe import load_universe  # noqa: PLC0415

    tickers = sorted(load_universe().all_tickers())
    if not with_company_names:
        return [UniverseEntry(ticker=t) for t in tickers]

    from core.social_media.reddit.ticker_resolver import company_name_for  # noqa: PLC0415

    entries: list[UniverseEntry] = []
    for ticker in tickers:
        try:
            name = company_name_for(ticker)
        except Exception as exc:  # yfinance flakiness must not sink the sweep
            logger.warning("Company-name lookup failed for %s: %s", ticker, exc)
            name = None
        entries.append(UniverseEntry(ticker=ticker, company_name=name))
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
        "--save", action="store_true", default=_env_flag("SUBREDDIT_CATALOG_SAVE"),
        help="Write the per-stock map to config/ticker_subreddits.yaml.",
    )
    parser.add_argument(
        "--no-company-names", action="store_true",
        default=_env_flag("SUBREDDIT_CATALOG_NO_NAMES"),
        help="Skip yfinance name lookups (ticker-symbol matching only).",
    )
    parser.add_argument("--no-sleep", action="store_true", help="Skip polite delays (tests).")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv if argv is not None else sys.argv[1:])
    entries = universe_entries(with_company_names=not args.no_company_names)

    cached = load_catalog_csv(Path(args.from_catalog)) if args.from_catalog else None
    report = build_report(
        entries,
        min_subscribers=args.min_subscribers,
        ticker_min_subscribers=args.ticker_min_subscribers,
        max_requests=args.max_requests,
        sleep=not args.no_sleep,
        infos=cached,
    )
    if cached is not None:
        report.strategy = f"re-filtered {Path(args.from_catalog).name}"

    lines = report_lines(report, expected_tickers={e.ticker for e in entries})
    stamp = date.today().isoformat()

    if args.out:
        write_artifacts(report, Path(args.out), stamp)

    if args.save:
        mapping = report.by_ticker()
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
