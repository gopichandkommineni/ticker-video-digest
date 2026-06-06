"""Variance probe: run GetXAPI N times + twitterapi once, report counts & ID overlap.

Usage (GitHub Actions only — needs GETXAPI_KEY and TWITTERAPI_IO_KEY in env):
  python scripts/run_variance.py <handle> [--since YYYY-MM-DD] [--runs N]

Defaults: since=<current year>-01-01, runs=3.
"""

from __future__ import annotations

import argparse
import datetime
import os
import sys

from dotenv import load_dotenv

load_dotenv(".env")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from storage.handles import normalize_handle
from tweet_sources.factory import get_source


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("handle")
    parser.add_argument("--since", default=None)
    parser.add_argument("--runs", type=int, default=3)
    args = parser.parse_args()

    handle = normalize_handle(args.handle)
    today = datetime.date.today()
    start = datetime.date.fromisoformat(args.since) if args.since else datetime.date(today.year, 1, 1)
    end = today

    print(f"\n## Variance probe: @{handle}  {start} → {end}\n")

    gx_src = get_source("getxapi")
    tw_src = get_source("twitterapi")

    # --- GetXAPI repeat runs ---
    gx_id_sets: list[set[str]] = []
    gx_counts: list[int] = []
    gx_floors: list[bool] = []
    for i in range(args.runs):
        print(f"GetXAPI run {i+1}/{args.runs} …", flush=True)
        r = gx_src.fetch_tweets(handle, start, end)
        ids = {t.id for t in r.tweets}
        gx_id_sets.append(ids)
        gx_counts.append(len(ids))
        gx_floors.append(r.reached_floor)
        print(f"  → {len(ids)} tweets  reached_floor={r.reached_floor}")

    print()

    # --- twitterapi single run ---
    print("twitterapi run …", flush=True)
    tw_r = tw_src.fetch_tweets(handle, start, end)
    tw_ids = {t.id for t in tw_r.tweets}
    print(f"  → {len(tw_ids)} tweets  reached_floor={tw_r.reached_floor}\n")

    # --- Summary table ---
    print("### GetXAPI count variance")
    print(f"  min={min(gx_counts)}  max={max(gx_counts)}  delta={max(gx_counts)-min(gx_counts)}")
    print(f"  all reached_floor: {all(gx_floors)}")

    if len(gx_id_sets) >= 2:
        run0 = gx_id_sets[0]
        for j, s in enumerate(gx_id_sets[1:], 2):
            common = len(run0 & s)
            only_run0 = len(run0 - s)
            only_runj = len(s - run0)
            print(f"  run1 ∩ run{j}: {common}  run1-only: {only_run0}  run{j}-only: {only_runj}")

    print()
    print("### GetXAPI vs twitterapi")
    gx_union = set.union(*gx_id_sets) if gx_id_sets else set()
    both = gx_union & tw_ids
    gx_only_ids = gx_union - tw_ids
    tw_only_ids = tw_ids - gx_union
    union_all = gx_union | tw_ids
    print(f"  getxapi union ({len(gx_union)}) ∩ twitterapi ({len(tw_ids)}): {len(both)} shared")
    print(f"  getxapi-only: {len(gx_only_ids)}")
    print(f"  twitterapi-only: {len(tw_only_ids)}")
    print(f"  union of both providers: {len(union_all)}")
    if len(gx_union) > 0:
        print(f"  union lift over getxapi alone: +{len(union_all)-len(gx_union)} ({100*(len(union_all)-len(gx_union))/len(gx_union):.1f}%)")
    if len(tw_ids) > 0:
        print(f"  union lift over twitterapi alone: +{len(union_all)-len(tw_ids)} ({100*(len(union_all)-len(tw_ids))/len(tw_ids):.1f}%)")

    # GitHub step summary
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY", "/dev/null")
    lines = [
        f"## Variance probe: @{handle}  {start} → {end}",
        "",
        "### GetXAPI repeat runs",
        "| run | count | reached_floor |",
        "|-----|------:|--------------|",
    ]
    for i, (c, f) in enumerate(zip(gx_counts, gx_floors), 1):
        lines.append(f"| {i} | {c} | {f} |")
    lines += [
        "",
        f"count range: {min(gx_counts)} – {max(gx_counts)}  (delta {max(gx_counts)-min(gx_counts)})",
        "",
        "### twitterapi",
        f"count: {len(tw_ids)}  reached_floor: {tw_r.reached_floor}",
        "",
        "### Cross-provider union",
        f"| metric | value |",
        f"|--------|------:|",
        f"| getxapi union | {len(gx_union)} |",
        f"| twitterapi | {len(tw_ids)} |",
        f"| shared (∩) | {len(both)} |",
        f"| getxapi-only | {len(gx_only_ids)} |",
        f"| twitterapi-only | {len(tw_only_ids)} |",
        f"| union total | {len(union_all)} |",
    ]
    with open(summary_path, "w") as f:
        f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
