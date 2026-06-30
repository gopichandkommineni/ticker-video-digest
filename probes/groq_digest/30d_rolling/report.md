# Groq 30-Day Probe Report

**DESCRIPTIVE ANALYSIS ONLY — not investment advice.** Measures what
handles are *posting* (volume, ticker frequency, sector concentration).
No buy signals, no ranking by attractiveness, no recommendations.

- Database: `fintwit.db` · table `raw_tweets` (read-only)
- Window: last 30 days
- Provider: Groq · thesis `llama-3.1-8b-instant` · sector `llama-3.3-70b-versatile`

## Stage 1 — Volume (free, no LLM)

| Metric | Count |
|---|---:|
| Total non-deleted tweets (last 30d) | 2967 |
| Ticker-bearing tweets (cashtag regex) | 740 |
| Ratio | 24.9% |

## Stage 2 — Per-handle ticker profile (free, no LLM)

Deterministic counts. Handles sorted by ticker-bearing tweet volume.

- **@aleabitoreddit** — 443 tweets, 278 ticker-bearing; $SIVE (95), $NVDA (61), $AAOI (38), $LITE (36), $MRVL (25), $NBIS (24), $JBL (24), $XFAB (24), $SOI (21), $GFS (18), $MU (14), $AMD (13), $IREN (13), $IQE (13), $TSM (13), $POET (12), $GOOGL (12), $AXTI (11), $TSEM (11), $SNDK (11), $RDDT (11), $COHR (11), $INTC (11), $SPCX (10), $EWY (9), $LPK (8), $NOK (8), $AVGO (8), $AMZN (6), $RKLB (6), $META (6), $MTSI (6), $HOOD (6), $ARM (6), $POWI (5), $RPI (5), $WOLF (5), $MSFT (5), $TSLA (4), $ALAB (4), $AEHR (4), $NVTS (4), $CRWV (4), $AOSL (3), $ALRIB (3), $ON (3), $CIFR (3), $BKKT (3), $ASTS (2), $CBRS (2), $AEVA (2), $WEN (2), $BABA (2), $AAPL (2), $ASML (2), $WYFI (2), $WULF (2), $ASX (2), $VICR (2), $IBIT (2), $CRCL (2), $VPG (2), $SLNH (2), $COIN (2), $GM (1), $EOS (1), $QQQ (1), $DRAM (1), $MXL (1), $KOSPI (1), $SPY (1), $TOWA (1), $CAMT (1), $ACMR (1), $VRT (1), $HUT (1), $HIMX (1), $NFLX (1), $LRCX (1), $KLAC (1), $FN (1), $CLS (1), $AMKR (1), $YSS (1), $INHD (1), $XLU (1), $IFNNY (1), $LFUS (1), $VSH (1), $ENPH (1), $BDC (1), $EOSE (1), $SEDG (1), $CWR (1), $AMSC (1), $HYLN (1), $FCEL (1), $ASYS (1), $RELL (1), $PAY (1), $IPWR (1), $SNAP (1), $AMAT (1), $SHMD (1), $PL (1), $ETHA (1), $QCOM (1), $BRK (1), $HPS (1), $FLNC (1), $ASPI (1)
- **@spacanpanman** — 666 tweets, 180 ticker-bearing; $ASTS (79), $TE (34), $SPCX (14), $SHAZ (13), $RKLB (9), $BAER (8), $MRLN (8), $BCAR (7), $PL (6), $SPKL (5), $SPKLW (3), $ECON (3), $BRUN (2), $SRTA (2), $T (2), $WLAC (2), $BCARW (2), $TMUS (1), $KRKNF (1), $PNG (1), $CEPT (1), $SECZ (1), $SPACE (1), $AUR (1), $NXT (1), $CSIQ (1), $HAWK (1), $LIFE (1), $NBIS (1), $IREN (1), $BBC (1), $NPA (1)
- **@venu_7_** — 765 tweets, 139 ticker-bearing; $MU (18), $MRVL (17), $FPS (10), $SNOW (8), $STM (8), $CRDO (7), $NBIS (7), $FROG (7), $FSLR (7), $APH (6), $VSH (6), $BAND (6), $ALAB (5), $MCHP (5), $ICHR (5), $AMBQ (5), $QQQ (5), $DDOG (5), $FIVN (5), $LRCX (4), $ALGM (4), $RKLB (4), $TWLO (4), $NVDA (4), $TSLA (4), $INOD (4), $ARM (4), $TVTX (3), $TGTX (3), $GH (3), $XBI (3), $TXN (3), $ADI (3), $MPWR (3), $ON (3), $NVTS (3), $POWI (3), $WOLF (3), $IFNNY (3), $VICR (3), $AEIS (3), $DIOD (3), $AOSL (3), $AIXA (3), $ENTG (3), $RNECF (3), $ROHCY (3), $AMAT (3), $SNDK (3), $ACMR (3), $MDB (3), $VIAV (3), $ONDS (3), $LQDA (2), $AMD (2), $PLTR (2), $ALKS (2), $TWST (2), $RVMD (2), $RDDT (2), $HNGE (2), $LLY (2), $TTMI (2), $UCTT (2), $UMC (2), $SEZL (2), $CAVA (2), $GLD (2), $UNH (2), $OSCR (2), $FTNT (2), $DOCN (2), $AKAM (2), $JBHT (2), $PANW (2), $ORCL (2), $MP (2), $ABCL (1), $JAZZ (1), $ARGX (1), $HUT (1), $CRS (1), $ASTH (1), $MIRM (1), $DY (1), $TER (1), $HOOD (1), $NKE (1), $NVO (1), $PYPL (1), $FLNC (1), $LPG (1), $RSI (1), $VVX (1), $VCYT (1), $KRYS (1), $ARW (1), $COCO (1), $NBIX (1), $LINC (1), $INCY (1), $DAVE (1), $VIRT (1), $EVR (1), $CUBI (1), $ATLC (1), $TKO (1), $TTD (1), $KLAC (1), $ASML (1), $STX (1), $INTC (1), $DELL (1), $WDC (1), $VSXY (1), $TEV (1), $CEVA (1), $VIX (1), $SPY (1), $SLV (1), $MSTR (1), $CVS (1), $AMKR (1), $SN (1), $KEYS (1), $KEEL (1), $MRK (1), $JNJ (1), $ENPH (1), $SEDG (1), $NXT (1), $KLIC (1), $IONQ (1), $QNT (1), $NAVN (1), $CRWD (1), $RBRK (1), $NET (1), $LOGI (1), $APP (1), $GRAB (1), $HBM (1), $ETN (1), $UAMY (1), $USAR (1), $REMX (1), $MUU (1), $AMR (1), $AVGO (1), $AEVA (1)
- **@amitisinvesting** — 240 tweets, 45 ticker-bearing; $NVDA (17), $SPCX (17), $MSFT (13), $MU (12), $AAPL (12), $AMZN (12), $META (12), $GOOGL (11), $PLTR (11), $TSLA (11), $HOOD (8), $INTC (6), $AMD (6), $MRVL (6), $QQQ (5), $ORCL (5), $NOK (5), $NFLX (4), $RDDT (3), $SPY (3), $ZETA (3), $F (3), $AVGO (3), $CRWD (3), $SHOP (3), $GME (2), $CBRS (2), $QCOM (2), $SOFI (2), $SPX (2), $CRWV (2), $SNDK (2), $BTC (2), $PANW (2), $NOW (2), $WEN (1), $VZ (1), $SMH (1), $ASTS (1), $EBAY (1), $INFQ (1), $QBTS (1), $IBM (1), $RGTI (1), $IONQ (1), $QNT (1), $CVX (1), $DRAM (1), $SPCH (1), $IBIT (1), $SNAP (1), $NBIS (1), $RKLB (1), $TER (1), $ALAB (1), $SMCI (1), $SOXS (1), $QLD (1), $SSO (1), $GLW (1), $IREN (1), $MSTR (1), $UBER (1), $CRM (1), $IGV (1), $DDOG (1), $SNOW (1)
- **@kaizen_investor** — 165 tweets, 35 ticker-bearing; $PL (19), $WOLF (5), $RKLB (5), $MRVL (4), $SIVE (3), $ASTS (3), $SPCX (2), $ASML (2), $ASM (2), $GOOGL (2), $OUST (2), $PLTR (2), $FLNC (2), $MU (1), $SAP (1), $NASA (1), $SPIR (1), $BKSY (1), $ENHA (1), $AMZN (1), $SATL (1), $FLY (1), $LUNR (1), $POET (1), $NVDA (1), $TMDX (1), $AMPX (1), $IREN (1), $HIMS (1)
- **@michaelsikand** — 179 tweets, 29 ticker-bearing; $NOK (5), $AAOI (4), $BRUN (4), $MRVL (3), $KRKNF (3), $NBIS (3), $SPCX (2), $SATS (2), $LITE (2), $SKM (2), $ZM (2), $SIVE (2), $PENG (2), $LASR (2), $NVDA (2), $WEN (1), $RDDT (1), $NYT (1), $COHR (1), $RKLB (1), $ASTS (1), $STCK (1), $CRM (1), $COKE (1), $DELL (1), $RCAT (1), $AVAV (1), $KTOS (1), $AVEX (1), $EOS (1), $CIEN (1), $SGOV (1), $MXL (1), $HOOD (1), $DRAM (1), $GLXY (1), $CRWV (1), $IREN (1), $BE (1), $CRCL (1), $MU (1)
- **@kawzinvests** — 76 tweets, 27 ticker-bearing; $NVDA (10), $AAOI (5), $SKM (5), $LITE (4), $COHR (4), $CIEN (3), $BRUN (3), $CRWV (3), $FN (2), $CSCO (2), $STM (2), $DELL (2), $NBIS (2), $NOK (1), $KXIAY (1), $MU (1), $SNDK (1), $MRVL (1), $RDDT (1), $ZM (1), $PENG (1), $CRDO (1), $SMTC (1), $MTSI (1), $VRT (1), $PWR (1), $IFX (1), $MPWR (1), $VICR (1), $NVTS (1), $ON (1), $TXN (1), $ADI (1), $POWI (1), $DIOD (1), $WOLF (1), $AOSL (1), $APLD (1), $IBM (1), $ORCL (1), $HPE (1), $SMCI (1), $SNX (1), $TSM (1)
- **@speculator_io** — 9 tweets, 6 ticker-bearing; $SNDK (4), $DELL (4), $NBIS (4), $MU (3), $STX (3), $WDC (3), $DOCN (3), $BE (3), $HUT (3), $IREN (3), $RXT (2), $HYLN (2), $VPG (2), $AMBQ (2), $INTC (2), $FLEX (2), $GEV (2), $AMPX (2), $VICR (2), $NVTS (2), $AMD (2), $ARM (2), $MRVL (2), $AAOI (2), $AXTI (2), $OPTX (2), $ICHR (2), $AEHR (2), $CRWV (2), $APLD (2), $VRT (2), $HPE (2), $ORCL (2), $STM (1), $MCHP (1), $IFX (1), $ON (1), $WOLF (1), $STRL (1), $SILC (1), $HIMX (1), $PWR (1), $VST (1), $BWXT (1), $CEG (1), $UEC (1), $CCJ (1), $NVDA (1), $TSM (1), $AVGO (1), $ASML (1), $COHR (1), $LITE (1), $GOOGL (1), $META (1), $AMZN (1), $TSLA (1), $NOW (1), $PLTR (1), $SNOW (1), $NET (1), $FSLY (1), $INOD (1), $IBM (1), $CDNS (1), $J (1), $PCOR (1), $PTC (1), $SIE (1), $SU (1), $DSY (1), $TT (1), $ABBN (1), $CAT (1), $ETN (1), $ENGI (1), $DLR (1), $EQIX (1), $SIFY (1), $SMCI (1), $DGXX (1), $HIVE (1), $WYFI (1), $BTDR (1), $RIOT (1), $CLSK (1), $CORZ (1), $CIFR (1), $CIEN (1), $ASX (1), $ENLT (1), $NOK (1), $GLW (1), $RKLB (1), $ALAB (1), $MXL (1), $VSH (1), $VIAV (1), $PL (1), $SEDG (1), $BLDP (1), $SATL (1), $MX (1), $SPIR (1), $CPSH (1), $FEL (1), $PURR (1), $PENG (1), $MRAM (1), $BKSY (1), $OSS (1), $UMAC (1), $USAR (1)
- **@zephyr_z9** — 424 tweets, 1 ticker-bearing; $TTM (1)

## Stage 3 — Sector grouping (LLM, probe-only)

> ⚠️ **Probe-only.** Sectors are assigned by a single Groq call and the
> model can miscategorize. Production would use a deterministic map.

Unique tickers across all handles: **355**


### Overall sector concentration (by total mentions)

