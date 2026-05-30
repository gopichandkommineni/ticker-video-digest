#!/usr/bin/env python3
"""
compare_providers.py — GetXAPI vs twitterapi.io completeness audit.

Decision metric: cashtag recall and earliest-mention accuracy.
Run on account 1 first; script pauses after raw JSON probe and again
after account-1 report, waiting for go-ahead before account 2.

Usage:
    python compare_providers.py
"""
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

# ── Load secrets ──────────────────────────────────────────────────────────────
_env_path = Path(__file__).parent / ".env"
load_dotenv(_env_path)

GETXAPI_KEY       = os.environ["GETXAPI_KEY"]
TWITTERAPI_IO_KEY = os.environ["TWITTERAPI_IO_KEY"]

# ── User config — edit these before running ───────────────────────────────────
ACCOUNTS     = ["rklbofficial", "AboveAltitude_"]   # handles without @
WINDOW_START = "2025-01-01"   # ISO date, inclusive
WINDOW_END   = "2025-01-31"   # ISO date, inclusive
MAX_PAGES    = 50             # safety valve per provider per account

# ── Constants ─────────────────────────────────────────────────────────────────
GX_BASE   = "https://api.getxapi.com"
TW_BASE   = "https://api.twitterapi.io"
CASHTAG_RE = re.compile(r"\$[A-Z]{1,5}\b")

WIN_START_DT = datetime.fromisoformat(WINDOW_START).replace(tzinfo=timezone.utc)
WIN_END_DT   = (
    datetime.fromisoformat(WINDOW_END)
    .replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)
)


# ─────────────────────────────────────────────────────────────────────────────
# Snowflake decode
# ─────────────────────────────────────────────────────────────────────────────

def snowflake_to_utc(tweet_id: str) -> datetime:
    ts_ms = (int(tweet_id) >> 22) + 1288834974657
    return datetime.fromtimestamp(ts_ms / 1000.0, tz=timezone.utc)


# ─────────────────────────────────────────────────────────────────────────────
# Date parsing — handle both "Mon Jan 06 …" (v1) and ISO-8601 variants
# ─────────────────────────────────────────────────────────────────────────────

_DATE_FMTS = [
    "%a %b %d %H:%M:%S +0000 %Y",   # Twitter v1  "Mon Jan 06 12:00:00 +0000 2025"
    "%Y-%m-%dT%H:%M:%S.%fZ",         # ISO w/ ms
    "%Y-%m-%dT%H:%M:%SZ",            # ISO no ms
    "%Y-%m-%d %H:%M:%S+00:00",
    "%Y-%m-%dT%H:%M:%S+00:00",
]

