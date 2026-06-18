# Variance Probe: @kaizen_investor

Window: 2026-01-01 → 2026-06-18  |  Runs per provider: 2

## GetXAPI

**VERDICT: VARIABLE (count spread 73%)**

| run | tweets | reached_floor | earliest_utc | 429s | aborted |
|-----|-------:|:-------------:|--------------|-----:|:-------:|
| 1 | 420 | True | 2026-04-27T20:29:23Z | 0 | False |
| 2 | 1560 | True | 2026-01-03T06:56:40Z | 0 | False |

**Same-provider ID overlap (run 1 as baseline)**

| compared | ∩ (shared) | run1-only | runN-only | overlap % |
|----------|----------:|----------:|----------:|----------:|
| run1 vs run2 | 420 | 0 | 1140 | 26.9% |

## twitterapi.io

**VERDICT: STABLE**

| run | tweets | reached_floor | earliest_utc | 429s | aborted |
|-----|-------:|:-------------:|--------------|-----:|:-------:|
| 1 | 1574 | True | 2026-01-01T12:59:09Z | 0 | False |
| 2 | 1573 | True | 2026-01-01T12:59:09Z | 0 | False |

**Same-provider ID overlap (run 1 as baseline)**

| compared | ∩ (shared) | run1-only | runN-only | overlap % |
|----------|----------:|----------:|----------:|----------:|
| run1 vs run2 | 1573 | 1 | 0 | 99.9% |

## Cross-provider union

| metric | count |
|--------|------:|
| GetXAPI union (all runs) | 1560 |
| twitterapi.io union (all runs) | 1574 |
| shared (∩) | 1555 |
| GetXAPI-only | 5 |
| twitterapi.io-only | 19 |
| **combined union** | **1579** |
| lift over GetXAPI alone | +19 (1.2%) |
| lift over twitterapi.io alone | +5 (0.3%) |

## Sample tweets (cashtag-ranked)

- [2026-03-04T16:47:39Z] (quote) I have written a full article on the AI chip supply chain.   The supply chain is structured into 4 different phases with 13 layers:  1. Raw Materials: $SHECY, $SUOPY, GlobalWafers, $WAF.DE, $SHWDF, $A
- [2026-04-07T17:06:49Z] (original) Q4 Energy transition update. I follow 7 big energy waves to keep track of the transition.   Wind: $GEV, SIFG, ORSTED, $CDLR, PNE, NDX, VWS, Goldwind, Windey  Green Hydrogen: $PLUG, $NEL, $ITM, TKA, LH
- [2026-03-14T21:23:09Z] (quote) Big companies are announcing huge layoffs.   $AMZN to cut 30,000 jobs, $META potentially 15,000 jobs.   $ORCL, $XYZ, $CRM, $ASML,… all announced cuts as well.   It’s not that those companies are doing
- [2026-02-13T19:19:25Z] (original) We’re still in the early innings of the AI boom. Don’t let the price swings scare you! Every drop can be a buy signal.   Here’s a breakdown of the sectors and stocks that should be on every investors 
- [2026-03-01T20:02:36Z] (original) Some interesting earnings next week, I’ll be looking at following earnings.   Monday: $BRK.B, $QURE, $RIOT, $BBAI, $MDB, $PLUG, $QUBT, $ASTS, $ACHR  Tuesday: $SE, $ASM.AS, $CRWD, $GTLB  Wednesday: $AV
- [2026-04-05T20:13:34Z] (quote) War-driven energy inflation is inevitable, but companies solving the AI bottleneck are uniquely positioned to protect their margins.   Their critical role gives them the pricing power to simply pass c
- [2026-04-12T13:48:13Z] (original) Some key catalysts I'm looking forward to in 2026-2027.  Q2 2026 - $POET: high-volume light source scaling.  POET unveiled its next-generation Starlight and Blazar hybrid external light sources at the
- [2026-02-02T21:42:33Z] (original) Kaizen Portfolio update of January. The portfolio was up 11.56% with some big shifts in the distribution. I did not buy or sold anything this month. For the first time since 2 years, $PLTR is not my b
- [2026-05-31T15:10:44Z] (quote) Time for my monthly portfolio update.  MTD performance: +40.4%.  YTD performance: +97.8%  I made a couple of trades this month. Bought some $WOLF and $FLNC in the beginning of the month and sold my $T
- [2026-02-27T21:33:33Z] (original) February Portfolio Recap  February Performance: -15.6% Year-to-Date (YTD) Performance: -0.9%  If you only looked at February, you might think the sky was falling. A -15.6% drop in a single month sound