| Sector | Mentions | Tickers |
|---|---:|---|
| semiconductors | 480 | $ACMR, $ADI, $AEHR, $AEIS, $AMAT, $AMD, $AMKR, $AOSL, $APH, $ARM, $ASM, $ASML, $ASX, $ASYS, $AVGO, $AXTI, $CEVA, $DIOD, $ENTG, $FLEX, $HIMX, $ICHR, $IFX, $INTC, $IQE, $KLAC, $KLIC, $LRCX, $MCHP, $MPWR, $MRAM, $MRVL, $MU, $MXL, $NVDA, $ON, $QCOM, $SMTC, $STM, $TER, $TSEM, $TSM, $TTMI, $TXN, $UMC, $VSH, $XFAB |
| biotech | 420 | $ABCL, $AEVA, $AIXA, $ALAB, $ALKS, $ALRIB, $ARGX, $ASPI, $ASTH, $AVEX, $BAER, $BBC, $BCAR, $BCARW, $BRUN, $CAVA, $CEPT, $CLS, $CLSK, $COCO, $CORZ, $CPSH, $CRCL, $CRDO, $ENHA, $EOSE, $FEL, $FLNC, $FROG, $GH, $GLXY, $HAWK, $INCY, $INHD, $INOD, $IREN, $J, $JAZZ, $KEEL, $KRKNF, $KRYS, $KXIAY, $LFUS, $LIFE, $LINC, $LLY, $LQDA, $MIRM, $MRK, $MRLN, $NAVN, $NBIS, $NBIX, $NPA, $NVO, $NVTS, $OPTX, $OSCR, $OUST, $PCOR, $PURR, $RCAT, $RDDT, $RELL, $RGTI, $RKLB, $RNECF, $ROHCY, $RPI, $RVMD, $RXT, $SECZ, $SEZL, $SHAZ, $SHMD, $SILC, $SIVE, $SLNH, $SRTA, $SSO, $TEV, $TGTX, $TKO, $TMDX, $TOWA, $TVTX, $VCYT, $VICR, $VRT, $VSXY, $YSS |
| software | 352 | $AAPL, $ALGM, $AMBQ, $AMPX, $AMR, $APLD, $APP, $ARW, $BAND, $BE, $BKKT, $BKSY, $BTDR, $CAMT, $CDNS, $CIFR, $CRM, $CRWD, $CRWV, $DAVE, $DDOG, $DGXX, $DOCN, $DRAM, $DSY, $DY, $ECON, $EOS, $ETHA, $EVR, $FIVN, $FN, $FSLY, $FTNT, $GFS, $HIVE, $HUT, $IBIT, $IBM, $INFQ, $KEYS, $MDB, $MP, $MSFT, $MSTR, $MUU, $NOW, $NXT, $ONDS, $ORCL, $OSS, $PANW, $PAY, $PL, $PLTR, $PTC, $QBTS, $QNT, $RBRK, $RIOT, $RSI, $SAP, $SGOV, $SIFY, $SMCI, $SN, $SNDK, $SNOW, $SNX, $SOI, $SPCH, $SPKL, $SPKLW, $STCK, $TT, $TTD, $TWLO, $TWST, $UCTT, $UMAC, $VIRT, $VPG, $VST, $WOLF, $WULF, $ZETA, $ZM |
| energy | 112 | $AMSC, $BLDP, $BWXT, $CCJ, $CEG, $CSIQ, $CVX, $CWR, $ENGI, $ENLT, $ENPH, $FCEL, $FPS, $FSLR, $GEV, $HNGE, $HPS, $HYLN, $IPWR, $LPG, $PENG, $PNG, $POET, $POWI, $PWR, $SEDG, $SU, $TE, $UEC, $WEN |
| optical/photonics | 94 | $AAOI, $LASR, $LITE |
| space | 88 | $ASTS, $LUNR, $SPACE |
| etf | 87 | $EWY, $GLD, $IGV, $KOSPI, $QLD, $QQQ, $REMX, $SLV, $SMH, $SOXS, $SPCX, $SPX, $SPY, $VIX, $VVX, $XBI, $XLU |
| internet | 84 | $AKAM, $AMZN, $BABA, $EBAY, $GOOGL, $GRAB, $META, $NET, $NFLX, $SHOP, $SNAP, $UBER |
| telecom | 54 | $ABBN, $ATLC, $CBRS, $CIEN, $CSCO, $MTSI, $NOK, $STRL, $T, $TMUS, $USAR, $VIAV, $VZ, $WYFI |
| hardware | 44 | $DELL, $HPE, $JBL, $LOGI, $STX, $WDC |
| automotive | 29 | $F, $GM, $IFNNY, $TSLA, $TTM |
| finance | 27 | $BDC, $BTC, $COIN, $CUBI, $HOOD, $PYPL, $SOFI, $WLAC |
| industrials | 22 | $CAT, $COHR, $CRS, $ETN, $SIE |
| materials | 20 | $GLW, $HBM, $LPK, $MX, $SKM, $UAMY |
| aerospace | 9 | $FLY, $KTOS, $NASA, $SATL, $SATS, $SPIR |
| healthcare | 5 | $CVS, $HIMS, $JNJ, $UNH |
| ai infrastructure | 3 | $AVAV, $IONQ |
| retail | 2 | $GME |
| consumer goods | 2 | $COKE, $NKE |
| transportation | 2 | $JBHT |
| real estate | 2 | $DLR, $EQIX |
| mining | 1 | $AUR |
| conglomerate | 1 | $BRK |
| media | 1 | $NYT |

### Per-handle sector concentration (by mentions)

- **@aleabitoreddit** — semiconductors (234), biotech (184), software (86), optical/photonics (74), internet (28), energy (27), hardware (24), etf (23), telecom (18), industrials (11), finance (9), materials (8), automotive (6), space (2), conglomerate (1)
- **@spacanpanman** — space (80), biotech (60), energy (36), software (18), etf (14), telecom (3), finance (2), mining (1)
- **@venu_7_** — semiconductors (121), biotech (94), software (83), energy (25), etf (15), automotive (7), telecom (5), hardware (4), healthcare (4), internet (4), finance (3), industrials (2), transportation (2), materials (2), consumer goods (1), ai infrastructure (1)
- **@amitisinvesting** — software (67), semiconductors (53), internet (45), etf (31), automotive (14), finance (12), biotech (9), telecom (8), energy (2), retail (2), space (1), ai infrastructure (1), materials (1)
- **@kaizen_investor** — software (29), biotech (15), semiconductors (10), aerospace (4), space (4), internet (3), etf (2), energy (1), healthcare (1)
- **@michaelsikand** — biotech (19), software (9), optical/photonics (8), semiconductors (7), telecom (6), energy (3), aerospace (3), etf (2), materials (2), media (1), industrials (1), space (1), consumer goods (1), hardware (1), ai infrastructure (1), finance (1)
- **@kawzinvests** — semiconductors (23), software (13), biotech (11), optical/photonics (9), telecom (7), materials (5), industrials (4), energy (3), hardware (3)
- **@speculator_io** — software (47), semiconductors (32), biotech (28), energy (15), hardware (12), telecom (7), industrials (4), internet (4), optical/photonics (3), real estate (2), materials (2), aerospace (2), automotive (1)
- **@zephyr_z9** — automotive (1)

## Stage 4 — Thesis extraction (LLM, ticker-bearing only)

Descriptive structure per tweet: thesis, whether the claim is
falsifiable, its horizon and a checkpoint, and the stance.

Batched **30/call** on `llama-3.1-8b-instant`, paced under the
free-tier TPM; every 429 honors `retry-after` and the run continues.

_Ledger (`thesis.jsonl`): 726 already extracted; **15** remaining this run._


Thesis ledger now holds **741** of 740 ticker-bearing tweets (**+15** this run).

Stance distribution: opinion (252), prediction (186), news (171), other (95), question (22), promotion (14), (blank) (1)