def parse_dt(s: str) -> datetime | None:
    if not s:
        return None
    s = s.strip()
    for fmt in _DATE_FMTS:
        try:
            return datetime.strptime(s, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Schema-agnostic tweet normalization
# Detects field names from the actual payload on first call.
# ─────────────────────────────────────────────────────────────────────────────

def _pick(d: dict, *keys, default=""):
    for k in keys:
        v = d.get(k)
        if v is not None:
            return v
    return default


def normalize_tweet(raw: dict) -> dict | None:
    """
    Return a normalized dict or None if the tweet is a pure retweet.

    Normalized fields:
        id, created_at_reported, created_at_decoded, text, type
        (type ∈ {original, reply, quote, retweet})
    """
    tid = str(_pick(raw, "id", "id_str") or "").strip()
    if not tid:
        return None

    text = str(_pick(raw, "text", "full_text") or "").strip()
    created_reported = str(_pick(raw, "createdAt", "created_at") or "").strip()

    # ── Detect type ──────────────────────────────────────────────────────────
    # Pure retweet: nested retweeted payload exists, or type/is_retweet flag
    has_rt_nested = bool(
        raw.get("retweetedTweet")
        or raw.get("retweeted_tweet")
        or raw.get("retweeted_status")
    )
    is_rt_flag = bool(
        raw.get("isRetweet")
        or raw.get("is_retweet")
        or raw.get("retweeted")
        # twitterapi.io sets type="retweeted" for pure RTs
        or (str(raw.get("type", "")).lower() in ("retweeted", "retweet"))
    )
    # Text-based fallback: starts with "RT @"
    is_rt_text = text.startswith("RT @")

    is_pure_retweet = has_rt_nested or is_rt_flag or is_rt_text

    has_quote = bool(
        raw.get("quotedTweet")
        or raw.get("quoted_tweet")
        or raw.get("quoted_status")
        or raw.get("quotedStatus")
        or (str(raw.get("type", "")).lower() in ("quoted",))
    )
    is_reply = bool(
        raw.get("isReply")
        or raw.get("is_reply")
        or raw.get("in_reply_to_status_id")
        or raw.get("in_reply_to_status_id_str")
        or raw.get("inReplyToId")
        or (str(raw.get("type", "")).lower() in ("replied_to", "reply"))
    )

    if is_pure_retweet:
        return None  # exclude per spec

    tweet_type = "quote" if has_quote else ("reply" if is_reply else "original")

    decoded_dt = snowflake_to_utc(tid)

    return {
        "id":                  tid,
        "created_at_reported": created_reported,
        "created_at_decoded":  decoded_dt.isoformat(),
        "text":                text,
        "type":                tweet_type,
        "_decoded_dt":         decoded_dt,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Date-window helpers
# ─────────────────────────────────────────────────────────────────────────────

def tweet_dt(norm: dict) -> datetime | None:
    """Best-effort datetime for a normalized tweet."""
    # Prefer reported date; fall back to Snowflake
    dt = parse_dt(norm["created_at_reported"])
    if dt:
        return dt
    return norm.get("_decoded_dt")


def in_window(norm: dict) -> bool:
    dt = tweet_dt(norm)
    if dt is None:
        return True   # can't determine — include to be safe
    return WIN_START_DT <= dt <= WIN_END_DT


def before_window(norm: dict) -> bool:
    dt = tweet_dt(norm)
    if dt is None:
        return False
    return dt < WIN_START_DT


# ─────────────────────────────────────────────────────────────────────────────
# GetXAPI fetcher
# Uses advanced_search with from:/since:/until: operators so the window
# is server-filtered, not just client-filtered.
# ─────────────────────────────────────────────────────────────────────────────

def _gx_headers() -> dict:
    return {"Authorization": f"Bearer {GETXAPI_KEY}"}


def gx_fetch_page(handle: str, cursor: str | None, req_counter: list) -> dict:
    q = f"from:{handle} since:{WINDOW_START} until:{WINDOW_END}"
    params: dict = {"q": q, "product": "Latest"}
    if cursor:
        params["cursor"] = cursor
    r = requests.get(
        f"{GX_BASE}/twitter/tweet/advanced_search",
        headers=_gx_headers(),
        params=params,
        timeout=30,
    )
    req_counter[0] += 1
    r.raise_for_status()
    return r.json()


def gx_fetch_all(handle: str, first_page_data: dict) -> tuple[list[dict], int]:
    """
    Paginate GetXAPI starting from already-fetched first_page_data.
    Returns (normalized_tweets, total_extra_requests).
    """
    tweets: list[dict] = []
    req_counter = [0]

    def _ingest(page: dict):
        for raw in page.get("tweets", []):
            norm = normalize_tweet(raw)
            if norm and in_window(norm):
                tweets.append(norm)

    _ingest(first_page_data)

    cursor = first_page_data.get("next_cursor")
    has_more = first_page_data.get("has_more", False)

    for _ in range(MAX_PAGES - 1):
        if not has_more or not cursor:
            break
        time.sleep(0.25)
        page = gx_fetch_page(handle, cursor, req_counter)
        _ingest(page)
        has_more = page.get("has_more", False)
        cursor = page.get("next_cursor")

    return tweets, req_counter[0]


# ─────────────────────────────────────────────────────────────────────────────
# twitterapi.io fetcher
# No server-side date filter — paginate until we pass WINDOW_START.
# ─────────────────────────────────────────────────────────────────────────────

def _tw_headers() -> dict:
    return {"X-API-Key": TWITTERAPI_IO_KEY}


def tw_fetch_page(handle: str, cursor: str | None, req_counter: list) -> dict:
    params: dict = {"userName": handle}
    if cursor:
        params["cursor"] = cursor
    r = requests.get(
        f"{TW_BASE}/twitter/user/last_tweets",
        headers=_tw_headers(),
        params=params,
        timeout=30,
    )
    req_counter[0] += 1
    r.raise_for_status()
    return r.json()


def tw_fetch_all(handle: str, first_page_data: dict) -> tuple[list[dict], int]:
    tweets: list[dict] = []
    req_counter = [0]

    def _ingest(page: dict) -> bool:
        """Returns True if we should stop (hit a tweet before WINDOW_START)."""
        for raw in page.get("tweets", []):
            norm = normalize_tweet(raw)
            if norm is None:
                continue
            if before_window(norm):
                return True   # stop paginating
            if in_window(norm):
                tweets.append(norm)
        return False

    stop = _ingest(first_page_data)

    cursor = first_page_data.get("next_cursor")
    has_more = first_page_data.get("has_next_page", False)

    for _ in range(MAX_PAGES - 1):
        if stop or not has_more or not cursor:
            break
        time.sleep(0.25)
        page = tw_fetch_page(handle, cursor, req_counter)
        stop = _ingest(page)
        has_more = page.get("has_next_page", False)
        cursor = page.get("next_cursor")

    return tweets, req_counter[0]


# ─────────────────────────────────────────────────────────────────────────────
# Analysis helpers
# ─────────────────────────────────────────────────────────────────────────────

def cashtag_earliest(tweets: list[dict]) -> dict[str, dict]:
    """Map cashtag → {id, date} of its earliest mention."""
    result: dict[str, dict] = {}
    for t in sorted(tweets, key=lambda x: x["id"]):
        for tag in CASHTAG_RE.findall(t["text"]):
            if tag not in result:
                result[tag] = {"id": t["id"], "date": t["created_at_reported"] or t["created_at_decoded"]}
    return result


def snowflake_vs_reported_mismatches(tweets: list[dict]) -> list[dict]:
    mismatches = []
    for t in tweets:
        rep = parse_dt(t["created_at_reported"])
        dec = t["_decoded_dt"]
        if rep and abs((rep - dec).total_seconds()) > 2:
            mismatches.append({
                "id":       t["id"],
                "reported": t["created_at_reported"],
                "decoded":  t["created_at_decoded"],
                "delta_s":  round((rep - dec).total_seconds(), 1),
            })
    return mismatches


def earliest_tweet(tweets: list[dict]) -> dict | None:
    if not tweets:
        return None
    return min(tweets, key=lambda t: t["id"])


# ─────────────────────────────────────────────────────────────────────────────
# Markdown report builder
# ─────────────────────────────────────────────────────────────────────────────

def build_report(
    handle: str,
    gx_tweets: list[dict],
    tw_tweets: list[dict],
    gx_reqs: int,
    tw_reqs: int,
) -> str:
    gx_ids = {t["id"] for t in gx_tweets}
    tw_ids = {t["id"] for t in tw_tweets}

    both       = gx_ids & tw_ids
    gx_only    = gx_ids - tw_ids
    tw_only    = tw_ids - gx_ids

    gx_cash = cashtag_earliest(gx_tweets)
    tw_cash = cashtag_earliest(tw_tweets)
    cash_gx_only = set(gx_cash) - set(tw_cash)
    cash_tw_only = set(tw_cash) - set(gx_cash)
    cash_both    = set(gx_cash) & set(tw_cash)

    gx_earliest = earliest_tweet(gx_tweets)
    tw_earliest = earliest_tweet(tw_tweets)

    gx_mismatches = snowflake_vs_reported_mismatches(gx_tweets)
    tw_mismatches = snowflake_vs_reported_mismatches(tw_tweets)

    def _type_counts(tweets: list[dict]) -> str:
        from collections import Counter
        c = Counter(t["type"] for t in tweets)
        return ", ".join(f"{k}={v}" for k, v in sorted(c.items()))

    lines = [
        f"# Provider Comparison Report — @{handle}",
        f"",
        f"**Window:** {WINDOW_START} → {WINDOW_END}  ",
        f"**Requests:** GetXAPI={gx_reqs}, twitterapi.io={tw_reqs}  ",
        f"",
        f"---",
        f"",
        f"## Tweet Counts (non-retweets)",
        f"",
        f"| Provider | Count | Types |",
        f"|----------|-------|-------|",
        f"| GetXAPI | {len(gx_tweets)} | {_type_counts(gx_tweets)} |",
        f"| twitterapi.io | {len(tw_tweets)} | {_type_counts(tw_tweets)} |",
        f"",
        f"## Set Diff",
        f"",
        f"| Set | Count |",
        f"|-----|-------|",
        f"| A∩B  (both) | {len(both)} |",
        f"| A−B  (GetXAPI-only) | {len(gx_only)} |",
        f"| B−A  (twitterapi.io-only) | {len(tw_only)} |",
        f"",
    ]

    if gx_only:
        lines.append("### GetXAPI-only tweet IDs (first 20)")
        for tid in sorted(gx_only)[:20]:
            lines.append(f"- `{tid}`")
        lines.append("")

    if tw_only:
        lines.append("### twitterapi.io-only tweet IDs (first 20)")
        for tid in sorted(tw_only)[:20]:
            lines.append(f"- `{tid}`")
        lines.append("")

    lines += [
        f"## Earliest Tweet per Provider",
        f"",
        f"| Provider | Tweet ID | Reported Date |",
        f"|----------|----------|---------------|",
    ]
    if gx_earliest:
        lines.append(
            f"| GetXAPI | `{gx_earliest['id']}` | {gx_earliest['created_at_reported']} |"
        )
    else:
        lines.append("| GetXAPI | — | — |")

    if tw_earliest:
        lines.append(
            f"| twitterapi.io | `{tw_earliest['id']}` | {tw_earliest['created_at_reported']} |"
        )
    else:
        lines.append("| twitterapi.io | — | — |")

    lines += [
        f"",
        f"## Cashtag Recall",
        f"",
        f"| Cashtag | GetXAPI earliest | twitterapi.io earliest |",
        f"|---------|-----------------|------------------------|",
    ]
    all_tags = sorted(set(gx_cash) | set(tw_cash))
    for tag in all_tags:
        gx_e = gx_cash.get(tag)
        tw_e = tw_cash.get(tag)
        gx_str = f"`{gx_e['id']}` {gx_e['date']}" if gx_e else "**MISSING**"
        tw_str = f"`{tw_e['id']}` {tw_e['date']}" if tw_e else "**MISSING**"
        lines.append(f"| {tag} | {gx_str} | {tw_str} |")

    lines += [
        f"",
        f"### Cashtag set differences",
        f"",
        f"- GetXAPI-only cashtags ({len(cash_gx_only)}): {', '.join(sorted(cash_gx_only)) or '—'}",
        f"- twitterapi.io-only cashtags ({len(cash_tw_only)}): {', '.join(sorted(cash_tw_only)) or '—'}",
        f"- In both ({len(cash_both)}): {', '.join(sorted(cash_both)) or '—'}",
        f"",
        f"## Snowflake vs Reported Date Mismatches (>2 s)",
        f"",
    ]

    if not gx_mismatches and not tw_mismatches:
        lines.append("No mismatches detected in either provider.")
    else:
        if gx_mismatches:
            lines.append(f"**GetXAPI** — {len(gx_mismatches)} mismatch(es):")
            for m in gx_mismatches[:10]:
                lines.append(
                    f"  - id=`{m['id']}` reported={m['reported']} decoded={m['decoded']} Δ={m['delta_s']}s"
                )
        if tw_mismatches:
            lines.append(f"**twitterapi.io** — {len(tw_mismatches)} mismatch(es):")
            for m in tw_mismatches[:10]:
                lines.append(
                    f"  - id=`{m['id']}` reported={m['reported']} decoded={m['decoded']} Δ={m['delta_s']}s"
                )

    # ── VERDICT ───────────────────────────────────────────────────────────────
    if not gx_tweets and not tw_tweets:
        verdict_winner = "INCONCLUSIVE — no tweets found in either provider"
        verdict_detail = "Check account handles and window."
        verdict_dates = "Cannot compare."
    else:
        # Cashtag recall
        gx_recall = len(gx_cash)
        tw_recall = len(tw_cash)
        if gx_recall > tw_recall:
            recall_winner = f"GetXAPI ({gx_recall} vs {tw_recall} unique cashtags)"
        elif tw_recall > gx_recall:
            recall_winner = f"twitterapi.io ({tw_recall} vs {gx_recall} unique cashtags)"
        else:
            recall_winner = f"TIE — both found {gx_recall} unique cashtags"

        # Earliest date correctness (fewer mismatches is better)
        gx_m = len(gx_mismatches)
        tw_m = len(tw_mismatches)
        if gx_m < tw_m:
            date_winner = f"GetXAPI (fewer date mismatches: {gx_m} vs {tw_m})"
        elif tw_m < gx_m:
            date_winner = f"twitterapi.io (fewer date mismatches: {tw_m} vs {gx_m})"
        else:
            date_winner = f"TIE — both had {gx_m} date mismatch(es)"

        # Tweet volume completeness
        gx_vol = len(gx_tweets)
        tw_vol = len(tw_tweets)
        if gx_vol > tw_vol:
            vol_winner = f"GetXAPI ({gx_vol} vs {tw_vol} tweets)"
        elif tw_vol > gx_vol:
            vol_winner = f"twitterapi.io ({tw_vol} vs {gx_vol} tweets)"
        else:
            vol_winner = f"TIE — both returned {gx_vol} tweets"

        verdict_winner = recall_winner
        verdict_detail = f"Volume: {vol_winner}"
        verdict_dates  = f"Date accuracy: {date_winner}"

    lines += [
        f"",
        f"---",
        f"",
        f"## VERDICT",
        f"",
        f"**Cashtag recall winner:** {verdict_winner}  ",
        f"**{verdict_detail}**  ",
        f"**{verdict_dates}**  ",
    ]

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Main per-account runner
# ─────────────────────────────────────────────────────────────────────────────

def run_account(handle: str) -> str:
    sep = "=" * 64
    print(f"\n{sep}")
    print(f"  ACCOUNT: @{handle}   |   window: {WINDOW_START} → {WINDOW_END}")
    print(sep)

    # ── PHASE 1: raw first-page probe ────────────────────────────────────────
    print("\n>>> [GetXAPI] Fetching raw FIRST page …")
    gx_req_counter = [1]
    try:
        gx_page1 = gx_fetch_page(handle, None, gx_req_counter)
    except Exception as e:
        print(f"ERROR: GetXAPI first page failed: {e}")
        gx_page1 = {}

    print("\n" + "─" * 40)
    print("GetXAPI — RAW FIRST PAGE JSON")
    print("─" * 40)
    print(json.dumps(gx_page1, indent=2)[:4000])
    if len(json.dumps(gx_page1)) > 4000:
        print("… (truncated — full object in memory)")

    print("\n>>> [twitterapi.io] Fetching raw FIRST page …")
    tw_req_counter = [1]
    try:
        tw_page1 = tw_fetch_page(handle, None, tw_req_counter)
    except Exception as e:
        print(f"ERROR: twitterapi.io first page failed: {e}")
        tw_page1 = {}

    print("\n" + "─" * 40)
    print("twitterapi.io — RAW FIRST PAGE JSON")
    print("─" * 40)
    print(json.dumps(tw_page1, indent=2)[:4000])
    if len(json.dumps(tw_page1)) > 4000:
        print("… (truncated — full object in memory)")

    print(f"\n>>> GetXAPI requests so far:      {gx_req_counter[0]}")
    print(f">>> twitterapi.io requests so far: {tw_req_counter[0]}")

    # ── Pause for schema confirmation ─────────────────────────────────────────
    try:
        input("\n[PAUSE] Review raw JSON above. Press Enter to continue with full pagination …\n")
    except EOFError:
        print("[non-interactive mode — continuing automatically]")

    # ── PHASE 2: full pagination ──────────────────────────────────────────────
    print("\n>>> [GetXAPI] Paginating full window …")
    gx_tweets, gx_extra = gx_fetch_all(handle, gx_page1)
    gx_total_reqs = gx_req_counter[0] + gx_extra
    print(f"    Done. Requests: {gx_total_reqs}  |  tweets (non-RT): {len(gx_tweets)}")

    print("\n>>> [twitterapi.io] Paginating full window …")
    tw_tweets, tw_extra = tw_fetch_all(handle, tw_page1)
    tw_total_reqs = tw_req_counter[0] + tw_extra
    print(f"    Done. Requests: {tw_total_reqs}  |  tweets (non-RT): {len(tw_tweets)}")

    # ── PHASE 3: build and save report ───────────────────────────────────────
    report = build_report(handle, gx_tweets, tw_tweets, gx_total_reqs, tw_total_reqs)

    out_path = Path(__file__).parent / f"report_{handle}.md"
    out_path.write_text(report, encoding="utf-8")
    print(f"\n>>> Report saved to: {out_path}")
    print("\n" + report)

    return report


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def main():
    if len(ACCOUNTS) < 1:
        print("ERROR: Set at least one handle in ACCOUNTS.")
        sys.exit(1)

    print(f"Providers: GetXAPI  vs  twitterapi.io")
    print(f"Accounts:  {ACCOUNTS}")
    print(f"Window:    {WINDOW_START} → {WINDOW_END}")
    print(f"Max pages: {MAX_PAGES} per provider per account")

    # Account 1
    run_account(ACCOUNTS[0])

    if len(ACCOUNTS) < 2:
        print("\n[Only one account configured — done.]")
        return

    # Pause before account 2
    print("\n" + "=" * 64)
    try:
        input(
            f"[PAUSE] Account-1 report shown above.\n"
            f"Press Enter to run account 2 (@{ACCOUNTS[1]}) …\n"
        )
    except EOFError:
        print("[non-interactive — continuing]")

    run_account(ACCOUNTS[1])
    print("\nAll done.")


if __name__ == "__main__":
    main()
