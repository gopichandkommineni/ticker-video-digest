"""Variance probe — run both providers N times each, emit report + fixtures + meta.

Usage (GitHub Actions only — needs GETXAPI_KEY and TWITTERAPI_IO_KEY in env):
  python scripts/run_variance.py <handle> [--since YYYY-MM-DD] [--runs N]

Defaults: since=<current year>-01-01, runs=3.

Outputs land in:  research/probes/variance/YYYY-MM-DD_<handle>/
  report.md              human-readable verdict + sample tweets
  getxapi_run<N>.json    full normalized Tweet objects for each GetXAPI run
  twitterapi_run<N>.json full normalized Tweet objects for each twitterapi run
  meta.md                run parameters + verdict (Conclusion: blank for manual fill)
"""

from __future__ import annotations

import argparse
import dataclasses
import datetime
import json
import logging
import os
import re
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(".env")

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

from fintwit.storage.handles import normalize_handle
from fintwit.storage.db import init_db, close_connection
from fintwit.tweet_sources.base import Tweet
from fintwit.tweet_sources.factory import get_source
from import_probe_data import import_folder

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("variance_probe")


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclasses.dataclass
class RunRecord:
    run_index: int          # 1-based
    provider: str
    count: int
    tweet_ids: set[str]
    tweets: list[Tweet]
    reached_floor: bool
    earliest_utc: str | None
    rate_429_count: int     # how many 429s were seen (recovered or not)
    aborted: bool           # True if retries exhausted mid-run


# ---------------------------------------------------------------------------
# Output folder helpers
# ---------------------------------------------------------------------------

def _dated_folder(handle: str, base_date: str) -> Path:
    """Return research/probes/variance/YYYY-MM-DD_<handle>/, adding _2/_3/… if it exists."""
    base = Path("research") / "probes" / "variance" / f"{base_date}_{handle}"
    if not base.exists():
        return base
    n = 2
    while True:
        candidate = base.parent / f"{base.name}_{n}"
        if not candidate.exists():
            return candidate
        n += 1


def _git_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], text=True
        ).strip()
    except Exception:
        return "unknown"


# ---------------------------------------------------------------------------
# Fetch helpers
# ---------------------------------------------------------------------------

def _run_provider(
    provider: str,
    handle: str,
    start: datetime.date,
    end: datetime.date,
    run_index: int,
) -> RunRecord:
    """Run one fetch against *provider* and return a RunRecord."""
    src = get_source(provider)
    logger.info("[%s] run %d — fetching %s → %s ...", provider, run_index, start, end)

    # Monkey-patch the HTTP layer to count 429s without changing prod code.
    import fintwit.tweet_sources._http as _http_mod
    _429_seen = [0]
    _aborted = [False]
    _orig_get_json = _http_mod.get_json

    def _counting_get_json(url, headers, **kwargs):
        try:
            return _orig_get_json(url, headers, **kwargs)
        except _http_mod.RateLimitExhausted:
            _429_seen[0] += 1
            _aborted[0] = True
            raise
        except Exception:
            raise

    # Also patch the per-retry warning so we can count recoveries.
    _orig_sleep = None
    import time as _time_mod
    _sleep_calls = [0]
    _orig_sleep = _time_mod.sleep

    # Count 429 retries via log inspection — simpler: count calls to _orig_get_json
    # that eventually succeed but threw 429 internally.
    # Simplest accurate approach: wrap urlopen to count 429 responses.
    import urllib.request
    import urllib.error
    _orig_urlopen = urllib.request.urlopen
    _429_count = [0]
    _abort_flag = [False]

    def _counting_urlopen(req, timeout=None):
        try:
            return _orig_urlopen(req, timeout=timeout)
        except urllib.error.HTTPError as exc:
            if exc.code == 429:
                _429_count[0] += 1
            raise

    urllib.request.urlopen = _counting_urlopen
    try:
        result = src.fetch_tweets(handle, start, end)
    except _http_mod.RateLimitExhausted:
        _abort_flag[0] = True
        result = None  # type: ignore[assignment]
    finally:
        urllib.request.urlopen = _orig_urlopen

    tweets = result.tweets if result is not None else []
    reached_floor = result.reached_floor if result is not None else False
    earliest = min((t.created_at_utc for t in tweets), default=None)

    logger.info(
        "[%s] run %d → %d tweets  reached_floor=%s  429s=%d  aborted=%s",
        provider, run_index, len(tweets), reached_floor, _429_count[0], _abort_flag[0],
    )

    return RunRecord(
        run_index=run_index,
        provider=provider,
        count=len(tweets),
        tweet_ids={t.id for t in tweets},
        tweets=tweets,
        reached_floor=reached_floor,
        earliest_utc=earliest,
        rate_429_count=_429_count[0],
        aborted=_abort_flag[0],
    )


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

