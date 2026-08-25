"""argparse CLI entrypoint.

Subcommands:
- ``ticker <SYMBOL>`` : YouTube digest for one ticker. Sources come either
                        from a YouTube search (default) or from a channel the
                        user names with ``--channel``.
- ``threads``         : list or print previously generated insight threads.
- ``market``          : prints the broader-market Reality Score, top
                        contributors, and the Claude-generated thesis.
"""
from __future__ import annotations

import argparse
import logging
import sys
from collections import Counter

from core.market import compute_reality_score, generate_thesis, get_snapshot
from core.models import DigestRun, InsightThread, MarketSnapshot, RealityScore

log = logging.getLogger(__name__)

_BAR_WIDTH = 30

_NOVELTY_LABEL = {
    "new": "NEW",
    "developing": "DEVELOPING",
    "known": "KNOWN",
}


def _ascii_bar(z: float) -> str:
    """Return a centered ASCII bar for a signed z-score in roughly [-3, +3]."""
    clamped = max(-3.0, min(3.0, z))
    units = int(round(abs(clamped) / 3.0 * _BAR_WIDTH))
    if z >= 0:
        return " " * _BAR_WIDTH + "|" + "█" * units
    return " " * (_BAR_WIDTH - units) + "█" * units + "|"


def _print_market_report(snapshot: MarketSnapshot, score: RealityScore) -> None:
    print(f"\nReality Score: {score.score:+.2f}  [{score.band}]")
    print(
        f"  market z = {score.market_z}  |  economy z = {score.economy_z}  |  "
        f"{len(score.used_indicators)} of {len(score.used_indicators) + len(score.skipped_indicators)} indicators used"
    )
    print("\nContributions (signed z, sorted by magnitude):")
    for sid, z in sorted(score.contributions.items(), key=lambda kv: abs(kv[1]), reverse=True):
        ind = snapshot.indicators[sid]
        print(f"  {sid:<22} {z:+.2f}  {_ascii_bar(z)}  {ind.name}")
    if score.skipped_indicators:
        print(f"\nSkipped: {', '.join(score.skipped_indicators)}")


def _cmd_market(args: argparse.Namespace) -> int:
    snapshot = get_snapshot(force=args.force)
    score = compute_reality_score(snapshot)
    _print_market_report(snapshot, score)
    if args.thesis:
        try:
            thesis = generate_thesis(snapshot, score)
        except Exception as exc:  # noqa: BLE001
            print(f"\n[thesis generation failed: {exc}]", file=sys.stderr)
            return 1
        print(f"\nRegime: {thesis.regime}")
        print(f"\n{thesis.narrative}\n")
        print("Bull case:")
        for b in thesis.bull_case:
            print(f"  - {b}")
        print("\nBear case:")
        for b in thesis.bear_case:
            print(f"  - {b}")
        print("\nWatch items:")
        for w in thesis.key_watch_items:
            print(f"  - {w}")
    print("\nNot investment advice.")
    return 0


# ---------------------------------------------------------------------------
# YouTube digest
# ---------------------------------------------------------------------------


def render_thread(thread: InsightThread) -> str:
    """Render a stored thread as plain text for the terminal."""
    lines = [
        "",
        f"{thread.headline}",
        (
            f"  {thread.ticker} ({thread.company_name}) · {thread.source_label} · "
            f"{thread.video_count} videos · {thread.new_claim_count} new claims · "
            f"sentiment: {thread.overall_sentiment}"
        ),
        f"  thread {thread.thread_id} · {thread.generated_at:%Y-%m-%d %H:%M} UTC",
        "",
    ]
    for post in thread.posts:
        tag = _NOVELTY_LABEL.get(post.novelty, post.novelty.upper())
        lines.append(f"{post.position}. [{tag}] {post.headline}")
        lines.append(f"   {post.body}")
        for citation in post.citations:
            lines.append(f"   ↳ {citation.quote_paraphrase} — {citation.url}")
        lines.append("")
    lines.append(thread.disclaimer)
    return "\n".join(lines)


def claim_summary(run: DigestRun) -> str:
    """One line on what the run's claims turned out to be."""
    counts = Counter(claim.novelty for claim in run.claims)
    line = (
        f"Claims: {counts.get('new', 0)} new · "
        f"{counts.get('developing', 0)} developing · "
        f"{counts.get('known', 0)} known"
    )
    corroborated = sum(1 for claim in run.claims if claim.newly_corroborated)
    if corroborated:
        line += f"  ({corroborated} newly corroborated)"
    multi = sum(1 for claim in run.claims if claim.source_count > 1)
    if multi:
        line += f"  ({multi} backed by more than one video)"
    return line


