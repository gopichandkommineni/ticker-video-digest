# Variance Probe: @speculator_io

Window: 2026-01-01 → 2026-06-06  |  Runs per provider: 3

## GetXAPI

**VERDICT: STABLE**

| run | tweets | reached_floor | earliest_utc | 429s | aborted |
|-----|-------:|:-------------:|--------------|-----:|:-------:|
| 1 | 151 | True | 2026-01-01T22:02:44Z | 0 | False |
| 2 | 151 | True | 2026-01-01T22:02:44Z | 0 | False |
| 3 | 154 | True | 2026-01-01T22:02:44Z | 0 | False |

**Same-provider ID overlap (run 1 as baseline)**

| compared | ∩ (shared) | run1-only | runN-only | overlap % |
|----------|----------:|----------:|----------:|----------:|
| run1 vs run2 | 151 | 0 | 0 | 100.0% |
| run1 vs run3 | 151 | 0 | 3 | 98.1% |

## twitterapi.io

**VERDICT: STABLE**

| run | tweets | reached_floor | earliest_utc | 429s | aborted |
|-----|-------:|:-------------:|--------------|-----:|:-------:|
| 1 | 151 | True | 2026-01-01T22:02:44Z | 0 | False |
| 2 | 151 | True | 2026-01-01T22:02:44Z | 0 | False |
| 3 | 151 | True | 2026-01-01T22:02:44Z | 0 | False |

**Same-provider ID overlap (run 1 as baseline)**

| compared | ∩ (shared) | run1-only | runN-only | overlap % |
|----------|----------:|----------:|----------:|----------:|
| run1 vs run2 | 151 | 0 | 0 | 100.0% |
| run1 vs run3 | 151 | 0 | 0 | 100.0% |

## Cross-provider union

| metric | count |
|--------|------:|
| GetXAPI union (all runs) | 154 |
| twitterapi.io union (all runs) | 151 |
| shared (∩) | 151 |
| GetXAPI-only | 3 |
| twitterapi.io-only | 0 |
| **combined union** | **154** |
| lift over GetXAPI alone | +0 (0.0%) |
| lift over twitterapi.io alone | +3 (2.0%) |

## Sample tweets (cashtag-ranked)

- [2026-05-31T21:35:59Z] (original) The Leadings Stocks in 2026:  Market Leaders $SNDK Sandisk +593.67% $MU Micron +229.01% $DELL Dell +227.94% $BE Bloom Energy +214.67% $ARM Arm +213.12% $STX Seagate +212.02% $WDC Western Digital +199.
- [2026-05-14T19:54:17Z] (original) This is Trump's personal portfolio:  $AVGO Broadcom $DELL Dell $TXN Texas Instruments $DVA DaVita $JBL Jabil $KLAC KLA $COMT GSCI Commodity ETF $FFIV F5 $GOOGL Alphabet $ETN Eaton $NVDA NVIDIA $XLK Te
- [2026-03-17T22:31:07Z] (original) Focus on the leading stocks:  Market Leaders $SNDK Sandisk +194.73% $WDC Western Digital +77.09% $BE Bloom Energy +76.71% $ESLT Elbit Systems +73.68% $LITE Lumentum +71.22% $CRCL Circle +63.67% $ENLT 
- [2026-03-10T21:08:22Z] (quote) 𝗧𝗵𝗲 𝗙𝗶𝘃𝗲 𝗟𝗮𝘆𝗲𝗿𝘀 𝗼𝗳 𝘁𝗵𝗲 𝗔𝗜 𝗥𝗲𝘃𝗼𝗹𝘂𝘁𝗶𝗼𝗻  Layer 1: Energy $UEC $BE $GEV $PWR $AMPX $VICR $VST $NVTS $BWXT $LEU $CEG  Layer 2: Chips $NVDA $TSM $AVGO $AMD $ASML $ARM $MRVL $AAOI $AXTI $COHR $MU $SNDK $STX 
- [2026-01-27T22:30:22Z] (original) Focus on the leading stocks:  Market Leaders $SNDK Sandisk $BE Bloom Energy $CRWV CoreWeave $WDC Western Digital $MU Micron $CCJ Cameco Corp $LRCX Lam Research $STX Seagate $ASML ASML $KLAC KLA $ESLT 
- [2026-01-17T21:48:41Z] (quote) Here’s a simple investing cheat sheet:  • AI: $GOOGL  • chips: $TSM $ASML $NVDA $SKYT • space: $RKLB $ASTS $PL $FLY $RDW • crypto: $FIGR $GLXY $IREN $HUT  • energy: $BE $GEV $PWR  • drones: $ONDS $UMA
- [2026-01-06T20:44:42Z] (original) 𝗧𝗵𝗲 𝗟𝗲𝗮𝗱𝗶𝗻𝗴 𝗦𝘁𝗼𝗰𝗸𝘀 𝗶𝗻 𝟮𝟬𝟮𝟲  𝗠𝗮𝗿𝗸𝗲𝘁 𝗟𝗲𝗮𝗱𝗲𝗿𝘀 $SNDK Sandisk $WDC Western Digital $RKLB Rocket Lab $LRCX Lam Research $SYM Symbotic $STX Seagate $TER Teradyne $MU Micron $KLAC KLA $CCJ Cameco Corp $ASML A
- [2026-01-01T22:02:44Z] (original) J.P. Morgan's Top Picks for 2026  $GOOGL Alphabet $AVGO Broadcom $LLY Eli Lilly $V Visa $XOM Exxon Mobil $CAT Caterpillar $CRM Salesforce $TMO Thermo Fisher $C Citigroup $DIS Disney $SCHW Charles Schw
- [2026-06-02T23:09:06Z] (quote) Jensen literally told you where to invest.  This is his 5-Layer AI Cake:  Layer 1: Energy $BE $GEV $PWR $AMPX $VICR $VST $NVTS $BWXT $CEG $UEC $CCJ  Layer 2: Chips $NVDA $TSM $INTC $AVGO $AMD $ASML $A
- [2026-05-29T16:04:08Z] (original) Trump has been telling you what to buy for months:  • AI: $DELL $MU $SNDK $WDC • chips: $INTC $AMD $NVDA $TSMC $ARM • space: $RKLB $PL $ASTS • crypto: $HOOD $CRCL $PURR • energy: $BE $GEV $FCEL $TE • 