_STABLE_COUNT_TOLERANCE = 0.05   # counts within 5 % of max
_STABLE_OVERLAP_THRESHOLD = 0.95  # ≥ 95 % ID overlap across all runs


def _verdict(records: list[RunRecord]) -> str:
    if any(r.aborted for r in records):
        return "VARIABLE (429-abort)"
    if not all(r.reached_floor for r in records):
        return "VARIABLE (floor not reached)"
    counts = [r.count for r in records]
    if max(counts, default=0) == 0:
        return "VARIABLE (zero tweets)"
    spread = (max(counts) - min(counts)) / max(counts)
    if spread > _STABLE_COUNT_TOLERANCE:
        return f"VARIABLE (count spread {spread:.0%})"
    # ID-set overlap: pairwise intersection over union of run-0
    if len(records) >= 2:
        base_ids = records[0].tweet_ids
        for r in records[1:]:
            if not base_ids and not r.tweet_ids:
                continue
            union = base_ids | r.tweet_ids
            overlap = len(base_ids & r.tweet_ids) / len(union) if union else 1.0
            if overlap < _STABLE_OVERLAP_THRESHOLD:
                return f"VARIABLE (ID overlap {overlap:.0%} run1 vs run{r.run_index})"
    return "STABLE"


def _sample_tweets(tweets: list[Tweet], n: int = 10) -> list[str]:
    """Pick up to n tweets that mention a cashtag or look like ticker discussion."""
    cashtag_re = re.compile(r'\$[A-Z]{1,5}')
    scored: list[tuple[int, Tweet]] = []
    for t in tweets:
        text = t.text or ""
        score = len(cashtag_re.findall(text))
        scored.append((score, t))
    scored.sort(key=lambda x: -x[0])
    sample = [t for _, t in scored[:n]]
    if len(sample) < n:
        seen = {t.id for t in sample}
        for t in tweets:
            if t.id not in seen:
                sample.append(t)
                if len(sample) >= n:
                    break
    lines = []
    for t in sample:
        text = (t.text or "").replace("\n", " ")[:200]
        lines.append(f"- [{t.created_at_utc}] ({t.type}) {text}")
    return lines


