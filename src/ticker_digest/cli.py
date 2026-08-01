"""argparse CLI entrypoint.

Subcommands:
- ``ticker <SYMBOL>`` : per-ticker YouTube digest (placeholder).
- ``market``          : prints the broader-market Reality Score, top
                        contributors, and the Claude-generated thesis.
"""
from __future__ import annotations

import argparse
import logging
import sys

from core.market import compute_reality_score, generate_thesis, get_snapshot
from core.models import MarketSnapshot, RealityScore

log = logging.getLogger(__name__)

_BAR_WIDTH = 30


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


def _cmd_ticker(args: argparse.Namespace) -> int:
    print(f"Ticker analysis for {args.symbol} not yet implemented.")
    return 0


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    parser = argparse.ArgumentParser(prog="ticker-digest", description="Ticker Video Digest CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p_ticker = sub.add_parser("ticker", help="Per-ticker YouTube digest (placeholder)")
    p_ticker.add_argument("symbol", help="Stock ticker symbol, e.g. RKLB")
    p_ticker.set_defaults(func=_cmd_ticker)

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
