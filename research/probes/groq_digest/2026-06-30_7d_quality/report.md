# Groq Probe Report

**Script:** `groq_probe.py` (throwaway quality probe — read-only, terminal output)
**Database:** `data/fintwit.db` · table `raw_tweets`
**Window:** last 7 days (run date 2026-06-30)
**Model:** `llama-3.3-70b-versatile`

---

## Funnel

| Stage | Count |
|---|---:|
| Tweets pulled (last 7d, non-deleted) | **321** |
| Survived cashtag regex `\$[A-Z]{1,5}\b` | **64** (19.9%) |
| Sent to Groq (capped at 50) | 50 |
| Skipped by 50-call cap | 14 |
| **Succeeded** | **50** |
| Failed — HTTP 429 quota | 0 |

> A clean run: all 50 calls succeeded with zero rate-limiting. The 7-day
> per-tweet pass (50 short calls, ~2s apart) stays comfortably under Groq's
> per-minute token bucket — throttling only bites on the batched 30-day pass.
> Before this clean run, the first attempt failed all 50 calls with HTTP 403
> (Cloudflare error `1010`): Groq's endpoint blocks the default `Python-urllib`
> User-Agent. Setting an explicit `User-Agent` header cleared the filter.

---

## Architecture validation

- **Regex owns ticker extraction, not the LLM** — confirmed. Groq never
  extracted cashtags; multi-ticker tweets (e.g. an 18-ticker market recap) were
  caught deterministically by regex.
- **Strict JSON every time** — all 50 successes parsed into exactly
  `{thesis, sentiment, stance}`; JSON mode (`response_format: json_object`)
  held with no fence-stripping fallbacks needed.
- **"none" handling is correct** — pure ticker-dumps and recap tweets returned
  `thesis: "none"` (9 of 50) rather than a hallucinated claim.
- **Multilingual / mixed content** — Japanese-context and Rakuten/J-LEO tweets
  were summarized accurately into English theses.

---

## Distribution (n = 50 successful)

- **Sentiment:** bullish 38 · bearish 6 · neutral 6
- **Stance:** opinion 40 · news 7 · other 1 · prediction 1 · question 1

### Sentiment discrimination — notably better than Gemini
The parallel Gemini 7-day probe scored **21/22 bullish** (1 neutral, 0 bearish)
— almost no discriminative power. On the same corpus, Llama 3.3 70B produced
**6 bearish and 6 neutral** calls, correctly flagging cautionary tweets
(e.g. #24 a hedged $CBRS position, #34 a memory-bottleneck warning, #41 a
meme-stock caution). Stance skews heavily to `opinion` (40/50), which is honest
for this commentary-heavy corpus but leaves `prediction`/`news` underused.

---

## Successful summaries (50)