def _build_report(
    handle: str,
    start: datetime.date,
    end: datetime.date,
    runs: int,
    gx_records: list[RunRecord],
    tw_records: list[RunRecord],
) -> str:
    lines: list[str] = []
    lines += [
        f"# Variance Probe: @{handle}",
        f"",
        f"Window: {start} → {end}  |  Runs per provider: {runs}",
        f"",
    ]

    for provider_label, records in [("GetXAPI", gx_records), ("twitterapi.io", tw_records)]:
        v = _verdict(records)
        lines += [
            f"## {provider_label}",
            f"",
            f"**VERDICT: {v}**",
            f"",
            f"| run | tweets | reached_floor | earliest_utc | 429s | aborted |",
            f"|-----|-------:|:-------------:|--------------|-----:|:-------:|",
        ]
        for r in records:
            lines.append(
                f"| {r.run_index} | {r.count} | {r.reached_floor} "
                f"| {r.earliest_utc or 'n/a'} | {r.rate_429_count} | {r.aborted} |"
            )
        lines.append("")

        # Same-provider ID overlap
        if len(records) >= 2:
            lines.append("**Same-provider ID overlap (run 1 as baseline)**")
            lines.append("")
            lines.append("| compared | ∩ (shared) | run1-only | runN-only | overlap % |")
            lines.append("|----------|----------:|----------:|----------:|----------:|")
            base = records[0].tweet_ids
            for r in records[1:]:
                shared = base & r.tweet_ids
                base_only = base - r.tweet_ids
                rn_only = r.tweet_ids - base
                union_size = len(base | r.tweet_ids)
                overlap_pct = f"{100*len(shared)/union_size:.1f}%" if union_size else "n/a"
                lines.append(
                    f"| run1 vs run{r.run_index} | {len(shared)} "
                    f"| {len(base_only)} | {len(rn_only)} | {overlap_pct} |"
                )
            lines.append("")

    # Cross-provider union
    lines += [
        "## Cross-provider union",
        "",
    ]
    gx_union = set().union(*(r.tweet_ids for r in gx_records)) if gx_records else set()
    tw_union = set().union(*(r.tweet_ids for r in tw_records)) if tw_records else set()
    both = gx_union & tw_union
    gx_only = gx_union - tw_union
    tw_only = tw_union - gx_union
    union_all = gx_union | tw_union

    def _pct_lift(union: set, base: set) -> str:
        if not base:
            return "n/a"
        lift = len(union) - len(base)
        return f"+{lift} ({100*lift/len(base):.1f}%)"

    lines += [
        f"| metric | count |",
        f"|--------|------:|",
        f"| GetXAPI union (all runs) | {len(gx_union)} |",
        f"| twitterapi.io union (all runs) | {len(tw_union)} |",
        f"| shared (∩) | {len(both)} |",
        f"| GetXAPI-only | {len(gx_only)} |",
        f"| twitterapi.io-only | {len(tw_only)} |",
        f"| **combined union** | **{len(union_all)}** |",
        f"| lift over GetXAPI alone | {_pct_lift(union_all, gx_union)} |",
        f"| lift over twitterapi.io alone | {_pct_lift(union_all, tw_union)} |",
        "",
    ]

    # Sample tweets from the combined union
    all_tweets: dict[str, Tweet] = {}
    for r in gx_records + tw_records:
        for t in r.tweets:
            all_tweets[t.id] = t
    sample_lines = _sample_tweets(list(all_tweets.values()))
    if sample_lines:
        lines += [
            "## Sample tweets (cashtag-ranked)",
            "",
        ] + sample_lines + [""]

    return "\n".join(lines)


def _build_meta(
    handle: str,
    run_dt: datetime.datetime,
    start: datetime.date,
    runs: int,
    git_sha: str,
    gx_verdict: str,
    tw_verdict: str,
) -> str:
    lines = [
        "# Probe meta",
        "",
        f"| parameter | value |",
        f"|-----------|-------|",
        f"| handle | @{handle} |",
        f"| run date/time (UTC) | {run_dt.strftime('%Y-%m-%dT%H:%M:%SZ')} |",
        f"| since | {start} |",
        f"| runs per provider | {runs} |",
        f"| providers | getxapi, twitterapi |",
        f"| git SHA (main) | {git_sha} |",
        f"| GetXAPI verdict | {gx_verdict} |",
        f"| twitterapi.io verdict | {tw_verdict} |",
        "",
        "Conclusion: ",
    ]
    return "\n".join(lines)


