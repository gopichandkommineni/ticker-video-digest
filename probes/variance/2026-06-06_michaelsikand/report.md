# Variance Probe: @michaelsikand

Window: 2026-01-01 → 2026-06-06  |  Runs per provider: 3

## GetXAPI

**VERDICT: STABLE**

| run | tweets | reached_floor | earliest_utc | 429s | aborted |
|-----|-------:|:-------------:|--------------|-----:|:-------:|
| 1 | 1143 | True | 2026-01-05T17:34:21Z | 0 | False |
| 2 | 1165 | True | 2026-01-05T17:34:21Z | 0 | False |
| 3 | 1165 | True | 2026-01-05T17:34:21Z | 0 | False |

**Same-provider ID overlap (run 1 as baseline)**

| compared | ∩ (shared) | run1-only | runN-only | overlap % |
|----------|----------:|----------:|----------:|----------:|
| run1 vs run2 | 1134 | 9 | 31 | 96.6% |
| run1 vs run3 | 1134 | 9 | 31 | 96.6% |

## twitterapi.io

**VERDICT: STABLE**

| run | tweets | reached_floor | earliest_utc | 429s | aborted |
|-----|-------:|:-------------:|--------------|-----:|:-------:|
| 1 | 1152 | True | 2026-01-05T17:34:21Z | 0 | False |
| 2 | 1134 | True | 2026-01-05T17:34:21Z | 0 | False |
| 3 | 1141 | True | 2026-01-05T17:34:21Z | 0 | False |

**Same-provider ID overlap (run 1 as baseline)**

| compared | ∩ (shared) | run1-only | runN-only | overlap % |
|----------|----------:|----------:|----------:|----------:|
| run1 vs run2 | 1134 | 18 | 0 | 98.4% |
| run1 vs run3 | 1134 | 18 | 7 | 97.8% |

## Cross-provider union

| metric | count |
|--------|------:|
| GetXAPI union (all runs) | 1205 |
| twitterapi.io union (all runs) | 1159 |
| shared (∩) | 1142 |
| GetXAPI-only | 63 |
| twitterapi.io-only | 17 |
| **combined union** | **1222** |
| lift over GetXAPI alone | +17 (1.4%) |
| lift over twitterapi.io alone | +63 (5.4%) |

## Sample tweets (cashtag-ranked)

- [2026-04-13T22:19:32Z] (original) I just put 15% of my $5,000,000 fund in $FLY 🪰🌖  Firefly Aerospace is a misunderstood space stock trading 35% off its ATH with an extremely unique set of assets.  Here's why I think this $6B space pio
- [2026-06-01T16:41:57Z] (original) $BRUN is surging today.   I loaded this morning on my Asymmetrical Bets fund ($16M AUM following) on @joinautopilot with a 20% allocation at $34.50.  Shoutout @mkfilko for inspiring me with his early 
- [2026-03-07T20:13:51Z] (original) This is crazy.  $SATS just became the FIRST pure play space stock added to the S&P 500.  $ASTS $RKLB $PL holders pay close attention.  Yesterday the committee looked past a $14B GAAP loss to add Space
- [2026-04-20T16:50:46Z] (original) I just put 20% of my $6,200,000 @joinautopilot fund in one stock.  $AVEX is a newly IPO'd drone stock with a vast battle tested portfolio, a vertically integrated software platform, and 1K/month of ma
- [2026-04-20T14:03:31Z] (original) $AVEX - This $3.6B Anduril competitor could be the next 5x drone stock.   Calling it at $34/share as the most asymmetrical defense stock since $KRKNF.  AEVEX went public on the NYSE last Thursday but 
- [2026-03-05T20:43:39Z] (original) $AAOI is the most asymmetrical stock in the world.  Before it's 100% post ER rally, I had 2% of my portfolio in $AAOI.  Now $AAOI is around 25% of it so here's why I'm concentrating at least in the sh
- [2026-05-22T15:28:11Z] (original) Morgan Stanley's new research on AI racks has $DELL trading like it's a penny stock.  They modeled the next gen VR200 NVL72 rack at $7.8M per rack. That's up 95% from the $4M GB300.  But almost none o
- [2026-04-12T22:30:39Z] (quote) ALL OF THE LIGHTS.  $LWLG is up 70% since I pointed out its $TSEM partnership.  In a hot sector, I typically view big moves in pre-rev names as a *potential* top signal.  BUT $LWLG is a genuinely inte
- [2026-04-02T16:12:56Z] (original) Someone put a gun to my head.  They said "make me $1M from $100K with 10 stocks".  This answer saved my life.  1) $KRKNF - This subsea drone component monopoly is on the verge of revenue explosion as 
- [2026-04-26T21:22:00Z] (original) $QCOM - the CPU supercycle's dark horse trading at a dirt cheap multiple?  Qualcomm has been punishing investors for years.  But with growing attention towards CPUs, I'm going to be watching their ER 
