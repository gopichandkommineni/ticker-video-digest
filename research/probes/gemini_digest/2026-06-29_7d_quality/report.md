# Gemini Probe Report

**Script:** `gemini_probe.py` (throwaway quality probe — read-only, terminal output)
**Database:** `data/fintwit.db` · table `raw_tweets`
**Window:** last 7 days (run date 2026-06-29)
**Model:** `gemini-2.5-flash`

---

## Funnel

| Stage | Count |
|---|---:|
| Tweets pulled (last 7d, non-deleted) | **291** |
| Survived cashtag regex `\$[A-Z]{1,5}\b` | **70** (24.1%) |
| Sent to Gemini (capped at 50) | 50 |
| Skipped by 50-call cap | 20 |
| **Succeeded** | **22** |
| Failed — HTTP 429 quota (free-tier limit hit mid-run) | 28 |

> The 28 failures are **not code bugs**. The test key is free-tier; Gemini's
> rate/daily quota ran out at call #18. Per-tweet error isolation worked as
> designed — each 429 was caught and printed, and the run completed.

---

## Architecture validation

- **Regex owns ticker extraction, not the LLM** — confirmed. Gemini never
  extracted cashtags; multi-ticker tweets (e.g. a 15-ticker IBD list) were
  caught deterministically by regex.
- **Strict JSON every time** — all 22 successes parsed into exactly
  `{thesis, sentiment, stance}`; no fence-stripping fallbacks needed.
- **"none" handling is correct** — pure ticker-dumps and emoji-only tweets
  returned `thesis: "none"` rather than a hallucinated claim.
- **Multilingual** — a Japanese-language `$SIVE` tweet was summarized
  accurately into an English thesis.

---

## Distribution (n = 22 successful)

- **Sentiment:** bullish 21 · neutral 1 · bearish 0
- **Stance:** opinion 14 · prediction 6 · news 2

### ⚠️ Quality flag — sentiment has low discriminative power
21 of 22 tweets scored `bullish`. Much of that is real (these handles skew
long/momentum), but cautionary tweets also read as bullish. If sentiment is
going to drive anything downstream, the prompt needs sharper bearish/neutral
criteria or a confidence field.

---

## Successful summaries (22)

| # | Handle | Tickers (regex) | Sentiment | Stance | Thesis |
|---|---|---|---|---|---|
| 1 | spacanpanman | $RKLB | bullish | opinion | Rocket Lab's acquisition of Iridium will create a vertically integrated space powerhouse primed for growth. |
| 2 | aleabitoreddit | $ASTS, $SPCX | bullish | news | Rakuten's JV with ASTS to build LEO satellite networks in Japan is a strategic move that could enhance ASTS's market position. |
| 3 | spacanpanman | $ASTS | bullish | prediction | AST SpaceMobile and Rakuten are expected to win the J-LEO Project. |
| 4 | spacanpanman | $ASTS | bullish | opinion | AST's potential J-LEO involvement, once confirmed, brings full commercial approval, partnerships, funding, and spectrum — substantial growth. |
| 5 | spacanpanman | $ASTS | bullish | news | AST SpaceMobile is expected to be selected for Japan's $1B J-LEO project, partnering with Rakuten. |
| 6 | aleabitoreddit | $GM, $NVDA, $AMZN | bullish | prediction | Robotics automation is at an inflection point, demonstrating increased operational efficiency and profitability. |
| 7 | amitisinvesting | $MU, $NVDA, $AAPL | bullish | opinion | Micron is gaining prominence in the S&P 500, becoming a top-10 holding as Nvidia/Apple weightings decline. |
| 8 | aleabitoreddit | $POET | bullish | prediction | The laser bottleneck likely extends to 2029, per POET's statement that laser players are sold out for two years. |
| 9 | aleabitoreddit | $POET, $LITE, $SIVE, $AAOI | bullish | opinion | POET has a very positive outlook if it delivers, driven by strong optical demand and potential large commercial agreements. |
| 10 | aleabitoreddit | $RKLB, $SPCX, $EOS, $LITE, $TSLA | bullish | opinion | 2020–2030 predicted to be exceptionally transformative (space, AI, robotics, lasers, self-driving, quantum) — major opportunities. |
| 11 | venu_7_ | $ABCL, $JAZZ | bullish | prediction | ABCL is poised for a run if it closes above IPO VWAP; JAZZ also looks promising. |
| 12 | venu_7_ | $MU, $ALAB, $ARGX, +12 | neutral | opinion | none |
| 13 | venu_7_ | $PLTR | bullish | opinion | PLTR is at a strong support level (VWAP) and likely to form a base. |
| 14 | venu_7_ | $TER | bullish | opinion | The hidden robotics play is an early-stage investment similar to $TER. |
| 15 | venu_7_ | $SNOW | bullish | prediction | $SNOW looks ready to begin a Stage 2 uptrend and could be a software leader this cycle. |
| 16 | aleabitoreddit | $META, $NBIS, $GOOGL | bullish | opinion | Google's reported restriction of Meta's compute explains Meta's cloud deals; positive for AI data-center capex amid shortages. |
| 17 | spacanpanman | $TE | bullish | opinion | none |
| 19 | aleabitoreddit | $CBRS, $JBL | bullish | opinion | Author initiated a CBRS position due to tech validation from OpenAI's model launch and potential OpenAI-exposure premium. |
| 20 | aleabitoreddit | $SIVE | bullish | opinion | SIVE likely benefits from SPCX's Mesh acquisition given SIVE's track record collaborating with early-stage startups. |
| 23 | aleabitoreddit | $SIVE | bullish | opinion | The company is making steady progress toward NASDAQ/dual listing — positive developments. |
| 25 | aleabitoreddit | $SIVE, $JBL, $GFS, +5 | bullish | opinion | SIVE undervalued due to numerous recent/upcoming positive developments, partnerships, and market trends. |
| 26 | aleabitoreddit | $SIVE, $EWY, $NBIS, +3 | bullish | prediction | SIVE expected to volume-ramp by 2027, list on NASDAQ, and grow via M&A, potentially mirroring LITE's past growth. |

*(Rows #18, #21–22, #24, #27–50 returned HTTP 429 quota errors and are omitted.)*

---

## Notes

- The API key was passed only as an inline environment variable for the run —
  never written to disk, committed, or persisted.
- Nothing from this run was committed; the probe is terminal-only by design.
- `gemini-2.0-flash` returned free-tier `limit: 0` for the earlier keys; the
  model is now set to `gemini-2.5-flash`, which is reachable.
