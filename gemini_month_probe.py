#!/usr/bin/env python3
"""gemini_month_probe.py — read-only 30-day descriptive analysis probe.

DESCRIPTIVE ANALYSIS ONLY. This probe measures what handles are *posting*.
It is NOT investment advice: no buy signals, no ranking of tickers by
attractiveness, no "best picks", no recommendations. The reader draws their
own conclusions from the concentration data.

Read-only on the SQLite DB. No DB writes, no schema changes, no new tables.
Prints to the terminal AND writes a single markdown report.

Stages:
  1. Pull & count (free)        — 30-day volume + cashtag ratio.
  2. Per-handle profile (free)  — deterministic ticker frequency per handle.
  3. Sector grouping (LLM)      — ONE Gemini call maps unique tickers -> sector.
                                  PROBE-ONLY; production would use a
                                  deterministic ticker->sector map.
  4. Thesis extraction (LLM)    — {thesis, claim{falsifiable,horizon,checkpoint},
                                  stance} per ticker-bearing tweet, capped at 50.

Usage:  GEMINI_API_KEY=... python gemini_month_probe.py
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
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

# --- Config -----------------------------------------------------------------

DB_PATH = Path(__file__).parent / "data" / "fintwit.db"
DAYS_BACK = 30
GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    f"{GEMINI_MODEL}:generateContent"
)
BATCH_SIZE = 50                # Stage 4 tweets per Gemini call (batched)
MAX_THESIS_BATCHES = 18        # safety cap so Stage3(1)+Stage4 stays < 20/day free tier
MAX_LLM_CALLS = 19             # hard daily budget guard (free tier = 20/day/model)
BATCH_TEXT_TRUNCATE = 300      # per-tweet chars sent inside a batch (smaller = faster)
DELAY_SECONDS = 4.5            # politeness: keep under 15 req/min on free tier
REQUEST_TIMEOUT = 150          # large batched responses are slow; allow headroom
RUN_DATE = datetime.now(timezone.utc).strftime("%Y-%m-%d")
REPORT_DIR = Path(__file__).parent / "probes" / "gemini_digest" / f"{RUN_DATE}_30d"
REPORT_PATH = REPORT_DIR / "report.md"
# Resumable ledger: one JSON line per tweet_id already extracted, so re-runs
# only process uncovered tweets (no DB writes — a file artifact in the probe).
LEDGER_PATH = REPORT_DIR / "thesis.jsonl"
SECTOR_CACHE_PATH = REPORT_DIR / "sectors.json"

CASHTAG_RE = re.compile(r"\$[A-Z]{1,5}\b")

SECTOR_PROMPT = """You are mapping stock tickers to broad market sectors.

For EACH ticker below, return its primary sector using a concise lowercase
label (examples: semiconductors, memory, optical/photonics, space, biotech,
ai infrastructure, software, internet, automotive, telecom, etf, other).

Return STRICT JSON: a single object mapping each ticker string (keep the
leading $) to a sector string. No commentary, no extra keys.

Tickers:
{tickers}
"""

THESIS_PROMPT = """You are analyzing financial tweets. Describe each; do not
give advice.

Do NOT extract tickers — that is already done deterministically.

You will receive a JSON array of tweets, each with an integer "id" and "text".
Return STRICT JSON: an array of the SAME length, one object per input tweet,
echoing each "id". Each object must have EXACTLY these fields:
{{
  "id": <the input id>,
  "thesis": "<one sentence stating the claim being made, or \\"none\\">",
  "claim": {{
    "falsifiable": <true or false: could this be proven wrong by an observable outcome>,
    "horizon": "<timeframe over which the claim would resolve, or \\"none\\">",
    "checkpoint": "<one observable event that would confirm or refute it, or \\"none\\">"
  }},
  "stance": "<one of: prediction, news, opinion, question, promotion, other>"
}}

Return ONLY the JSON array, nothing else.

