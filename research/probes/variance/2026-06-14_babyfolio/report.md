# Variance Probe: @babyfolio

Window: 2026-01-01 → 2026-06-14  |  Runs per provider: 2

## GetXAPI

**VERDICT: VARIABLE (ID overlap 91% run1 vs run2)**

| run | tweets | reached_floor | earliest_utc | 429s | aborted |
|-----|-------:|:-------------:|--------------|-----:|:-------:|
| 1 | 2161 | True | 2026-01-01T00:15:23Z | 0 | False |
| 2 | 2215 | True | 2026-01-01T00:15:23Z | 0 | False |

**Same-provider ID overlap (run 1 as baseline)**

| compared | ∩ (shared) | run1-only | runN-only | overlap % |
|----------|----------:|----------:|----------:|----------:|
| run1 vs run2 | 2079 | 82 | 136 | 90.5% |

## twitterapi.io

**VERDICT: VARIABLE (ID overlap 94% run1 vs run2)**

| run | tweets | reached_floor | earliest_utc | 429s | aborted |
|-----|-------:|:-------------:|--------------|-----:|:-------:|
| 1 | 2158 | True | 2026-01-01T00:15:23Z | 0 | False |
| 2 | 2130 | True | 2026-01-01T00:15:23Z | 0 | False |

**Same-provider ID overlap (run 1 as baseline)**

| compared | ∩ (shared) | run1-only | runN-only | overlap % |
|----------|----------:|----------:|----------:|----------:|
| run1 vs run2 | 2074 | 84 | 56 | 93.7% |

## Cross-provider union

| metric | count |
|--------|------:|
| GetXAPI union (all runs) | 2297 |
| twitterapi.io union (all runs) | 2214 |
| shared (∩) | 2108 |
| GetXAPI-only | 189 |
| twitterapi.io-only | 106 |
| **combined union** | **2403** |
| lift over GetXAPI alone | +106 (4.6%) |
| lift over twitterapi.io alone | +189 (8.5%) |

## Sample tweets (cashtag-ranked)

- [2026-06-06T19:50:18Z] (original) I've been asked for my watchlist, so here it is.  This is NOT a buy recommendation.  Many of these names are not at prices I'd consider ideal entries today, and I only hold a handful of them.  This is
- [2026-06-09T05:08:18Z] (original) It shouldn't be hard to start investing. Just pick any quality AI infra related stock and start DCAing, they will all do well.  My personal favourite US common stocks: $NBIS  $CRDO $MU or $DRAM $BE $A
- [2026-06-01T04:53:10Z] (quote) Top 10 Most Mentioned Tickers in the Comments(in order): $TMC (wow) $PENG $VPG $HIMX $POWI $FLNC $SYNA $AAOI $NOK $KEEL
- [2026-04-17T18:40:48Z] (original) My portfolio after this eventful war: $NBIS 65% $KRKNF 5% $CRDO 8% $HIMS 5% 17% Cash  What changed?  * 20% $NBIS position got CC assigned  * $IREN got CCs assigned  * Increased $KRKNF position after e
- [2026-04-25T09:56:04Z] (original) What’s your portfolios looking like right now?  I’ll go first YTD: +89%  Not the craziest return out there, but I’m genuinely happy with it especially since I play it more conservatively (using option
- [2026-06-11T04:14:34Z] (original) Those who have followed $NBIS for a while know that $ORCL earnings don't mean much for Nebius.  $NBIS tends to get dragged down whenever there's bad news or disappointing earnings from $CRWV or $ORCL,
- [2026-05-30T19:01:14Z] (original) Portfolio Update:  $402430 SK Square - 42% $NBIS - 23% $OUST - 15% $PNG - 9% $FCEL - 9% $6324 Harmonic Drive - 2%  Changes:  Added: $6324 Harmonic Drive 0% => 2% (Starter position) $NBIS 15% => 23%  S
- [2026-05-20T08:49:42Z] (reply) @DrTEHughes Waiting for my high conviction names to add or buy.  $CRDO $NBIS $BE $DRAM / SK Square $OUST $KRKNF / $PNG  I have more but they're giga overvalued so it'd take a big correction
- [2026-05-04T11:40:04Z] (original) Dropped $HIMS at a small loss - cash was used to buy SK Square ($402340) today.  My portfolio today: $NBIS 60% $KRKNF 4% $402340 (SK Square) 36%  The rest of the small positions were dropped ( $SHMD, 
- [2026-04-26T05:02:09Z] (original) Some potential high fliers I'm looking at that don't have as much X following: $LPK / $LPKFF - Glass substrates, an AI supply chain bottleneck, confirmed by $INTC in their latest earnings  $SHMD - Sam
