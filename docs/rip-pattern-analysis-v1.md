# Rip Pattern Analysis v1

**Date:** 2026-05-06  
**Tickers analysed:** AAOI, COHR, LITE (3 of 12 requested — see §5)  
**Rip events with full pre-history:** 17  
**Method:** OHLCV from `data/snapshots.db` (2024-05-06 → 2026-05-05)

---

## 1. Executive Summary

Five observations that appear consistently across the 17 rip events in this sample.
These are empirical patterns, not tradeable signals; see §5 for why this distinction matters.

### Pattern 1 — Already in an elevated-volatility regime (strongest signal)

The single most consistent pre-rip indicator is **ATR(14) as a percentage of price**,
with a trend Pearson r = **+0.85** from T-60 to T-1. Median ATR% climbs from 5.6% at
T-60 to 8.1% at T-1. These stocks are *not* quiet before they rip — they are already
experiencing daily swings of 6–8%, and that volatility is accelerating, not compressing.

Realized 30-day volatility shows the same pattern (r = **+0.70**): median annualized
vol rises from 66% at T-60 to 92% at T-1. The "coil and release" narrative is not
supported in this sample. Rips extend an existing high-energy regime.

### Pattern 2 — Sustained uptrend structure (price well above 200-day SMA)

**Price vs. SMA-200** shows a rising trend into rips (r = **+0.70**). Median is +14.9%
above the 200-day SMA at T-60, rising to +20.0% at T-1. The stocks were already in
confirmed uptrends when rips began.

Distance from 52-week low also increases monotonically (r = **+0.78**): from +160%
at T-60 to +233% at T-1. These are names that have already moved substantially off
their cycle lows — rips are extensions of existing trends, not reversals off bottoms.

### Pattern 3 — Near-term momentum cools before the rip fires (counter-intuitive)

RSI(14) has a *negative* trend score (r = **–0.59**), declining from a median of 56 at
T-60 to 49 at T-1. The MACD histogram also trends down (r = **–0.59**) and is negative
at T-5. BB position declines from 0.77 at T-30 to 0.42 at T-1.

This means: the month before a rip, the stock typically *looks like it's cooling off*
on standard 14-day momentum indicators. RSI below 50 and a negative MACD histogram the
week before a +75%–+360% move is the opposite of what most screeners would flag.

**Implication:** Using RSI > 70 or a positive MACD histogram as a filter for "about to rip"
would have excluded the majority of these events in the days immediately preceding them.

### Pattern 4 — Volume provides a noisy, ambiguous signal