def _tweet_to_dict(t: Tweet) -> dict:
    return {
        "id": t.id,
        "text": t.text,
        "created_at_utc": t.created_at_utc,
        "type": t.type,
        "is_reply": t.is_reply,
        "is_quote": t.is_quote,
        "in_reply_to_id": t.in_reply_to_id,
        "quoted_tweet_id": t.quoted_tweet_id,
        "quoted_author_id": t.quoted_author_id,
        "conversation_id": t.conversation_id,
        "like_count": t.like_count,
        "retweet_count": t.retweet_count,
        "reply_count": t.reply_count,
        "quote_count": t.quote_count,
        "view_count": t.view_count,
        "bookmark_count": t.bookmark_count,
        "has_media": t.has_media,
        "media_urls": t.media_urls,
        "url": t.url,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("handle")
    parser.add_argument("--since", default=None)
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument(
        "--no-persist",
        action="store_true",
        help="Skip seeding raw_tweets + day_fetch_log from this run's fixtures.",
    )
    args = parser.parse_args()

    handle = normalize_handle(args.handle)
    today = datetime.date.today()
    start = datetime.date.fromisoformat(args.since) if args.since else datetime.date(today.year, 1, 1)
    end = today
    run_dt = datetime.datetime.utcnow()

    out_dir = _dated_folder(handle, today.isoformat())
    out_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Output folder: %s", out_dir)

    git_sha = _git_sha()

    # --- Run all providers ---
    gx_records: list[RunRecord] = []
    tw_records: list[RunRecord] = []

    for i in range(1, args.runs + 1):
        gx_records.append(_run_provider("getxapi", handle, start, end, i))

    for i in range(1, args.runs + 1):
        tw_records.append(_run_provider("twitterapi", handle, start, end, i))

    # --- Write JSON fixtures ---
    for r in gx_records:
        path = out_dir / f"getxapi_run{r.run_index}.json"
        path.write_text(json.dumps([_tweet_to_dict(t) for t in r.tweets], indent=2))
        logger.info("Wrote %s (%d tweets)", path, len(r.tweets))

    for r in tw_records:
        path = out_dir / f"twitterapi_run{r.run_index}.json"
        path.write_text(json.dumps([_tweet_to_dict(t) for t in r.tweets], indent=2))
        logger.info("Wrote %s (%d tweets)", path, len(r.tweets))

    # --- Write report.md ---
    report = _build_report(handle, start, end, args.runs, gx_records, tw_records)
    (out_dir / "report.md").write_text(report)
    logger.info("Wrote report.md")

    # --- Write meta.md ---
    gx_v = _verdict(gx_records)
    tw_v = _verdict(tw_records)
    meta = _build_meta(handle, run_dt, start, args.runs, git_sha, gx_v, tw_v)
    (out_dir / "meta.md").write_text(meta)
    logger.info("Wrote meta.md")

    # --- Persist into raw_tweets + day_fetch_log (idempotent) ---
    persist: dict | None = None
    if not args.no_persist:
        init_db()
        persist = import_folder(out_dir)
        close_connection()  # checkpoint WAL so the committed .db has no sidecar
        logger.info(
            "Persisted @%s: inserted=%d ok=%d mismatch=%d",
            handle, persist["inserted"], persist["days_ok"], persist["days_mismatch"],
        )

    # --- stdout summary ---
    print(f"\n## Variance probe: @{handle}  {start} → {end}  ({args.runs} runs each)\n")
    print(f"Output: {out_dir}\n")
    print(f"GetXAPI    verdict: {gx_v}")
    print(f"twitterapi verdict: {tw_v}\n")
    for r in gx_records + tw_records:
        print(
            f"  [{r.provider}] run{r.run_index}: {r.count} tweets  "
            f"floor={r.reached_floor}  429s={r.rate_429_count}  aborted={r.aborted}"
        )
    if persist is not None:
        print(
            f"\nPersisted to DB: inserted={persist['inserted']} ignored={persist['ignored']} "
            f"| day-slots ok={persist['days_ok']} mismatch={persist['days_mismatch']} "
            f"failed={persist['days_failed']}"
        )

    # --- GitHub job summary ---
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY", "/dev/null")
    with open(summary_path, "w") as f:
        f.write(report)
        f.write("\n\n---\n\n")
        f.write(meta)
        if persist is not None:
            f.write(
                f"\n\n---\n\n### DB persistence\n"
                f"- tweets inserted: **{persist['inserted']}** (ignored {persist['ignored']})\n"
                f"- day-slots: ok **{persist['days_ok']}**, "
                f"mismatch **{persist['days_mismatch']}**, failed **{persist['days_failed']}**\n"
            )


if __name__ == "__main__":
    main()