Tweets:
{tweets_json}
"""


# --- DB (read-only) ----------------------------------------------------------

def fetch_recent_tweets(db_path: Path, days_back: int) -> list[dict]:
    """Read non-deleted tweets from the last `days_back` days. Read-only."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
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


def extract_cashtags(text: str) -> list[str]:
    """Deterministic cashtag extraction, order-preserving & de-duplicated."""
    seen: dict[str, None] = {}
    for m in CASHTAG_RE.findall(text or ""):
        seen.setdefault(m, None)
    return list(seen)


# --- Gemini ------------------------------------------------------------------

class RateLimited(Exception):
    """Raised on HTTP 429 so callers can count and continue."""


def _oneline(s: object) -> str:
    """Collapse whitespace/newlines so error blobs stay on one markdown line."""
    return " ".join(str(s).split())


def _chunk(items: list, n: int):
    for i in range(0, len(items), n):
        yield items[i:i + n]


def load_ledger(path: Path) -> dict[str, dict]:
    """Load already-extracted thesis records keyed by tweet_id."""
    if not path.exists():
        return {}
    out: dict[str, dict] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
            out[str(rec["tweet_id"])] = rec
        except (json.JSONDecodeError, KeyError):
            continue
    return out


def append_ledger(path: Path, records: list[dict]) -> None:
    """Append thesis records as JSON lines (idempotent caller skips dupes)."""
    if not records:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")


def _strip_fences(s: str) -> str:
    s = s.strip()
    if s.startswith("```"):
        s = s.split("\n", 1)[1] if "\n" in s else s[3:]
        if s.rstrip().endswith("```"):
            s = s.rstrip()[:-3]
    return s.strip()


def gemini_json(prompt: str, api_key: str) -> dict:
    """Single Gemini call returning parsed JSON. Raises RateLimited on 429."""
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.0,
            "responseMimeType": "application/json",
        },
    }
    req = urllib.request.Request(
        f"{GEMINI_URL}?key={api_key}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 429:
            raise RateLimited(e.read().decode("utf-8", "replace")[:200]) from e
        raise
    text = body["candidates"][0]["content"]["parts"][0]["text"]
    return json.loads(_strip_fences(text))


# --- Report helper -----------------------------------------------------------

class Report:
    """Accumulates markdown lines and mirrors them to the terminal."""

    def __init__(self) -> None:
        self.lines: list[str] = []

    def __call__(self, line: str = "") -> None:
        print(line)
        self.lines.append(line)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(self.lines) + "\n", encoding="utf-8")


# --- Main --------------------------------------------------------------------

