"""Cross-provider comparison: same window, both adapters, diff report."""

from __future__ import annotations

import datetime
import logging
from typing import Any

from .base import Tweet
from .factory import get_source

logger = logging.getLogger(__name__)


def compare_sources(
    handle: str,
    start: datetime.date,
    end: datetime.date,
) -> dict[str, Any]:
    """
    Run both adapters over the same [start, end] window and return a report dict.
    Also prints a markdown summary to stdout.
    """
    gx_src = get_source("getxapi")
    tw_src = get_source("twitterapi")

    logger.info("compare: fetching getxapi …")
    gx_result = gx_src.fetch_tweets(handle, start, end)
    gx_tweets = gx_result.tweets
    logger.info("compare: fetching twitterapi …")
    tw_result = tw_src.fetch_tweets(handle, start, end)
    tw_tweets = tw_result.tweets

    gx_ids = {t.id for t in gx_tweets}
    tw_ids = {t.id for t in tw_tweets}
    both = gx_ids & tw_ids
    gx_only = gx_ids - tw_ids
    tw_only = tw_ids - gx_ids

    # Earliest UTC per provider
    def _earliest(tweets: list[Tweet]) -> str | None:
        return min((t.created_at_utc for t in tweets), default=None)

    gx_earliest = _earliest(gx_tweets)
    tw_earliest = _earliest(tw_tweets)

    # Snowflake-vs-reported-date mismatch (>2s) — both providers report createdAt
    # We already store Snowflake-decoded time in created_at_utc, but we can compare
    # against the raw createdAt string from raw_json.
    def _parse_twitter_date(s: str) -> datetime.datetime | None:
        # Format: "Fri Jun 05 09:30:46 +0000 2026"
        try:
            return datetime.datetime.strptime(s, "%a %b %d %H:%M:%S +0000 %Y")
        except Exception:
            return None

    def _check_mismatches(tweets: list[Tweet], label: str) -> list[str]:
        mismatches = []
        for t in tweets:
            raw_created = t.raw_json.get("createdAt", "")
            raw_dt = _parse_twitter_date(raw_created)
            if raw_dt is None:
                continue
            snow_dt = datetime.datetime.strptime(t.created_at_utc, "%Y-%m-%dT%H:%M:%SZ")
            delta = abs((snow_dt - raw_dt).total_seconds())
            if delta > 2:
                mismatches.append(
                    f"{label} tweet {t.id}: snowflake={t.created_at_utc} "
                    f"reported={raw_created} diff={delta:.1f}s"
                )
        return mismatches

    gx_mismatches = _check_mismatches(gx_tweets, "getxapi")
    tw_mismatches = _check_mismatches(tw_tweets, "twitterapi")
    all_mismatches = gx_mismatches + tw_mismatches

    report = {
        "handle": handle,
        "window": {"start": start.isoformat(), "end": end.isoformat()},
        "getxapi": {
            "count": len(gx_tweets),
            "earliest_utc": gx_earliest,
            "reached_floor": gx_result.reached_floor,
        },
        "twitterapi": {
            "count": len(tw_tweets),
            "earliest_utc": tw_earliest,
            "reached_floor": tw_result.reached_floor,
        },
        "intersection": len(both),
        "getxapi_only": sorted(gx_only),
        "twitterapi_only": sorted(tw_only),
        "date_mismatches": all_mismatches,
    }

    _print_markdown(report)
    return report


def _print_markdown(r: dict[str, Any]) -> None:
    print(f"\n## compare_sources: @{r['handle']}  {r['window']['start']} → {r['window']['end']}\n")
    print(f"| Provider   | Tweets | Earliest UTC |")
    print(f"|------------|-------:|--------------|")
    print(f"| getxapi    | {r['getxapi']['count']:>6} | {r['getxapi']['earliest_utc'] or 'n/a'} | {r['getxapi']['reached_floor']} |")
    print(f"| twitterapi | {r['twitterapi']['count']:>6} | {r['twitterapi']['earliest_utc'] or 'n/a'} | {r['twitterapi']['reached_floor']} |")
    print()
    print(f"- Intersection: **{r['intersection']}** tweets on both")
    print(f"- getxapi-only: **{len(r['getxapi_only'])}** IDs")
    print(f"- twitterapi-only: **{len(r['twitterapi_only'])}** IDs")
    print(f"- Date mismatches (>2s): **{len(r['date_mismatches'])}**")
    if r["getxapi_only"]:
        print(f"\n### getxapi-only IDs\n```\n" + "\n".join(r["getxapi_only"]) + "\n```")
    if r["twitterapi_only"]:
        print(f"\n### twitterapi-only IDs\n```\n" + "\n".join(r["twitterapi_only"]) + "\n```")
    if r["date_mismatches"]:
        print(f"\n### Date mismatches\n```\n" + "\n".join(r["date_mismatches"]) + "\n```")
