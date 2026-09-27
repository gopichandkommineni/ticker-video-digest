"""Copy recent digests from one reddit.db into another.

Used by the laptop digest job (scripts/reddit_brief_laptop.sh): it writes the
day's digests into a scratch copy, then merges only those digest rows into the
latest production data/reddit.db before committing — so it never pushes back a
stale copy of the posts GitHub Actions ingested meanwhile.

Usage:
    python -m casino_dashboard.jobs.reddit_digest_merge SRC.db DST.db [--days 2]
"""
import argparse
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from core.social_media.reddit.digest.store import merge_recent


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("src", type=Path)
    ap.add_argument("dst", type=Path)
    ap.add_argument("--days", type=int, default=2, help="copy digests from the last N days")
    args = ap.parse_args(argv)
    if not args.src.exists():
        print(f"{args.src} not found", file=sys.stderr)
        return 1
    since = (datetime.now(tz=timezone.utc) - timedelta(days=args.days)).date().isoformat()
    copied = merge_recent(args.src, args.dst, since)
    shown = ", ".join(copied[:10]) + (f", … (+{len(copied) - 10} more)" if len(copied) > 10 else "")
    print(f"Merged {len(copied)} digest(s){': ' + shown if copied else ''}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