def main() -> int:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not DB_PATH.exists():
        print(f"ERROR: DB not found at {DB_PATH}", file=sys.stderr)
        return 1

    R = Report()
    R("# Gemini 30-Day Probe Report")
    R()
    R("**DESCRIPTIVE ANALYSIS ONLY — not investment advice.** This report")
    R("measures what handles are *posting*: volume, ticker frequency, and")
    R("sector concentration. It contains no buy signals, no ranking of tickers")
    R("by attractiveness, and no recommendations. The reader draws their own")
    R("conclusions from the concentration data.")
    R()
    R(f"- Database: `{DB_PATH.name}` · table `raw_tweets` (read-only)")
    R(f"- Window: last {DAYS_BACK} days")
    R(f"- Model: `{GEMINI_MODEL}` (Stages 3 & 4 only)")
    R()

    # ---- Stage 1: pull & count ---------------------------------------------
    tweets = fetch_recent_tweets(DB_PATH, DAYS_BACK)
    for t in tweets:
        t["tickers"] = extract_cashtags(t["text"])
    ticker_bearing = [t for t in tweets if t["tickers"]]

    total = len(tweets)
    bearing = len(ticker_bearing)
    ratio = (bearing / total * 100) if total else 0.0

    R("## Stage 1 — Volume (free, no LLM)")
    R()
    R("| Metric | Count |")
    R("|---|---:|")
    R(f"| Total non-deleted tweets (last {DAYS_BACK}d) | {total} |")
    R(f"| Ticker-bearing tweets (cashtag regex) | {bearing} |")
    R(f"| Ratio | {ratio:.1f}% |")
    R()

    if total == 0:
        R("No tweets in window. Nothing to analyze.")
        R.save(REPORT_PATH)
        return 0

    # ---- Stage 2: per-handle profile ---------------------------------------
    handle_total: Counter = Counter()
    handle_bearing: Counter = Counter()
    handle_tickers: dict[str, Counter] = defaultdict(Counter)

    for t in tweets:
        h = t["account_handle"]
        handle_total[h] += 1
        if t["tickers"]:
            handle_bearing[h] += 1
            for tk in t["tickers"]:
                handle_tickers[h][tk] += 1

    R("## Stage 2 — Per-handle ticker profile (free, no LLM)")
    R()
    R("Deterministic counts. Handles sorted by ticker-bearing tweet volume.")
    R()
    for h, _ in handle_bearing.most_common():
        freq = handle_tickers[h]
        mentions = ", ".join(f"{tk} ({n})" for tk, n in freq.most_common())
        R(f"- **@{h}** — {handle_total[h]} tweets, "
          f"{handle_bearing[h]} ticker-bearing; {mentions}")
    # Handles with no cashtags at all (still part of the corpus).
    silent = [h for h in handle_total if handle_bearing[h] == 0]
    if silent:
        R()
        R(f"_Handles with no cashtag tweets in window: "
          f"{', '.join('@' + h for h in silent)}_")
    R()

    # Unique ticker set across all handles.
    unique_tickers = sorted({tk for c in handle_tickers.values() for tk in c})
    overall_ticker_freq: Counter = Counter()
    for c in handle_tickers.values():
        overall_ticker_freq.update(c)

    # Track LLM call accounting across stages 3 & 4. `llm_calls` counts every
    # attempt (incl. retries) and enforces the free-tier daily budget.
    succeeded = 0
    rate_limited = 0
    llm_calls = 0

    # ---- Stage 3: sector grouping (ONE LLM call) ---------------------------
    R("## Stage 3 — Sector grouping (LLM, probe-only)")
    R()
    R("> ⚠️ **Probe-only.** Sectors below are assigned by a single Gemini call")
    R("> and the model can miscategorize. In production this would be replaced")
    R("> by a deterministic ticker→sector map.")
    R()
    R(f"Unique tickers across all handles: **{len(unique_tickers)}**")
    R()

    sector_map: dict[str, str] = {}
    cached_sectors = {}
    if SECTOR_CACHE_PATH.exists():
        try:
            cached_sectors = json.loads(SECTOR_CACHE_PATH.read_text("utf-8"))
        except json.JSONDecodeError:
            cached_sectors = {}
    if not api_key:
        R("_GEMINI_API_KEY not set — Stage 3 & 4 skipped._")
    elif cached_sectors:
        # Reuse a prior sector call; spend no quota.
        sector_map = {tk: cached_sectors.get(tk, "unmapped") for tk in unique_tickers}
        R("_Sector map loaded from cache (`sectors.json`); no Gemini call spent._")
    elif unique_tickers:
        prompt = SECTOR_PROMPT.format(tickers=", ".join(unique_tickers))
        try:
            llm_calls += 1
            raw = gemini_json(prompt, api_key)
            succeeded += 1
            # Normalize keys: keep $ prefix, upper-case, match our set.
            norm = { (k if k.startswith("$") else f"${k}").upper(): str(v)
                     for k, v in raw.items() }
            for tk in unique_tickers:
                sector_map[tk] = norm.get(tk.upper(), "unmapped")
            SECTOR_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
            SECTOR_CACHE_PATH.write_text(
                json.dumps(sector_map, ensure_ascii=False, indent=2), "utf-8")
        except RateLimited as e:
            rate_limited += 1
            R(f"_Stage 3 rate-limited (HTTP 429): {_oneline(e)[:160]}_")
            R("_Sector rollups below are unavailable for this run._")
        except Exception as e:  # noqa: BLE001
            R(f"_Stage 3 failed: {type(e).__name__}: {e}_")
        time.sleep(DELAY_SECONDS)

    if sector_map:
        # Overall sector concentration (by total mentions).
        sector_mentions: Counter = Counter()
        for tk, n in overall_ticker_freq.items():
            sector_mentions[sector_map.get(tk, "unmapped")] += n

        R()
        R("### Overall sector concentration (by total mentions)")
        R()
        R("| Sector | Mentions | Tickers |")
        R("|---|---:|---|")
        for sec, n in sector_mentions.most_common():
            tks = sorted(tk for tk in unique_tickers if sector_map.get(tk) == sec)
            R(f"| {sec} | {n} | {', '.join(tks)} |")
        R()

        R("### Per-handle sector concentration (by mentions)")
        R()
        for h, _ in handle_bearing.most_common():
            per_sec: Counter = Counter()
            for tk, n in handle_tickers[h].items():
                per_sec[sector_map.get(tk, "unmapped")] += n
            dist = ", ".join(f"{sec} ({n})" for sec, n in per_sec.most_common())
            R(f"- **@{h}** — {dist}")
        R()

    # ---- Stage 4: thesis extraction (LLM, filtered, capped) ----------------
    R("## Stage 4 — Thesis extraction (LLM, ticker-bearing only)")
    R()
    R("Descriptive structure per tweet: thesis, whether the claim is")
    R("falsifiable, its horizon and a checkpoint, and the stance. No judgement")
    R("of whether the claim is *good*.")
    R()

    R(f"Tweets are batched **{BATCH_SIZE} per Gemini call** so the full month")
    R("fits within the free-tier daily request cap (one per-tweet call would not).")
    R()

    stance_counts: Counter = Counter()
    ledger = load_ledger(LEDGER_PATH)          # {tweet_id: record} from prior runs
    done_before = len(ledger)
    if not api_key:
        R("_GEMINI_API_KEY not set — Stage 4 skipped._")
    else:
        # Resume: only process tweets not already in the ledger.
        todo = [t for t in ticker_bearing if str(t["tweet_id"]) not in ledger]
        R(f"_Ledger (`{LEDGER_PATH.name}`): {done_before} tweet(s) already "
          f"extracted; **{len(todo)}** remaining this run._")
        R()
        # Batch the remainder; bound batches as a daily-quota backstop.
        batches = list(_chunk(todo, BATCH_SIZE))[:MAX_THESIS_BATCHES]
        covered = sum(len(b) for b in batches)
        skipped = len(todo) - covered
        if skipped > 0:
            R(f"_Batch backstop: processing {len(batches)} batches "
              f"({covered} tweets); {skipped} remaining tweet(s) deferred to a "
              f"later run to stay under the daily quota._")
            R()

        def run_batch(bi: int, batch: list[dict], label: str) -> bool:
            """Process one batch; append results to the ledger. False ⇒ retry."""
            nonlocal succeeded, rate_limited, llm_calls
            payload = [
                {"id": j, "text": (t["text"] or "")[:BATCH_TEXT_TRUNCATE]}
                for j, t in enumerate(batch)
            ]
            prompt = THESIS_PROMPT.format(
                tweets_json=json.dumps(payload, ensure_ascii=False)
            )
            try:
                llm_calls += 1
                parsed = gemini_json(prompt, api_key)
                succeeded += 1
                # Accept a bare list, or a dict wrapping one list value.
                if isinstance(parsed, dict):
                    parsed = next(
                        (v for v in parsed.values() if isinstance(v, list)), []
                    )
                by_id = {int(o["id"]): o for o in parsed
                         if isinstance(o, dict) and "id" in o}
                new_recs = []
                for j, t in enumerate(batch):
                    res = by_id.get(j)
                    if not res:
                        continue
                    claim = res.get("claim", {}) or {}
                    rec = {
                        "tweet_id": str(t["tweet_id"]),
                        "handle": t["account_handle"],
                        "created": t["created_at_utc"],
                        "tickers": t["tickers"],
                        "thesis": res.get("thesis", ""),
                        "claim": {
                            "falsifiable": claim.get("falsifiable"),
                            "horizon": claim.get("horizon"),
                            "checkpoint": claim.get("checkpoint"),
                        },
                        "stance": str(res.get("stance", "")).strip().lower(),
                    }
                    ledger[rec["tweet_id"]] = rec
                    new_recs.append(rec)
                append_ledger(LEDGER_PATH, new_recs)
                print(f"[{label} {bi}] {len(batch)} tweets -> "
                      f"{len(new_recs)} parsed")
                return True
            except RateLimited as e:
                rate_limited += 1
                print(f"[{label} {bi}] RATE-LIMITED (429)")
                R(f"_Batch {bi} rate-limited (HTTP 429): {_oneline(e)[:120]}_")
                return False
            except Exception as e:  # noqa: BLE001 — transient; eligible for retry
                print(f"[{label} {bi}] ERROR: {e}")
                return False

        # First pass over all batches.
        failed: list[tuple[int, list[dict]]] = []
        for bi, batch in enumerate(batches, 1):
            if not run_batch(bi, batch, "batch"):
                failed.append((bi, batch))
            if bi < len(batches):
                time.sleep(DELAY_SECONDS)

        # Retry pass for transient failures, bounded by the daily call budget.
        if failed and llm_calls < MAX_LLM_CALLS:
            R(f"_Retrying {len(failed)} failed batch(es) "
              f"(transient timeout/5xx); {MAX_LLM_CALLS - llm_calls} calls of "
              f"daily budget remain._")
            R()
            still_failed = []
            for bi, batch in failed:
                if llm_calls >= MAX_LLM_CALLS:
                    still_failed.append((bi, batch))
                    continue
                time.sleep(DELAY_SECONDS)
                if not run_batch(bi, batch, "retry"):
                    still_failed.append((bi, batch))
            failed = still_failed

        if failed:
            lost = sum(len(b) for _, b in failed)
            R(f"_Note: {len(failed)} batch(es) (~{lost} tweets) not recovered "
              f"this run (transient errors / budget); the ledger lets a later "
              f"run pick them up._")
            R()

    # Build the table from the FULL ledger union (all runs), newest first.
    all_recs = sorted(ledger.values(), key=lambda r: r.get("created", ""),
                      reverse=True)
    for rec in all_recs:
        stance_counts[rec.get("stance", "")] += 1
    added = len(ledger) - done_before
    R()
    R(f"Thesis ledger now holds **{len(all_recs)}** of {bearing} ticker-bearing "
      f"tweets (**+{added}** this run).")
    R()
    if stance_counts:
        R("Stance distribution: "
          + ", ".join(f"{s or '(blank)'} ({n})"
                      for s, n in stance_counts.most_common()))
        R()
    if all_recs:
        R("| Handle | Tickers | Stance | Falsifiable | Horizon | Thesis |")
        R("|---|---|---|---|---|---|")
        for rec in all_recs:
            claim = rec.get("claim", {}) or {}
            thesis = _oneline(rec.get("thesis", "")).replace("|", "\\|")
            horizon = _oneline(claim.get("horizon", "")).replace("|", "\\|")
            R(f"| @{rec['handle']} | {', '.join(rec.get('tickers', []))} | "
              f"{rec.get('stance', '')} | {claim.get('falsifiable', '')} | "
              f"{horizon} | {thesis} |")
        R()

    # ---- Run summary --------------------------------------------------------
    R("## Run summary")
    R()
    R(f"- Gemini calls attempted: **{llm_calls}** (daily free-tier budget: "
      f"{MAX_LLM_CALLS})")
    R(f"- Gemini calls succeeded: **{succeeded}**")
    R(f"- Gemini calls rate-limited (429): **{rate_limited}**")
    R(f"- Stage 1–2 are deterministic and always complete (no LLM).")
    R()
    R("_Read-only run. No database writes, no schema changes. "
      "Descriptive analysis only — not investment advice._")

    R.save(REPORT_PATH)
    print(f"\nMarkdown report written to: {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