| # | Handle | Tickers (regex) | Sentiment | Stance | Thesis |
|---|---|---|---|---|---|
| 1 | aleabitoreddit | $NBIS | neutral | other | none |
| 2 | amitisinvesting | $PLTR, $NVDA, $RKLB, +15 | neutral | news | none |
| 3 | aleabitoreddit | $RPI, $SIVE, $JBL, +7 | neutral | opinion | none |
| 4 | spacanpanman | $ASTS | bullish | question | none |
| 5 | amitisinvesting | $RKLB, $SPCX | bullish | opinion | The Rocket Lab acquisition is a significant step in transforming the company into a vertically integrated space and communications company with recurring cash flows, making it a strong investment opportunity. |
| 6 | amitisinvesting | $PLTR, $NVDA | bullish | news | The partnership between Palantir and Nvidia will enable the US government to unleash the full power of AI while removing security risks and concerns around proprietary insights. |
| 7 | spacanpanman | $RKLB | bullish | news | Rocket Lab is poised for growth after acquiring Iridium in a historic deal. |
| 8 | aleabitoreddit | $ASTS, $SPCX | neutral | news | Rakuten is responding to Starlink's growing influence in Japan by establishing a joint venture to build out LEO satellite networks |
| 9 | spacanpanman | $ASTS | bullish | prediction | AST will win the J-LEO project with Rakuten |
| 10 | spacanpanman | $ASTS | bullish | opinion | AST SpaceMobile will benefit from the J-LEO project award, gaining commercial approval and partnerships with major Japanese companies. |
| 11 | spacanpanman | $ASTS | bullish | news | AST Space Mobile is expected to be selected for Japan's $1 billion J-LEO project in partnership with Rakuten Group |
| 12 | aleabitoreddit | $GM, $NVDA, $AMZN | neutral | opinion | The adoption of robotics in industries like manufacturing and warehousing will lead to increased efficiency and profitability, but at the cost of human jobs. |
| 13 | amitisinvesting | $MU, $NVDA, $AAPL | bullish | opinion | Micron is now a top 10 holding in the S&P 500, surpassing other major companies |
| 14 | aleabitoreddit | $POET | bullish | opinion | The laser bottleneck is likely to extend into 2029. |
| 15 | aleabitoreddit | $POET, $LITE, $SIVE, +1 | bullish | opinion | POET's future looks very positive if management delivers on their projections, despite some questionable aspects |
| 16 | aleabitoreddit | $RKLB, $SPCX, $EOS, +2 | bullish | opinion | The decade from 2020-2030 will be the most significant in human history due to rapid technological advancements. |
| 17 | venu_7_ | $ABCL, $JAZZ | bullish | opinion | The stock is ready to increase in value once a weekly close above IPO VWAP is reached. |
| 18 | venu_7_ | $MU, $ALAB, $ARGX, +12 | bullish | opinion | none |
| 19 | venu_7_ | $PLTR | bullish | opinion | The stock is likely to find support and form a base at its current level. |
| 20 | venu_7_ | $TER | bullish | opinion | The investment is similar to TER in its early stages |
| 21 | venu_7_ | $SNOW | bullish | opinion | The stock is ready to begin a Stage 2 uptrend and could be one of the software leaders this cycle. |
| 22 | aleabitoreddit | $META, $NBIS, $GOOGL | bullish | opinion | Restrictions on computing power are likely to be positive for the AI DC capex buildout. |
| 23 | spacanpanman | $TE | bullish | opinion | none |
| 24 | aleabitoreddit | $CBRS | bearish | opinion | The author is cautious about their position in $CBRS due to evolving market conditions. |
| 25 | aleabitoreddit | $CBRS, $JBL | bullish | opinion | Cerebras is a good investment due to its technology validation and potential premiums from OpenAI exposure. |
| 26 | aleabitoreddit | $SIVE | bullish | opinion | SIVE is likely to benefit from SPCX's acquisition of Mesh. |
| 27 | spacanpanman | $ASTS | bearish | opinion | The T-Mobile and Starlink partnership was a strategic mistake for T-Mobile as it helped SpaceX overcome its regulatory and spectrum validation hurdles, ultimately making SpaceX a competitor. |
| 28 | aleabitoreddit | $SPCX, $SIVE, $POET, +2 | bullish | opinion | Elon Musk's acquisition of Mesh is a positive development for optical interconnects and merchant laser suppliers like $SIVE, $LITE, and $MTSI. |
| 29 | aleabitoreddit | $SIVE | bullish | opinion | The company is making progress on its dual listing and other initiatives. |
| 30 | aleabitoreddit | $NBIS | neutral | opinion | none |
| 31 | aleabitoreddit | $SIVE, $JBL, $GFS, +5 | bullish | opinion | The stock is undervalued relative to its forward revenue potential. |
| 32 | aleabitoreddit | $SIVE, $EWY, $NBIS, +3 | bullish | opinion | The author is confident in their research on Sivers and expects the company to volume ramp in 2027 and list on NASDAQ, leading to significant growth. |
| 33 | aleabitoreddit | $SIVE, $AAOI | bullish | opinion | The user is confident that $SIVE and $AAOI will revenue ramp with lasers in 2027. |
| 34 | aleabitoreddit | $MU | bearish | opinion | Elon Musk is warning about a memory bottleneck due to high demand and price hikes for memory relative to supply. |
| 35 | aleabitoreddit | $SOI, $RKLB | bearish | opinion | High beta stocks get hit harder in a global correction but usually recover earlier than indexes. |
| 36 | aleabitoreddit | $AXTI, $AAOI, $TSEM, +7 | bullish | opinion | The author's investment ideas will recover despite a potential massive correction due to macro drop. |
| 37 | aleabitoreddit | $JBL, $SIVE | bullish | opinion | none |
| 38 | aleabitoreddit | $AAOI, $AMD | bullish | opinion | The user is confident in AMD's prospects due to its current reports and future projections. |
| 39 | aleabitoreddit | $AOSL, $POWI | bullish | opinion | The recent price hikes in the power semiconductor industry are a bullish sign for the US power semi trade. |
| 40 | spacanpanman | $BAER | bullish | opinion | none |
| 41 | michaelsikand | $WEN | bearish | opinion | The current market favors established companies over meme stocks. |
| 42 | kaizen_investor | $MU | bullish | news | Sk Hynix stock is up due to Micron's strong earnings |
| 43 | aleabitoreddit | $WEN, $RDDT | bullish | opinion | The $WEN stock has gone up ~50%, outperforming some other investments. |
| 44 | aleabitoreddit | $MU, $TSM, $TSLA | bullish | opinion | The CEO of MU predicts a multi-decade memory demand cycle driven by humanoid robots, which will require significantly more memory than current autonomous vehicles. |
| 45 | kawzinvests | $NOK | bullish | opinion | The acquisition of Infinera was a massive turning point for the company. |
| 46 | kawzinvests | $KXIAY, $MU, $SNDK | bullish | news | Kioxia will have US depositary shares around April or May 2027 |
| 47 | aleabitoreddit | $AXTI, $SOI, $AAOI | bullish | opinion | The author believes we're still early in the Supercycle with photonics and many related names will have a major inflection point in midway through 2027 scaling up to 2028. |
| 48 | venu_7_ | $MU | bullish | opinion | As long as MU holds above the 50-day moving average and guidance stays strong, the investment view remains positive. |
| 49 | aleabitoreddit | $DRAM, $MU, $SNDK | bullish | opinion | The DRAM ETF is a positive investment due to its exposure to key memory companies. |
| 50 | aleabitoreddit | $BABA | bearish | opinion | The rewards of using Qwen outweigh the risks because there have been no penalties, which is bearish. |

---

## Notes

- The API key was read only from the `GROQ_API_KEY` environment variable for the
  run — never written to disk, committed, or persisted.
- The probe is read-only on `data/fintwit.db`: no DB writes, no schema changes.
- Throwaway quality probe; `groq_probe.py` is terminal-only by design, this
  report captures that terminal run for the record.
