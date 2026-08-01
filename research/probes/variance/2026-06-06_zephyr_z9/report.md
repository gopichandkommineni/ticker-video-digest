# Variance Probe: @zephyr_z9

Window: 2026-01-01 → 2026-06-06  |  Runs per provider: 3

## GetXAPI

**VERDICT: VARIABLE (count spread 74%)**

| run | tweets | reached_floor | earliest_utc | 429s | aborted |
|-----|-------:|:-------------:|--------------|-----:|:-------:|
| 1 | 3610 | True | 2026-01-01T03:52:16Z | 0 | False |
| 2 | 940 | True | 2026-04-21T22:06:32Z | 0 | False |
| 3 | 3612 | True | 2026-01-01T03:52:16Z | 0 | False |

**Same-provider ID overlap (run 1 as baseline)**

| compared | ∩ (shared) | run1-only | runN-only | overlap % |
|----------|----------:|----------:|----------:|----------:|
| run1 vs run2 | 940 | 2670 | 0 | 26.0% |
| run1 vs run3 | 3609 | 1 | 3 | 99.9% |

## twitterapi.io

**VERDICT: STABLE**

| run | tweets | reached_floor | earliest_utc | 429s | aborted |
|-----|-------:|:-------------:|--------------|-----:|:-------:|
| 1 | 3616 | True | 2026-01-01T03:52:16Z | 0 | False |
| 2 | 3615 | True | 2026-01-01T03:52:16Z | 0 | False |
| 3 | 3615 | True | 2026-01-01T03:52:16Z | 0 | False |

**Same-provider ID overlap (run 1 as baseline)**

| compared | ∩ (shared) | run1-only | runN-only | overlap % |
|----------|----------:|----------:|----------:|----------:|
| run1 vs run2 | 3612 | 4 | 3 | 99.8% |
| run1 vs run3 | 3612 | 4 | 3 | 99.8% |

## Cross-provider union

| metric | count |
|--------|------:|
| GetXAPI union (all runs) | 3613 |
| twitterapi.io union (all runs) | 3622 |
| shared (∩) | 3610 |
| GetXAPI-only | 3 |
| twitterapi.io-only | 12 |
| **combined union** | **3625** |
| lift over GetXAPI alone | +12 (0.3%) |
| lift over twitterapi.io alone | +3 (0.1%) |

## Sample tweets (cashtag-ranked)

- [2026-06-05T09:13:48Z] (quote) Pretty good for TTMI  "U.S. Congress are pushing the Protecting Circuit Boards and Substrates Act, offering a 25% tax credit to companies choosing U.S.-made PCBs and planning to allocate $3 billion to
- [2026-04-14T13:05:52Z] (quote) "We observed that the OCS ratio in Scale Up scenarios is still rising rapidly, and we also found that $MRVL is involved not only in TPU but also in LPU."
- [2026-04-08T06:40:42Z] (original) PSUs from Delta &amp; $AEIS have a 16-32 week lead time now
- [2026-06-06T20:31:26Z] (reply) @racetrack275 @lithos_graphein Ask them about DUVi demand due to more memory (NAND/DRAM) and how fast can they ramp EUV production if needed
- [2026-06-06T16:41:42Z] (reply) @9527qingfeng @fi56622380 yeah
- [2026-06-06T16:18:57Z] (reply) @fi56622380 "Users will be able to manually add and install DRAM themselves. Vera, which features 8 SOCAMM slots per CPU"  Users will have to replace the 96GB SOCAMM with 192GB SOCAMM if they want to 
- [2026-06-06T11:47:14Z] (quote) They can probably get around 700GB-800GB from one D1a node wafer (HBM dies with TSVs) Most Chinese accelerators have 144GB of HBM So they can ship 400k-450k XPUs per month from 100k WPM capacity
- [2026-06-06T11:35:21Z] (quote) Alleged Ascend 950DT GPU https://t.co/mwEs3ifJvY
- [2026-06-06T10:31:10Z] (reply) @tphuang @teortaxesTex They in source, use CXMT and XMC
- [2026-06-06T10:07:35Z] (quote) Nvidia is offering dual configs 1.5TB per CPU for racks assigned to agentic workloads 750GB per CPU for the rest of the stuff