| Handle | Tickers | Stance | Falsifiable | Horizon | Thesis |
|---|---|---|---|---|---|
| @spacanpanman | $RKLB | news | True | none | Rocket Lab is acquiring Iridium in a historic deal. |
| @aleabitoreddit | $ASTS, $SPCX | news | True | none | Rakuten is establishing a joint venture with ASTS to build out LEO satellite networks for Japan. |
| @spacanpanman | $ASTS | news | True | none | ASTS has won the J-LEO project. |
| @spacanpanman | $ASTS | opinion | False | none | AST SpaceMobile is a big player in Japan. |
| @spacanpanman | $ASTS | news | True | none | Japan's Ministry of Internal Affairs and Communications is expected to select Rakuten and AST SpaceMobile for the $1 billion J-LEO project. |
| @aleabitoreddit | $GM, $NVDA, $AMZN | prediction | True | none | GM is cutting 1,000 workers and replacing them with 50 robots, demonstrating increased opex margins and efficiency from employee automation. |
| @amitisinvesting | $MU, $NVDA, $AAPL | news | True | none | Micron is now a top 10 holding in the S&P 500. |
| @aleabitoreddit | $POET | opinion | False | none | The author has read the $POET AGM transcript and compared it to what markets might have known already. |
| @aleabitoreddit | $POET, $LITE, $SIVE, $AAOI | prediction | True | 2029 | The top three laser suppliers control 68% of the market and are completely sold out for the next two years. |
| @aleabitoreddit | $RKLB, $SPCX, $EOS, $LITE, $TSLA | opinion | False | none | This decade from 2020-2030 might be the most goated in human history. |
| @venu_7_ | $ABCL, $JAZZ | prediction | True | none | $ABCL is ready to run with a monster base. |
| @venu_7_ | $MU, $ALAB, $ARGX, $TVTX, $LQDA, $HUT, $CRDO, $AMD, $TGTX, $CRS, $ASTH, $GH, $MIRM, $LRCX, $DY | opinion | False | none | The IBD Top 15 is a quick way to see where institutional money is flowing. |
| @venu_7_ | $PLTR | opinion | False | none | $PLTR is at a very interesting spot. |
| @venu_7_ | $TER | prediction | False | none | There is a hidden robotics play. |
| @venu_7_ | $SNOW | prediction | True | none | $SNOW is ready to begin a Stage 2 uptrend. |
| @aleabitoreddit | $META, $NBIS, $GOOGL | news | True | none | $META signed massive agreements with Neoclouds like $NBIS back in March. |
| @spacanpanman | $TE | opinion | False | none | $TE is a hot stock. |
| @aleabitoreddit | $CBRS | opinion | False | none | $CBRS is a cautionary position. |
| @aleabitoreddit | $CBRS, $JBL | news | True | none | OpenAI's 5.6 Sol frontier model is launching on $CBRS. |
| @aleabitoreddit | $SIVE | prediction | True | none | $SIVE will benefit from the Mesh acquisition. |
| @spacanpanman | $ASTS | opinion | True | none | The T-Mobile / Starlink partnership looks like a big strategic mistake. |
| @aleabitoreddit | $SPCX, $SIVE, $POET, $LITE, $MTSI | news | True | none | SpaceX has acquired Mesh, an optical networking startup. |
| @aleabitoreddit | $SIVE | news | True | none | $SIVE has dropped the employee incentive program. |
| @aleabitoreddit | $NBIS | opinion | False | none | The author has been supported by their followers. |
| @aleabitoreddit | $SIVE, $JBL, $GFS, $AMD, $NVDA, $POET, $AEVA, $MRVL | opinion | False | none | $SIVE is undervalued. |
| @aleabitoreddit | $SIVE, $EWY, $NBIS, $IREN, $QQQ, $LITE | opinion | False | none | The author has conviction in their hyperscaler mapping research with $SIVE. |
| @aleabitoreddit | $SIVE, $AAOI | prediction | True | 2027 | $SIVE and $AAOI will revenue ramp with lasers in 2027. |
| @aleabitoreddit | $MU | prediction | True | none | There is massive demand and price hikes for $MU / SK Hynix / Samsung memory relative to supply. |
| @aleabitoreddit | $SOI, $RKLB | opinion | False | none | There is a global correction right now. |
| @aleabitoreddit | $AXTI, $AAOI, $TSEM, $LITE, $MU, $SNDK, $EWY, $SIVE, $IQE, $SOI | opinion | False | none | High beta stocks get hit a lot harder during corrections. |
| @aleabitoreddit | $JBL, $SIVE | news | False | none | none |
| @aleabitoreddit | $AAOI, $AMD | opinion | True | next year | photonics theme selloff combined with macro drop will negatively impact $AAOI |
| @aleabitoreddit | $AOSL, $POWI | prediction | True | before the 800V DC shift fully hits | Power Semis are already starting price hikes, which is bullish thematically for US power semi trade |
| @spacanpanman | $BAER | promotion | False | none | none |
| @michaelsikand | $WEN | opinion | True | none | $1T company is up more pre-market than WSB's latest meme stock $WEN |
| @kaizen_investor | $MU | prediction | True | none | $MU earnings will positively impact Sk Hynix |
| @aleabitoreddit | $WEN, $RDDT | news | False | none | $WEN meme traders made it to Global Media from Japan to US |
| @aleabitoreddit | $MU, $TSM, $TSLA | news | True | before the decade is out | $MU CEO predicts a multi-decade memory demand cycle driven by humanoid robots |
| @kawzinvests | $NOK | opinion | False | none | The Infinera acquisition really was a massive turning point for $NOK |
| @kawzinvests | $KXIAY, $MU, $SNDK | prediction | True | around april or may 2027 | $KXIAY $MU $SNDK will be impacted by Kioxia's US depositary shares |
| @aleabitoreddit | $AXTI, $SOI, $AAOI | opinion | True | none | Diversified Losses strategy will help mitigate losses |
| @venu_7_ | $MU | prediction | True | none | $MU is generating $33B in operating profit with 85% gross margins |
| @aleabitoreddit | $DRAM, $MU, $SNDK | opinion | False | none | $DRAM is one of the more positive ETFs |
| @aleabitoreddit | $BABA | opinion | True | none | $BABA Qwen AI lab's distilling of frontier AI models will have consequences |
| @aleabitoreddit | $BABA | news | False | none | $BABA Qwen AI lab has been accused of distilling frontier AI models |
| @michaelsikand | $NOK | news | False | none | $NOK is officially a Trump stock |
| @aleabitoreddit | $JBL, $SIVE, $MRVL, $MXL, $TSEM | opinion | False | none | OpenLight (private) is getting bigger and bigger |
| @aleabitoreddit | $AMZN, $TSLA, $GOOGL | opinion | True | none | Capex for massive revenue increase or margin increase is not 'siphoned off' |
| @amitisinvesting | $RDDT | promotion | False | none | none |
| @amitisinvesting | $MU | opinion | True | none | People who missed semis are deciding to turn random names into their own version of $MU |
| @venu_7_ | $HOOD | prediction | True | none | $HOOD is a strong stock with institutional accumulation |
| @amitisinvesting | $WEN | news | False | none | $WEN is up 20% overnight as the stock is going viral on r/WallStreetBets |
| @venu_7_ | $TGTX, $TVTX, $ALKS, $TWST, $RVMD, $LQDA, $XBI | opinion | False | none | Names like $TGTX $TVTX $ALKS $TWST $RVMD & $LQDA look great |
| @aleabitoreddit | $RDDT, $WEN | news | False | none | Degens on $RDDT are starting a viral campaign to save Wendy’s ( $WEN ) |
| @venu_7_ | $MU, $NKE, $NVO, $PYPL | opinion | True | none | $MU isn't a pre-revenue story stock trading on hopes and dreams |
| @spacanpanman | $BAER | promotion | False | none | none |
| @amitisinvesting | $SPY, $SPCX, $MU, $GOOGL, $VZ, $AMZN, $AAPL, $MSFT, $NVDA, $META, $SMH, $PLTR, $ZETA, $ASTS, $GME, $EBAY, $CBRS | news | False | none | Markets were under pressure today, with the S&P $SPY down ~1.5% |
| @amitisinvesting | $MU | question | False | none | none |
| @venu_7_ | $GH | opinion | True | none | The stock $GH found support at the 200-day SMA during the last pullback, which is a sign of a leader within its group. |
| @aleabitoreddit | $KOSPI, $EWY | opinion | True | none | Bank of America's predictions are often wrong and can cause retail investors to sell their positions. |
| @aleabitoreddit | $SIVE, $AAPL | opinion | False | none | none |
| @spacanpanman | $BAER | prediction | False | none | none |
| @aleabitoreddit | $LITE, $COHR | opinion | False | none | none |
| @aleabitoreddit | $LITE, $NVDA, $AMD, $AAOI, $SIVE, $SOI, $TSEM | opinion | False | none | none |
| @aleabitoreddit | $ALAB, $MRVL | prediction | False | none | none |
| @amitisinvesting | $SPCX, $NVDA, $PLTR, $TSLA, $AMZN, $AAPL, $GOOGL, $MSFT, $NFLX, $INTC, $QCOM, $INFQ, $QBTS, $IBM, $RGTI, $IONQ, $QNT, $MU, $CVX | news | False | none | none |
| @aleabitoreddit | $TSM | opinion | False | none | none |
| @aleabitoreddit | $IREN, $NBIS | opinion | False | none | none |
| @aleabitoreddit | $IREN, $NBIS | opinion | False | none | none |
| @aleabitoreddit | $NBIS, $IREN | opinion | False | none | none |
| @kawzinvests | $MRVL | news | False | none | none |
| @spacanpanman | $SHAZ | news | False | none | none |
| @kaizen_investor | $SAP | opinion | False | none | none |
| @michaelsikand | $MRVL | prediction | False | none | none |
| @aleabitoreddit | $LPK, $AEHR | prediction | False | none | none |
| @venu_7_ | $RDDT | prediction | False | none | none |
| @venu_7_ | $MCHP | prediction | False | none | none |
| @venu_7_ | $FLNC | prediction | False | none | none |
| @aleabitoreddit | $SIVE | prediction | False | none | none |
| @aleabitoreddit | $NVDA, $TSM | opinion | False | none | none |
| @aleabitoreddit | $SPY | prediction | False | none | none |
| @venu_7_ | $HNGE | prediction | False | none | none |
| @venu_7_ | $MU, $NBIS, $MRVL, $FPS | opinion | False | none | none |
| @venu_7_ | $TXN, $ADI, $MCHP, $APH, $MPWR, $ON, $STM, $NVTS, $POWI, $WOLF, $IFNNY, $VICR, $AEIS, $VSH, $ALGM, $DIOD, $AOSL, $AIXA, $ENTG, $ICHR, $AMBQ, $RNECF, $ROHCY | other | False | none | none |
| @venu_7_ | $RNECF, $ROHCY | other | False | none | none |
| @venu_7_ | $AIXA, $ENTG, $ICHR, $AMBQ | other | False | none | none |
| @venu_7_ | $VSH, $ALGM, $DIOD, $AOSL | other | False | none | none |
| @venu_7_ | $VICR, $AEIS | other | False | none | none |
| @venu_7_ | $ON, $STM, $NVTS, $POWI, $WOLF, $IFNNY | other | False | none | none |
| @venu_7_ | $TXN, $ADI, $APH, $MCHP, $MPWR, $MRVL, $FPS | other | False | none | none |
| @venu_7_ | $TXN, $ADI, $MCHP, $APH, $MPWR, $ON, $STM, $NVTS, $POWI, $WOLF, $IFNNY, $VICR, $AEIS, $VSH, $ALGM, $DIOD, $AOSL, $AIXA, $ENTG, $ICHR, $AMBQ, $RNECF, $ROHCY | news | False | none | none |
| @venu_7_ | $GH | prediction | True | short-term | $GH is in a massive stage 2 uptrend. |
| @venu_7_ | $XBI, $TGTX, $TVTX, $ALKS, $TWST, $RVMD | prediction | True | short-term | $XBI is in a massive stage 2 uptrend with clear institutional accumulation. |
| @venu_7_ | $STM | opinion | True | short-term | $STM is one of the best-looking semiconductor names in the market today. |
| @aleabitoreddit | $LITE, $SIVE | other | False | none | none |
| @aleabitoreddit | $JBL, $SIVE, $NVDA | other | False | none | none |
| @aleabitoreddit | $POET, $GFS | other | False | none | none |
| @aleabitoreddit | $SIVE, $JBL, $POET, $MRVL, $GFS | opinion | True | short-term | $SIVE is the laser supplier for next gen architectures, not just CPO scale up. |
| @aleabitoreddit | $COHR, $LITE, $NVDA, $AMD | other | False | none | none |
| @aleabitoreddit | $SNDK | opinion | True | long-term | $SNDK could triple company valuations if they followed $SNDK's pricing strategy. |
| @aleabitoreddit | $LITE, $COHR | other | False | none | none |
| @aleabitoreddit | $AAOI, $COHR, $LITE, $SIVE, $JBL, $GFS | other | False | none | none |
| @aleabitoreddit | $SNDK | other | False | none | none |
| @aleabitoreddit | $HOOD | other | False | none | none |
| @venu_7_ | $MU | other | False | none | none |
| @aleabitoreddit | $ASML, $TOWA, $LPK | other | False | none | none |
| @spacanpanman | $SHAZ, $BCAR | other | False | none | none |
| @aleabitoreddit | $CAMT, $WYFI, $SIVE, $ACMR | other | False | none | none |
| @aleabitoreddit | $RPI | other | False | none | none |
| @aleabitoreddit | $EWY | other | False | none | none |
| @aleabitoreddit | $XFAB | prediction | True | long-term | $XFAB is a 2027/2028 play. |
| @aleabitoreddit | $AAOI | other | False | none | none |
| @michaelsikand | $RDDT, $NYT | other | False | none | none |
| @aleabitoreddit | $INTC | other | False | none | none |
| @aleabitoreddit | $ASML | other | False | none | none |
| @spacanpanman | $ASTS | news | False | none | none |
| @kaizen_investor | $WOLF | opinion | True | short-term | $WOLF is one of the most undervalued AI stocks at the moment. |
| @kaizen_investor | $SIVE | other | False | none | none |
| @kaizen_investor | $MRVL | opinion | True | short-term | $MRVL is a great company with a lot of tailwinds. |
| @aleabitoreddit | $AAOI, $SIVE, $COHR | other | False | none | none |
| @aleabitoreddit | $ALRIB | news | False | none | none |
| @spacanpanman | $ASTS | news | False | none | none |
| @amitisinvesting | $AMD, $HOOD, $AAPL, $SPCX, $NVDA, $GOOGL, $META, $SPY, $QQQ, $AMZN, $MSFT, $TSLA, $SOFI, $MU, $DRAM | news | False | none | none |
| @aleabitoreddit | $RDDT | prediction | False | none | none |
| @spacanpanman | $BAER | news | False | none | none |
| @spacanpanman | $ASTS | news | False | none | none |
| @spacanpanman | $ASTS | other | False | none | none |
| @spacanpanman | $ASTS | other | False | none | none |
| @spacanpanman | $SHAZ | news | False | none | none |
| @spacanpanman | $ASTS | news | False | none | none |
| @kaizen_investor | $PL, $RKLB | opinion | False | none | none |
| @spacanpanman | $ASTS | news | False | none | none |
| @spacanpanman | $ASTS | news | False | none | none |
| @spacanpanman | $ASTS | news | False | none | none |
| @spacanpanman | $ASTS | news | False | none | none |
| @aleabitoreddit | $SIVE | opinion | False | none | none |
| @spacanpanman | $ASTS | news | False | none | none |
| @spacanpanman | $ASTS | other | False | none | none |
| @aleabitoreddit | $INTC | opinion | False | none | none |
| @aleabitoreddit | $INTC | opinion | False | none | none |
| @aleabitoreddit | $AEHR, $AAOI | opinion | False | none | none |
| @amitisinvesting | $SPCH, $IBIT, $SPCX, $SPX, $TSLA, $NVDA, $AAPL, $INTC, $NFLX, $MU, $AMZN, $MSFT, $SOFI, $HOOD, $SNAP | news | False | none | none |
| @aleabitoreddit | $AAOI, $AMD, $NVDA, $LITE, $NBIS | opinion | False | none | none |
| @spacanpanman | $ASTS | other | False | none | none |
| @spacanpanman | $ASTS | other | False | none | none |
| @michaelsikand | $SPCX, $SATS | prediction | False | none | none |
| @kaizen_investor | $NASA | question | False | none | none |
| @kaizen_investor | $PL | opinion | False | none | none |
| @spacanpanman | $ASTS, $RKLB, $PL, $SPCX | prediction | False | none | none |
| @spacanpanman | $ASTS | other | False | none | none |
| @spacanpanman | $RKLB | prediction | True | short-term | Rocket Lab's stock will increase due to KeyBanc's upgrade and the rapidly growing space sector. |
| @aleabitoreddit | $SIVE | news | False | none | The author is waiting for a general meeting to happen. |
| @aleabitoreddit | $IQE | news | False | none | The author is welcoming someone. |
| @aleabitoreddit | $IQE, $TSEM, $MTSI | prediction | True | short-term | $IQE and $TSEM signing a multi-year InP epiwafer deal will have a positive impact on IQE's stock. |
| @aleabitoreddit | $WOLF | prediction | True | short-term | $WOLF's stock will increase due to market support and subsidies. |
| @aleabitoreddit | $SIVE, $LITE | prediction | True | short-term | $SIVE's stock will increase due to EU macro positivity, $LITE's price increase, and a possible Nasdaq listing timeline announcement. |
| @aleabitoreddit | $WOLF, $LITE, $SPCX | prediction | True | short-term | The author believes that the market will go up due to Trump's actions and the successful IPO of $SPCX. |
| @aleabitoreddit | $POET | opinion | False | none | $POET has a lot of cash and can acquire other companies to scale. |
| @aleabitoreddit | $AXTI, $IQE, $AAOI, $LITE, $SIVE | prediction | True | short-term | China easing InP substrate exports will relieve mass production bottlenecks in the photonics market. |
| @aleabitoreddit | $NVTS, $POWI, $ON, $WOLF, $AOSL, $XFAB | prediction | True | short-term | $NVTS, $POWI, $ON, $WOLF, $AOSL, $XFAB, and others with power semi exposure will get a bump from Q3 pull forward. |
| @aleabitoreddit | $NVDA, $GOOGL, $VRT | prediction | True | short-term | $NVDA and $GOOGL are leading the 800V DC market ahead of schedule. |
| @amitisinvesting | $SPCX | opinion | False | none | $SPCX is undervalued. |
| @kaizen_investor | $WOLF | opinion | False | none | $WOLF is a good stock to look at. |
| @michaelsikand | $AAOI, $LITE, $COHR | opinion | False | none | $AAOI is a good stock to invest in. |
| @aleabitoreddit | $SPCX, $SIVE, $SOI | opinion | False | none | The author has different opinions on stocks based on their location. |
| @aleabitoreddit | $SIVE | prediction | True | short-term | $SIVE's Nasdaq listing will be positive. |
| @aleabitoreddit | $SIVE, $SNDK | opinion | False | none | $SIVE is a good stock to invest in. |
| @kawzinvests | $LITE, $AAOI, $FN, $CIEN, $CSCO | prediction | True | short-term | The 800G and 1.6T supply chain is under shipping demand. |
| @spacanpanman | $ASTS | news | False | none | $ASTS has a batch-2 loading soon. |
| @kawzinvests | $RDDT | opinion | False | none | $RDDT is a unique company. |
| @spacanpanman | $ASTS | opinion | False | none | $ASTS has revolutionary technology. |
| @kaizen_investor | $PL | opinion | False | none | $PL is a good space investment. |
| @spacanpanman | $ASTS | opinion | False | none | $ASTS has an impressive roadmap. |
| @aleabitoreddit | $TSM | prediction | True | short-term | Foosung will be a beneficiary soon. |
| @aleabitoreddit | $AXTI | opinion | False | none | The AI supremacy wars will present interesting opportunities. |
| @spacanpanman | $ASTS | news | False | none | The author's trading position is shares, options, and/or levered ETFs. |
| @spacanpanman | $ASTS | news | False | none | The author's trading position is shares, options, and/or levered ETFs. |
| @spacanpanman | $ASTS | opinion | False | none | The author is surprised at the magnitude of the drawdown today. |
| @amitisinvesting | $SPCX | news | False | none | $SPCX broke the record for largest volume of shares traded intraday of IPO. |
| @spacanpanman | $SHAZ | prediction | True | none | The S-1 registration related to the $350m convertible notes funded by Oaktree will lead to pressure on the stock $SHAZ. |
| @spacanpanman | $SPCX, $ASTS | promotion | False | none | none |
| @amitisinvesting | $SPCX | news | False | none | none |
| @aleabitoreddit | $SPCX | news | False | none | none |
| @kaizen_investor | $SPCX, $PL, $ASTS, $RKLB | other | False | none | none |
| @aleabitoreddit | $SIVE | opinion | False | none | none |
| @spacanpanman | $TE | prediction | False | none | none |
| @spacanpanman | $SHAZ | prediction | False | none | none |
| @aleabitoreddit | $SNDK, $SPCX | other | False | none | none |
| @spacanpanman | $ASTS | promotion | False | none | none |
| @spacanpanman | $SPKL | other | False | none | none |
| @kaizen_investor | $SPIR, $BKSY | question | False | none | none |
| @amitisinvesting | $SPCX, $HOOD | opinion | False | none | none |
| @spacanpanman | $SPCX | question | False | none | none |
| @venu_7_ | $RKLB | prediction | False | none | none |
| @spacanpanman | $SPCX | news | False | none | none |
| @spacanpanman | $SHAZ | opinion | False | none | none |
| @spacanpanman | $SHAZ | news | False | none | none |
| @kaizen_investor | $PL | opinion | False | none | none |
| @spacanpanman | $SPCX | news | False | none | none |
| @spacanpanman | $BAER | other | False | none | none |
| @spacanpanman | $ASTS | opinion | False | none | none |
| @kaizen_investor | $ASML | opinion | False | none | none |
| @aleabitoreddit | $IQE, $XFAB | opinion | False | none | none |
| @aleabitoreddit | $IQE, $MTSI | other | False | none | none |
| @aleabitoreddit | $AXTI | opinion | False | none | none |
| @aleabitoreddit | $RDDT | opinion | False | none | none |
| @aleabitoreddit | $ALAB, $LITE, $AAOI, $NBIS, $RKLB, $TSM, $SIVE, $AXTI | opinion | False | none | none |
| @aleabitoreddit | $NBIS | opinion | False | none | none |
| @aleabitoreddit | $ALAB | opinion | False | none | none |
| @aleabitoreddit | $NBIS, $ALAB, $RKLB | other | False | none | none |
| @michaelsikand | $SPCX | opinion | True | none | The sentiment on this app has shifted from skepticism to optimism about $SPCX. |
| @spacanpanman | $RKLB | promotion | False | none | $RKLB is a good stock to invest in. |
| @amitisinvesting | $QQQ, $NBIS, $RKLB, $CRWV, $TER, $ALAB | news | True | none | $NBIS, $RKLB, $CRWV, $TER, and $ALAB are new companies joining the NASDAQ 100. |
| @spacanpanman | $SPKLW | opinion | False | none | $SPKLW is a good stock to invest in. |
| @spacanpanman | $SPCX | opinion | True | none | $SPCX feels like an NFT. |
| @venu_7_ | $NBIS, $RKLB | prediction | False | none | $NBIS and $RKLB are good stocks to invest in. |
| @spacanpanman | $TE | prediction | False | none | $TE is a good stock to invest in. |
| @venu_7_ | $MRVL | opinion | False | none | $MRVL is a good stock to invest in. |
| @spacanpanman | $ASTS | prediction | False | none | $ASTS is a good stock to invest in. |
| @spacanpanman | $TE | prediction | False | none | $TE is a good stock to invest in. |
| @venu_7_ | $QQQ | prediction | True | Tuesday's lows | $QQQ will reach new ATHs if Tuesday's lows hold. |
| @venu_7_ | $MU | prediction | True | none | $MU will reach $1,200. |
| @spacanpanman | $TE | prediction | True | none | $TE will run 100% or 150% to $15 or $20. |
| @kawzinvests | $SKM | news | True | none | Management of the company is thinking about the long-term impact of Anthropic. |
| @aleabitoreddit | $SNDK, $MRVL, $LITE | news | True | none | Indexes and individual names like $SNDK to $MRVL to $LITE are green due to Trump canceling attacks on Iran. |
| @kawzinvests | $ZM | prediction | False | none | $ZM is a good stock to invest in. |
| @spacanpanman | $ASTS | prediction | True | none | $ASTS will break above $100 and reach $120. |
| @spacanpanman | $TE | prediction | False | none | $TE is a good stock to invest in. |
| @venu_7_ | $CRDO, $LPG, $RSI, $VVX, $LLY, $VCYT, $KRYS, $ARW, $COCO, $TTMI, $NBIX, $LINC, $INCY, $DAVE, $VIRT, $EVR, $CUBI, $ATLC, $TKO, $LRCX | news | True | none | CANSLIM Top 20 leaders are showing the same characteristics. |
| @aleabitoreddit | $WULF, $CIFR, $WYFI, $HUT | news | True | none | New Anthropic news is a potential tailwind for the Neocloud colo sector. |
| @kawzinvests | $SKM | opinion | True | 2030 | Anthropic could be one of the biggest companies on earth by 2030. |
| @kawzinvests | $SKM, $NVDA, $PENG | news | True | none | $SKM is quietly assembling the full stack. |
| @venu_7_ | $MRVL | prediction | False | none | $MRVL is a good stock to invest in. |
| @kawzinvests | $SKM, $NVDA | news | True | none | $SKM is the backbone of Korea's AI ecosystem. |
| @michaelsikand | $SKM, $ZM | news | True | none | $SKM has 4x more Anthropic exposure per dollar of market cap than second place $ZM. |
| @aleabitoreddit | $NVDA | prediction | False | none | Investing in $NVDA is a good idea. |
| @aleabitoreddit | $NVDA | prediction | True | $5B | Lightmatter/Ayar type companies will go higher than $5B if they IPO. |
| @aleabitoreddit | $AAOI, $INTC, $IQE, $XFAB, $MU, $WOLF, $SOI, $SIVE | opinion | True | none | Markets should be cheering on domestic champions like $AAOI. |
| @spacanpanman | $SPKL | news | True | none | $SPKL has great key stats. |
| @venu_7_ | $TTD | opinion | True | none | Bear flags are a good indicator of market trends. |
| @venu_7_ | $KLAC, $LRCX, $AMAT, $ASML, $ICHR, $UCTT | prediction | True | short-term | The semi equipment sector is experiencing a bid today, with some stocks outperforming others. |
| @venu_7_ | $MU | prediction | True | short-term | $MRVL is holding a gap up candle low, which is a strong support level. |
| @kaizen_investor | $SPCX | prediction | True | short-term | The $SPCX IPO will have three main effects on other space tickers. |
| @venu_7_ | $UMC | opinion | False | none | $UMC looks great. |
| @venu_7_ | $SNDK, $MU, $STX, $INTC, $DELL, $WDC, $AMD, $AMAT, $LRCX | opinion | False | none | A 5-6% pullback in the indexes can feel brutal, but the year is still phenomenal. |
| @aleabitoreddit | $META, $MSFT, $SPCX | question | True | short-term | It's unclear whether markets are correcting due to macro factors or liquidity pull from $SPCX. |
| @venu_7_ | $SNDK, $MU | opinion | False | none | Aria is killing it on the entire memory theme. |
| @michaelsikand | $SATS, $RKLB, $ASTS, $STCK, $ZM, $CRM, $SKM | opinion | False | none | The Anthropic trade isn't as straightforward as the SpaceX trade. |
| @aleabitoreddit | $AAOI | prediction | True | short-term | $AAOI has potential with its high revenue growth. |
| @venu_7_ | $VSXY | prediction | True | short-term | $VSXY is breaking out of a 4-year base in an AI bull market. |
| @aleabitoreddit | $SPCX | prediction | True | short-term | The $SPCX IPO might create a liquidity vacuum in the market. |
| @kawzinvests | $SKM, $NVDA | news | False | none | $SKM's stake in Anthropic is now worth an estimated $2.7 billion. |
| @spacanpanman | $ASTS | news | True | short-term | Blue Origin expects to fly again before the end of the year. |
| @venu_7_ | $ICHR, $SNDK, $ALAB, $ACMR, $UMC, $MRVL, $MU, $TTMI, $TEV, $SEZL, $CAVA, $STM, $CEVA, $AMBQ, $APH | opinion | False | none | Many quality names are setting up for the next leg higher. |
| @spacanpanman | $ASTS | question | True | short-term | Where does $ASTS trade when T-Mobile joins AT&T and Verizon as strategic partners? |
| @spacanpanman | $TE | prediction | True | short-term | The invoices being peddled by Fuddy Panza actually indicate the exact opposite of what they claim. |
| @venu_7_ | $STM | prediction | True | short-term | $STM is breaking out of a 26-year base tied closely to the SpaceX ecosystem. |
| @aleabitoreddit | $SPCX | prediction | True | short-term | 8% of the US current-account deficit could be refinanced in a single day by overseas demand for SpaceX shares. |
| @spacanpanman | $SPKL, $SPKLW | news | False | none | ZincFive is an interesting data center infrastructure play that just announced it's going public via $SPKL. |
| @venu_7_ | $CRDO, $ALAB | opinion | False | none | $CRDO and $ALAB don't seem to care much about the recent market weakness. |
| @spacanpanman | $SPCX | news | False | none | The new research initiations for $SPCX show insane growth. |
| @spacanpanman | $TE | news | False | none | UBS raises First Solar's price target to $330 due to expected Section 232 tariffs. |
| @spacanpanman | $SPKL | news | False | none | The trust value of $SPKL is at $11.39. |
| @spacanpanman | $SPKL, $SPKLW | news | False | none | The float of $SPKL is small at 2.24M shares. |
| @kaizen_investor | $ASM | opinion | False | none | $ASM.AS has been a successful investment for the author. |
| @spacanpanman | $SPCX | news | False | none | Banks are initiating research coverage for $SPCX before its IPO. |
| @spacanpanman | $ASTS | news | False | none | AST SpaceMobile gives operators three concrete and valuable things. |
| @spacanpanman | $TE | news | False | none | The author picked up some shares of $TE last night. |
| @spacanpanman | $ASTS | other | False | none | none |
| @aleabitoreddit | $RDDT, $RKLB, $HOOD | news | True | none | The study "Democratization of Retail Trading" found that WSB outperformed investment banks at detecting top-performing stocks. |
| @aleabitoreddit | $XFAB, $TSEM, $GFS, $NVDA | prediction | False | 2028 | none |
| @aleabitoreddit | $LPK | news | False | none | none |
| @aleabitoreddit | $SIVE | opinion | False | none | none |
| @aleabitoreddit | $AXTI, $RDDT | opinion | False | none | none |
| @aleabitoreddit | $AXTI | news | False | none | none |
| @aleabitoreddit | $SOI, $AAOI | opinion | False | none | none |
| @amitisinvesting | $ORCL, $PLTR, $TSLA, $NVDA, $AAPL, $AMZN, $SMCI, $MSFT, $META, $MU, $HOOD, $SOXS, $QLD, $SSO, $SPCX | news | False | none | none |
| @aleabitoreddit | $SIVE, $NBIS, $RKLB, $NVDA, $TSM, $HIMX | opinion | False | none | none |
| @amitisinvesting | $NVDA | opinion | False | none | none |
| @speculator_io | $STM, $MCHP, $IFX, $ON, $MU, $SNDK, $STX, $WDC | opinion | False | none | none |
| @amitisinvesting | $ORCL | news | False | none | none |
| @spacanpanman | $ASTS | news | False | none | none |
| @spacanpanman | $BAER | news | False | none | none |
| @spacanpanman | $TE | news | False | none | none |
| @spacanpanman | $TE | news | False | none | none |
| @venu_7_ | $CAVA | opinion | False | none | none |
| @aleabitoreddit | $NVDA | question | False | none | none |
| @aleabitoreddit | $RDDT, $HOOD, $NFLX | opinion | False | none | none |
| @aleabitoreddit | $SNDK | news | False | none | none |
| @kaizen_investor | $ENHA | opinion | False | none | none |
| @venu_7_ | $VIX, $SPY | opinion | False | none | none |
| @spacanpanman | $ASTS | news | False | none | none |
| @venu_7_ | $GLD | opinion | False | none | none |
| @venu_7_ | $GLD, $SLV, $MSTR | opinion | False | none | none |
| @kawzinvests | $AAOI | news | False | none | none |
| @aleabitoreddit | $AXTI, $ALRIB, $LPK | opinion | False | none | none |
| @venu_7_ | $FROG, $TWLO, $SNOW, $DDOG | opinion | False | none | none |
| @kawzinvests | $LITE, $AAOI, $COHR, $FN, $CIEN, $CSCO | news | False | none | none |
| @aleabitoreddit | $SOI, $XFAB, $IQE | opinion | False | none | none |
| @spacanpanman | $ASTS | news | False | none | none |
| @aleabitoreddit | $LITE, $AAOI, $SIVE | opinion | True | none | The initial selloff of optical players from $LITE to $AAOI and $SIVE was stupid. |
| @venu_7_ | $CRDO, $UNH, $APH, $ALAB, $OSCR, $CVS, $FTNT, $FROG, $FPS, $MDB, $DOCN, $AMAT, $HNGE, $AMKR, $VIAV, $ACMR, $SNOW, $DDOG, $NBIS, $MRVL, $VSH | prediction | False | none | Some of the best relative strength names in the market are $CRDO, $UNH, $APH, $ALAB, $OSCR, $CVS, $FTNT, $FROG, $FPS, $MDB, $DOCN, $AMAT, $HNGE, $AMKR, $VIAV, $ACMR, $SNOW, $DDOG, $NBIS, $MRVL, and $VSH. |
| @spacanpanman | $ECON | question | True | none | The spike higher in jobs may be related to front-loading for the World Cup. |
| @spacanpanman | $RKLB, $ASTS | news | False | none | Fellow space nerds made it to Dow Jones News and earned millions betting on space years before the SpaceX IPO made it cool. |
| @spacanpanman | $ECON | prediction | True | none | If and when the Iranian conflict is resolved, the biggest drivers of CPI will crater. |
| @spacanpanman | $ASTS | prediction | False | none | AST SpaceMobile is inevitable. |
| @spacanpanman | $ECON | other | False | none | none |
| @aleabitoreddit | $SIVE | opinion | False | none | Blackrock is passive and tracks Sivers based on MC. |
| @aleabitoreddit | $NVDA, $ASTS | opinion | True | none | Projections should be accurate for $NVDA. |
| @aleabitoreddit | $NVDA | opinion | True | none | I think I'll trust Nvidia since they probably have an idea on their own timelines. |
| @aleabitoreddit | $NVDA, $MU | opinion | True | none | The selloff from the claim $MU had 0 share of Nvidia HBM4 is the dumbest CPO/800V selloff I've seen. |
| @aleabitoreddit | $SIVE | news | False | none | Blackrock has now entered $SIVE positions as passive owners following index listing. |
| @aleabitoreddit | $NVDA | prediction | True | none | Nvidia and Lumentum executives are bullish on CPO, timelines accelerating. |
| @aleabitoreddit | $NVDA | prediction | True | none | I'm going long with Nvidia here. |
| @aleabitoreddit | $LITE, $NVDA | prediction | True | 2027 | The company expects to start shipping CPO scale up optical products in the second half of 2027. |
| @aleabitoreddit | $NVDA | prediction | True | none | There is no delay in H2 CPO product delivery schedule. |
| @spacanpanman | $ASTS | question | False | none | You claim you were 'early' on $ASTS, but this is your first post - April 10, 2026. |
| @spacanpanman | $ASTS | question | False | none | Your first post on ASTS was in April of 2026 lol. |
| @spacanpanman | $ASTS | news | False | none | AT&T FirstNet AVP Matt Walsh discusses the importance of AST SpaceMobile's broadband satellite coverage to America's First Responder Network. |
| @aleabitoreddit | $NVDA, $MU | opinion | False | none | Retail managed to completely frontrun institutions on multiple names, but institutions need liquidity to enter. |
| @amitisinvesting | $QQQ, $NVDA, $AMD, $TSLA, $AAPL, $MU, $AMZN, $MSFT, $INTC, $MRVL, $NOK, $PLTR, $HOOD, $SPCX | news | False | none | A TON OF THINGS HAPPENED IN THE STOCK MARKET TODAY. |
| @aleabitoreddit | $MU | opinion | True | none | I would trust Foxconn/Lumentum/Nvidia industry projections over an analyst firm that messed up $MU HBM4 so badly. |
| @aleabitoreddit | $AAOI | opinion | False | none | $AAOI revenues are dominated by pluggable. |
| @aleabitoreddit | $NVDA, $LITE, $MU | prediction | True | none | CPO scale out earlier than expected. |
| @amitisinvesting | $SPX | opinion | False | none | It just happened all at once so it created that feeling of mass hysteria. |
| @venu_7_ | $SN, $UCTT, $CRDO | prediction | False | none | The names that refuse to break down often become the next leaders when the market turns back up. |
| @amitisinvesting | $QQQ, $NVDA, $MRVL | news | False | none | The Nasdaq $QQQ fell 5.3% intraday. |
| @venu_7_ | $APH | prediction | False | none | $APH is quietly growing while benefiting from multiple secular themes at once. |
| @michaelsikand | $AAOI | prediction | True | none | The Semi Analysis report that CPO is delayed will throw water on photonics names, including $AAOI. |
| @venu_7_ | $FPS | prediction | True | none | $FPS has a good chance. |
| @venu_7_ | $SNOW, $AKAM, $JBHT, $KEYS | opinion | True | none | The low of a Power Earnings Gap (PEG) often acts as a major support level. |
| @kawzinvests | $AAOI, $CRDO, $SMTC, $MTSI, $COHR | prediction | True | none | The market will paint the whole sector with one brush. |
| @spacanpanman | $ASTS, $TMUS | news | False | none | none |
| @spacanpanman | $KRKNF, $PNG | opinion | True | none | The future of naval warfare is Unmanned Surface and Underwater Vehicles. |
| @venu_7_ | $QQQ | prediction | False | none | none |
| @spacanpanman | $SPCX | news | False | none | none |
| @venu_7_ | $FPS | opinion | False | none | none |
| @aleabitoreddit | $AAOI, $LITE, $SIVE | opinion | True | none | Photonics from $AAOI to $LITE or $SIVE are not disappearing anytime soon. |
| @venu_7_ | $AMBQ | news | False | none | none |
| @aleabitoreddit | $NVDA | prediction | False | none | none |
| @venu_7_ | $NBIS | opinion | True | none | Nebius is on its way to $300. |
| @aleabitoreddit | $EWY | prediction | False | none | none |
| @venu_7_ | $VSH | news | False | none | none |
| @spacanpanman | $MRLN | news | False | none | none |
| @venu_7_ | $CRDO | prediction | False | none | none |
| @aleabitoreddit | $XFAB | opinion | False | none | none |
| @spacanpanman | $ASTS | news | False | none | none |
| @spacanpanman | $ASTS | prediction | False | none | none |
| @aleabitoreddit | $LRCX, $KLAC | opinion | False | none | none |
| @spacanpanman | $ASTS | news | False | none | none |
| @aleabitoreddit | $ASX, $JBL, $VICR, $GFS, $AAOI, $TSEM, $FN, $CLS, $NBIS, $NOK, $AMKR, $LITE, $COHR, $ARM, $MRVL | opinion | False | none | none |
| @spacanpanman | $ASTS | prediction | False | none | none |
| @spacanpanman | $ASTS | news | False | none | none |
| @aleabitoreddit | $GFS, $JBL, $SIVE | opinion | False | none | none |
| @aleabitoreddit | $IREN, $BKKT | prediction | False | none | none |
| @aleabitoreddit | $IREN | other | False | none | none |
| @aleabitoreddit | $NVDA, $JBL, $GFS, $AEVA, $POET | opinion | False | none | none |
| @aleabitoreddit | $SIVE, $YSS, $MRVL | prediction | False | none | none |
| @aleabitoreddit | $JBL, $SIVE, $INTC, $AAOI | opinion | False | none | none |
| @aleabitoreddit | $SIVE, $RPI | other | False | none | none |
| @aleabitoreddit | $GOOGL, $MSFT, $AXTI | opinion | False | none | none |
| @venu_7_ | $NVDA | opinion | True | none | $NVDA is still the king! |
| @venu_7_ | $NVDA | opinion | True | none | $NVDA is one of the greatest profit-printing machines Wall Street has ever seen. |
| @amitisinvesting | $NVDA, $INTC, $AAPL, $TSLA, $MSFT, $AMZN, $MU, $GOOGL, $META, $NOK, $AMD, $NFLX, $HOOD, $PLTR, $F, $GLW, $SPCX, $SNDK | news | True | none | $NVDA is still at the beginning of the AI supercycle and that market weakness should be viewed as a buying opportunity. |
| @aleabitoreddit | $INHD | question | True | none | Can someone tell me what caused $INHD to go up 3660.95%? |
| @aleabitoreddit | $RDDT | opinion | True | none | Jim Cramer is like the 4th Newton’s Law. |
| @aleabitoreddit | $EWY | opinion | True | none | Bank of America quotes now about selling are not reliable. |
| @spacanpanman | $ASTS | prediction | True | none | $ASTS is looking to go directly to consumers with Starlink Mobile globally. |
| @spacanpanman | $ASTS, $SPCX | news | True | 2 years | $ASTS and $SPCX are planning to roll out Starlink Mobile globally to compete with MNOS over the next 2 years. |
| @venu_7_ | $TSLA | opinion | True | none | $TSLA is still a good investment. |
| @venu_7_ | $FROG | opinion | True | none | $FROG is a good investment because it's related to AI infrastructure. |
| @amitisinvesting | $AAPL, $GOOGL, $NVDA | news | True | none | $AAPL, $GOOGL, and $NVDA are teaming up to level up Apple's AI for more compute. |
| @amitisinvesting | $F | news | True | none | Robinhood gave millions of new users a free share of $F to sign up back in 2018-2020. |
| @amitisinvesting | $AMD, $NFLX, $HOOD, $META, $GOOGL, $AMZN, $MSFT, $NVDA, $PLTR, $F, $TSLA | news | True | none | $AMD replaced $NFLX as one of the top 10 held stocks across the platform on Robinhood. |
| @venu_7_ | $KEEL | prediction | True | none | $KEEL is a potential new small-cap leader. |
| @amitisinvesting | $MRVL | opinion | True | none | Jensen didn’t say $MRVL would reach $1T. |
| @spacanpanman | $TE | news | True | late June 2026 | A Section 232 ruling on polysilicon and solar derivatives is expected by late June 2026. |
| @venu_7_ | $MU | opinion | True | none | $MU is turning into a cash-printing machine. |
| @venu_7_ | $LLY, $MRK, $UNH, $JNJ | opinion | True | none | Four legacy healthcare names worth watching are $LLY, $MRK, $UNH, and $JNJ. |
| @spacanpanman | $SPCX | news | True | none | SpaceX’s initial public offering is well oversubscribed. |
| @venu_7_ | $STM | prediction | True | none | $STM is ready for the next leg higher. |
| @kaizen_investor | $PL, $GOOGL | opinion | True | none | $PL has a bullish partnership with $GOOGL. |
| @amitisinvesting | $QCOM | prediction | True | none | JENSEN: BUY QUALCOMM $QCOM STOCK. |
| @spacanpanman | $ASTS | opinion | True | none | $ASTS' PNT capabilities are critical for national security. |
| @amitisinvesting | $MU, $NVDA, $TSLA, $SNDK, $AMD | news | True | none | $MU, $NVDA, $TSLA, $SNDK, and $AMD had the largest retail single stock net inflows for the month of May. |
| @venu_7_ | $MRVL | opinion | True | none | $MRVL is showing characteristics of a High Tight Flag. |
| @venu_7_ | $OSCR | prediction | True | none | $OSCR has room to grow towards $36. |
| @aleabitoreddit | $XFAB | opinion | True | none | $XFAB is a good investment because it's European. |
| @spacanpanman | $ASTS, $TE | prediction | True | none | Covered all my short $ASTS calls and added to $TE with strategic financing package coming soon. |
| @spacanpanman | $CEPT, $SECZ | prediction | True | 6/29 | The merger between Securitized and $SECZ will be successful. |
| @venu_7_ | $JBHT, $VIAV | other | False | none | none |
| @venu_7_ | $SNOW | prediction | True | Stage 2 advance | Snowflake is finding support at the 9-day EMA and PEG low. |
| @aleabitoreddit | $MRVL, $ARM, $AAOI | opinion | True | none | Marvell and Arm have a lot of room to go. |
| @aleabitoreddit | $IBIT, $XLU, $META, $CRCL, $HOOD, $NBIS | news | True | none | Only a few stocks are red since the mention. |
| @venu_7_ | $VSH, $STM, $FSLR | prediction | True | Dot-Com and 2008 highs | Three names are approaching Dot-Com and 2008 highs. |
| @spacanpanman | $TE | news | True | none | Microsoft is acquiring land in Finland for a large data center project. |
| @aleabitoreddit | $MRVL, $ARM, $INTC | opinion | True | none | The US list from Marvell to Arm was goated. |
| @kaizen_investor | $WOLF | prediction | True | none | SiC is necessary for the pivot to 800V HVDC architecture. |
| @aleabitoreddit | $SIVE, $GFS, $JBL, $NVDA, $MRVL, $AMD | opinion | True | none | $SIVE is a compelling long idea. |
| @aleabitoreddit | $SIVE | news | True | none | US institutional accumulation of 5%+ of $SIVE is significant. |
| @aleabitoreddit | $SIVE | prediction | True | none | JP Morgan's disclosure of buying 5.25%+ of $SIVE has significant implications. |
| @aleabitoreddit | $NVDA | other | False | none | There are many names related to $NVDA 800V DC. |
| @kaizen_investor | $PL | opinion | True | none | $PL is a good stock. |
| @aleabitoreddit | $SIVE | news | True | none | $SIVE is only up 3.36% off the news JP Morgan bought 5%+ ownership. |
| @aleabitoreddit | $IFNNY, $ON, $VICR, $LFUS, $VSH, $ENPH, $NVTS, $POWI, $BDC, $EOSE, $SEDG, $AEHR, $WOLF, $CWR, $AMSC, $XFAB, $AOSL, $HYLN, $FCEL, $IQE, $ASYS, $RELL, $PAY, $IPWR, $POET | other | False | none | There are many names related to 800V DC. |
| @aleabitoreddit | $TSLA, $VPG | prediction | True | none | LeaderDrive is China's standout component leader in the robotics sector. |
| @spacanpanman | $BAER | prediction | True | none | Bridger Aerospace has a high price target. |
| @aleabitoreddit | $MRVL | opinion | True | none | LeaderDrive is a good stock. |
| @spacanpanman | $ASTS | other | False | none | STAY FOCUSED. |
| @kawzinvests | $NVDA | other | False | none | Jensen Huang is getting dressed in the morning. |
| @amitisinvesting | $SPCX | news | True | none | $SPCX is already 2x oversubscribed. |
| @amitisinvesting | $QQQ, $SPCX, $AVGO, $META | news | True | none | The Nasdaq had a bad day. |
| @michaelsikand | $MRVL | news | True | none | The "Inverse Cramer" portfolio made a good call on $MRVL. |
| @kaizen_investor | $PL | opinion | True | none | $PL has a good moat. |
| @kaizen_investor | $PL | prediction | True | none | The market is looking for an entry in $PL. |
| @kawzinvests | $VRT, $PWR | other | False | none | $VRT and $PWR are the picks and shovels of the picks and shovels. |
| @kawzinvests | $STM | prediction | True | Kyber ramp | $STM holders will be eating well when Kyber ramps. |
| @kawzinvests | $NVDA, $IFX, $MPWR, $VICR, $NVTS, $STM, $ON, $TXN, $ADI, $POWI, $DIOD, $WOLF, $AOSL | prediction | True | Rubin Ultra | Nvidia's power system will hit a point of saturation. |
| @aleabitoreddit | $NVDA, $SIVE, $SOI | prediction | True | none | Nvidia will require "supply volumes beyond imagination" for Silicon Photonics. |
| @aleabitoreddit | $NVDA, $MU, $EWY | prediction | True | many years | Memory shortage is expected to persist for many years. |
| @kaizen_investor | $PL | question | False | none | none |
| @aleabitoreddit | $AAOI, $SIVE, $IQE, $MTSI, $IREN, $SLNH, $BKKT | opinion | True | H1 2027 | none |
| @aleabitoreddit | $IREN, $NBIS, $NVDA, $CRWV, $SLNH, $BKKT, $SNAP | opinion | True | none | none |
| @aleabitoreddit | $AXTI, $RPI, $SIVE, $IQE, $LITE, $XFAB, $NVDA, $TSEM, $AAOI, $JBL, $TSM, $INTC, $MRVL | opinion | False | none | none |
| @aleabitoreddit | $TSM | prediction | False | none | none |
| @aleabitoreddit | $AMAT, $AMD, $AVGO, $INTC, $TSM, $SHMD, $LPK | prediction | True | H2 2026 | none |
| @kawzinvests | $NVDA | news | True | four years | none |
| @michaelsikand | $SIVE, $LITE | opinion | False | none | none |
| @kaizen_investor | $PL, $WOLF, $OUST | prediction | False | none | none |
| @kaizen_investor | $PL, $PLTR, $MRVL | opinion | False | none | none |
| @aleabitoreddit | $SIVE, $AAOI | opinion | False | none | none |
| @spacanpanman | $ASTS | prediction | False | none | none |
| @aleabitoreddit | $XFAB | prediction | True | H2 2027/2028 | none |
| @aleabitoreddit | $XFAB, $TSEM, $ASX, $NVDA, $NOK | opinion | True | none | none |
| @aleabitoreddit | $NOK, $NVDA | prediction | False | none | none |
| @aleabitoreddit | $RDDT, $AAOI, $MRVL | question | False | none | none |
| @spacanpanman | $ASTS | prediction | False | none | none |
| @aleabitoreddit | $SIVE | opinion | False | none | none |
| @aleabitoreddit | $SIVE | prediction | False | none | none |
| @aleabitoreddit | $SIVE | opinion | False | none | none |
| @venu_7_ | $MRVL | prediction | False | none | none |
| @venu_7_ | $FROG, $DDOG, $PANW | prediction | False | none | none |
| @venu_7_ | $QQQ | news | False | none | none |
| @michaelsikand | $COKE | prediction | False | none | none |
| @spacanpanman | $SPCX | news | False | none | none |
| @amitisinvesting | $META, $GOOGL, $MSFT, $AMZN | news | False | none | none |
| @amitisinvesting | $PLTR | opinion | False | none | none |
| @venu_7_ | $QQQ | prediction | False | none | none |
| @aleabitoreddit | $NVDA, $GOOGL, $AMZN, $MRVL, $LITE, $COHR, $INTC | opinion | False | none | none |
| @aleabitoreddit | $NVDA, $MU, $PL, $AAOI | news | False | none | none |
| @spacanpanman | $PL | other | False | none | none |
| @spacanpanman | $PL, $RKLB | news | True | none | An At-The-Market facility allows you to flexibly raise capital from time-to-time depending on corporate needs and market conditions. The size of an ATM should be |
| @spacanpanman | $SPCX | prediction | True | none | There are investors that have been selling positions to free up capital to participate in the $SPCX IPO. When they only get a 1-3% allocation, what will they do with those funds? |
| @aleabitoreddit | $TSM | prediction | True | H2 2026 | Xintec (3374) also looks like an interesting idea (TSMC packaging/test subsidary). MC is at ~ $2.18B. $TSM COUPE mass production starts this half, H2 2026. and... they have plans for "Aggressively pursuing CPO opportunities with subsidiaries Xintec" |
| @aleabitoreddit | $SIVE | opinion | True | none | The founding co-manager of that hedge fund quitting is probably a big sign their firms is going under from $SIVE going up |
| @aleabitoreddit | $SIVE | prediction | True | none | At this rate their firm is going under being YTD -31.02% from $SIVE |
| @venu_7_ | $FROG | prediction | True | none | $FROG - JFrog is becoming an important piece of the Agentic AI stack |
| @aleabitoreddit | $SIVE, $AAOI, $TSM, $NVDA, $TSEM, $SOI | other | False | none | $SIVE is #1, $AAOI is #2 used wrong wording above. Generally a fan of: |
| @aleabitoreddit | $AAOI | other | False | none | No, $AAOI is primarily pluggable exposure. But they have large exposure to CPO too, hence why I included the word photonics |
| @aleabitoreddit | $JBL, $SIVE, $NVDA | prediction | True | H1 2027 | H1 2027 all the 1.6T pluggable players like $JBL |
| @venu_7_ | $CRDO | prediction | True | none | $CRDO - Credo earnings are out of the way and the stock is forming a flag after breaking out of a 6-month base |
| @aleabitoreddit | $SIVE, $GFS, $JBL | opinion | False | none | $SIVE is my favorite CPO / photonics stock after AAOI |
| @venu_7_ | $QQQ | prediction | True | none | $QQQ - The Nasdaq is about to test its 21-day EMA for the first time since this uptrend began and is already up nearly 30% from the lows |
| @spacanpanman | $ASTS, $TE | other | False | none | $ASTS $TE: Adding upside here |
| @kaizen_investor | $PL | question | True | none | Is there ever a good time to announce an ATM? While all analysts raise their $PL price targets, Planet just announced a $1.5B ATM (around 10% of the market cap) |
| @spacanpanman | $ASTS | prediction | True | none | $ASTS: Short sellers steadily covering and have probably another 20M shares to go to get back to Feb/Mar levels |
| @aleabitoreddit | $GOOGL | opinion | False | none | Because most of the time, technical analysis doesn’t actually mean anything, since fundamentals are the most important! |
| @spacanpanman | $PL | news | False | none | $PL: CLEAR STREET RAISES PLANET LABS PRICE TARGET TO $53 FROM $34, MAINTAINS BUY RATING |
| @spacanpanman | $MRLN | news | False | none | $MRLN: Real-time short interest now at 4.9M shares and 37% borrow fee as of 6/4 |
| @spacanpanman | $PL | news | False | none | $PL: Research Price Target Upgrades |
| @spacanpanman | $SPCX | prediction | True | none | $SPCX: The projections are mind blowing. Looks like xAI is expected to really ramp growth |
| @spacanpanman | $ASTS, $RKLB, $PL, $SPACE | other | False | none | $ASTS $RKLB $PL $SPACE: Will take notes / record |
| @spacanpanman | $AUR | news | False | none | $AUR: CRAIG HALLUM INITIATES RESEARCH COVERAGE OF AURORA INNOVATION WITH BUY RATING AND $18 PRICE TARGET |
| @spacanpanman | $RKLB | news | False | none | $RKLB: 6/4 STIFEL RAISED ROCKET LAB PRICE TARGET TO $132 FROM $110, MAINTAINS BUY RATING |
| @aleabitoreddit | $AAOI, $JBL, $SIVE, $RDDT, $MRVL | opinion | False | none | $AAOI is my current favorite US long |
| @aleabitoreddit | $XFAB, $NVDA, $NOK, $TSEM |  | False | none | @Jornka329996 Are you high, I posted about $XFAB this week |
| @aleabitoreddit | $SOI, $RPI, $SIVE | opinion | False | none | The people who are fighting with the author are not going to learn. |
| @zephyr_z9 | $TTM | news | True | none | The Protecting Circuit Boards and Substrates Act will benefit $TTMI. |
| @aleabitoreddit | $RPI | prediction | True | none | $RPI will experience revenue growth due to strong AI-related demand. |
| @spacanpanman | $TE | prediction | True | coming weeks/months | T1 Energy will receive research coverage from major banks. |
| @spacanpanman | $MRLN | prediction | True | completion of USSOCOM CDR | The author thinks there's a good chance both TD Cowen and Roth Capital will raise their price targets on Merlin after the completion of USSOCOM CDR. |
| @spacanpanman | $TE, $NXT | opinion | True | future performance of Nextpower and T1 Energy | The acquisition of Prevalon by Nextpower is a good deal compared to T1 Energy's acquisition of KORE NRI. |
| @aleabitoreddit | $AAOI, $AMD, $NVDA, $LITE | prediction | True | execution of Aoi's plans | Aoi is likely to double or triple if they execute. |
| @spacanpanman | $MRLN | other | False | none | none |
| @spacanpanman | $MRLN | news | False | none | Crossroads Capital's Ryan O'Connor will discuss Merlin's US Special Operations Command CDR approval. |
| @michaelsikand | $DELL, $MRVL | opinion | False | none | Dell is Trump's favorite stock, and Marvell is Jensen's. |
| @michaelsikand | $RCAT | question | True | future performance of RCAT | The author is unsure if RCAT will be the next trending stock. |
| @michaelsikand | $PENG | opinion | False | none | Peng is still getting a lot of love and has crushed it. |
| @spacanpanman | $MRLN | prediction | True | future price movement of Merlin | Merlin's price may go back to $15-17. |
| @kaizen_investor | $PL | news | False | none | The author will make a detailed thread or article about PL's earnings call. |
| @speculator_io | $SNDK, $RXT, $HYLN, $WOLF, $DOCN, $DELL, $VPG, $BE, $STRL, $AMBQ, $INTC, $SILC, $HIMX, $HUT, $FLEX | opinion | False | none | Looking for stocks with blowout earnings is a good way to find the next big winner. |
| @spacanpanman | $MRLN | news | False | none | Merlin's short interest is at an all-time high. |
| @spacanpanman | $MRLN | other | False | none | none |
| @kaizen_investor | $PL | prediction | True | future price movement of PL | PL's stock price may increase after the earnings call. |
| @michaelsikand | $KRKNF, $AVAV, $KTOS, $AVEX, $LASR, $EOS | news | False | none | The author's trading caught the attention of NYMag. |
| @spacanpanman | $ASTS | opinion | False | none | ASTS is big and true. |
| @spacanpanman | $TE | prediction | True | 2032 | Solar will make up the largest chunk of global generation by 2032. |
| @venu_7_ | $FSLR, $ENPH, $SEDG, $NXT | opinion | False | none | FSLR, ENPH, SEDG, and NXT are good stocks. |
| @spacanpanman | $BAER | opinion | False | none | BAER is doing well. |
| @spacanpanman | $TE | opinion | False | none | Data centers will need a lot of power. |
| @kaizen_investor | $PL | prediction | True | Q1 earnings | PL's Q1 earnings will be good. |
| @kaizen_investor | $AMZN, $ASTS | prediction | True | production of GaN V-band Amps | Asts will be able to play a whole different game if they succeed in producing GaN V-band Amps. |
| @venu_7_ | $TSLA, $MU, $NBIS | opinion | False | none | TSLA, MU, and NBIS are good stocks. |
| @michaelsikand | $CIEN | prediction | True | future price movement of CIEN | CIEN's stock price will increase after the earnings call. |
| @venu_7_ | $KLIC, $ACMR, $VIAV, $MCHP | opinion | False | none | The High, Tight Flag is a powerful chart pattern. |
| @venu_7_ | $FPS | prediction | True | future price movement of FPS | FPS will continue to increase in price. |
| @amitisinvesting | $PLTR | news | False | none | Palantir's CEO said something interesting. |
| @kawzinvests | $CIEN, $AAOI, $COHR, $LITE | news | False | none | CIEN's earnings were good. |
| @venu_7_ | $RKLB | prediction | True | future price movement of RKLB | RKLB will increase in price. |
| @spacanpanman | $TE | opinion | True | none | Polysilicon solar cell fab producers are subject to cyclically, but AI will create unfathomable demand for the next several decades. |
| @venu_7_ | $XBI | opinion | False | none | The author thinks $XBI is not a bad spot. |
| @venu_7_ | $FSLR | prediction | True | short-term | One of the largest bases in the entire market is starting to wake up. |
| @venu_7_ | $NBIS | opinion | False | none | $NBIS is a core position in the author's portfolio. |
| @venu_7_ | $MRVL, $ALAB | question | True | short-term | The author thinks it will be between $MRVL vs $ALAB. |
| @venu_7_ | $FROG, $SNOW, $DDOG, $BAND, $FIVN | promotion | False | none | The author thinks $FROG, $SNOW, $DDOG, $BAND, and $FIVN are good stocks. |
| @venu_7_ | $IONQ, $QNT | prediction | False | none | The author thinks $IONQ is a good stock. |
| @venu_7_ | $MU | opinion | False | none | The author hasn't trimmed their $MU position since $370. |
| @aleabitoreddit | $RDDT | opinion | False | none | $RDDT is a good stock. |
| @venu_7_ | $MRVL | prediction | True | short-term | Marvell building a base here is a good sign. |
| @venu_7_ | $ONDS | opinion | False | none | $ONDS is a good stock. |
| @venu_7_ | $INOD | prediction | False | none | $INOD is a good stock. |
| @spacanpanman | $BCAR, $SHAZ | opinion | False | none | The author is long $BCAR and $SHAZ. |
| @venu_7_ | $SNOW, $INOD, $ORCL, $DDOG, $TWLO, $FTNT, $BAND, $FIVN, $FROG, $DOCN, $AKAM, $RDDT, $NAVN, $CRWD, $PANW, $RBRK, $NET, $LOGI, $APP, $MDB | opinion | False | none | The author sees risk/reward opportunities in software and cybersecurity. |
| @spacanpanman | $TE | prediction | True | short-term | The BESS deal is bullish for T1 Energy. |
| @spacanpanman | $ASTS | promotion | False | none | The author thinks $ASTS is a good stock. |
| @spacanpanman | $BRUN, $SHAZ, $BCAR | prediction | False | none | The author thinks $BRUN is a good stock. |
| @spacanpanman | $TE | opinion | False | none | The author bought more $TE overnight. |
| @spacanpanman | $SRTA | prediction | False | none | The author thinks $SRTA is a good stock. |
| @aleabitoreddit | $SIVE | opinion | False | none | The author thinks $SIVE is a good stock. |
| @spacanpanman | $ASTS | promotion | False | none | The author thinks $ASTS is a good stock. |
| @aleabitoreddit | $NVDA | opinion | False | none | The author thinks $NVDA is a good stock. |
| @aleabitoreddit | $SIVE, $IQE, $MTSI, $GFS, $JBL | opinion | False | none | It's hard for major companies to acquire CHIPS act funded companies like $SIVE. |
| @aleabitoreddit | $SIVE | prediction | True | short-term | Win Semi can scale up significant volume for $SIVE. |
| @aleabitoreddit | $SIVE | opinion | False | none | The author is confident in their $SIVE thesis. |
| @aleabitoreddit | $NVDA, $MU | opinion | False | none | Insider selling means nothing. |
| @aleabitoreddit | $SIVE | prediction | True | short-term | $SIVE has technical dominance over ASIC/Merchant CPO route architectures. |
| @aleabitoreddit | $SIVE, $LITE, $NVDA, $SNDK, $MRVL, $COHR, $AVGO, $MTSI, $JBL, $GFS, $AMD | prediction | True | short-term | $SIVE is a chokepoint and bottleneck for CPO next year. |
| @aleabitoreddit | $SIVE, $NVDA | opinion | False | none | $SIVE was probably the most recent visible laser chokepoint. |
| @venu_7_ | $SNOW | prediction | False | none | Snowflake is becoming a key platform for Enterprise AI and Agentic AI. |
| @venu_7_ | $ALGM | opinion | False | none | Allegro MicroSystems is a leader in magnetic sensors and power semiconductors. |
| @aleabitoreddit | $GOOGL, $META, $AMZN, $SIVE, $SOI | news | False | none | none |
| @venu_7_ | $MU, $TSLA | promotion | False | none | none |
| @venu_7_ | $TSLA | prediction | False | none | none |
| @aleabitoreddit | $IBIT, $ETHA, $HOOD, $COIN | opinion | False | none | none |
| @amitisinvesting | $BTC, $AVGO, $META, $NVDA, $TSLA, $AAPL, $AMZN, $MSFT, $NOK, $INTC, $GOOGL, $PLTR, $IREN, $CRWD, $SPCX, $SPY | news | False | none | none |
| @venu_7_ | $GRAB | opinion | False | none | none |
| @aleabitoreddit | $COIN, $HOOD, $CRCL | opinion | False | none | none |
| @aleabitoreddit | $AVGO, $GOOGL | opinion | False | none | none |
| @aleabitoreddit | $QCOM, $AMZN, $GOOGL | opinion | False | none | none |
| @aleabitoreddit | $AVGO, $NVDA, $MRVL, $LITE, $META | opinion | False | none | none |
| @amitisinvesting | $CRWD, $SPCX | opinion | False | none | none |
| @kawzinvests | $BRUN | prediction | False | none | none |
| @michaelsikand | $BRUN, $SGOV | opinion | False | none | none |
| @kawzinvests | $BRUN, $CRWV | opinion | False | none | none |
| @spacanpanman | $ASTS, $T | news | False | none | none |
| @spacanpanman | $CSIQ | opinion | False | none | none |
| @michaelsikand | $NOK, $SIVE, $MXL | news | False | none | none |
| @michaelsikand | $NBIS, $BRUN, $NVDA | news | False | none | none |
| @spacanpanman | $ASTS | news | False | none | none |
| @michaelsikand | $AAOI | opinion | False | none | none |
| @spacanpanman | $ASTS | prediction | False | none | none |
| @spacanpanman | $ASTS, $T | news | False | none | none |
| @kawzinvests | $BRUN, $NVDA, $DELL, $CRWV, $NBIS, $APLD | news | False | none | none |
| @kaizen_investor | $PL, $RKLB, $SATL, $ASTS, $FLY, $LUNR | opinion | False | none | none |
| @spacanpanman | $TE | prediction | False | none | none |
| @aleabitoreddit | $SOI, $SIVE | opinion | False | none | none |
| @spacanpanman | $WLAC, $BRUN, $BCAR, $BCARW | opinion | False | none | none |
| @aleabitoreddit | $SIVE, $XFAB, $SOI | news | False | none | none |
| @spacanpanman | $HAWK | opinion | False | none | none |
| @spacanpanman | $TE | prediction | False | none | none |
| @spacanpanman | $SRTA | news | True | none | Strata executes another highly accretive strategic tuck-in acquisition. |
| @aleabitoreddit | $XFAB | news | True | none | CHIPS ACT 2 was just published now and photonics was added. |
| @spacanpanman | $TE | news | True | none | KORE NRI Acquisition - Strategic Rationale & Financial Impact |
| @aleabitoreddit | $XFAB | question | True | none | $XFAB suddenly rose 7%, I wonder if there was any mention there. |
| @aleabitoreddit | $POET, $XFAB, $NVDA, $NOK, $NVTS, $POWI | other | True | none | The difference between NASDAQ and EU listing: |
| @spacanpanman | $TE | prediction | False | none | I’m a buyer premarket on the back of the KORE NRI acquisition. |
| @spacanpanman | $TE | news | True | none | T1 Energy's recent M&A hire from Skadden and transaction award in the contract extension of Peter Matrai makes a ton of sense now. |
| @spacanpanman | $TE | news | False | none | NORTHLAND SECURTIES INITIATES RESEARCH COVERAGE OF T1 ENERGY WITH AN OUTPERFORM RATING AND $16 PRICE TARGET |
| @spacanpanman | $TE | news | False | none | KORE NRI DEAL IS A HIGHLY ACCRETIVE AND ABSOLUTE GAME CHANGING DEAL FOR T1 ENERGY |
| @aleabitoreddit | $NBIS | opinion | False | none | $NBIS turned out well, that drawdown after blowout earnings was pretty brutal. |
| @aleabitoreddit | $NVDA, $MRVL | opinion | True | none | I actually didn't expect $NVDA to partner and take a stake in $MRVL this year. |
| @aleabitoreddit | $CRWV, $IREN, $NBIS | opinion | True | none | Financing structure is much different, $CRWV is getting eaten alive by debt interest. |
| @aleabitoreddit | $NBIS, $IREN, $CRWV | opinion | True | none | I wrote a thesis last year on the Neocloud sector becoming a major theme. |
| @aleabitoreddit | $SIVE, $JBL | opinion | True | none | There's active short sellers probably doubling down on $SIVE. |
| @aleabitoreddit | $NVDA, $SIVE | other | True | none | $NVDA directly. |
| @aleabitoreddit | $NVDA, $AMD, $GFS, $SIVE, $INTC, $GOOGL | opinion | True | none | I knew $NVDA was an investor in Ayar, so Id assume they wanted some strategic collaboration like NVlink ecosystem. |
| @aleabitoreddit | $SIVE, $NVDA, $LITE, $COHR | prediction | True | none | But maybe for gen-1 my guess is a lot sole source / primary source with $SIVE for the $NVDA CPO NVlink ecosystem. |
| @aleabitoreddit | $SIVE | prediction | True | none | Its still on a Swedish exchange, but NASDAQ listing should close the gap. |
| @aleabitoreddit | $NVDA, $MRVL, $SIVE, $GFS | news | False | none | $SIVE 100% confirmed laser supplier to Ayar. |
| @aleabitoreddit | $SIVE | prediction | False | none | $SIVE is now the laser source for likely: |
| @aleabitoreddit | $NVDA | prediction | False | none | Making a certain photonics company: |
| @aleabitoreddit | $EWY | other | True | none | I did all my DD on memory earlier this year. |
| @aleabitoreddit | $SIVE | news | True | none | There's actually even bigger news for $SIVE today than the EU CHIPS Act policy framework announcements. |
| @aleabitoreddit | $SOI, $NOK, $SIVE, $XFAB | other | True | none | I looked into it deeper, and the proposals were focused around 30-500M funding and revenue incentives, to bridge the pre-volume production players to HVM. |
| @aleabitoreddit | $XFAB, $SIVE | news | True | none | This includes, CHIPS ACT 2.0, which is expected to prioritize photonics. |
| @amitisinvesting | $MRVL, $META, $NVDA, $TSLA, $AAPL, $MSFT, $GOOGL, $INTC, $NOK, $MSTR, $AMZN, $BTC, $PANW, $CRWV, $SPCX, $UBER, $GME, $SHOP | other | True | none | Here's a full recap: |
| @aleabitoreddit | $SIVE, $NVDA | opinion | False | none | It’s really big news to have $SIVE as the laser supplier to $NVDA nvlink fusion ecosystem. |
| @aleabitoreddit | $TSM | other | True | none | They happen to be owned by TSMC too. |
| @aleabitoreddit | $LPK | other | True | none | kinda no news aside from waiting on that to happen. |
| @aleabitoreddit | $AEHR, $LPK | prediction | True | none | $AEHR will receive volume orders. |
| @speculator_io | $BE, $GEV, $PWR, $AMPX, $VICR, $VST, $NVTS, $BWXT, $CEG, $UEC, $CCJ, $NVDA, $TSM, $INTC, $AVGO, $AMD, $ASML, $ARM, $MRVL, $AAOI, $AXTI, $COHR, $MU, $SNDK, $STX, $OPTX, $LITE, $ICHR, $AEHR, $WDC, $NBIS, $IREN, $CRWV, $APLD, $VRT, $DELL, $HPE, $ORCL, $GOOGL, $META, $AMZN, $TSLA, $NOW, $PLTR, $DOCN, $SNOW, $NET, $FSLY, $INOD | other | False | none | none |
| @spacanpanman | $BCAR, $BCARW | prediction | False | none | none |
| @michaelsikand | $BRUN, $NVDA, $NBIS | prediction | False | none | none |
| @venu_7_ | $FSLR | other | False | none | none |
| @venu_7_ | $MRVL | other | False | none | none |
| @amitisinvesting | $SHOP | news | False | none | none |
| @venu_7_ | $MRVL | other | False | none | none |
| @aleabitoreddit | $MRVL, $NBIS | other | False | none | none |
| @spacanpanman | $ASTS | other | False | none | none |
| @spacanpanman | $ASTS | other | False | none | none |
| @venu_7_ | $FPS | prediction | False | none | none |
| @spacanpanman | $SHAZ | other | False | none | none |
| @michaelsikand | $KRKNF | other | False | none | none |
| @venu_7_ | $HBM, $FSLR | other | False | none | none |
| @spacanpanman | $BCAR | prediction | False | none | none |
| @spacanpanman | $BCAR | other | False | none | none |
| @spacanpanman | $TE, $LIFE | other | False | none | none |
| @venu_7_ | $SEZL | other | False | none | none |
| @spacanpanman | $ASTS, $RKLB | prediction | False | none | none |
| @spacanpanman | $ASTS | other | False | none | none |
| @spacanpanman | $SHAZ | other | False | none | none |
| @spacanpanman | $SHAZ | other | False | none | none |
| @spacanpanman | $SHAZ, $NBIS, $IREN | other | False | none | none |
| @amitisinvesting | $NVDA, $MRVL | other | False | none | none |
| @kaizen_investor | $PL, $RKLB | other | False | none | none |
| @spacanpanman | $WLAC | other | False | none | none |
| @speculator_io | $CRWV, $NBIS, $IREN, $IBM, $CDNS, $J, $PCOR, $PTC, $SIE, $SU, $DSY, $VRT, $GEV, $TT, $ABBN, $CAT, $ETN, $ENGI, $DLR, $EQIX, $SIFY, $DELL, $HPE, $SMCI | other | False | none | none |
| @spacanpanman | $TE | other | False | none | none |
| @spacanpanman | $TE | other | False | none | none |
| @aleabitoreddit | $LITE, $SIVE | other | False | none | none |
| @venu_7_ | $ETN | prediction | True | none | Eaton is one of the highest-quality electrical infrastructure names, benefiting from AI data centers, grid modernization, electrification, and industrial automation. |
| @spacanpanman | $ASTS, $TE | news | True | none | Blue Origin FUD, AST's Open Ended Straight Flush Draw, Smash & Grabbers, and more |
| @venu_7_ | $MP | opinion | False | none | none |
| @aleabitoreddit | $SOI, $XFAB | opinion | False | none | none |
| @venu_7_ | $FSLR | prediction | True | none | $FSLR is setting up to break out of an 18-year base. |
| @venu_7_ | $MP, $UAMY, $USAR, $REMX | prediction | True | none | Rare Earths... Enough teasing. Time to send it. |
| @spacanpanman | $ASTS | news | True | none | Real-time short interest has come down markedly as short sellers and convert arbs have used the Blue Origin New Glenn setback to cover shares. |
| @aleabitoreddit | $XFAB, $TSEM, $NVDA, $NOK | opinion | False | none | none |
| @spacanpanman | $TE | opinion | False | none | SOLAR IS THE FUTURE |
| @michaelsikand | $KRKNF, $HOOD | prediction | True | none | The AI trade is on fire. |
| @venu_7_ | $MRVL | news | False | none | none |
| @venu_7_ | $MRVL | opinion | False | none | none |
| @kaizen_investor | $SIVE, $POET | prediction | True | none | Best strategy might be to let your AI agents search X on short reports and go long. |
| @kaizen_investor | $NVDA, $FLNC, $MRVL, $SIVE | opinion | True | none | Is Jensen following me? |
| @aleabitoreddit | $SIVE | news | True | none | DID YOU LISTEN ANON? |
| @aleabitoreddit | $NVDA, $AVGO, $AMD, $MRVL | opinion | True | none | The most consequential event of an entire company’s history. |
| @aleabitoreddit | $GFS, $SIVE, $JBL, $AVGO, $MRVL, $NVDA | opinion | True | none | I’m not sure people realize the gravity of this news with $GFS yet. |
| @aleabitoreddit | $SIVE, $GFS | news | True | none | Woah that’s structurally massive news with $SIVE and $GFS. |
| @aleabitoreddit | $NVDA, $MRVL | news | True | none | Marvell is currently trading at $191B. |
| @amitisinvesting | $MRVL | news | False | none | none |
| @venu_7_ | $NVDA, $MRVL | news | True | none | $MRVL up +12% overnight! |
| @venu_7_ | $MRVL | opinion | False | none | none |
| @venu_7_ | $MDB | prediction | True | none | MongoDB powers the data layer behind modern applications and AI workloads. |
| @venu_7_ | $TWLO, $BAND, $FIVN | prediction | True | none | God candles across the AI voice layer. |
| @amitisinvesting | $GOOGL, $CRM, $NVDA, $TSLA, $MSFT, $AMZN, $META, $AAPL, $PLTR, $MU, $NOK, $ORCL, $SPCX, $HOOD, $CBRS, $AMD | news | True | none | Alphabet is proposing an $80 billion equity capital raise to expand its AI infrastructure and compute capacity. |
| @aleabitoreddit | $SIVE | news | True | none | I’ve uncovered a bot farm with dozens of accounts used to spread disinformation about $SIVE in the past few days. |
| @venu_7_ | $MU, $MUU | opinion | False | none | none |
| @venu_7_ | $MU, $AMR | opinion | False | none | none |
| @amitisinvesting | $RDDT, $ORCL, $GOOGL | opinion | True | none | Talking about $RDDT $ORCL $GOOGL etc can’t be manipulated |
| @amitisinvesting | $ZETA | opinion | False | none | He is the $ZETA ! |
| @amitisinvesting | $AVGO | news | False | none | none |
| @aleabitoreddit | $NBIS, $META, $MSFT, $GOOGL, $CIFR, $WULF | news | False | none | none |
| @aleabitoreddit | $GOOGL, $BRK, $LITE, $AVGO, $TSM, $MU | news | False | none | none |
| @venu_7_ | $MU, $ARM | opinion | False | none | none |
| @speculator_io | $DGXX, $HIVE, $WYFI, $HUT, $BTDR, $RIOT, $NBIS, $CLSK, $ORCL, $APLD, $CORZ, $CIFR, $IREN | news | False | none | none |
| @michaelsikand | $DRAM | news | False | none | none |
| @venu_7_ | $ARM | news | False | none | none |
| @aleabitoreddit | $NBIS | news | False | none | none |
| @aleabitoreddit | $SIVE, $GFS, $LITE, $JBL, $POET, $MRVL | news | False | none | none |
| @venu_7_ | $NVDA, $AVGO | prediction | False | none | none |
| @michaelsikand | $NOK | prediction | False | none | none |
| @venu_7_ | $MU | prediction | False | none | none |
| @venu_7_ | $ARM | prediction | False | none | none |
| @venu_7_ | $INOD | prediction | False | none | none |
| @aleabitoreddit | $HPS | opinion | False | none | none |
| @aleabitoreddit | $SIVE | other | False | none | none |
| @aleabitoreddit | $AAOI, $SNDK | prediction | False | none | none |
| @michaelsikand | $BRUN, $GLXY, $CRWV, $IREN, $NBIS, $NOK, $BE, $LASR, $CRCL, $AAOI, $MU, $PENG | prediction | False | none | none |
| @aleabitoreddit | $ARM | other | False | none | none |
| @aleabitoreddit | $SOI | other | False | none | none |
| @aleabitoreddit | $ARM | other | False | none | none |
| @aleabitoreddit | $CRWV, $IREN, $NBIS | opinion | False | none | none |
| @aleabitoreddit | $NBIS | other | False | none | none |
| @aleabitoreddit | $EWY, $MU | prediction | False | none | none |
| @aleabitoreddit | $SIVE, $AAOI | other | False | none | none |
| @aleabitoreddit | $IQE, $LPK, $SOI, $XFAB, $ALRIB | other | False | none | none |
| @aleabitoreddit | $SIVE, $MRVL, $POET, $AAPL, $AVGO, $LITE, $COHR | other | False | none | none |
| @venu_7_ | $NBIS | prediction | False | none | none |
| @venu_7_ | $RKLB | prediction | False | none | none |
| @aleabitoreddit | $NVDA, $FLNC | news | False | none | none |
| @aleabitoreddit | $IREN | opinion | True | none | Calling something by a different name doesn't change its inherent value. |
| @aleabitoreddit | $NBIS | opinion | False | none | $NBIS has the power of Plot Armor no Jutsu. |
| @aleabitoreddit | $NBIS, $IREN, $CIFR | opinion | False | none | $NBIS has anime plot armor! |
| @spacanpanman | $ASTS | news | True | none | AST SpaceMobile is not scheduled to launch with Blue Origin. |
| @aleabitoreddit | $LITE | opinion | False | none | Sentiment shifts after a good looking guy who runs a hedge fund sold $LITE positions. |
| @aleabitoreddit | $LITE, $AAOI, $SIVE, $JBL | opinion | True | none | Going long on $LITE doesn't send it to a $70B MC. |
| @aleabitoreddit | $AAOI, $SIVE, $LITE, $AMD, $NVDA | opinion | True | none | It's mainly just 'follow the leader' algorithmic selloff in current photonics markets. |
| @aleabitoreddit | $SIVE | opinion | False | none | $SIVE would do just fine without me. |
| @aleabitoreddit | $LITE, $COHR, $SIVE | opinion | True | none | There's only a few major pluggable players that I can think of that don't vertically integrate lasers like $LITE and $COHR. |
| @aleabitoreddit | $SIVE | opinion | True | none | This is the biggest TAM expansion + revenue driver with $SIVE, markets haven't noticed. |
| @aleabitoreddit | $SIVE | opinion | False | none | This cultural battle is just normal volatility to embrace and laugh at. |
| @aleabitoreddit | $SIVE, $JBL | opinion | False | none | I'd probably consider launching a fund to just buy out $SIVE if it reached those levels lol. |
| @aleabitoreddit | $SIVE, $JBL, $SOI | opinion | True | none | It's actually just a cultural thing in Sweden to dislike anything special or growth related. |
| @aleabitoreddit | $XFAB, $SOI | prediction | True | 2025 | Cyclical slump 2025. |
| @aleabitoreddit | $XFAB, $NVDA, $NVTS, $ON, $POWI, $GFS, $NOK, $INTC, $SOI | opinion | False | none | Just some mobile shower thoughts around $XFAB and train of thought. |
| @kawzinvests | $IBM | opinion | False | none | Sometimes it's best to keep it simple $IBM. |
| @kawzinvests | $NVDA, $NBIS, $ORCL, $CRWV, $DELL, $HPE, $SMCI, $SNX | news | False | none | $NVDA Vera CPU partner list from GTC Taipei. |
| @kawzinvests | $NVDA, $TSM, $LITE, $COHR | news | False | none | $NVDA 'Vera Rubin Ramps Into Full Production to Power Agentic AI Factories Worldwide'. |
| @kawzinvests | $NVDA | news | False | none | 'Vera Rubin is in Full Production'- Jensen Huang $NVDA GTC Taipei 2026 Keynote. |
| @venu_7_ | $MRVL, $FPS | opinion | False | none | I actually did for $MRVL. |
| @venu_7_ | $ARM | opinion | False | none | On April 14th, I initiated a 10% position in $ARM at $160 and shared a thesis covering Agentic AI, CPU theme, Robotics, fundamentals & technicals. |
| @amitisinvesting | $META | opinion | False | none | $META is a screaming buy and will eventually be $1000 in my opinion. |
| @aleabitoreddit | $NVDA | prediction | False | none | I think we'll hear about the next AI bottleneck. |
| @aleabitoreddit | $AAOI | prediction | True | 2027 | $AAOI hits $5.7B ARR entering h2 2027. |
| @aleabitoreddit | $MSFT, $AAOI, $SNDK | opinion | False | none | You would need to calculate your own fwd P/E ratios with hypergrowth names like $AAOI or $SNDK. |
| @aleabitoreddit | $AAOI, $AMZN, $MSFT, $NVDA, $AMD | opinion | False | none | $AAOI is actually my favorite photonics exposure in the US market right now. |
| @aleabitoreddit | $ARM, $NVDA | opinion | False | none | $ARM went straight from $134 to $354 when I took positions. |
| @venu_7_ | $FSLR | opinion | False | none | $FSLR isn't just a solar company anymore. |
| @spacanpanman | $BBC | opinion | False | none | You also lost big on $BBC. |
| @spacanpanman | $ASTS, $NPA | opinion | True | none | $ASTS is a good investment. |
| @speculator_io | $SNDK, $MU, $DELL, $BE, $ARM, $STX, $WDC, $NBIS, $FLEX, $CIEN, $MRVL, $AMD, $ASX, $ENLT, $NOK, $GLW, $RKLB, $ALAB, $MXL, $AAOI, $ICHR, $VSH, $DOCN, $VPG, $VICR, $VIAV, $AMBQ, $HUT, $PL, $SEDG, $BLDP, $AMPX, $AXTI, $RXT, $SATL, $AEHR, $HYLN, $NVTS, $OPTX, $MX, $SPIR, $CPSH, $FEL, $PURR, $PENG, $MRAM, $BKSY, $OSS, $UMAC, $USAR | news | False | none | none |
| @michaelsikand | $NOK | opinion | True | short-term | $NOK insider buying at these levels is insane. |
| @spacanpanman | $ASTS | promotion | False | none | none |
| @venu_7_ | $ONDS | promotion | False | none | none |
| @venu_7_ | $AEVA, $ONDS, $BAND, $INOD | news | False | none | none |
| @spacanpanman | $ASTS | question | False | none | none |
| @amitisinvesting | $NOW | question | False | none | none |
| @amitisinvesting | $IGV, $PLTR, $ZETA, $RDDT, $SHOP, $ORCL, $MSFT, $META, $DDOG, $SNOW, $NOW, $CRWD, $PANW | question | True | short-term | none |
| @venu_7_ | $FPS | promotion | False | none | none |
| @venu_7_ | $PLTR | opinion | True | short-term | $PLTR remains one of the strongest growth software companies in the market. |
| @venu_7_ | $FPS | opinion | True | short-term | $FPS - Forgent's entire bull case is summed up in one picture. |
| @venu_7_ | $FIVN | promotion | False | none | none |
| @venu_7_ | $BAND | opinion | True | short-term | The accumulation in $BAND is especially impressive. |
| @venu_7_ | $TWLO, $BAND, $FIVN | opinion | True | short-term | AI voice layer still looks like one of the most explosive themes in software while these names kick off Stage 2 uptrends. |
| @venu_7_ | $ORCL | opinion | True | short-term | $ORCL is one of the software names kicking off a new Stage 2 uptrend after reclaiming the 200-day SMA and building a 6-month Stage 1 base. |
| @kaizen_investor | $WOLF, $FLNC, $TMDX, $PL, $RKLB, $OUST, $PLTR, $ASML, $AMPX, $IREN, $MRVL, $ASM, $GOOGL, $HIMS | news | False | none | none |
| @spacanpanman | $ASTS | opinion | True | short-term | $ASTS: AST SpaceMobile + Vodafone solves this |
| @spacanpanman | $ASTS | opinion | True | short-term | $ASTS: Looking at SpaceX Falcon-9 precedent, AST confirmed the 9/12/25 targeted Block-1 BlueBird launch on 9/4/25 (8 days) |
| @aleabitoreddit | $VPG, $ASPI | question | False | none | none |
| @spacanpanman | $ASTS | question | False | none | $ASTS: Should I do a space covering the worst AST haters and FUD merchants? |
| @aleabitoreddit | $LPK | news | False | none | none |

## Run summary

- Groq calls attempted: **2**
- succeeded: **2**  ·  rate-limited (429): **0**
- Stage 1–2 are deterministic and always complete (no LLM).

_Read-only run. No database writes, no schema changes. Descriptive analysis only — not investment advice._
