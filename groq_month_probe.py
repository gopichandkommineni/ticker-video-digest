#!/usr/bin/env python3
"""groq_month_probe.py — read-only 30-day descriptive analysis probe (Groq).

Groq twin of gemini_month_probe.py. Same contract: DESCRIPTIVE ANALYSIS ONLY
(no buy signals, no recommendations), read-only on data/fintwit.db, prints to
terminal AND writes a markdown report + a resumable thesis ledger.

Stages:
  1. Pull & count (free)        — 30-day volume + cashtag ratio.
  2. Per-handle profile (free)  — deterministic ticker frequency per handle.
  3. Sector grouping (LLM)      — ONE call maps unique tickers -> sector
                                  (probe-only; production uses a static map).
  4. Thesis extraction (LLM)    — {thesis, claim{falsifiable,horizon,checkpoint},
                                  stance} per ticker-bearing tweet, batched +
                                  resumable via thesis.jsonl.

Groq notes (free tier, org-level — extra keys do NOT raise limits):
  llama-3.1-8b-instant : 30 RPM / 14,400 RPD / 6,000 TPM / 500,000 TPD
  llama-3.3-70b-versatile: 30 RPM / 1,000 RPD / 12,000 TPM / 100,000 TPD
  A 429 may come from any of RPM/RPD/TPM/TPD. Responses carry x-ratelimit-*
  headers and retry-after. TPM is the binding throttle for bulk extraction, so
  we pace by tokens and honor retry-after.

Usage:  GROQ_API_KEY=... python groq_month_probe.py
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
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
# 8b-instant: highest free RPD/TPD -> right model for bulk thesis extraction.
THESIS_MODEL = "llama-3.1-8b-instant"
# 70b: one sector call, favor quality over throughput there.
SECTOR_MODEL = "llama-3.3-70b-versatile"

# Sized so one call stays well under 8b TPM (6,000): ~30 tweets * (~70 in + ~60
# out) + prompt ≈ 5k tokens/call. Pace keeps us under TPM across the minute.
BATCH_SIZE = 30
BATCH_TEXT_TRUNCATE = 300
DELAY_SECONDS = 2.5            # base pace; raised dynamically from headers/429
MAX_LLM_CALLS = 200            # generous backstop (free RPD is 14,400)
REQUEST_TIMEOUT = 90
RETRY_AFTER_CAP = 75           # never sleep longer than this on a single 429
MAX_BATCH_RETRIES = 4         # transient/429 retries per batch

REPORT_DIR = Path(__file__).parent / "probes" / "groq_digest" / "30d_rolling"
REPORT_PATH = REPORT_DIR / "report.md"
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
Return STRICT JSON: an object {{"results": [...]}} whose "results" array has one
object per input tweet, echoing each "id", each EXACTLY:
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

Return ONLY the JSON object.

Tweets:
{tweets_json}
"""


# --- DB (read-only) ----------------------------------------------------------

def fetch_recent_tweets(db_path: Path, days_back: int) -> list[dict]:
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
    seen: dict[str, None] = {}
    for m in CASHTAG_RE.findall(text or ""):
        seen.setdefault(m, None)
    return list(seen)


# --- Helpers -----------------------------------------------------------------

def _oneline(s: object) -> str:
    return " ".join(str(s).split())


def _chunk(items: list, n: int):
    for i in range(0, len(items), n):
        yield items[i:i + n]


def _strip_fences(s: str) -> str:
    s = s.strip()
    if s.startswith("```"):
        s = s.split("\n", 1)[1] if "\n" in s else s[3:]
        if s.rstrip().endswith("```"):
            s = s.rstrip()[:-3]
    return s.strip()


def load_ledger(path: Path) -> dict[str, dict]:
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
    if not records:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")


# --- Groq (OpenAI-compatible) ------------------------------------------------

class RateLimited(Exception):
    """HTTP 429. Carries retry_after seconds (float) when the header is present."""

    def __init__(self, message: str, retry_after: float = 0.0) -> None:
        super().__init__(message)
        self.retry_after = retry_after