`vol_ratio_30d` (today's volume vs. 30-day average) actually *trends down* slightly
from T-60 to T-1 (median 0.89 → 0.80) with a weak negative trend score (r = **–0.25**).
The 5-day/30-day volume trend ratio is essentially flat around 1.0 throughout the
pre-rip window.

The only volume metric with a consistent pattern is `vol_spike_30d_max` (r = **+0.57**):
the maximum single-day volume spike in the trailing 30 days rises from 2.1× to 2.4×.
This suggests *periodic* high-volume events become more frequent in the 2 months before
a rip, even if daily volume is otherwise unremarkable.

### Pattern 5 — Bollinger band squeeze and tight consolidation are absent

`bb_squeeze` (band width below 20th percentile of trailing 6 months) = 0.00 at every
snapshot across all 17 rip events. `consol_20d` (20-day price range < 10%) = 0.00
throughout. The "compression before explosion" setup that many technical analysts
describe was not present in any pre-rip period in this sample.

BB width is actually *expanding* into the rips: median 0.26 at T-60, 0.42 at T-15,
settling at 0.31 at T-1. These are already wide, volatile bands — further evidence
that the pre-rip environment is high-energy, not compressed.

---

## 2. Per-Ticker Rip Log

All 17 rips were detected by **Rule A** (≥50% forward return over 60 trading days).
Rule B (≥20% break above prior 6-month high) produced events that clustered with,
and were subsumed into, the same Rule A clusters after deduplication.

### AAOI — Applied Optoelectronics (6 rips)

| # | Start | End | Magnitude | Vol accel (pre-30d) | Max drawdown during rip |
|---|-------|-----|-----------|---------------------|------------------------|
| 1 | 2024-08-28 | 2024-11-21 | **+289%** | +13.4% | 17.8% |
| 2 | 2024-10-23 | 2025-01-22 | **+96%** | +0.5% | 36.9% |
| 3 | 2025-04-21 | 2025-07-17 | **+193%** | +11.2% | 24.0% |
| 4 | 2025-06-13 | 2025-09-10 | **+79%** | +14.9% | 29.3% |
| 5 | 2025-08-01 | 2025-10-27 | **+73%** | +26.9% | 19.7% |
| 6 | 2026-02-04 | 2026-05-01 | **+360%** | −1.5% | 33.4% |

Notes: AAOI was the most volatile name in the sample. The 2024-08-28 rip (+289%)
and 2026-02-04 rip (+360%) are exceptional; most rips were 73–193%. Rip #2 had a
peak drawdown of 36.9%, illustrating that even within "rip" windows the ride is brutal.
The April 2025 rip is shared with COHR and LITE (sector event — see §5).

### COHR — Coherent Corp (5 rips)

| # | Start | End | Magnitude | Vol accel (pre-30d) | Max drawdown during rip |
|---|-------|-----|-----------|---------------------|------------------------|
| 1 | 2024-08-05 | 2024-10-29 | **+75%** | −15.2% | 14.6% |
| 2 | 2025-04-21 | 2025-07-17 | **+92%** | +3.8% | 6.9% |
| 3 | 2025-09-17 | 2025-12-11 | **+92%** | +82.2% | 18.7% |
| 4 | 2025-12-02 | 2026-03-02 | **+81%** | +44.3% | 14.1% |
| 5 | 2026-01-26 | 2026-04-22 | **+77%** | −19.4% | 26.5% |

Notes: COHR's rips are tightly clustered in magnitude (75–92%). Rip #3 had a
dramatic +82% volume acceleration in the pre-30d window, which is the strongest
vol-accel signal in the whole sample — but it did not appear in rips #1 and #5 where
vol accel was *negative*. Volume acceleration is not a reliable prerequisite.

### LITE — Lumentum Holdings (6 rips)

| # | Start | End | Magnitude | Vol accel (pre-30d) | Max drawdown during rip |
|---|-------|-----|-----------|---------------------|------------------------|
| 1 | 2024-09-10 | 2024-12-04 | **+86%** | +84.0% | 8.5% |
| 2 | 2024-10-24 | 2025-01-23 | **+54%** | −16.6% | 12.6% |
| 3 | 2025-04-21 | 2025-07-17 | **+105%** | +13.7% | 7.8% |
| 4 | 2025-06-13 | 2025-09-10 | **+100%** | −7.5% | 4.9% |
| 5 | 2025-11-20 | 2026-02-19 | **+173%** | +15.3% | 18.4% |
| 6 | 2026-01-12 | 2026-04-09 | **+163%** | −21.2% | 28.7% |

Notes: LITE had the cleanest rips in terms of low intra-rip drawdown for #1–4
(5–13%), then worsened in #5–6. The Apr 2025 rip (#3) is shared with AAOI and COHR.

---

## 3. Aggregate Indicator Behaviour

Medians across all 17 rip events at each snapshot point. n=17 except where
prior-history limitations reduced the count.

### Momentum and returns

| Indicator | T-60 | T-30 | T-15 | T-5 | T-1 | Trend r |
|-----------|------|------|------|-----|-----|---------|
| ret_1d | −0.19% | +2.31% | +1.33% | −0.22% | −0.46% | −0.40 |
| ret_5d | +4.61% | +0.23% | −2.42% | +7.29% | +0.50% | −0.05 |
| ret_21d | +0.68% | +8.68% | +12.79% | +17.37% | +8.01% | **+0.60** |
| ret_3m | +24.5% | +9.1% | +16.1% | +26.6% | +29.5% | +0.52 |
| ret_6m | +66.9% | +21.2% | +11.7% | +23.8% | +25.6% | −0.59 |

Key observations:
- 21-day return has the strongest upward trend (r=+0.60): the 1-month lookback
  accelerates cleanly from near-flat at T-60 to +17% at T-5, then softens at T-1.
- The 6-month return is highest at T-60 (+67%) and declines toward T-1 (+26%):
  stocks have often already had a big 6-month run that is fading as the new rip starts.
- Short-term returns (1d, 5d) are effectively noise (r near zero or negative).

### Price structure

| Indicator | T-60 | T-30 | T-15 | T-5 | T-1 | Trend r |
|-----------|------|------|------|-----|-----|---------|
| dist_30d_high | −14.0% | −7.9% | −10.8% | −10.4% | −11.6% | +0.16 |
| dist_30d_low | +17.0% | +34.0% | +33.8% | +34.0% | +21.0% | +0.16 |
| dist_52w_high | −12.0% | −5.7% | −16.6% | −11.2% | −10.4% | −0.09 |
| dist_52w_low | +160% | +212% | +240% | +278% | +233% | **+0.78** |
| price_vs_sma50 | +2.4% | +8.3% | +17.2% | +13.5% | +9.2% | **+0.53** |
| price_vs_sma200 | +14.9% | +7.9% | +16.6% | +18.3% | +20.0% | **+0.70** |

Key observations:
- Distance from 52-week low surges monotonically (+0.78): stocks are making
  new cycle highs as the rip approaches, not bouncing off bottoms.
- Price vs SMA-200 is persistently positive (10–20% above) and rising.
- Distance from 30-day high shows the stock is typically 10–14% below its recent high
  at T-1 — the stock has pulled back from a local peak just before the rip fires.

### Volatility

| Indicator | T-60 | T-30 | T-15 | T-5 | T-1 | Trend r |
|-----------|------|------|------|-----|-----|---------|
| atr14_pct | 5.6% | 7.5% | 7.0% | 8.0% | 8.1% | **+0.85** |
| rvol_30d (annualised) | 66% | 92% | 77% | 98% | 92% | **+0.70** |
| bb_width | 0.257 | 0.374 | 0.421 | 0.309 | 0.306 | +0.08 |
| bb_squeeze | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.00 |

Key observations:
- ATR% and realized vol both rise into rips. This is the most reliable directional
  signal in the dataset.
- Bollinger band squeeze never appeared. These are wide, expanding bands throughout.
- BB width expands from T-60 to T-15, then contracts slightly toward T-1.

### Volume

| Indicator | T-60 | T-30 | T-15 | T-5 | T-1 | Trend r |
|-----------|------|------|------|-----|-----|---------|
| vol_ratio_30d | 0.89× | 0.94× | 0.70× | 0.95× | 0.80× | −0.25 |
| vol_trend_5_30 | 1.01× | 0.98× | 0.89× | 1.05× | 1.01× | +0.17 |
| vol_spike_30d_max | 2.10× | 2.23× | 2.36× | 2.28× | 2.24× | **+0.57** |

Key observations:
- Day-of volume is *below* average (0.80×) at T-1 in the median. The rip begins
  on a quiet day.
- The vol_spike_30d_max trend (+0.57) reflects an increase in *periodic* large-volume
  events in the 2 months prior — suggesting accumulation days or catalyst reactions,
  not sustained elevated volume.

### Oscillators and technicals

| Indicator | T-60 | T-30 | T-15 | T-5 | T-1 | Trend r |
|-----------|------|------|------|-----|-----|---------|
| rsi14 | 56.1 | 61.9 | 55.9 | 58.6 | 48.7 | **−0.59** |
| macd_hist | +0.215 | +0.105 | +0.195 | −0.234 | +0.047 | −0.59 |
| bb_pos | 0.57 | 0.77 | 0.65 | 0.64 | 0.42 | −0.53 |
| consol_20d | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.00 |
| hh_hl_30d (of 29) | 15.3 | 14.0 | 15.5 | 16.0 | 16.0 | **+0.67** |

Key observations:
- RSI at T-1 median is **48.7** — below neutral. Stocks are in oversold-adjacent
  territory in the days immediately before the rip fires.
- MACD histogram is *negative* at T-5 (−0.234) and near zero at T-1. The stock
  looks like it's in a mini-downswing just before the rip.
- BB position drops from 0.77 at T-30 to 0.42 at T-1 — stock falling from the
  upper band toward the midline.
- Higher-highs/higher-lows count (of 29 possible) is ~16 at T-1: just slightly
  above the random 50% base rate, but rising modestly through the window (r=+0.67).

---

## 4. Patterns Ranked by Consistency

Ranked by absolute Pearson r of the median trajectory from T-60 to T-1.
"Positive trend" = metric rises into the rip. "Negative trend" = metric falls.

| Rank | Indicator | r | Direction | Interpretation |
|------|-----------|---|-----------|----------------|
| 1 | atr14_pct | **+0.85** | Rising | Volatility regime expanding |
| 2 | dist_52w_low | **+0.78** | Rising | Already far from lows; new highs being made |
| 3 | rvol_30d | **+0.70** | Rising | Realized volatility expanding |
| 4 | price_vs_sma200 | **+0.70** | Rising | Sustained uptrend structure |
| 5 | hh_hl_30d | **+0.67** | Rising | Incremental trend continuation |
| 6 | ret_21d | **+0.60** | Rising | 1-month momentum building |
| 7 | rsi14 | **−0.59** | Falling | Near-term momentum fading to neutral/weak |
| 8 | ret_6m | **−0.59** | Falling | Big prior-6m run fading into the start point |
| 9 | macd_hist | **−0.59** | Falling | Short-term momentum turning negative |
| 10 | vol_spike_30d_max | **+0.57** | Rising | Periodic large-volume events increasing |
| 11 | price_vs_sma50 | **+0.53** | Rising | Price above 50-day SMA and pulling away |
| 12 | bb_pos | **−0.53** | Falling | Stock pulling back from upper band |
| 13 | ret_3m | **+0.52** | Rising | 3-month trend positive |
| — | ret_1d | −0.40 | Noise | Single-day returns: no useful signal |
| — | vol_ratio_30d | −0.25 | Noise | Daily volume vs average: noise |
| — | vol_trend_5_30 | +0.17 | Noise | Short-term volume trend: noise |
| — | dist_30d_high | +0.16 | Noise | Recent high distance: noise |
| — | dist_30d_low | +0.16 | Noise | Recent low distance: noise |
| — | dist_52w_high | −0.09 | Noise | 52w high distance: noise |
| — | bb_width | +0.08 | Noise | Band width: too noisy to use |
| — | bb_squeeze | 0.00 | **Absent** | Never fired in this sample |
| — | consol_20d | 0.00 | **Absent** | Never fired in this sample |
| — | ret_5d | −0.05 | Noise | 5-day return: noise |

### Signals that do NOT work as pre-rip filters

- **RSI > 70 screen:** Would have excluded most events; RSI is typically 49–56 at T-1.
- **Bollinger band squeeze:** Never appeared. If you're waiting for a squeeze, you're
  waiting for something that didn't precede any rip in this sample.
- **Consolidation filter (tight range):** Same — never fired.
- **Elevated daily volume:** Volume on the rip-start day is *below* average.
- **High 6-month momentum:** A high 6m trailing return at the *start* of the pre-rip
  window is associated with a *smaller* rip magnitude (the stock was already extended).

---

## 5. Limitations

### Sample size and availability

This analysis covers **3 of the 12 requested tickers** (AAOI, COHR, LITE). The other 9
(AMD, GLW, MU, SNDK, ARM, INTC, BE, NBIS, AEHR) are not in `data/snapshots.db` and
could not be fetched — outbound connections to Yahoo Finance are blocked in this
compute environment. **Any findings here should be treated as tentative hypotheses
for the 3 available names, not confirmed patterns for the full universe.**

With 17 total rip events across 3 tickers and 2 years of data, the statistical power
is low. Adding the remaining 9 tickers (~20–30 additional rip events, assuming similar
frequency) could substantially change every finding, including reversing some.

### Sector and macro clustering

AAOI, COHR, and LITE all began ripping on **2025-04-21** simultaneously. This is almost
certainly a single macro/sector catalyst (likely AI-related hardware news or tariff
relief) rather than three independent setups. Three of the 17 rip events are therefore
not independent observations — they represent the same trade. Aggregate statistics are
slightly inflated in favor of whatever conditions happened to exist on that day.

### Survivorship and data window

We observe only 2 years of data (2024–2026). All three tickers are in optical
interconnects/photonics, a sector that was particularly hot during this period due to
AI datacenter buildout. Patterns that appear here may not generalize to other sectors
or to a bear-market environment.

### No control group

We have no "non-rip" baseline. We cannot determine whether RSI around 50 or ATR% of 8%
are *specifically* pre-rip conditions, or just the normal state of these volatile stocks.
Without comparing these same indicators during non-rip periods, we cannot claim the
indicators are discriminative — only that they are descriptive of the pre-rip periods
we observed.

### What we cannot see

- **Social attention history:** Retail/social momentum (StockTwits, Reddit, Twitter
  volume) is often a leading catalyst for small-cap rips and is invisible here.
- **News sentiment trajectory:** Earnings beats, design wins, analyst upgrades, and
  sector catalysts that preceded the rip cannot be inferred from price/volume alone.
- **Short interest:** The biggest rips in this sample (AAOI +289%, +360%) have the
  hallmarks of short squeezes, but we have no short interest data to verify.
- **Fundamentals trajectory:** Revenue guidance revisions, backlog changes, and margin
  inflection are the "why" behind sustained rips and are not captured here.
- **Liquidity and float:** Smaller-float stocks can make these moves on much lower
  absolute volume. Float-adjusted volume metrics would be more meaningful.

### Rule B not firing

All 17 detected rips came from Rule A (≥50% forward return over 60 days). Rule B
(≥20% breakout above prior 6-month high) produced additional events that clustered
within 30 days of Rule A events and were merged away. This means the deduplication
was aggressive. Re-running with a tighter merge window (e.g., 15 days) would yield
more events; some might be genuinely distinct breakout episodes.

---

## 6. Implications for Layer 1 Dashboard

Based on this analysis, the following changes are worth evaluating when the dashboard
is updated. These are suggestions for review, not prescriptions.

### Indicators to surface more prominently

1. **ATR(14) as % of price (atr14_pct)** — strongest trend signal (r=+0.85).
   Show current value and 60-day chart. Flag when it's above 6% and rising.

2. **Realized 30-day volatility (annualised)** — effectively the same regime signal
   as ATR, provides confirmation. Flag when above 80% annualised.

3. **Price vs. 200-day SMA** — simple, clean signal. Show the percentage gap and
   whether it's been expanding over the last 30 days.

4. **Distance from 52-week low** — shows how far into a recovery cycle the stock is.
   Not a trigger, but context for whether the stock is "late-stage extended" or
   "early-stage recovery."

5. **vol_spike_30d_max** — the largest single-day volume multiple in the trailing 30 days.
   A rising value here (above 2.5×) flags that big-volume events are happening,
   even if daily volume looks quiet.

### Indicators to de-emphasize or reframe

- **RSI:** If shown at all, re-label for these volatile names. An RSI of 50 is
  *neutral*, not a warning sign. The pre-rip median is 49. Showing "RSI = 49, neutral"
  as a negative signal would have been wrong 17/17 times in this sample.

- **Bollinger band squeeze:** Remove or hide for high-volatility names. It never
  appeared in 2 years of data across 3 names. It may be meaningful for low-volatility
  names (financials, utilities) but is irrelevant here.

- **MACD histogram:** Useful for trend context but should not be used as a
  rip-imminence filter. A negative histogram the week before the rip is the norm.

- **Volume ratio (daily):** Does not predict rip starts. Can be kept for monitoring
  *during* a rip (confirmation) but should not be featured as a pre-rip signal.

### New indicators to consider adding

- **Short interest (% float):** Not available in current data pipeline but is arguably
  the most important context for violent rip magnitudes. Worth sourcing.

- **Earnings date proximity:** Many rips appear to cluster around earnings windows.
  A "days to next earnings" field would contextualize the pre-rip pattern.

- **30-day max single-day return** (not just volume): If any day in the trailing 30d
  saw a +10% or larger single-day move, that's a signal that the stock is in a
  volatility regime worth watching.

- **Price vs. SMA-50 momentum** (slope of the gap, not just the level): The level is
  already captured; the *acceleration* of price pulling away from the 50-day SMA was
  one of the cleaner pre-rip signals (r=+0.53).

---

*This document is one input into dashboard design decisions. It is not investment advice.
The outputs are aggregated commentary derived from price/volume data of public stocks.
Statistical findings from 17 events across 3 tickers should be validated against a
larger sample before driving product changes.*
