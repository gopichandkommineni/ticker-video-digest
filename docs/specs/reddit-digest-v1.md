# Reddit Daily Digest — v1

**Project:** Casino-Coherent Momentum Dashboard / Reddit
**Date drafted:** 2026-09-27
**Status:** Implemented. The Claude CLI path was run end to end on demo posts
(2026-09-27); not yet run on live Reddit data. Switch on with the
`CLAUDE_CODE_OAUTH_TOKEN` or `GEMINI_API_KEY` repository secret.
**Builds on:** [reddit-ingestion-v1](reddit-ingestion-v1.md) (the posts it reads)

---

## 1. What it is for

Every day, for each stock, answer two questions on its Ticker Detail page:

1. **What is Reddit talking about?** — a 1–3 sentence brief and an overall mood.
2. **Is there anything worth reading?** — a short list of concrete insights
   (a contract, a release, earnings or guidance, a thesis someone laid out, a
   risk…), each with a link to the post(s) it came from.

## 2. Which LLM, and why

Requirement: **no extra spend**, and able to handle one summary per stock per
day (64 stocks, each call ~5–15k tokens of posts in). Two clients share one
interface (`generate_json(system, prompt, schema)`), picked by
`REDDIT_DIGEST_LLM` (`auto` = Claude if the CLI is installed, else Gemini).

### 2a. Claude Code CLI on a Claude subscription (`digest/claude_cli.py`)

The owner already pays for Claude Pro. `claude -p` (print mode) is the same
Claude Code CLI, answering once and exiting, and it runs on the account it is
signed in as: a laptop's own login, or in GitHub Actions the
`CLAUDE_CODE_OAUTH_TOKEN` that `claude setup-token` prints. Calls count
against the plan's usage limits (5-hour and weekly, shared with the owner's
own Claude use), **not** per-token API billing.

- **Never the API.** Claude Code prefers an `ANTHROPIC_API_KEY` over the
  subscription, and the workflow sets one for other jobs. The client removes
  `ANTHROPIC_API_KEY` / `ANTHROPIC_AUTH_TOKEN` from the CLI's environment.
- **Answer only.** `--tools ""`: the model can't read files or run commands,
  which matters because posts are untrusted and the job can push to the
  repo. `--setting-sources ""`, `--strict-mcp-config` and
  `--disable-slash-commands` keep local settings, MCP servers and skills out.
