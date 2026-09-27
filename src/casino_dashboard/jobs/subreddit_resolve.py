"""Subreddit resolver from the command line — the same two inputs as the
Subreddits page.

    company   find the subreddits for a company name (or ticker), then save the
              ones you pick
    add       add a subreddit by name, for one stock or on the general list
    remove    take a subreddit off the map
    list      show what is saved

Usage:
    python -m casino_dashboard.jobs.subreddit_resolve company "Rocket Lab"
    python -m casino_dashboard.jobs.subreddit_resolve company "Rocket Lab" --save
    python -m casino_dashboard.jobs.subreddit_resolve company "Rocket Lab" --pick RocketLab,RKLB
    python -m casino_dashboard.jobs.subreddit_resolve company "Some Co" --ticker SOME --save
    python -m casino_dashboard.jobs.subreddit_resolve add wallstreetbets
    python -m casino_dashboard.jobs.subreddit_resolve add r/RKLB --ticker RKLB
    python -m casino_dashboard.jobs.subreddit_resolve remove wallstreetbets
    python -m casino_dashboard.jobs.subreddit_resolve list --ticker RKLB

`company` only prints matches unless you pass --save (the confident ones) or
--pick (exactly those). Everything writes config/ticker_subreddits.yaml — a
small config file, safe to review and commit.
"""
import argparse
import logging
import sys

from core.social_media.reddit.resolver import (
    add_subreddit,
    clean_subreddit_name,
    load_entries,
    remove_entry,
    resolve_company,
    save_resolved,
)
from casino_dashboard.jobs.subreddit_match_run import _universe_tickers, result_lines

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def _parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="python -m casino_dashboard.jobs.subreddit_resolve",
        description="Find, add, remove and list the subreddits read for each stock.",
    )
    sub = p.add_subparsers(dest="command", required=True)

    c = sub.add_parser("company", help="find subreddits for a company name or ticker")
    c.add_argument("query", help='company name or ticker, e.g. "Rocket Lab" or RKLB')
    c.add_argument("--ticker", default="", help="save under this ticker (if it can't be worked out)")
    c.add_argument("--save", action="store_true", help="save the confident matches")
    c.add_argument("--pick", default="", help="save exactly these, comma-separated")
    c.add_argument("--no-metrics", action="store_true", help="skip activity lookups (faster)")

    a = sub.add_parser("add", help="add a subreddit by name")
    a.add_argument("name", help="e.g. wallstreetbets, r/wallstreetbets or a reddit.com URL")
    a.add_argument("--ticker", default="", help="tie it to this stock (default: general list)")

    r = sub.add_parser("remove", help="take a subreddit off the map")
    r.add_argument("name")
    r.add_argument("--ticker", default="", help="the stock it is listed under (default: general list)")

    ls = sub.add_parser("list", help="show saved subreddits")
    ls.add_argument("--ticker", default="", help="only this stock")

    args = p.parse_args(argv)
    if args.command == "company" and args.save and args.pick:
        p.error("use --save or --pick, not both")
    return args


def _company(args: argparse.Namespace) -> int:
    result = resolve_company(
        args.query, universe=_universe_tickers(), ticker=args.ticker or None,
        with_metrics=not args.no_metrics,
    )
    print("\n".join(result_lines(result)))
    if args.pick:
        names = [n.strip().removeprefix("r/") for n in args.pick.split(",") if n.strip()]
    elif args.save:
        names = [c.metrics.name for c in result.candidates if c.selected]
    else:
        print("Nothing saved — add --save (confident matches) or --pick A,B.")
        return 0
    if not names:
        print("No confident match to save. Use --pick to choose candidates by hand.")
        return 1
    if not result.archive_ok:
        print("⚠️ The archive search was incomplete; check the candidates before trusting them.")
    try:
        saved = save_resolved(result, names, ticker=args.ticker or None)
    except ValueError as exc:
        print(f"✗ {exc}")
        return 1
    target = (args.ticker or result.ticker or "").upper()
    if saved:
        print(f"✓ Saved under {target}: " + ", ".join(f"r/{e.name}" for e in saved))
    else:
        print(f"Already saved under {target} — nothing new.")
    return 0


def _list(ticker: str) -> int:
    entries = load_entries()
    if ticker:
        entries = [e for e in entries if e.ticker == ticker.upper()]
    if not entries:
        print("No subreddits saved" + (f" for {ticker.upper()}." if ticker else "."))
        return 0
    print("| Stock | Subreddit | Source | Added | Members |")
    print("|---|---|---|---|---|")
    for e in entries:
        members = f"{e.subscribers:,}" if e.subscribers is not None else "—"
        print(f"| {e.ticker or 'general'} | r/{e.name} | {e.source or 'not recorded'} "
              f"| {e.added or '—'} | {members} |")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    if args.command == "company":
        return _company(args)
    if args.command == "list":
        return _list(args.ticker)

    where = args.ticker.upper() if args.ticker else "the general list"
    try:
        if args.command == "add":
            entry = add_subreddit(args.name, ticker=args.ticker or None)
            print(f"✓ Added r/{entry.name} to {where}." if entry
                  else f"Already on {where} — nothing changed.")
        else:
            name = clean_subreddit_name(args.name)
            removed = remove_entry(name, args.ticker or None)
            print(f"✓ Removed r/{name} from {where}." if removed else f"r/{name} isn't on {where}.")
    except ValueError as exc:
        print(f"✗ {exc}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
