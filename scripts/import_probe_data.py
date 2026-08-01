"""Import already-scraped probe JSON fixtures into raw_tweets + day_fetch_log.

Seeds the DB from data we already paid the API for, so a fresh handle does not
need to be re-fetched. Idempotent: re-running unions tweets (INSERT OR IGNORE)
and re-marks day rows.

For each research/probes/variance/<date>_<handle>/ folder:
  1. Parse meta.md for `since` and the run date (window end).
  2. Union all run JSONs per provider -> tweets.
  3. Upsert tweets into raw_tweets.
  4. Populate pending day rows for [since, end] x both providers.
  5. Bucket tweets per (date, provider) and run the SAME cross-provider
     verification the live pipeline uses, so ok/mismatch is honest.

Usage:
  python scripts/import_probe_data.py                 # import all probe folders
  python scripts/import_probe_data.py <folder> ...    # import specific folders
"""

from __future__ import annotations

import datetime
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fintwit.storage.db import init_db, close_connection  # noqa: E402
from fintwit.storage.handles import normalize_handle, upsert_handle  # noqa: E402
from fintwit.storage.tweets import upsert_tweets  # noqa: E402
from fintwit.storage.day_log import populate_pending_days  # noqa: E402
from fintwit.orchestration.day_fetcher import PROVIDERS, _verify_and_mark, _iso_now  # noqa: E402

_PROBE_ROOT = Path(__file__).parent.parent / "research" / "probes" / "variance"

# Filename prefixes -> canonical provider name used everywhere else.
_PROVIDER_FILES = {"getxapi": "getxapi", "twitterapi": "twitterapi"}


def _parse_meta(folder: Path) -> tuple[str, datetime.date, datetime.date]:
    """Return (handle, since_date, end_date) from meta.md."""
    text = (folder / "meta.md").read_text()
    handle = re.search(r"\|\s*handle\s*\|\s*@?([^\s|]+)\s*\|", text).group(1)
    since = re.search(r"\|\s*since\s*\|\s*([0-9]{4}-[0-9]{2}-[0-9]{2})", text).group(1)
    run_dt = re.search(r"run date/time.*?\|\s*([0-9]{4}-[0-9]{2}-[0-9]{2})", text).group(1)
    return (
        normalize_handle(handle),
        datetime.date.fromisoformat(since),
        datetime.date.fromisoformat(run_dt),
    )


def _load_provider_tweets(folder: Path, provider: str) -> dict[str, dict]:
    """Union all run JSONs for one provider -> {tweet_id: raw_dict}."""
    merged: dict[str, dict] = {}
    for path in sorted(folder.glob(f"{provider}_run*.json")):
        for t in json.loads(path.read_text()):
            merged[t["id"]] = t
    return merged


def _tweet_dict_to_row(t: dict, handle: str, provider: str, fetched_at: str) -> dict:
    """Map a probe JSON tweet dict to a raw_tweets row."""
    media = t.get("media_urls") or []
    return {
        "tweet_id":         t["id"],
        "account_handle":   handle,
        "display_name":     None,
        "user_id":          None,
        "text":             t.get("text"),
        "created_at_utc":   t["created_at_utc"],
        "type":             t.get("type"),
        "is_reply":         int(bool(t.get("is_reply"))),
        "is_quote":         int(bool(t.get("is_quote"))),
        "in_reply_to_id":   t.get("in_reply_to_id"),
        "quoted_tweet_id":  t.get("quoted_tweet_id"),
        "quoted_author_id": t.get("quoted_author_id"),
        "conversation_id":  t.get("conversation_id"),
        "like_count":       t.get("like_count"),
        "retweet_count":    t.get("retweet_count"),
        "reply_count":      t.get("reply_count"),
        "quote_count":      t.get("quote_count"),
        "view_count":       t.get("view_count"),
        "bookmark_count":   t.get("bookmark_count"),
        "has_media":        int(bool(media)),
        "media_urls":       ",".join(media) if media else None,
        "url":              t.get("url"),
        "is_deleted":       0,
        "fetched_at":       fetched_at,
        "source_provider":  provider,
        "raw_json":         None,
    }


def import_folder(folder: Path, db_path=None) -> dict:
    """Import one probe folder. Returns a summary dict."""
    handle, since, end = _parse_meta(folder)
    fetched_at = _iso_now()

    # 1+2+3: union tweets per provider, upsert to raw_tweets.
    per_provider: dict[str, dict[str, dict]] = {}
    inserted_total = ignored_total = 0
    for provider in PROVIDERS:
        tweets = _load_provider_tweets(folder, provider)
        per_provider[provider] = tweets
        if tweets:
            rows = [_tweet_dict_to_row(t, handle, provider, fetched_at) for t in tweets.values()]
            res = upsert_tweets(rows, db_path=db_path)
            inserted_total += res.inserted
            ignored_total += res.ignored

    # 4: ensure a day row exists for every day in the window.
    populate_pending_days(handle, since, end, PROVIDERS, db_path)

    # 5: per-day counts per provider, then cross-verify exactly like the pipeline.
    counts_by_day: dict[str, dict[str, int]] = {}
    for provider, tweets in per_provider.items():
        bucket = Counter(
            t["created_at_utc"][:10]
            for t in tweets.values()
            if since.isoformat() <= t["created_at_utc"][:10] <= end.isoformat()
        )
        for date_str, n in bucket.items():
            counts_by_day.setdefault(date_str, {})[provider] = n

    day = since
    statuses = Counter()
    while day <= end:
        date_str = day.isoformat()
        counts = {p: counts_by_day.get(date_str, {}).get(p, 0) for p in PROVIDERS}
        status = _verify_and_mark(handle, date_str, counts, {}, db_path)
        statuses[status] += 1
        day += datetime.timedelta(days=1)

    # Mark the handle ready so it joins the normal daily-delta rotation.
    upsert_handle(handle, {"status": "ready", "last_fetch_at": fetched_at,
                           "last_fetch_status": "imported"}, db_path=db_path)

    return {
        "handle": handle,
        "window": f"{since} → {end}",
        "getxapi_tweets": len(per_provider["getxapi"]),
        "twitterapi_tweets": len(per_provider["twitterapi"]),
        "inserted": inserted_total,
        "ignored": ignored_total,
        "days_ok": statuses["ok"],
        "days_mismatch": statuses["mismatch"],
        "days_failed": statuses["failed"],
    }


def main() -> None:
    init_db()

    if len(sys.argv) > 1:
        folders = [Path(a) for a in sys.argv[1:]]
    else:
        folders = sorted(p for p in _PROBE_ROOT.iterdir() if p.is_dir())

    print(f"Importing {len(folders)} probe folder(s)\n")
    rows = []
    for folder in folders:
        if not (folder / "meta.md").exists():
            print(f"  skip {folder} (no meta.md)")
            continue
        try:
            rows.append(import_folder(folder))
        except Exception as exc:
            print(f"  ERROR {folder}: {exc}")

    print(f"\n{'handle':<20} {'window':<26} {'gx':>5} {'tw':>5} {'ins':>6} "
          f"{'ok':>4} {'mis':>4} {'fail':>4}")
    print("-" * 84)
    for r in rows:
        print(f"{r['handle']:<20} {r['window']:<26} {r['getxapi_tweets']:>5} "
              f"{r['twitterapi_tweets']:>5} {r['inserted']:>6} "
              f"{r['days_ok']:>4} {r['days_mismatch']:>4} {r['days_failed']:>4}")

    close_connection()


if __name__ == "__main__":
    main()