- **Structured output.** The same schema goes on `--json-schema` (type names
  lower-cased from Gemini's dialect); the answer is read from the envelope's
  `structured_output`.
- **Model.** `haiku` by default, to go easy on the plan's allowance;
  `REDDIT_DIGEST_CLAUDE_MODEL=sonnet` for more depth. About 30–60 s per stock;
  no pacing needed between calls.
- **Stops.** A plan usage limit (`QuotaExhausted`), a sign-in problem or a CLI
  that gives no result at all (`LLMFatal`) stop the run like Gemini's fatal
  errors; a timeout or odd answer fails that stock only.

### 2b. Gemini free tier (`digest/gemini.py`)

The repository already measured this. The `research/probes/gemini_digest` and
`groq_digest` probes ran the same summarisation job on both free tiers:

| Free tier | Measured | Why |
|---|---|---|
| Gemini 2.5 Flash | Strict JSON every time, but **stopped at ~20 calls/day** (HTTP 429, daily limit) | Since Google's Dec-2025 cut, full Flash gets ~20 requests/day on the free tier — too few for 64 stocks |
| Groq, Llama 3.3 70B | Throttled on batched prompts | ~12k tokens-per-minute bucket; one digest-sized prompt nearly empties it (and the model has since left Groq's free tier) |

**Gemini default: Flash-Lite.** The model is
**`gemini-flash-lite-latest`**, Google's moving alias for the current
Flash-Lite model, whose free tier allows several hundred requests a day
(reported Sep 2026; Google shows each project's real limits in AI Studio).
An alias rather than a version, because by September 2026 Google already
refused `gemini-2.5-flash` for new keys ("no longer available to new users") —
a pinned version is a scheduled breakage. Pin one on purpose with the
`REDDIT_DIGEST_MODEL` repository variable. Plain HTTPS to `generateContent`
with a response schema, so the answer is JSON that parses (`digest/gemini.py`).

Free-tier caveats, accepted: limits are set by Google and change; free-tier
prompts may be used to improve Google's products — the input is public Reddit
posts, so nothing private is sent.

## 3. One run

Runs in `reddit_ingest.yml` right after ingestion (same job, same commit):

```
for each stock:
  posts = this stock's posts first seen since the previous day's digest
          (first digest: last 7 days), ≤ 7 days old, busiest first, ≤ 30
  none  → "quiet" digest ("No new Reddit posts…"), no LLM call
  else  → one LLM call (Claude CLI or Gemini):
            in:  [P1] r/sub · score · comments · date / title / body (≤1,200 chars)
                 + top 5 comments (≤300 chars each), for each post
            out: {summary, mood, insights[{headline, detail, kind, stance, sources[P#]}]}
          → resolve P# tags to real posts in code; drop insights with no real source
          → save to reddit.db
```

- **Links are never written by the model.** It cites tags; code maps tags to
  stored posts and their URLs. An unknown tag is ignored; an insight left with
  no source is dropped.
- **Kinds:** contract, product, earnings, guidance, partnership, regulatory,
  analyst, thesis, risk, rumor, other. **Stance:** bullish / bearish / neutral.
- **At most 6 insights**, most important first. Price-only chatter, memes and
  empty questions are excluded by instruction; if nothing substantive was said
  the list is empty and the brief says so.
- **Prompt injection.** Post text is declared untrusted data in the system
  prompt; the output is constrained by the schema and rendered as escaped text.
- **Pacing.** Gemini: ~7 seconds between calls (free tier ≈ 10/minute); Claude: none. A per-minute
  429 is waited out using the server's retry delay. A **per-day** quota — or
  any error that would repeat for every stock (bad key, no billing credit,
  retired model, rejected request: any other 4xx) — stops the run at the
  first stock, with the reason in the report; remaining stocks are listed as
  skipped and the next run's window still covers their posts.
- **Failures.** One stock failing is recorded (`status=failed`) and the run
  continues. A failed digest doesn't count as read, so its posts are retried.
- **Re-running a day** rebuilds that day's digest from everything since the
  previous day's, and never replaces a good digest with a failed or quiet one.

## 4. Storage (`data/reddit.db`)

| Table | Holds |
|---|---|
| `digests` | one row per (stock, day): status `ok`/`quiet`/`failed`, model, posts considered, summary, mood, error |
| `insights` | the day's insights in order: kind, stance, headline, detail, and `sources` — JSON of each source post's id, URL, title, subreddit and score |

Sources are copied into the insight so links keep working after ingestion
prunes old or quiet posts. Digests are kept 90 days.

## 5. On the page

Ticker Detail → **What Reddit is saying** (above Recent News):

- mood chip + brief, then "date · from N new posts · summarised by <model>";
- each insight: **headline** — coloured tag (▲ green bullish, ▼ red bearish,
  • grey neutral) and kind; the detail; underneath, a clickable link per source
  post (`r/sub: title ↗`);
- earlier days of the week in an expander;
- the disclaimer: AI summary of public posts, can be wrong, read the linked
  posts, not investment advice.

All text from Reddit or the model is Markdown-escaped; only `https://` links
are rendered. The page reads `reddit.db` read-only and shows a short note when
there is no digest yet.

## 6. Operating it

- **Switch on:** add the repository secret **`CLAUDE_CODE_OAUTH_TOKEN`** (run
  `claude setup-token` on a computer signed in to the Claude subscription) —
  the workflow then installs the Claude Code CLI and uses it — or
  **`GEMINI_API_KEY`** (free key from Google AI Studio). Without either, the
  step prints "skipped" and the page says there is no digest yet.
- **Or on the owner's computer:** `./run reddit-brief install` schedules the
  Claude digest on a laptop's own Claude Code login (hourly check, runs once
  per GitHub collection, merges only digest rows into `main`'s reddit.db).
  Runbook §5e.
- **By hand:** `python -m casino_dashboard.jobs.reddit_digest RKLB` with
  `REDDIT_DB_PATH` pointing at a scratch copy, and either Claude Code signed
  in or `GEMINI_API_KEY` set.
- The run report (Actions → Summary) lists stocks digested, insight counts,
  quiet stocks, failures and any quota skip.

## 7. Not in v1

- Novelty against earlier days (the YouTube "new / developing / known"
  treatment). Today each day stands alone; the expander shows the week.
- Cross-stock views (e.g. "what's hot on Reddit today" on the Sector Heat page).
- A second free provider as automatic fallback.
