"""CLI for standalone storage testing.

Usage:
  python -m fintwit.storage init
  python -m fintwit.storage show-handle --handle H
  python -m fintwit.storage list-handles
  python -m fintwit.storage tweets --handle H [--limit N] [--since ISO_UTC]
"""

import argparse
import json
import sys
from pathlib import Path

from .db import init_db
from .handles import get_handle, list_handles, normalize_handle
from .reads import get_tweets_by_handle, count_tweets


def cmd_init(args: argparse.Namespace) -> None:
    db = Path(args.db) if args.db else None
    init_db(db)
    print("DB initialized.")


def cmd_show_handle(args: argparse.Namespace) -> None:
    db = Path(args.db) if args.db else None
    row = get_handle(normalize_handle(args.handle), db_path=db)
    if row is None:
        print(f"Handle '{args.handle}' not found.")
        sys.exit(1)
    print(json.dumps(row, indent=2))


def cmd_list_handles(args: argparse.Namespace) -> None:
    db = Path(args.db) if args.db else None
    rows = list_handles(db_path=db)
    if not rows:
        print("No handles in DB.")
        return
    header = f"{'handle':<24} {'status':<12} {'tweets':>7}  {'watermark':<24}  {'earliest':<24}"
    print(header)
    print("-" * len(header))
    for r in rows:
        print(
            f"{r['handle']:<24} "
            f"{(r['status'] or ''):<12} "
            f"{(r['total_tweets'] or 0):>7}  "
            f"{(r['tweets_watermark_utc'] or ''):<24}  "
            f"{(r['earliest_tweet_utc'] or ''):<24}"
        )


def cmd_tweets(args: argparse.Namespace) -> None:
    db = Path(args.db) if args.db else None
    rows = get_tweets_by_handle(
        normalize_handle(args.handle),
        limit=args.limit,
        since=args.since,
        db_path=db,
    )
    handle = normalize_handle(args.handle)
    total = count_tweets(handle, db_path=db)
    print(f"Stored total for @{handle}: {total}")
    print(f"Returning {len(rows)} row(s) (limit={args.limit}):\n")
    for r in rows:
        print(f"  [{r['created_at_utc']}] {r['tweet_id']}: {(r['text'] or '')[:80]}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="storage")
    parser.add_argument("--db", default=None, help="Path to fintwit.db (default: data/fintwit.db)")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init", help="Create tables if they don't exist")
    p_init.add_argument("--db", default=None)

    p_show = sub.add_parser("show-handle", help="Show one handle row")
    p_show.add_argument("--handle", required=True)
    p_show.add_argument("--db", default=None)

    p_list = sub.add_parser("list-handles", help="List all handles")
    p_list.add_argument("--db", default=None)

    p_tweets = sub.add_parser("tweets", help="List tweets for a handle")
    p_tweets.add_argument("--handle", required=True)
    p_tweets.add_argument("--limit", type=int, default=20)
    p_tweets.add_argument("--since", default=None, help="ISO 8601 UTC lower bound (exclusive)")
    p_tweets.add_argument("--db", default=None)

    args = parser.parse_args()

    dispatch = {
        "init": cmd_init,
        "show-handle": cmd_show_handle,
        "list-handles": cmd_list_handles,
        "tweets": cmd_tweets,
    }
    dispatch[args.cmd](args)


if __name__ == "__main__":
    main()