def _print_run_sources(run: DigestRun) -> None:
    print(f"\nSources ({len(run.videos)} selected):")
    for scored in run.videos:
        meta = scored.metadata
        status = run.skipped.get(meta.video_id, "analysed")
        print(
            f"  {scored.reliability_score:.2f}  {meta.channel_title} — {meta.title}"
        )
        print(
            f"        {meta.view_count:,} views · {meta.channel_subscriber_count:,} subs · "
            f"{meta.duration_seconds // 60}m · {meta.published_at:%Y-%m-%d} · {status}"
        )


def _cmd_ticker(args: argparse.Namespace) -> int:
    from core.models import DigestRequest
    from ticker_digest.pipeline import DigestSetupError, run_digest
    from ticker_digest.sources import SourceResolutionError, resolve_company_name
    from ticker_digest.youtube_client import YouTubeAccessError

    ticker = args.symbol.upper()
    company_name = args.company or resolve_company_name(ticker)

    request = DigestRequest(
        ticker=ticker,
        company_name=company_name,
        source_kind="channel" if args.channel else "ticker_search",
        channel_query=args.channel,
        days=args.days,
        max_videos=args.limit,
    )

    try:
        run = run_digest(request, persist=not args.no_store)
    except (SourceResolutionError, YouTubeAccessError, DigestSetupError) as exc:
        # Expected, actionable failures: say what to fix, not where it broke.
        print(f"\n{exc}\n", file=sys.stderr)
        return 1

    if args.json:
        print(run.model_dump_json(indent=2))
        return 0

    if not run.videos:
        where = f"on {args.channel}" if args.channel else "in search results"
        print(
            f"No videos about {ticker} {where} in the last {args.days} days "
            f"that pass the quality filters."
        )
        return 0

    _print_run_sources(run)
    if run.claims:
        print(f"\n{claim_summary(run)}")

    if run.thread is None:
        print("\nNo transcripts could be analysed, so there is no thread.")
        for video_id, reason in run.skipped.items():
            print(f"  {video_id}: {reason}")
        return 0

    print(render_thread(run.thread))
    return 0


def _cmd_threads(args: argparse.Namespace) -> int:
    from ticker_digest import store

    if args.show:
        thread = store.get_thread(args.show)
        if thread is None:
            print(f"No thread with id {args.show}", file=sys.stderr)
            return 1
        print(thread.model_dump_json(indent=2) if args.json else render_thread(thread))
        return 0

    threads = store.list_threads(ticker=args.ticker, limit=args.limit)
    if not threads:
        scope = f" for {args.ticker.upper()}" if args.ticker else ""
        print(f"No stored threads{scope} yet. Generate one with: ticker <SYMBOL>")
        return 0

    if args.json:
        print("[" + ",".join(t.model_dump_json() for t in threads) + "]")
        return 0

    print(f"\n{len(threads)} stored thread(s), newest first:\n")
    for thread in threads:
        print(
            f"  {thread.thread_id}  {thread.generated_at:%Y-%m-%d %H:%M}  "
            f"{thread.ticker:<6} {thread.new_claim_count} new  "
            f"{thread.headline}"
        )
    print("\nPrint one with:  threads --show <id>")
    return 0


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    parser = argparse.ArgumentParser(prog="ticker-digest", description="Ticker Video Digest CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p_ticker = sub.add_parser("ticker", help="YouTube insight thread for a ticker")
    p_ticker.add_argument("symbol", help="Stock ticker symbol, e.g. RKLB")
    p_ticker.add_argument(
        "--channel",
        help="Use this YouTube channel as the source (name, @handle, URL or id) "
        "instead of searching",
    )
    p_ticker.add_argument(
        "--company", help="Company name, if the automatic lookup gets it wrong"
    )
    p_ticker.add_argument(
        "--days", type=int, default=7, help="How far back to look (default: 7)"
    )
    p_ticker.add_argument(
        "--limit", type=int, default=5, help="Maximum videos to analyse (default: 5)"
    )
    p_ticker.add_argument(
        "--no-store", action="store_true", help="Do not save the run or its thread"
    )
    p_ticker.add_argument("--json", action="store_true", help="Print the run as JSON")
    p_ticker.set_defaults(func=_cmd_ticker)

    p_threads = sub.add_parser("threads", help="List or print stored insight threads")
    p_threads.add_argument("--ticker", help="Only threads for this ticker")
    p_threads.add_argument(
        "--limit", type=int, default=20, help="How many to list (default: 20)"
    )
    p_threads.add_argument("--show", metavar="THREAD_ID", help="Print one thread in full")
    p_threads.add_argument("--json", action="store_true", help="Print as JSON")
    p_threads.set_defaults(func=_cmd_threads)

    p_market = sub.add_parser("market", help="Broader-market Reality Score + thesis")
    p_market.add_argument(
        "--force", action="store_true", help="Bypass indicator cache and refetch"
    )
    p_market.add_argument(
        "--thesis", action="store_true", help="Also generate a Claude market thesis"
    )
    p_market.set_defaults(func=_cmd_market)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