def _parse_retry_after(headers) -> float:
    ra = headers.get("retry-after")
    if ra:
        try:
            return float(ra)
        except ValueError:
            pass
    # Groq also exposes x-ratelimit-reset-* like "7.66s" / "2m59s".
    for key in ("x-ratelimit-reset-tokens", "x-ratelimit-reset-requests"):
        v = headers.get(key)
        if not v:
            continue
        m = re.findall(r"(\d+(?:\.\d+)?)\s*([dhms])", v)
        if m:
            mult = {"d": 86400, "h": 3600, "m": 60, "s": 1}
            return sum(float(n) * mult[u] for n, u in m)
    return 0.0


def groq_json(prompt: str, api_key: str, model: str) -> tuple[dict, dict]:
    """One Groq chat-completion in JSON mode. Returns (parsed, headers).

    Raises RateLimited on 429 (with retry_after); re-raises other HTTPErrors.
    """
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "response_format": {"type": "json_object"},
    }
    req = urllib.request.Request(
        GROQ_URL,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            # Cloudflare 403s the default Python-urllib UA (error 1010); send a
            # normal UA so requests are accepted.
            "User-Agent": "ticker-digest-probe/1.0 (+groq)",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            headers = {k.lower(): v for k, v in resp.headers.items()}
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        hdrs = {k.lower(): v for k, v in e.headers.items()}
        if e.code == 429:
            raise RateLimited(
                e.read().decode("utf-8", "replace")[:200],
                retry_after=_parse_retry_after(hdrs),
            ) from e
        raise
    text = payload["choices"][0]["message"]["content"]
    return json.loads(_strip_fences(text)), headers


# --- Report helper -----------------------------------------------------------

class Report:
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
    api_key = os.environ.get("GROQ_API_KEY")
    if not DB_PATH.exists():
        print(f"ERROR: DB not found at {DB_PATH}", file=sys.stderr)
        return 1

    R = Report()
    R("# Groq 30-Day Probe Report")
    R()
    R("**DESCRIPTIVE ANALYSIS ONLY — not investment advice.** Measures what")
    R("handles are *posting* (volume, ticker frequency, sector concentration).")
    R("No buy signals, no ranking by attractiveness, no recommendations.")
    R()
    R(f"- Database: `{DB_PATH.name}` · table `raw_tweets` (read-only)")
    R(f"- Window: last {DAYS_BACK} days")
    R(f"- Provider: Groq · thesis `{THESIS_MODEL}` · sector `{SECTOR_MODEL}`")
    R()

    # ---- Stage 1: pull & count ---------------------------------------------
    tweets = fetch_recent_tweets(DB_PATH, DAYS_BACK)
    for t in tweets:
        t["tickers"] = extract_cashtags(t["text"])
    ticker_bearing = [t for t in tweets if t["tickers"]]
    total, bearing = len(tweets), len([t for t in tweets if t["tickers"]])
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
        R("No tweets in window.")
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
        mentions = ", ".join(f"{tk} ({n})"
                             for tk, n in handle_tickers[h].most_common())
        R(f"- **@{h}** — {handle_total[h]} tweets, "
          f"{handle_bearing[h]} ticker-bearing; {mentions}")
    R()

    unique_tickers = sorted({tk for c in handle_tickers.values() for tk in c})
    overall_ticker_freq: Counter = Counter()
    for c in handle_tickers.values():
        overall_ticker_freq.update(c)

    succeeded = 0
    rate_limited = 0
    llm_calls = 0

    # ---- Stage 3: sector grouping (ONE LLM call, cached) -------------------
    R("## Stage 3 — Sector grouping (LLM, probe-only)")
    R()
    R("> ⚠️ **Probe-only.** Sectors are assigned by a single Groq call and the")
    R("> model can miscategorize. Production would use a deterministic map.")
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
        R("_GROQ_API_KEY not set — Stage 3 & 4 skipped._")
    elif cached_sectors:
        sector_map = {tk: cached_sectors.get(tk, "unmapped") for tk in unique_tickers}
        R("_Sector map loaded from cache (`sectors.json`); no call spent._")
    elif unique_tickers:
        sector_prompt = SECTOR_PROMPT.format(tickers=", ".join(unique_tickers))
        for attempt in range(MAX_BATCH_RETRIES):
            try:
                llm_calls += 1
                raw, _ = groq_json(sector_prompt, api_key, SECTOR_MODEL)
                succeeded += 1
                norm = {(k if k.startswith("$") else f"${k}").upper(): str(v)
                        for k, v in raw.items()}
                for tk in unique_tickers:
                    sector_map[tk] = norm.get(tk.upper(), "unmapped")
                SECTOR_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
                SECTOR_CACHE_PATH.write_text(
                    json.dumps(sector_map, ensure_ascii=False, indent=2), "utf-8")
                break
            except RateLimited as e:
                rate_limited += 1
                wait = min(e.retry_after or DELAY_SECONDS * 2, RETRY_AFTER_CAP)
                print(f"[sector] 429 (attempt {attempt + 1}); sleeping {wait:.0f}s")
                time.sleep(wait)
            except Exception as e:  # noqa: BLE001
                print(f"[sector] ERROR (attempt {attempt + 1}): {e}")
                time.sleep(DELAY_SECONDS * (attempt + 1))
        if not sector_map:
            R("_Stage 3 could not complete (rate-limited); sector rollups "
              "deferred to a later run._")
        time.sleep(DELAY_SECONDS)

    if sector_map:
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

    # ---- Stage 4: thesis extraction (batched, resumable) -------------------
    R("## Stage 4 — Thesis extraction (LLM, ticker-bearing only)")
    R()
    R("Descriptive structure per tweet: thesis, whether the claim is")
    R("falsifiable, its horizon and a checkpoint, and the stance.")
    R()
    R(f"Batched **{BATCH_SIZE}/call** on `{THESIS_MODEL}`, paced under the")
    R("free-tier TPM; every 429 honors `retry-after` and the run continues.")
    R()

    stance_counts: Counter = Counter()
    ledger = load_ledger(LEDGER_PATH)
    done_before = len(ledger)
    if not api_key:
        R("_GROQ_API_KEY not set — Stage 4 skipped._")
    else:
        todo = [t for t in ticker_bearing if str(t["tweet_id"]) not in ledger]
        R(f"_Ledger (`{LEDGER_PATH.name}`): {done_before} already extracted; "
          f"**{len(todo)}** remaining this run._")
        R()
        batches = list(_chunk(todo, BATCH_SIZE))

        def run_batch(bi: int, batch: list[dict]) -> bool:
            """Process one batch with bounded 429/transient retries."""
            nonlocal succeeded, rate_limited, llm_calls
            payload = [
                {"id": j, "text": (t["text"] or "")[:BATCH_TEXT_TRUNCATE]}
                for j, t in enumerate(batch)
            ]
            prompt = THESIS_PROMPT.format(
                tweets_json=json.dumps(payload, ensure_ascii=False))
            for attempt in range(MAX_BATCH_RETRIES):
                if llm_calls >= MAX_LLM_CALLS:
                    return False
                try:
                    llm_calls += 1
                    parsed, _ = groq_json(prompt, api_key, THESIS_MODEL)
                    succeeded += 1
                    if isinstance(parsed, dict):
                        parsed = next(
                            (v for v in parsed.values() if isinstance(v, list)),
                            [])
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
                    print(f"[batch {bi}] {len(batch)} tweets -> "
                          f"{len(new_recs)} parsed")
                    return True
                except RateLimited as e:
                    rate_limited += 1
                    wait = min(e.retry_after or DELAY_SECONDS * 2, RETRY_AFTER_CAP)
                    print(f"[batch {bi}] 429 (attempt {attempt + 1}); "
                          f"sleeping {wait:.0f}s")
                    time.sleep(wait)
                except Exception as e:  # noqa: BLE001 — transient; backoff+retry
                    print(f"[batch {bi}] ERROR (attempt {attempt + 1}): {e}")
                    time.sleep(DELAY_SECONDS * (attempt + 1))
            return False

        failed = 0
        for bi, batch in enumerate(batches, 1):
            if not run_batch(bi, batch):
                failed += 1
                R(f"_Batch {bi} ({len(batch)} tweets) not recovered "
                  f"(429/transient/budget); ledger lets a later run retry._")
            time.sleep(DELAY_SECONDS)

    # Build table from the full ledger union, newest first.
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
    R(f"- Groq calls attempted: **{llm_calls}**")
    R(f"- succeeded: **{succeeded}**  ·  rate-limited (429): **{rate_limited}**")
    R(f"- Stage 1–2 are deterministic and always complete (no LLM).")
    R()
    R("_Read-only run. No database writes, no schema changes. "
      "Descriptive analysis only — not investment advice._")

    R.save(REPORT_PATH)
    print(f"\nMarkdown report written to: {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
