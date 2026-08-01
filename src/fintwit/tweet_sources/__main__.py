"""CLI for tweet_sources adapters.

Usage:
  python -m fintwit.tweet_sources user-info  --provider PROVIDER --handle HANDLE
  python -m fintwit.tweet_sources tweets     --provider PROVIDER --handle HANDLE --start YYYY-MM-DD --end YYYY-MM-DD
  python -m fintwit.tweet_sources compare    --handle HANDLE --start YYYY-MM-DD --end YYYY-MM-DD
"""

from __future__ import annotations

import argparse
import datetime
import json
import logging
import os
import sys
from pathlib import Path

# Load .env from repo root so keys are available
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parents[1] / ".env")
except ImportError:
    pass


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def cmd_user_info(args: argparse.Namespace) -> None:
    from .factory import get_source
    src = get_source(args.provider)
    info = src.fetch_user_info(args.handle)
    print(json.dumps(info.__dict__, indent=2, default=str))


def cmd_tweets(args: argparse.Namespace) -> None:
    from .factory import get_source
    src = get_source(args.provider)
    start = datetime.date.fromisoformat(args.start)
    end = datetime.date.fromisoformat(args.end)
    tweets = src.fetch_tweets(args.handle, start, end)
    print(f"Fetched {len(tweets)} tweets for @{args.handle} [{start} → {end}]")
    for t in tweets:
        print(f"  {t.created_at_utc}  {t.id}  [{t.type}]  {(t.text or '')[:80]}")


def cmd_compare(args: argparse.Namespace) -> None:
    from .compare import compare_sources
    start = datetime.date.fromisoformat(args.start)
    end = datetime.date.fromisoformat(args.end)
    compare_sources(args.handle, start, end)


def main() -> None:
    parser = argparse.ArgumentParser(prog="tweet_sources")
    parser.add_argument("-v", "--verbose", action="store_true")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_info = sub.add_parser("user-info")
    p_info.add_argument("--provider", required=True, choices=["getxapi", "twitterapi"])
    p_info.add_argument("--handle", required=True)

    p_tweets = sub.add_parser("tweets")
    p_tweets.add_argument("--provider", required=True, choices=["getxapi", "twitterapi"])
    p_tweets.add_argument("--handle", required=True)
    p_tweets.add_argument("--start", required=True, help="YYYY-MM-DD (inclusive)")
    p_tweets.add_argument("--end", required=True, help="YYYY-MM-DD (inclusive)")

    p_cmp = sub.add_parser("compare")
    p_cmp.add_argument("--handle", required=True)
    p_cmp.add_argument("--start", required=True, help="YYYY-MM-DD (inclusive)")
    p_cmp.add_argument("--end", required=True, help="YYYY-MM-DD (inclusive)")

    args = parser.parse_args()
    _setup_logging(args.verbose)

    dispatch = {
        "user-info": cmd_user_info,
        "tweets": cmd_tweets,
        "compare": cmd_compare,
    }
    dispatch[args.cmd](args)


if __name__ == "__main__":
    main()
