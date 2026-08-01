#!/usr/bin/env python3
"""groq_probe.py — throwaway quality probe for Groq tweet summarization.

NOT a production integration: no DB writes, no schema changes, no new tables.
Read-only on the SQLite DB. Prints results to the terminal only.

This is the Groq counterpart of `gemini_probe.py`. Same pipeline, same
strict-JSON contract, different provider — so the two can be compared directly.

Pipeline:
  1. Pull tweets from raw_tweets created in the last 7 days (read-only).
  2. Regex-filter for cashtags ($TICKER) FIRST, before any LLM call. Only
     tweets containing >=1 cashtag proceed to Groq. This is deterministic;
     ticker extraction is never the LLM's job.
  3. For each survivor, ask Groq for STRICT JSON with exactly three fields:
     thesis, sentiment, stance. Groq does NOT extract tickers.

Usage:  GROQ_API_KEY=... python groq_probe.py
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

# --- Config -----------------------------------------------------------------

DB_PATH = Path(__file__).parent / "data" / "fintwit.db"
DAYS_BACK = 7
GROQ_MODEL = "llama-3.3-70b-versatile"
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MAX_GROQ_CALLS = 50            # cap to see quality, not drain quota
DELAY_SECONDS = 2.1           # politeness: free tier is ~30 req/min
TEXT_TRUNCATE = 240           # chars shown for the original tweet
REQUEST_TIMEOUT = 30          # seconds per Groq HTTP call
# Groq sits behind Cloudflare, which 403s (error 1010) the default
# "Python-urllib" User-Agent. A non-default UA clears the bot filter.
USER_AGENT = "groq-tweet-probe/1.0"

CASHTAG_RE = re.compile(r"\$[A-Z]{1,5}\b")

PROMPT_TEMPLATE = """You are analyzing a single financial tweet.

Do NOT extract tickers — that has already been done deterministically.

Return STRICT JSON with EXACTLY these three fields and nothing else:
{{
  "thesis": "<one sentence stating the investment claim, or \\"none\\">",
  "sentiment": "<one of: bullish, bearish, neutral>",
  "stance": "<one of: prediction, news, opinion, question, promotion, other>"
}}

Tweet:
\"\"\"{tweet_text}\"\"\"
"""


# --- DB ----------------------------------------------------------------------

def fetch_recent_tweets(db_path: Path, days_back: int) -> list[dict]:
    """Read tweets from the last `days_back` days. Read-only."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    # Open read-only via URI so we can never accidentally mutate the DB.
    uri = f"file:{db_path}?mode=ro"
    con = sqlite3.connect(uri, uri=True)
    con.row_factory = sqlite3.Row
    try:
        rows = con.execute(
            """
            SELECT tweet_id, account_handle, text, created_at_utc
            FROM raw_tweets
            WHERE created_at_utc >= ?
              AND COALESCE(is_deleted, 0) = 0
              AND text IS NOT NULL
            ORDER BY created_at_utc DESC
            """,
            (cutoff,),
        ).fetchall()
    finally:
        con.close()
    return [dict(r) for r in rows]


# --- Filter ------------------------------------------------------------------

def extract_cashtags(text: str) -> list[str]:
    """Deterministic cashtag extraction. Order-preserving, de-duplicated."""
    seen: dict[str, None] = {}
    for m in CASHTAG_RE.findall(text or ""):
        seen.setdefault(m, None)
    return list(seen)


# --- Groq --------------------------------------------------------------------

def _strip_fences(s: str) -> str:
    """Remove ```json ... ``` or ``` ... ``` markdown fences if present."""
    s = s.strip()
    if s.startswith("```"):
        s = s.split("\n", 1)[1] if "\n" in s else s[3:]
        if s.rstrip().endswith("```"):
            s = s.rstrip()[:-3]
    return s.strip()


def call_groq(tweet_text: str, api_key: str) -> dict:
    """Call Groq chat completions, return parsed JSON dict. Raises on failure."""
    payload = {
        "model": GROQ_MODEL,
        "temperature": 0.0,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "user", "content": PROMPT_TEMPLATE.format(tweet_text=tweet_text)}
        ],
    }
    req = urllib.request.Request(
        GROQ_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "User-Agent": USER_AGENT,
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
        body = json.loads(resp.read().decode("utf-8"))

    text = body["choices"][0]["message"]["content"]
    return json.loads(_strip_fences(text))


# --- Main --------------------------------------------------------------------

def main() -> int:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("ERROR: GROQ_API_KEY is not set in the environment.", file=sys.stderr)
        return 1
    if not DB_PATH.exists():
        print(f"ERROR: DB not found at {DB_PATH}", file=sys.stderr)
        return 1

    print(f"DB: {DB_PATH}  |  window: last {DAYS_BACK} days  |  model: {GROQ_MODEL}")
    print("=" * 72)

    tweets = fetch_recent_tweets(DB_PATH, DAYS_BACK)

    survivors: list[dict] = []
    for t in tweets:
        tickers = extract_cashtags(t["text"])
        if tickers:
            t["tickers"] = tickers
            survivors.append(t)

    pulled = len(tweets)
    kept = len(survivors)
    ratio = (kept / pulled * 100) if pulled else 0.0
    print(f"Pulled (last {DAYS_BACK}d): {pulled}")
    print(f"Survived cashtag filter:  {kept}  ({ratio:.1f}% of pulled)")
    print("=" * 72)

    if not survivors:
        print("No ticker-bearing tweets in window. Nothing to summarize.")
        return 0

    to_process = survivors[:MAX_GROQ_CALLS]
    skipped = kept - len(to_process)
    if skipped > 0:
        print(
            f"NOTE: capping Groq calls at {MAX_GROQ_CALLS}; "
            f"skipping {skipped} survivor(s) to preserve quota.\n"
        )

    ok = 0
    errors = 0
    for i, t in enumerate(to_process, 1):
        text = t["text"]
        shown = text[:TEXT_TRUNCATE] + ("…" if len(text) > TEXT_TRUNCATE else "")
        print(f"[{i}/{len(to_process)}] @{t['account_handle']}  ({t['created_at_utc']})")
        print(f"    tweet:   {shown!r}")
        print(f"    tickers: {t['tickers']}")
        try:
            result = call_groq(text, api_key)
            print(f"    groq:    {json.dumps(result, ensure_ascii=False)}")
            ok += 1
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:300]
            print(f"    ERROR (HTTP {e.code}): {detail}")
            errors += 1
        except Exception as e:  # noqa: BLE001 — per-tweet resilience, keep going
            print(f"    ERROR: {type(e).__name__}: {e}")
            errors += 1
        print("-" * 72)

        # Politeness delay between calls (skip after the last one).
        if i < len(to_process):
            time.sleep(DELAY_SECONDS)

    print("=" * 72)
    print(
        f"Done. Groq calls attempted: {len(to_process)}  "
        f"(ok: {ok}, errors: {errors}, skipped by cap: {skipped})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
