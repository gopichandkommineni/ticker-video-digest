# Groq 30-Day Probe Report

**DESCRIPTIVE ANALYSIS ONLY — not investment advice.** This report
measures what handles are *posting*: volume, ticker frequency, and
sector concentration. It contains no buy signals, no ranking of tickers
by attractiveness, and no recommendations. The reader draws their own
conclusions from the concentration data.

- Database: `fintwit.db` · table `raw_tweets` (read-only)
- Window: last 30 days
- Model: `llama-3.3-70b-versatile` (Stages 3 & 4 only)

## Stage 1 — Volume (free, no LLM)

| Metric | Count |
|---|---:|
| Total non-deleted tweets (last 30d) | 3032 |
| Ticker-bearing tweets (cashtag regex) | 747 |
| Ratio | 24.6% |

## Stage 2 — Per-handle ticker profile (free, no LLM)

Deterministic counts. Handles sorted by ticker-bearing tweet volume.

- **@aleabitoreddit** — 447 tweets, 281 ticker-bearing; $SIVE (96), $NVDA (61), $AAOI (38), $LITE (36), $NBIS (26), $JBL (25), $XFAB (25), $MRVL (25), $SOI (21), $GFS (19), $MU (14), $AMD (13), $IREN (13), $IQE (13), $TSM (13), $RDDT (12), $AXTI (12), $POET (12), $GOOGL (12), $TSEM (11), $SNDK (11), $COHR (11), $INTC (11), $SPCX (10), $EWY (9), $LPK (9), $NOK (8), $AVGO (8), $RPI (6), $AMZN (6), $RKLB (6), $META (6), $MTSI (6), $HOOD (6), $ARM (6), $ALAB (5), $POWI (5), $WOLF (5), $MSFT (5), $TSLA (4), $AEHR (4), $NVTS (4), $CRWV (4), $CBRS (3), $AOSL (3), $ALRIB (3), $ON (3), $CIFR (3), $BKKT (3), $ASTS (2), $AEVA (2), $WEN (2), $BABA (2), $AAPL (2), $ASML (2), $WYFI (2), $WULF (2), $ASX (2), $VICR (2), $IBIT (2), $CRCL (2), $VPG (2), $SLNH (2), $COIN (2), $GM (1), $EOS (1), $QQQ (1), $DRAM (1), $MXL (1), $KOSPI (1), $SPY (1), $TOWA (1), $CAMT (1), $ACMR (1), $VRT (1), $HUT (1), $HIMX (1), $NFLX (1), $LRCX (1), $KLAC (1), $FN (1), $CLS (1), $AMKR (1), $YSS (1), $INHD (1), $XLU (1), $IFNNY (1), $LFUS (1), $VSH (1), $ENPH (1), $BDC (1), $EOSE (1), $SEDG (1), $CWR (1), $AMSC (1), $HYLN (1), $FCEL (1), $ASYS (1), $RELL (1), $PAY (1), $IPWR (1), $SNAP (1), $AMAT (1), $SHMD (1), $PL (1), $ETHA (1), $QCOM (1), $BRK (1), $HPS (1), $FLNC (1), $ASPI (1)
- **@spacanpanman** — 688 tweets, 181 ticker-bearing; $ASTS (80), $TE (34), $SPCX (14), $SHAZ (13), $RKLB (9), $BAER (8), $MRLN (8), $BCAR (7), $PL (6), $SPKL (5), $SPKLW (3), $ECON (3), $BRUN (2), $SRTA (2), $T (2), $WLAC (2), $BCARW (2), $TMUS (1), $KRKNF (1), $PNG (1), $CEPT (1), $SECZ (1), $SPACE (1), $AUR (1), $NXT (1), $CSIQ (1), $HAWK (1), $LIFE (1), $NBIS (1), $IREN (1), $BBC (1), $NPA (1)
- **@venu_7_** — 768 tweets, 139 ticker-bearing; $MU (18), $MRVL (17), $FPS (10), $SNOW (8), $STM (8), $CRDO (7), $NBIS (7), $FROG (7), $FSLR (7), $APH (6), $VSH (6), $BAND (6), $ALAB (5), $MCHP (5), $ICHR (5), $AMBQ (5), $QQQ (5), $DDOG (5), $FIVN (5), $LRCX (4), $ALGM (4), $RKLB (4), $TWLO (4), $NVDA (4), $TSLA (4), $INOD (4), $ARM (4), $TVTX (3), $TGTX (3), $GH (3), $XBI (3), $TXN (3), $ADI (3), $MPWR (3), $ON (3), $NVTS (3), $POWI (3), $WOLF (3), $IFNNY (3), $VICR (3), $AEIS (3), $DIOD (3), $AOSL (3), $AIXA (3), $ENTG (3), $RNECF (3), $ROHCY (3), $AMAT (3), $SNDK (3), $ACMR (3), $MDB (3), $VIAV (3), $ONDS (3), $LQDA (2), $AMD (2), $PLTR (2), $ALKS (2), $TWST (2), $RVMD (2), $RDDT (2), $HNGE (2), $LLY (2), $TTMI (2), $UCTT (2), $UMC (2), $SEZL (2), $CAVA (2), $GLD (2), $UNH (2), $OSCR (2), $FTNT (2), $DOCN (2), $AKAM (2), $JBHT (2), $PANW (2), $ORCL (2), $MP (2), $ABCL (1), $JAZZ (1), $ARGX (1), $HUT (1), $CRS (1), $ASTH (1), $MIRM (1), $DY (1), $TER (1), $HOOD (1), $NKE (1), $NVO (1), $PYPL (1), $FLNC (1), $LPG (1), $RSI (1), $VVX (1), $VCYT (1), $KRYS (1), $ARW (1), $COCO (1), $NBIX (1), $LINC (1), $INCY (1), $DAVE (1), $VIRT (1), $EVR (1), $CUBI (1), $ATLC (1), $TKO (1), $TTD (1), $KLAC (1), $ASML (1), $STX (1), $INTC (1), $DELL (1), $WDC (1), $VSXY (1), $TEV (1), $CEVA (1), $VIX (1), $SPY (1), $SLV (1), $MSTR (1), $CVS (1), $AMKR (1), $SN (1), $KEYS (1), $KEEL (1), $MRK (1), $JNJ (1), $ENPH (1), $SEDG (1), $NXT (1), $KLIC (1), $IONQ (1), $QNT (1), $NAVN (1), $CRWD (1), $RBRK (1), $NET (1), $LOGI (1), $APP (1), $GRAB (1), $HBM (1), $ETN (1), $UAMY (1), $USAR (1), $REMX (1), $MUU (1), $AMR (1), $AVGO (1), $AEVA (1)
- **@amitisinvesting** — 269 tweets, 48 ticker-bearing; $NVDA (19), $SPCX (19), $MSFT (14), $PLTR (13), $META (13), $MU (13), $AAPL (13), $AMZN (13), $GOOGL (12), $TSLA (12), $HOOD (9), $INTC (7), $AMD (6), $MRVL (6), $QQQ (5), $ORCL (5), $NOK (5), $NFLX (4), $RKLB (3), $QCOM (3), $RDDT (3), $SPY (3), $ZETA (3), $F (3), $AVGO (3), $CRWD (3), $SHOP (3), $MSTR (2), $GME (2), $CBRS (2), $SOFI (2), $SPX (2), $CRWV (2), $SNDK (2), $BTC (2), $PANW (2), $NOW (2), $IRDM (1), $CCXI (1), $AGLT (1), $WEN (1), $VZ (1), $SMH (1), $ASTS (1), $EBAY (1), $INFQ (1), $QBTS (1), $IBM (1), $RGTI (1), $IONQ (1), $QNT (1), $CVX (1), $DRAM (1), $SPCH (1), $IBIT (1), $SNAP (1), $NBIS (1), $TER (1), $ALAB (1), $SMCI (1), $SOXS (1), $QLD (1), $SSO (1), $GLW (1), $IREN (1), $UBER (1), $CRM (1), $IGV (1), $DDOG (1), $SNOW (1)
- **@kaizen_investor** — 166 tweets, 35 ticker-bearing; $PL (19), $WOLF (5), $RKLB (5), $MRVL (4), $SIVE (3), $ASTS (3), $SPCX (2), $ASML (2), $ASM (2), $GOOGL (2), $OUST (2), $PLTR (2), $FLNC (2), $MU (1), $SAP (1), $NASA (1), $SPIR (1), $BKSY (1), $ENHA (1), $AMZN (1), $SATL (1), $FLY (1), $LUNR (1), $POET (1), $NVDA (1), $TMDX (1), $AMPX (1), $IREN (1), $HIMS (1)
- **@michaelsikand** — 179 tweets, 29 ticker-bearing; $NOK (5), $AAOI (4), $BRUN (4), $MRVL (3), $KRKNF (3), $NBIS (3), $SPCX (2), $SATS (2), $LITE (2), $SKM (2), $ZM (2), $SIVE (2), $PENG (2), $LASR (2), $NVDA (2), $WEN (1), $RDDT (1), $NYT (1), $COHR (1), $RKLB (1), $ASTS (1), $STCK (1), $CRM (1), $COKE (1), $DELL (1), $RCAT (1), $AVAV (1), $KTOS (1), $AVEX (1), $EOS (1), $CIEN (1), $SGOV (1), $MXL (1), $HOOD (1), $DRAM (1), $GLXY (1), $CRWV (1), $IREN (1), $BE (1), $CRCL (1), $MU (1)
- **@kawzinvests** — 76 tweets, 27 ticker-bearing; $NVDA (10), $AAOI (5), $SKM (5), $LITE (4), $COHR (4), $CIEN (3), $BRUN (3), $CRWV (3), $FN (2), $CSCO (2), $STM (2), $DELL (2), $NBIS (2), $NOK (1), $KXIAY (1), $MU (1), $SNDK (1), $MRVL (1), $RDDT (1), $ZM (1), $PENG (1), $CRDO (1), $SMTC (1), $MTSI (1), $VRT (1), $PWR (1), $IFX (1), $MPWR (1), $VICR (1), $NVTS (1), $ON (1), $TXN (1), $ADI (1), $POWI (1), $DIOD (1), $WOLF (1), $AOSL (1), $APLD (1), $IBM (1), $ORCL (1), $HPE (1), $SMCI (1), $SNX (1), $TSM (1)
- **@speculator_io** — 9 tweets, 6 ticker-bearing; $SNDK (4), $DELL (4), $NBIS (4), $MU (3), $STX (3), $WDC (3), $DOCN (3), $BE (3), $HUT (3), $IREN (3), $RXT (2), $HYLN (2), $VPG (2), $AMBQ (2), $INTC (2), $FLEX (2), $GEV (2), $AMPX (2), $VICR (2), $NVTS (2), $AMD (2), $ARM (2), $MRVL (2), $AAOI (2), $AXTI (2), $OPTX (2), $ICHR (2), $AEHR (2), $CRWV (2), $APLD (2), $VRT (2), $HPE (2), $ORCL (2), $STM (1), $MCHP (1), $IFX (1), $ON (1), $WOLF (1), $STRL (1), $SILC (1), $HIMX (1), $PWR (1), $VST (1), $BWXT (1), $CEG (1), $UEC (1), $CCJ (1), $NVDA (1), $TSM (1), $AVGO (1), $ASML (1), $COHR (1), $LITE (1), $GOOGL (1), $META (1), $AMZN (1), $TSLA (1), $NOW (1), $PLTR (1), $SNOW (1), $NET (1), $FSLY (1), $INOD (1), $IBM (1), $CDNS (1), $J (1), $PCOR (1), $PTC (1), $SIE (1), $SU (1), $DSY (1), $TT (1), $ABBN (1), $CAT (1), $ETN (1), $ENGI (1), $DLR (1), $EQIX (1), $SIFY (1), $SMCI (1), $DGXX (1), $HIVE (1), $WYFI (1), $BTDR (1), $RIOT (1), $CLSK (1), $CORZ (1), $CIFR (1), $CIEN (1), $ASX (1), $ENLT (1), $NOK (1), $GLW (1), $RKLB (1), $ALAB (1), $MXL (1), $VSH (1), $VIAV (1), $PL (1), $SEDG (1), $BLDP (1), $SATL (1), $MX (1), $SPIR (1), $CPSH (1), $FEL (1), $PURR (1), $PENG (1), $MRAM (1), $BKSY (1), $OSS (1), $UMAC (1), $USAR (1)
- **@zephyr_z9** — 430 tweets, 1 ticker-bearing; $TTM (1)

## Stage 3 — Sector grouping (LLM, probe-only)

> ⚠️ **Probe-only.** Sectors below are assigned by a single Groq call
> and the model can miscategorize. In production this would be replaced
> by a deterministic ticker→sector map.

Unique tickers across all handles: **358**

_Sector map loaded from cache (`sectors.json`); no Groq call spent._

### Overall sector concentration (by total mentions)

| Sector | Mentions | Tickers |
|---|---:|---|
| semiconductors | 548 | $ACMR, $ADI, $AEHR, $AEIS, $AMAT, $AMD, $AMKR, $AOSL, $APH, $ARM, $ASM, $ASML, $ASX, $ASYS, $AVGO, $AXTI, $CAMT, $CEVA, $DIOD, $DRAM, $ENTG, $FLEX, $HIMX, $ICHR, $IFX, $INTC, $IQE, $JBL, $KLAC, $KLIC, $LRCX, $MCHP, $MPWR, $MRAM, $MRVL, $MU, $MXL, $NVDA, $ON, $QCOM, $SMCI, $SMTC, $SNDK, $STM, $STX, $TER, $TSEM, $TSM, $TTMI, $TXN, $UMC, $VSH, $WDC, $XFAB |
| other | 413 | $BRK, $BTC, $BTDR, $CAT, $COCO, $COKE, $CORZ, $CPSH, $CRCL, $CRS, $CVS, $DGXX, $DY, $ECON, $EOS, $ETHA, $EVR, $EWY, $FLY, $FPS, $GFS, $GH, $GLD, $GLW, $GLXY, $GME, $HAWK, $HBM, $HIMS, $HPS, $HUT, $IBIT, $IFNNY, $J, $JBHT, $KEEL, $KOSPI, $KRKNF, $KXIAY, $LINC, $LPK, $MP, $MUU, $MX, $NKE, $NPA, $NXT, $NYT, $OSCR, $OUST, $PCOR, $PL, $PNG, $PURR, $QBTS, $QLD, $QNT, $RBRK, $RELL, $RIOT, $RKLB, $RNECF, $ROHCY, $RPI, $RSI, $SECZ, $SGOV, $SHAZ, $SILC, $SIVE, $SKM, $SLNH, $SLV, $SOI, $SPCH, $SPIR, $SPKL, $SPKLW, $SRTA, $SSO, $STCK, $TEV, $TOWA, $TT, $UAMY, $UCTT, $UMAC, $UNH, $USAR, $VIX, $VPG, $VRT, $VST, $VSXY, $VVX, $WEN, $WLAC, $WOLF, $WULF, $YSS, $ZETA |
| software | 211 | $AAPL, $ALGM, $AMBQ, $AMPX, $AMR, $APLD, $APP, $ARW, $BAND, $BDC, $BE, $BKKT, $BKSY, $CDNS, $CIFR, $CLSK, $COIN, $CRM, $CRWD, $CRWV, $CUBI, $DAVE, $DDOG, $DELL, $DOCN, $DSY, $FIVN, $FN, $FSLY, $FTNT, $HIVE, $HOOD, $HPE, $IBM, $IGV, $LOGI, $MDB, $MSFT, $MSTR, $NOW, $ONDS, $ORCL, $OSS, $PANW, $PAY, $PTC, $PYPL, $SAP, $SNOW, $SNX, $SOFI, $TTD, $TWLO, $TWST, $UBER, $VIRT, $ZM |
| biotech | 188 | $ABCL, $AEVA, $AGLT, $AIXA, $ALKS, $ALRIB, $ARGX, $ASPI, $ASTH, $AUR, $AVEX, $BAER, $BBC, $BRUN, $CCXI, $CLS, $CRDO, $ENHA, $EOSE, $FEL, $FLNC, $FROG, $INCY, $INFQ, $INHD, $INOD, $JAZZ, $JNJ, $KRYS, $LFUS, $LIFE, $LLY, $LQDA, $MIRM, $MRK, $MRLN, $NAVN, $NBIS, $NBIX, $NVO, $NVTS, $RCAT, $RDDT, $RGTI, $RVMD, $RXT, $SEZL, $SHMD, $TGTX, $TMDX, $TVTX, $VCYT, $VICR |
| optical/photonics | 117 | $AAOI, $COHR, $LASR, $LITE, $OPTX, $VIAV |
| telecom | 103 | $ABBN, $ALAB, $ATLC, $CAVA, $CBRS, $CEPT, $CIEN, $CSCO, $DLR, $EQIX, $IRDM, $KEYS, $MTSI, $NOK, $SIFY, $STRL, $T, $TE, $TMUS, $VZ, $WYFI |
| space | 94 | $ASTS, $LUNR, $NASA, $SATL, $SATS, $SPACE |
| internet | 87 | $AKAM, $AMZN, $BABA, $EBAY, $GOOGL, $GRAB, $META, $NET, $NFLX, $SHOP, $SN, $SNAP |
| energy | 86 | $AMSC, $BLDP, $BWXT, $CCJ, $CEG, $CSIQ, $CVX, $CWR, $ENGI, $ENLT, $ENPH, $ETN, $FCEL, $FSLR, $GEV, $HNGE, $HYLN, $IPWR, $IREN, $LPG, $PENG, $POET, $POWI, $PWR, $SEDG, $SIE, $SU, $TKO, $UEC |
| etf | 72 | $QQQ, $REMX, $SMH, $SOXS, $SPCX, $SPX, $SPY, $XBI, $XLU |
| automotive | 35 | $BCAR, $BCARW, $F, $GM, $TSLA, $TTM |
| ai infrastructure | 22 | $AVAV, $IONQ, $KTOS, $PLTR |

### Per-handle sector concentration (by mentions)

- **@aleabitoreddit** — semiconductors (274), other (195), optical/photonics (85), biotech (56), energy (37), internet (28), software (28), telecom (24), etf (13), automotive (5), space (2)
- **@spacanpanman** — space (81), other (49), telecom (38), biotech (22), etf (14), automotive (9), energy (2)
- **@venu_7_** — semiconductors (126), biotech (67), software (66), other (63), energy (17), etf (10), telecom (9), internet (5), automotive (4), ai infrastructure (3), optical/photonics (3)
- **@amitisinvesting** — semiconductors (62), software (60), internet (47), etf (31), other (18), automotive (15), ai infrastructure (14), telecom (10), biotech (8), energy (2), space (1)
- **@kaizen_investor** — other (37), semiconductors (10), space (6), biotech (4), software (3), internet (3), etf (2), ai infrastructure (2), energy (2)
- **@michaelsikand** — other (16), biotech (10), optical/photonics (9), semiconductors (8), software (7), telecom (6), space (3), energy (3), etf (2), ai infrastructure (2)
- **@kawzinvests** — semiconductors (25), optical/photonics (13), software (13), biotech (9), other (8), telecom (7), energy (3)
- **@speculator_io** — semiconductors (43), software (34), other (27), energy (20), biotech (12), telecom (9), optical/photonics (7), internet (4), automotive (1), ai infrastructure (1), space (1)
- **@zephyr_z9** — automotive (1)

## Stage 4 — Thesis extraction (LLM, ticker-bearing only)

Descriptive structure per tweet: thesis, whether the claim is
falsifiable, its horizon and a checkpoint, and the stance. No judgement
of whether the claim is *good*.

Tweets are batched **25 per Groq call** to stay within the
free-tier tokens-per-minute limit while covering the full month.

_Ledger (`thesis.jsonl`): 475 tweet(s) already extracted; **272** remaining this run._

_Batch 1 rate-limited (HTTP 429): {"error":{"message":"Rate limit reached for model `llama-3.3-70b-versatile` in organization `org_01kvv0mwjtftcbzc6rtaka5_
_Batch 2 rate-limited (HTTP 429): {"error":{"message":"Rate limit reached for model `llama-3.3-70b-versatile` in organization `org_01kvv0mwjtftcbzc6rtaka5_
_Batch 3 rate-limited (HTTP 429): {"error":{"message":"Rate limit reached for model `llama-3.3-70b-versatile` in organization `org_01kvv0mwjtftcbzc6rtaka5_
_Batch 4 rate-limited (HTTP 429): {"error":{"message":"Rate limit reached for model `llama-3.3-70b-versatile` in organization `org_01kvv0mwjtftcbzc6rtaka5_
_Batch 5 rate-limited (HTTP 429): {"error":{"message":"Rate limit reached for model `llama-3.3-70b-versatile` in organization `org_01kvv0mwjtftcbzc6rtaka5_
_Batch 6 rate-limited (HTTP 429): {"error":{"message":"Rate limit reached for model `llama-3.3-70b-versatile` in organization `org_01kvv0mwjtftcbzc6rtaka5_
_Batch 7 rate-limited (HTTP 429): {"error":{"message":"Rate limit reached for model `llama-3.3-70b-versatile` in organization `org_01kvv0mwjtftcbzc6rtaka5_
_Batch 8 rate-limited (HTTP 429): {"error":{"message":"Rate limit reached for model `llama-3.3-70b-versatile` in organization `org_01kvv0mwjtftcbzc6rtaka5_
_Batch 9 rate-limited (HTTP 429): {"error":{"message":"Rate limit reached for model `llama-3.3-70b-versatile` in organization `org_01kvv0mwjtftcbzc6rtaka5_
_Batch 10 rate-limited (HTTP 429): {"error":{"message":"Rate limit reached for model `llama-3.3-70b-versatile` in organization `org_01kvv0mwjtftcbzc6rtaka5_
_Batch 11 rate-limited (HTTP 429): {"error":{"message":"Rate limit reached for model `llama-3.3-70b-versatile` in organization `org_01kvv0mwjtftcbzc6rtaka5_
_Retrying 11 failed batch(es) (transient timeout/5xx); 89 calls of daily budget remain._

_Batch 1 rate-limited (HTTP 429): {"error":{"message":"Rate limit reached for model `llama-3.3-70b-versatile` in organization `org_01kvv0mwjtftcbzc6rtaka5_
_Batch 2 rate-limited (HTTP 429): {"error":{"message":"Rate limit reached for model `llama-3.3-70b-versatile` in organization `org_01kvv0mwjtftcbzc6rtaka5_
_Batch 3 rate-limited (HTTP 429): {"error":{"message":"Rate limit reached for model `llama-3.3-70b-versatile` in organization `org_01kvv0mwjtftcbzc6rtaka5_
_Batch 4 rate-limited (HTTP 429): {"error":{"message":"Rate limit reached for model `llama-3.3-70b-versatile` in organization `org_01kvv0mwjtftcbzc6rtaka5_
_Batch 5 rate-limited (HTTP 429): {"error":{"message":"Rate limit reached for model `llama-3.3-70b-versatile` in organization `org_01kvv0mwjtftcbzc6rtaka5_
_Batch 6 rate-limited (HTTP 429): {"error":{"message":"Rate limit reached for model `llama-3.3-70b-versatile` in organization `org_01kvv0mwjtftcbzc6rtaka5_
_Batch 7 rate-limited (HTTP 429): {"error":{"message":"Rate limit reached for model `llama-3.3-70b-versatile` in organization `org_01kvv0mwjtftcbzc6rtaka5_
_Batch 8 rate-limited (HTTP 429): {"error":{"message":"Rate limit reached for model `llama-3.3-70b-versatile` in organization `org_01kvv0mwjtftcbzc6rtaka5_
_Batch 9 rate-limited (HTTP 429): {"error":{"message":"Rate limit reached for model `llama-3.3-70b-versatile` in organization `org_01kvv0mwjtftcbzc6rtaka5_
_Batch 10 rate-limited (HTTP 429): {"error":{"message":"Rate limit reached for model `llama-3.3-70b-versatile` in organization `org_01kvv0mwjtftcbzc6rtaka5_
_Batch 11 rate-limited (HTTP 429): {"error":{"message":"Rate limit reached for model `llama-3.3-70b-versatile` in organization `org_01kvv0mwjtftcbzc6rtaka5_
_Note: 11 batch(es) (~272 tweets) not recovered this run (transient errors / budget); the ledger lets a later run pick them up._


Thesis ledger now holds **475** of 747 ticker-bearing tweets (**+0** this run).

Stance distribution: opinion (248), news (113), other (56), prediction (44), question (8), promotion (6)

| Handle | Tickers | Stance | Falsifiable | Horizon | Thesis |
|---|---|---|---|---|---|
| @aleabitoreddit | $NBIS | other | False | none | none |
| @amitisinvesting | $PLTR, $NVDA, $RKLB, $IRDM, $HOOD, $CCXI, $AGLT, $GOOGL, $META, $MU, $AAPL, $AMZN, $TSLA, $MSFT, $SPCX, $INTC, $MSTR, $QCOM | news | True | short-term | Palantir and Nvidia expanded their partnership to deliver sovereign AI for the U.S. government and critical infrastructure. |
| @aleabitoreddit | $RPI, $SIVE, $JBL, $GFS, $XFAB, $RDDT, $AXTI, $NBIS, $ALAB, $CBRS | other | False | none | none |
| @spacanpanman | $ASTS | opinion | True | medium-term | Japanese investors may not understand the J-LEO opportunity. |
| @amitisinvesting | $RKLB, $SPCX | opinion | True | long-term | The Rocket Lab acquisition is a significant step in transforming the company into a vertically integrated space and communications company. |
| @amitisinvesting | $PLTR, $NVDA | news | True | short-term | Palantir and Nvidia expanded their partnership to deliver sovereign AI for the U.S. government and critical infrastructure. |
| @spacanpanman | $RKLB | news | True | long-term | Rocket Lab's acquisition of Iridium will create a fully vertically integrated space powerhouse. |
| @aleabitoreddit | $ASTS, $SPCX | news | True | medium-term | Rakuten's joint venture with ASTS is a strategic response to the growing influence of Starlink in Japan. |
| @spacanpanman | $ASTS | prediction | True | short-term | AST and Rakuten will win the J-LEO project. |
| @spacanpanman | $ASTS | opinion | True | medium-term | The J-LEO project award will bring significant benefits to AST SpaceMobile. |
| @spacanpanman | $ASTS | prediction | True | short-term | Rakuten and AST SpaceMobile will be selected for the $1 billion J-LEO project. |
| @aleabitoreddit | $GM, $NVDA, $AMZN | opinion | True | long-term | GM's replacement of workers with robots is industry validation for robotics. |
| @amitisinvesting | $MU, $NVDA, $AAPL | news | True | short-term | Micron is now a top 10 holding in the S&P 500, while Nvidia and Apple have decreased in weighting. |
| @aleabitoreddit | $POET | other | False | none | none |
| @aleabitoreddit | $POET, $LITE, $SIVE, $AAOI | news | True | medium-term | The top three laser suppliers control 68% of the market and are completely sold out for the next two years. |
| @aleabitoreddit | $RKLB, $SPCX, $EOS, $LITE, $TSLA | opinion | False | none | This decade will be the most significant in human history due to advancements in technology. |
| @venu_7_ | $ABCL, $JAZZ | prediction | True | short-term | ABCL is ready to run with a strong base. |
| @venu_7_ | $MU, $ALAB, $ARGX, $TVTX, $LQDA, $HUT, $CRDO, $AMD, $TGTX, $CRS, $ASTH, $GH, $MIRM, $LRCX, $DY | opinion | True | medium-term | The IBD Top 15 list is a good indicator of where institutional money is flowing. |
| @venu_7_ | $PLTR | opinion | True | short-term | Palantir is at a strong support level and may base here. |
| @venu_7_ | $TER | opinion | True | long-term | A certain stock is a hidden robotics play and has potential for growth. |
| @venu_7_ | $SNOW | prediction | True | short-term | Snowflake is ready to begin a Stage 2 uptrend. |
| @aleabitoreddit | $META, $NBIS, $GOOGL | news | True | short-term | Meta signed agreements with Neoclouds due to compute restraints. |
| @spacanpanman | $TE | other | False | none | none |
| @aleabitoreddit | $CBRS | other | False | none | none |
| @aleabitoreddit | $CBRS, $JBL | news | True | short-term | OpenAI's launch of its heavyweight 5.6 Sol frontier model on Cerebras is a significant development. |
| @aleabitoreddit | $SIVE | opinion | True | short-term | The author thinks $SIVE will benefit from the acquisition of Mesh by $SPCX. |
| @spacanpanman | $ASTS | opinion | True | long-term | The T-Mobile and Starlink partnership was a strategic mistake because SpaceX did not stay in its lane as a passive infrastructure provider. |
| @aleabitoreddit | $SPCX, $SIVE, $POET, $LITE, $MTSI | news | True | short-term | Elon Musk's acquisition of Mesh, an optical networking startup, could benefit $SIVE. |
| @aleabitoreddit | $SIVE | opinion | True | short-term | The author thinks the shareholder meeting's authorization for share issuance is a positive development for $SIVE. |
| @aleabitoreddit | $NBIS | other | False | none | The author is grateful for their followers' support and is waiting for their thesis to play out. |
| @aleabitoreddit | $SIVE, $JBL, $GFS, $AMD, $NVDA, $POET, $AEVA, $MRVL | opinion | True | short-term | The author thinks $SIVE is undervalued based on its forward revenue potential. |
| @aleabitoreddit | $SIVE, $EWY, $NBIS, $IREN, $QQQ, $LITE | opinion | True | long-term | The author is confident in their hyperscaler mapping research with $SIVE and has a large position in the stock. |
| @aleabitoreddit | $SIVE, $AAOI | opinion | True | long-term | The author is confident in $SIVE and $AAOI's revenue growth with lasers in 2027. |
| @aleabitoreddit | $MU | news | True | short-term | Elon Musk is sounding the alarm on the massive demand and price hikes for memory relative to supply. |
| @aleabitoreddit | $SOI, $RKLB | opinion | True | short-term | There is a global correction in the market, and high beta stocks are getting hit harder. |
| @aleabitoreddit | $AXTI, $AAOI, $TSEM, $LITE, $MU, $SNDK, $EWY, $SIVE, $IQE, $SOI | other | False | none | The author had posted ideas about various stocks, including $AXTI and $SIVE, and is reflecting on their performance. |
| @aleabitoreddit | $JBL, $SIVE | other | False | none | The author is checking out the specs for $JBL and $SIVE. |
| @aleabitoreddit | $AAOI, $AMD | opinion | True | long-term | The author is confident in $AAOI's prospects due to $AMD's CW LTA reports and next year's projections. |
| @aleabitoreddit | $AOSL, $POWI | opinion | True | short-term | Power semis are starting to price hikes, which is bullish for the US power semi trade. |
| @spacanpanman | $BAER | other | False | none | none |
| @michaelsikand | $WEN | opinion | True | short-term | The market is currently favoring a $1T company over a meme stock. |
| @kaizen_investor | $MU | news | False | none | Sk Hynix's stock is up 14% due to $MU's earnings. |
| @aleabitoreddit | $WEN, $RDDT | other | False | none | The $WEN meme traders have been successful, and the author is reflecting on their own portfolio's performance. |
| @aleabitoreddit | $MU, $TSM, $TSLA | news | True | long-term | $MU's CEO predicts a multi-decade memory demand cycle driven by humanoid robots. |
| @kawzinvests | $NOK | opinion | True | long-term | The Infinera acquisition was a turning point for $NOK. |
| @kawzinvests | $KXIAY, $MU, $SNDK | news | False | none | Kioxia has announced plans to issue US depositary shares in 2027. |
| @aleabitoreddit | $AXTI, $SOI, $AAOI | other | False | none | The author's strategy is 'Diversified Losses' and they have experienced a massive drawdown recently. |
| @venu_7_ | $MU | opinion | True | short-term | The author thinks price action should decide whether $MU is cyclical or not. |
| @aleabitoreddit | $DRAM, $MU, $SNDK | opinion | True | short-term | The author has a positive view on the $DRAM ETF due to its exposure to memory stocks. |
| @aleabitoreddit | $BABA | opinion | True | short-term | The author thinks $BABA's Qwen market share increase could be beneficial due to its cost-effectiveness. |
| @aleabitoreddit | $BABA | opinion | False | none | Anthropic has accused the Qwen AI lab of distilling its frontier AI models, but there have been no real penalties enforced yet. |
| @michaelsikand | $NOK | news | True | short-term | Nokia is investing $30M to expand its semiconductor testing and packaging operations, creating thousands of jobs. |
| @aleabitoreddit | $JBL, $SIVE, $MRVL, $MXL, $TSEM | opinion | True | medium-term | OpenLight is getting bigger and has a public ecosystem outside of Advantest, including partnerships with JBL, MRVL, and TSEM. |
| @aleabitoreddit | $AMZN, $TSLA, $GOOGL | opinion | True | long-term | Amazon's capex is likely to lead to massive revenue increase or margin increase down the line. |
| @amitisinvesting | $RDDT | promotion | False | none | none |
| @amitisinvesting | $MU | opinion | False | none | The market is at a stage where people are turning random names into their own version of MU. |
| @venu_7_ | $HOOD | opinion | True | short-term | The market is sending signals that HOOD is a good investment, including decoupling from Bitcoin and strong institutional accumulation. |
| @amitisinvesting | $WEN | news | True | short-term | Wendy's stock is up 20% overnight as the stock is going viral on r/WallStreetBets. |
| @venu_7_ | $TGTX, $TVTX, $ALKS, $TWST, $RVMD, $LQDA, $XBI | opinion | True | medium-term | Names like TGTX, TVTX, ALKS, TWST, RVMD, and LQDA look great, and the XBI ETF itself looks amazing. |
| @aleabitoreddit | $RDDT, $WEN | news | True | short-term | The degens on RDDT are starting a viral campaign to save Wendy's, and the stock price is now up 20% overnight. |
| @venu_7_ | $MU, $NKE, $NVO, $PYPL | opinion | True | medium-term | MU is one of the biggest beneficiaries of the HBM and AI memory cycle, with earnings power inflecting dramatically. |
| @spacanpanman | $BAER | promotion | False | none | none |
| @amitisinvesting | $SPY, $SPCX, $MU, $GOOGL, $VZ, $AMZN, $AAPL, $MSFT, $NVDA, $META, $SMH, $PLTR, $ZETA, $ASTS, $GME, $EBAY, $CBRS | news | True | short-term | Markets were under pressure today, with the S&P down ~1.5%, largely due to a sharp selloff in South Korea. |
| @amitisinvesting | $MU | question | False | none | none |
| @venu_7_ | $GH | opinion | True | short-term | GH is a little tricky to trade, but it found support at the 200-day SMA during the last pullback. |
| @aleabitoreddit | $KOSPI, $EWY | opinion | True | medium-term | Bank of America's predictions are often incorrect, such as their call on KOSPI/EWY being an extreme bubble. |
| @aleabitoreddit | $SIVE, $AAPL | opinion | True | short-term | The recent PR about SIVE and AAPL is likely just to support their relationships and combat false short seller claims. |
| @spacanpanman | $BAER | other | False | none | none |
| @aleabitoreddit | $LITE, $COHR | opinion | True | medium-term | There is no good reason to invest in certain types of ETFs, such as those with basic names and high management fees. |
| @aleabitoreddit | $LITE, $NVDA, $AMD, $AAOI, $SIVE, $SOI, $TSEM | opinion | True | medium-term | The photonics theme and CW laser chokepoint are promising, and markets have short-term memory loss about LITE's growth. |
| @aleabitoreddit | $ALAB, $MRVL | opinion | True | short-term | The best time to long CXL for memory pooling was 4 months ago, as seen by the growth of ALAB and MRVL. |
| @amitisinvesting | $SPCX, $NVDA, $PLTR, $TSLA, $AMZN, $AAPL, $GOOGL, $MSFT, $NFLX, $INTC, $QCOM, $INFQ, $QBTS, $IBM, $RGTI, $IONQ, $QNT, $MU, $CVX | news | True | short-term | A major end-of-Q2 rebalancing wave could hit global markets, with institutional investors selling up to $165B of equities and rotating into bonds. |
| @aleabitoreddit | $TSM | opinion | True | short-term | Apollo fully bought out one of the TSM Japanese suppliers, which is a compelling M&A idea. |
| @aleabitoreddit | $IREN, $NBIS | opinion | True | medium-term | IREN was a bad investment due to endless dilution and a GPU pivot from Colo, and selling it for NBIS was the correct idea. |
| @aleabitoreddit | $IREN, $NBIS | opinion | True | medium-term | NBIS ended up compounding another 3-4x after being trashed by others, while IREN did not perform well. |
| @aleabitoreddit | $NBIS, $IREN | opinion | False | none | The speaker is expressing regret over missing out on potential investment opportunities in AI-related companies. |
| @kawzinvests | $MRVL | news | True | none | Marvell Technology is officially part of the S&P 500. |
| @spacanpanman | $SHAZ | news | True | 2H July | Sharon AI is planning to list shares on the Australian Stock Exchange with an expected IPO size of $200M or larger. |
| @kaizen_investor | $SAP | opinion | False | none | SAP is a high-quality ERP system but has limitations in its AI layer. |
| @michaelsikand | $MRVL | prediction | True | none | Jensen believes Marvell Technology's stock can increase four times from its current value. |
| @aleabitoreddit | $LPK, $AEHR | opinion | True | none | The speaker believes LPK's valuation could be reasonable at $3B-$5B when it fully ramps up volume. |
| @venu_7_ | $RDDT | prediction | True | less than a decade | RDDT is expected to grow its revenue nearly 20x in less than a decade. |
| @venu_7_ | $MCHP | opinion | False | none | Microchip Technology is a strong company in the analog semiconductor theme with a 24-month base and strong accumulation. |
| @venu_7_ | $FLNC | opinion | True | none | Fluence Energy is forming a constructive flag on the daily chart and has a solid monthly base forming. |
| @aleabitoreddit | $SIVE | prediction | True | short-term | The speaker expects Japan to win against Sweden in the World Cup. |
| @aleabitoreddit | $NVDA, $TSM | opinion | True | none | The speaker believes FOCI will be part of the bottleneck in the FAU and passive components ecosystem. |
| @aleabitoreddit | $SPY | prediction | True | short-term | The speaker expects the S&P 500 to be green tomorrow because the US won 2-0. |
| @venu_7_ | $HNGE | news | True | none | Hinge Health is a recent IPO with strong revenue growth, technicals, and exposure to AI software and healthcare-like margins. |
| @venu_7_ | $MU, $NBIS, $MRVL, $FPS | opinion | False | none | The speaker believes one name in the power semi theme can justify the investment and has other names like MU, NBIS, MRVL, and FPS in their portfolio. |
| @venu_7_ | $TXN, $ADI, $MCHP, $APH, $MPWR, $ON, $STM, $NVTS, $POWI, $WOLF, $IFNNY, $VICR, $AEIS, $VSH, $ALGM, $DIOD, $AOSL, $AIXA, $ENTG, $ICHR, $AMBQ, $RNECF, $ROHCY | opinion | False | none | The speaker suggests owning the chain, not one node, and lists various companies in different sub-sectors. |
| @venu_7_ | $RNECF, $ROHCY | opinion | False | none | The speaker highlights two international IDMs, Renesas and Rohm, with meaningful AI-DC content. |
| @venu_7_ | $AIXA, $ENTG, $ICHR, $AMBQ | opinion | False | none | The speaker lists four names in the equipment, materials, and edge AI sector, including Aixtron and Entegris. |
| @venu_7_ | $VSH, $ALGM, $DIOD, $AOSL | opinion | False | none | The speaker highlights four names in the discrete, sensing, and passives sector, including Vishay and Allegro. |
| @venu_7_ | $VICR, $AEIS | opinion | False | none | The speaker lists three names in the power modules and system-level conversion sector, including Vicor and Advanced Energy. |
| @venu_7_ | $ON, $STM, $NVTS, $POWI, $WOLF, $IFNNY | opinion | False | none | The speaker highlights seven names in the wide-bandgap device makers sector, including Onsemi and STMicro. |
| @venu_7_ | $TXN, $ADI, $APH, $MCHP, $MPWR, $MRVL, $FPS | opinion | False | none | The speaker lists five names in the broad analog and power management sector, including Texas Instruments and Analog Devices. |
| @venu_7_ | $TXN, $ADI, $MCHP, $APH, $MPWR, $ON, $STM, $NVTS, $POWI, $WOLF, $IFNNY, $VICR, $AEIS, $VSH, $ALGM, $DIOD, $AOSL, $AIXA, $ENTG, $ICHR, $AMBQ, $RNECF, $ROHCY | other | False | none | The speaker provides a list of the top 25 power semi companies, grouped by sub-sector. |
| @venu_7_ | $GH | opinion | True | none | The speaker mentions GH as another name in a massive stage 2 uptrend. |
| @venu_7_ | $XBI, $TGTX, $TVTX, $ALKS, $TWST, $RVMD | opinion | True | none | The speaker believes the biotech ETF XBI is in a massive stage 2 uptrend with clear institutional accumulation. |
| @venu_7_ | $STM | opinion | True | none | The speaker highlights STMicroelectronics as a strong company in the semiconductor sector with a 26-year massive base breakout and strong institutional accumulation. |
| @aleabitoreddit | $LITE, $SIVE | opinion | True | 2 years | The company $SIVE is at a similar starting point as Lumentum was in 2024. |
| @aleabitoreddit | $JBL, $SIVE, $NVDA | opinion | True | short-term | The market will react more significantly to an official release about $NVDA's cpo ecosystem than to rumors. |
| @aleabitoreddit | $POET, $GFS | other | False | none | None |
| @aleabitoreddit | $SIVE, $JBL, $POET, $MRVL, $GFS | opinion | True | long-term | The company $SIVE is a key supplier for next-gen architectures, not just CPO scale up. |
| @aleabitoreddit | $COHR, $LITE, $NVDA, $AMD | news | True | short-term | There is currently an EML bottleneck, and $COHR is buying EMLs from $LITE due to production constraints. |
| @aleabitoreddit | $SNDK | opinion | True | long-term | Nittobo could triple its company valuation if it followed the pricing strategy of $SNDK. |
| @aleabitoreddit | $LITE, $COHR | opinion | True | long-term | Korea is behind in laser technology, with the US, Japan, and China being more advanced. |
| @aleabitoreddit | $AAOI, $COHR, $LITE, $SIVE, $JBL, $GFS | opinion | True | long-term | OE Solutions is a small Korean optical transceiver company with potential for growth. |
| @aleabitoreddit | $SNDK | other | False | none | None |
| @aleabitoreddit | $HOOD | other | False | none | None |
| @venu_7_ | $MU | opinion | False | none | Technical analysis is a useful tool, but it should not be used to invalidate an entire framework. |
| @aleabitoreddit | $ASML, $TOWA, $LPK | opinion | True | long-term | The key to winning trade wars is through frontier supply chains like Quantum, AI, and Robotics. |
| @spacanpanman | $SHAZ, $BCAR | other | False | none | None |
| @aleabitoreddit | $CAMT, $WYFI, $SIVE, $ACMR | opinion | True | long-term | Priortech's ownership of $CAMT is significant, and Wistron is an interesting company to watch. |
| @aleabitoreddit | $RPI | opinion | True | short-term | The author's forecast modeling is more accurate than institutional reports. |
| @aleabitoreddit | $EWY | opinion | True | long-term | Samsung is undervalued given its operating income forecasts. |
| @aleabitoreddit | $XFAB | prediction | True | long-term | $XFAB is a 2027/2028 play that will recover independently in the second half of the year. |
| @aleabitoreddit | $AAOI | opinion | True | short-term | Bears are wrong when the entire industry is laser/capacity constrained, and $AAOI's projections are significant. |
| @michaelsikand | $RDDT, $NYT | opinion | True | long-term | The beneficiaries of the current market situation will be companies like $RDDT and publishers with legitimate news teams. |
| @aleabitoreddit | $INTC | other | False | none | None |
| @aleabitoreddit | $ASML | question | True | short-term | China's ability to smuggle in large items like those from $ASML is questionable. |
| @spacanpanman | $ASTS | news | False | none | SpaceX criticized the European Union's plans for satellite spectrum distribution. |
| @kaizen_investor | $WOLF | opinion | True | long-term | $WOLF is a volatile but undervalued AI stock. |
| @kaizen_investor | $SIVE | opinion | False | none | The author made a mistake by not buying $SIVE at 8SEK. |
| @kaizen_investor | $MRVL | opinion | True | long-term | $MRVL is a great company with tailwinds that will drive its growth. |
| @aleabitoreddit | $AAOI, $SIVE, $COHR | opinion | True | long-term | The author believes that laser companies like $AAOI and $SIVE have great potential for growth. |
| @aleabitoreddit | $ALRIB | news | True | short-term | ALRIB's general meeting notes reveal positive developments for the company. |
| @spacanpanman | $ASTS | news | False | none | New Street Research has published a report on AST SpaceMobile's joint venture policy issues and implications. |
| @amitisinvesting | $AMD, $HOOD, $AAPL, $SPCX, $NVDA, $GOOGL, $META, $SPY, $QQQ, $AMZN, $MSFT, $TSLA, $SOFI, $MU, $DRAM | news | False | none | The Fed did not cut rates at the recent meeting, and there was rigorous debate among policymakers. |
| @aleabitoreddit | $RDDT | other | False | none | The author is making a humorous comment about the potential poll results for $RDDT. |
| @spacanpanman | $BAER | other | False | none | none |
| @spacanpanman | $ASTS | news | True | short-term | AST SpaceMobile has several upcoming catalysts that could impact the company's performance. |
| @spacanpanman | $ASTS | other | False | none | none |
| @spacanpanman | $ASTS | opinion | False | none | The author is considering taking action related to $ASTS. |
| @spacanpanman | $SHAZ | news | False | none | Cantor has upgraded its price target for $SHAZ according to Bloomberg. |
| @spacanpanman | $ASTS | news | False | none | AST SpaceMobile has announced the successful orbital launch of BlueBirds 8, 9, and 10. |
| @kaizen_investor | $PL, $RKLB | opinion | True | long-term | The author is not worried about $PL dropping 50% because they invest in different 'investment waves'. |
| @spacanpanman | $ASTS | news | False | none | The author is sharing information about AST SpaceMobile's new Block-2 Composite Rings. |
| @spacanpanman | $ASTS | news | False | none | AST SpaceMobile's BlueBird8-10 mission was successfully delivered to orbit by SpaceX. |
| @spacanpanman | $ASTS | news | False | none | AST SpaceMobile has confirmed the successful deployment of its satellites. |
| @spacanpanman | $ASTS | news | False | none | AST SpaceMobile's BlueBird8-10 launch is available to watch. |
| @aleabitoreddit | $SIVE | opinion | False | none | The author is commenting on the difference between a legitimate stake in $SIVE and a retail meme. |
| @spacanpanman | $ASTS | news | False | none | AST SpaceMobile is at Cape Canaveral HQ. |
| @spacanpanman | $ASTS | other | False | none | none |
| @aleabitoreddit | $INTC | opinion | False | none | The author previously commented on $INTC's $36 PT report and its subsequent price increase. |
| @aleabitoreddit | $INTC | opinion | True | long-term | The author believes that Bernstein's analyst firm is not reliable and that their reports should be ignored. |
| @aleabitoreddit | $AEHR, $AAOI | news | False | none | There has not been much news or debate about $AEHR recently. |
| @amitisinvesting | $SPCH, $IBIT, $SPCX, $SPX, $TSLA, $NVDA, $AAPL, $INTC, $NFLX, $MU, $AMZN, $MSFT, $SOFI, $HOOD, $SNAP | news | False | none | The author is providing a recap of recent events in the stock market, including the upcoming FOMC meeting. |
| @aleabitoreddit | $AAOI, $AMD, $NVDA, $LITE, $NBIS | opinion | True | long-term | The author is confident in their long position on $AAOI and believes that the bears are wrong. |
| @spacanpanman | $ASTS | other | False | none | none |
| @spacanpanman | $ASTS | news | False | none | none |
| @michaelsikand | $SPCX, $SATS | prediction | True | long-term | In 50 years, $SPCX will be worth $100T. |
| @kaizen_investor | $NASA | opinion | False | none | There are good space ETFs like $NASA. |
| @kaizen_investor | $PL | opinion | True | short-term | The recent announcement by $PL was poorly timed and led to a stock price drop. |
| @spacanpanman | $ASTS, $RKLB, $PL, $SPCX | opinion | True | medium-term | The space industry is entering its AI moment, with smaller pure plays leading the upside chase. |
| @spacanpanman | $ASTS | opinion | False | none | The space has accomplished the impossible and made the author more bullish. |
| @spacanpanman | $RKLB | news | True | medium-term | KeyBanc upgraded Rocket Lab to Overweight with a $135 price target. |
| @aleabitoreddit | $SIVE | news | False | none | The author is waiting for the $SIVE general meeting to happen. |
| @aleabitoreddit | $IQE | other | False | none | none |
| @aleabitoreddit | $IQE, $TSEM, $MTSI | news | True | medium-term | IQE and $TSEM signed a multi-year InP epiwafer deal, which is important for Western optical supply chains. |
| @aleabitoreddit | $WOLF | opinion | False | none | The author is cheering for $WOLF despite not having a position in it. |
| @aleabitoreddit | $SIVE, $LITE | opinion | True | medium-term | The author is super bullish on their $SIVE position due to various positive factors. |
| @aleabitoreddit | $WOLF, $LITE, $SPCX | opinion | True | medium-term | It's stupid to be a bear when Trump is boosting markets and $WOLF and $LITE are set to go up. |
| @aleabitoreddit | $POET | opinion | True | medium-term | POET is sitting on too much cash and can acquire other companies to scale. |
| @aleabitoreddit | $AXTI, $IQE, $AAOI, $LITE, $SIVE | news | True | medium-term | China easing InP substrate exports will relieve mass production bottlenecks in the photonics market. |
| @aleabitoreddit | $NVTS, $POWI, $ON, $WOLF, $AOSL, $XFAB | prediction | True | short-term | Companies with power semi exposure, such as $NVTS and $POWI, will get a bump from Q3 pull forward. |
| @aleabitoreddit | $NVDA, $GOOGL, $VRT | news | True | medium-term | NVDA and GOOGL are leading the 800V DC charge ahead of schedule. |
| @amitisinvesting | $SPCX | opinion | True | medium-term | If Elon Musk is right, then $SPCX is pretty cheap. |
| @kaizen_investor | $WOLF | opinion | True | medium-term | WOLF is a good option for those looking for a stock that hasn't gone up too much. |
| @michaelsikand | $AAOI, $LITE, $COHR | opinion | False | none | AAOI is a controversial stock, but the author enjoys the disagreement and is long on it. |
| @aleabitoreddit | $SPCX, $SIVE, $SOI | opinion | False | none | The author's experiences with markets can be stereotyped based on regions, with America being bullish on futuristic stocks like $SPCX. |
| @aleabitoreddit | $SIVE | opinion | True | medium-term | The Nasdaq listing liquidity requirements and M&A are very positive for $SIVE. |
| @aleabitoreddit | $SIVE, $SNDK | opinion | True | long-term | The author likes $SIVE and thinks it will compound like $SNDK if it's important to AI. |
| @kawzinvests | $LITE, $AAOI, $FN, $CIEN, $CSCO | news | True | medium-term | The $LITE CEO said they are significantly under shipping demand, and the author mapped out the supply vs. demand across the 800G and 1.6T supply chain. |
| @spacanpanman | $ASTS | other | False | none | none |
| @kawzinvests | $RDDT | opinion | False | none | The company $RDDT is very unique. |
| @spacanpanman | $ASTS | opinion | False | none | A friend on Seal Team 6 says $ASTS has the most revolutionary technology he's ever seen. |
| @kaizen_investor | $PL | opinion | True | long-term | The author thinks $PL is the best space investment. |
| @spacanpanman | $ASTS | news | True | short-term | $ASTS has an impressive roadmap that brought Verizon onside over Starlink. |
| @aleabitoreddit | $TSM | prediction | True | medium-term | Foosung will be a massive beneficiary due to China's export control on Japan. |
| @aleabitoreddit | $AXTI | opinion | False | none | The AI supremacy wars will present interesting opportunities in the near future. |
| @spacanpanman | $ASTS | opinion | False | none | The author never uses margin and advises against it. |
| @spacanpanman | $ASTS | opinion | False | none | The author never uses margin. |
| @spacanpanman | $ASTS | opinion | False | none | The author is surprised by the magnitude of the drawdown in $ASTS. |
| @amitisinvesting | $SPCX | news | True | short-term | SpaceX $SPCX broke the record for largest volume of shares traded intraday of IPO. |
| @spacanpanman | $SHAZ | news | True | short-term | The S-1 registration for $SHAZ's $350m convertible notes may be causing pressure on the stock. |
| @spacanpanman | $SPCX, $ASTS | opinion | False | none | The author flipped out of $SPCX and deployed back into $ASTS. |
| @amitisinvesting | $SPCX | news | True | short-term | Elon Musk becomes the world's first trillionaire as $SPCX opens up 20%. |
| @aleabitoreddit | $SPCX | news | True | short-term | $SPCX is now trading and has a market capitalization of over $2.15T. |
| @kaizen_investor | $SPCX, $PL, $ASTS, $RKLB | opinion | True | short-term | There is a clear liquidity vacuum effect in $SPCX, making $PL, $ASTS, and $RKLB buying opportunities. |
| @aleabitoreddit | $SIVE | opinion | False | none | It's cool to see $SIVE on CNBC. |
| @spacanpanman | $TE | opinion | False | none | The author agrees that buying operating assets from another company takes time to transition. |
| @spacanpanman | $SHAZ | prediction | True | short-term | The author expects $SHAZ to rebound after the market digests SpaceX IPO volatility. |
| @aleabitoreddit | $SNDK, $SPCX | news | True | short-term | All the $SNDK short sellers went extinct as the stock price rose. |
| @spacanpanman | $ASTS | other | False | none | none |
| @spacanpanman | $SPKL | opinion | False | none | The author recommends watching the ZincFive management webcast with presentation slides. |
| @kaizen_investor | $SPIR, $BKSY | opinion | True | medium-term | $SPIR has a monopoly in commercial satellite weather data but a limited total addressable market. |
| @amitisinvesting | $SPCX, $HOOD | opinion | False | none | The author is grateful to Robinhood for giving access to the $SPCX IPO. |
| @spacanpanman | $SPCX | news | False | none | The author got filled on 26% of their request for SpaceX at Etrade/Morgan Stanley. |
| @venu_7_ | $RKLB | prediction | True | medium-term | $RKLB will be a $200 or more stock before the end of the year. |
| @venu_7_ | $SNDK, $MU, $STX, $INTC, $DELL, $WDC, $AMD, $AMAT, $LRCX | opinion | True | year | Despite a 5-6% pullback in indexes, the year is still phenomenal due to strong performance of some S&P 500 leaders. |
| @aleabitoreddit | $META, $MSFT, $SPCX | question | False | none | The reason for market correction is uncertain, possibly due to macro or liquidity pull. |
| @venu_7_ | $SNDK, $MU | opinion | True | short term | Aria is performing well with their investments in the memory theme. |
| @michaelsikand | $SATS, $RKLB, $ASTS, $STCK, $ZM, $CRM, $SKM | opinion | True | long term | The SpaceX proxy trade has generated significant returns, but the next trade, Anthropic, is more complex. |
| @aleabitoreddit | $AAOI | opinion | True | H1 2027 | The potential for a company to hit $471m/month revenue by the end of H1 2027 seems high. |
| @venu_7_ | $VSXY | news | True | short term | Victoria's Secret is breaking out of a 4-year base in an AI bull market. |
| @aleabitoreddit | $SPCX | opinion | True | short term | The impact of a liquidity vacuum on overall markets is uncertain, but it's positive for the USD. |
| @kawzinvests | $SKM, $NVDA | news | True | none | SKM's investment in Anthropic has increased significantly in value. |
| @spacanpanman | $ASTS | news | True | end of year | Blue Origin expects to fly again before the end of the year. |
| @venu_7_ | $ICHR, $SNDK, $ALAB, $ACMR, $UMC, $MRVL, $MU, $TTMI, $TEV, $SEZL, $CAVA, $STM, $CEVA, $AMBQ, $APH | opinion | True | short term | Many quality names are setting up for the next leg higher, making it hard to be overly bearish. |
| @spacanpanman | $ASTS | prediction | True | short term | The value of ASTS will increase when T-Mobile joins as a strategic partner. |
| @spacanpanman | $TE | opinion | True | none | The invoices peddled by Fuddy Panza are misleading. |
| @venu_7_ | $STM | opinion | True | long term | STM is a good investment opportunity due to its connection to the SpaceX ecosystem. |
| @aleabitoreddit | $SPCX | news | True | short term | Overseas demand for SpaceX shares could refinance 8% of the US current-account deficit in a single day. |
| @spacanpanman | $SPKL, $SPKLW | opinion | True | short term | ZincFive is an interesting data center infrastructure play going public via SPKL. |
| @venu_7_ | $CRDO, $ALAB | opinion | True | short term | CRDO and ALAB are potential new leaders due to their strong relative strength and growth fundamentals. |
| @spacanpanman | $SPCX | news | True | 2025-2027 | SpaceX's growth looks insane based on forward estimates. |
| @spacanpanman | $TE | news | True | short term | UBS raises First Solar price target to $330 due to expected Section 232 tariffs. |
| @spacanpanman | $SPKL | news | True | none | The trust value of SPKL is at $11.39. |
| @spacanpanman | $SPKL, $SPKLW | news | True | none | The float of SPKL is small at 2.24M shares. |
| @kaizen_investor | $ASM | opinion | True | long term | Holding a quality company for the long run can generate significant returns. |
| @spacanpanman | $SPCX | news | True | none | Banks have initiated research coverage of SpaceX before its IPO. |
| @spacanpanman | $ASTS | opinion | True | long term | AST SpaceMobile provides valuable services to operators, including real coverage without terrestrial capex. |
| @spacanpanman | $TE | other | False | none | The user has picked up some shares and warrants of TE. |
| @spacanpanman | $ASTS | other | False | none | none |
| @kawzinvests | $AAOI | prediction | True | 2027 | The company $AAOI is going to increase its laser production from 5k to 400k a month by 2027. |
| @aleabitoreddit | $AXTI, $ALRIB, $LPK | opinion | False | none | The user is holding onto their $AXTI position due to concerns about dilution and export controls. |
| @venu_7_ | $FROG, $TWLO, $SNOW, $DDOG | opinion | True | none | High tight flags are forming in leader stocks like $FROG, $TWLO, $SNOW, and $DDOG. |
| @kawzinvests | $LITE, $AAOI, $COHR, $FN, $CIEN, $CSCO | news | True | none | The demand for optics is high, with $LITE being sold out and $AAOI facing undershipping demand. |
| @aleabitoreddit | $SOI, $XFAB, $IQE | prediction | True | none | European supply chain companies like $SOI, $XFAB, and $IQE will recover from the recent selloff. |
| @spacanpanman | $ASTS | news | True | June 17th | There will be a Pitstop Ahead of June 17th BlueBird 8, 9, 10 Launch for $ASTS. |
| @aleabitoreddit | $LITE, $AAOI, $SIVE | opinion | False | none | The initial selloff of optical players like $LITE, $AAOI, and $SIVE was unjustified. |
| @venu_7_ | $CRDO, $UNH, $APH, $ALAB, $OSCR, $CVS, $FTNT, $FROG, $FPS, $MDB, $DOCN, $AMAT, $HNGE, $AMKR, $VIAV, $ACMR, $SNOW, $DDOG, $NBIS, $MRVL, $VSH | opinion | True | none | The listed stocks have the best relative strength in the market. |
| @spacanpanman | $ECON | question | True | none | The recent spike in jobs may be related to front-loading for the World Cup. |
| @spacanpanman | $RKLB, $ASTS | news | True | none | Everyday investors like space nerds have made millions betting on space before the SpaceX IPO. |
| @spacanpanman | $ECON | prediction | True | none | The resolution of the Iranian conflict will lead to a decrease in CPI drivers. |
| @spacanpanman | $ASTS | opinion | False | none | AST SpaceMobile is inevitable. |
| @spacanpanman | $ECON | other | False | none | none |
| @aleabitoreddit | $SIVE | news | True | none | Blackrock is a passive investor in $SIVE, tracking the MSCI/Nasdaq index. |
| @aleabitoreddit | $NVDA, $ASTS | opinion | False | none | Nvidia is a $5T company and knows its own timelines and difficulties. |
| @aleabitoreddit | $NVDA | news | True | none | Nvidia has denied reports about 800v and CPO delays. |
| @aleabitoreddit | $NVDA, $MU | opinion | True | none | The recent selloff of $NVDA due to reports of 800V DC and CPO delays is unjustified. |
| @aleabitoreddit | $SIVE | news | True | none | Blackrock and Fidelity Research have taken positions in $SIVE, indicating US institutional investment. |
| @aleabitoreddit | $NVDA | opinion | False | none | The market is overreacting to analyst reports about Nvidia's timelines. |
| @aleabitoreddit | $NVDA | opinion | False | none | Nvidia's statements about its timelines should be trusted over external analyst reports. |
| @aleabitoreddit | $LITE, $NVDA | news | True | 2027 | LITE's management expects to start shipping CPO scale-up optical products in the second half of 2027. |
| @aleabitoreddit | $NVDA | news | True | none | Nvidia's Networking Senior Vice President has refuted recent analyst reports on delays. |
| @spacanpanman | $ASTS | opinion | True | none | The user claiming to be 'early' on $ASTS is not credible. |
| @spacanpanman | $ASTS | opinion | True | none | The user's claim of being 'early' on $ASTS is false. |
| @spacanpanman | $ASTS | news | True | none | AST SpaceMobile's broadband satellite coverage is important for America's First Responder Network. |
| @venu_7_ | $TSLA | opinion | False | none | The user still thinks $TSLA looks good. |
| @venu_7_ | $FROG | promotion | False | none | Few are paying attention to the infrastructure managing AI agents, which is where $FROG comes in. |
| @amitisinvesting | $AAPL, $GOOGL, $NVDA | news | False | none | Apple, Google, and Nvidia are teaming up to level up Apple's AI for more compute. |
| @amitisinvesting | $F | news | True | none | Robinhood gave millions of new users a free share of $F to sign up back in 2018-2020, so many people just held it. |
| @amitisinvesting | $AMD, $NFLX, $HOOD, $META, $GOOGL, $AMZN, $MSFT, $NVDA, $PLTR, $F, $TSLA | news | True | none | The Top 10 investments across Robinhood just got updated for June, with $AMD replacing $NFLX as one of the top 10 held stocks. |
| @venu_7_ | $KEEL | prediction | True | short-term | A monster cup is forming in $KEEL, and a potential new small-cap leader is emerging. |
| @amitisinvesting | $MRVL | opinion | True | none | Jensen didn't say $MRVL was going to $1T like he did for $MRVL. |
| @spacanpanman | $TE | news | True | short-term | A Section 232 ruling on polysilicon and solar derivatives is expected by late June 2026, which could raise the value of US-made, non-FEOC solar products for $TE. |
| @venu_7_ | $MU | opinion | True | short-term | Micron is generating a significant amount of operating profit every quarter and is turning into a cash-printing machine. |
| @venu_7_ | $LLY, $MRK, $UNH, $JNJ | opinion | False | none | Four legacy healthcare names worth watching are $LLY, $MRK, $UNH, and $JNJ. |
| @spacanpanman | $SPCX | news | True | short-term | SpaceX's initial public offering is well oversubscribed, according to people familiar with the matter. |
| @venu_7_ | $STM | prediction | True | short-term | $STM looks ready for the next leg higher. |
| @kaizen_investor | $PL, $GOOGL | opinion | False | none | The partnership between $PL and $GOOGL is a significant advantage that no other company in the industry has. |
| @amitisinvesting | $QCOM | promotion | False | none | Jensen recommends buying $QCOM stock. |
| @spacanpanman | $ASTS | opinion | False | none | AST SpaceMobile's PNT capabilities are critical for national security. |
| @amitisinvesting | $MU, $NVDA, $TSLA, $SNDK, $AMD | news | True | none | The largest retail single stock net inflows for the month of May were $MU, $NVDA, $TSLA, $SNDK, and $AMD. |
| @venu_7_ | $MRVL | prediction | True | short-term | $MRVL is showing characteristics of a William O'Neil High Tight Flag, which could lead to a significant price increase. |
| @venu_7_ | $OSCR | prediction | True | short-term | $OSCR has room to move towards $36. |
| @aleabitoreddit | $XFAB | opinion | False | none | $XFAB is a European company that the user really likes, but the market is sleeping on it. |
| @spacanpanman | $ASTS, $TE | news | False | none | The user covered their short $ASTS calls and added to $TE with a strategic financing package coming soon. |
| @spacanpanman | $CEPT, $SECZ | news | True | short-term | The merger proxy for $CEPT is now effective, and the company will trade under the ticker $SECZ upon closing. |
| @venu_7_ | $JBHT, $VIAV | other | False | none | The user is referencing two charts for $JBHT and $VIAV. |
| @venu_7_ | $SNOW | prediction | True | short-term | Snowflake is finding support at the 9-day EMA and PEG low, which could be a good entry opportunity. |
| @aleabitoreddit | $MRVL, $ARM, $AAOI | opinion | True | short-term | The user's names, including $MRVL and $ARM, have performed well and have room to go higher. |
| @aleabitoreddit | $IBIT, $XLU, $META, $CRCL, $HOOD, $NBIS | opinion | True | none | The user's portfolio has performed well, with 25 out of 30 names being green and many up by triple digits. |
| @venu_7_ | $VSH, $STM, $FSLR | opinion | True | medium-term | The stocks $VSH, $STM, and $FSLR are approaching Dot-Com and 2008 highs and are worth paying attention to. |
| @spacanpanman | $TE | news | True | short-term | Microsoft's acquisition of land in Finland for a data center project is a significant development for $TE. |
| @aleabitoreddit | $MRVL, $ARM, $INTC | opinion | True | long-term | The US list from $MRVL to $ARM to $INTC is a strong selection of US equities. |
| @kaizen_investor | $WOLF | opinion | True | medium-term | NVIDIA's 800V HVDC architecture requires massive amounts of power and SiC is necessary for the pivot. |
| @aleabitoreddit | $SIVE, $GFS, $JBL, $NVDA, $MRVL, $AMD | opinion | True | long-term | The combination of $SIVE and other companies such as $JBL and $NVDA is compelling for long-term investment. |
| @aleabitoreddit | $SIVE | news | True | short-term | The news of US institutional accumulation of 5%+ of $SIVE is primarily new news. |
| @aleabitoreddit | $SIVE | opinion | True | medium-term | The implications of JP Morgan's disclosure of buying 5.25%+ of $SIVE are greater than people think. |
| @aleabitoreddit | $NVDA | other | False | none | None |
| @kaizen_investor | $PL | other | False | none | None |
| @aleabitoreddit | $SIVE | opinion | True | short-term | The stock $SIVE is only up 3.36% off the news of JP Morgan's institutional buying, which is surprising. |
| @aleabitoreddit | $IFNNY, $ON, $VICR, $LFUS, $VSH, $ENPH, $NVTS, $POWI, $BDC, $EOSE, $SEDG, $AEHR, $WOLF, $CWR, $AMSC, $XFAB, $AOSL, $HYLN, $FCEL, $IQE, $ASYS, $RELL, $PAY, $IPWR, $POET | other | False | none | None |
| @aleabitoreddit | $TSLA, $VPG | opinion | True | long-term | LeaderDrive is China's standout component leader in the robotics sector. |
| @spacanpanman | $BAER | opinion | True | medium-term | The research piece on Bridger Aerospace by @BDeveran has a price target of $5, which is a bullish sign. |
| @aleabitoreddit | $MRVL | news | False | none | The article from 中国证券报 on LeaderDrive analysis is objective and worth reading. |
| @spacanpanman | $ASTS | other | False | none | None |
| @kawzinvests | $NVDA | other | False | none | None |
| @amitisinvesting | $SPCX | news | True | short-term | $SPCX is already 2x oversubscribed. |
| @amitisinvesting | $QQQ, $SPCX, $AVGO, $META | question | True | medium-term | The -4% day on the Nasdaq $QQQ last Friday is a significant event that may be the start of something bigger. |
| @michaelsikand | $MRVL | news | True | short-term | The "Inverse Cramer" portfolio on @joinautopilot has performed well, with a 246% gain on $MRVL. |
| @kaizen_investor | $PL | opinion | True | long-term | The investor is only invested in $PL and thinks it has a strong moat. |
| @kaizen_investor | $PL | other | False | none | The deep dive on $PL is available for informational purposes. |
| @kawzinvests | $VRT, $PWR | opinion | True | long-term | $VRT and $PWR are the picks and shovels of the picks and shovels. |
| @kawzinvests | $STM | opinion | True | medium-term | $STM holders will benefit when Kyber ramps. |
| @kawzinvests | $NVDA, $IFX, $MPWR, $VICR, $NVTS, $STM, $ON, $TXN, $ADI, $POWI, $DIOD, $WOLF, $AOSL | opinion | True | medium-term | NVIDIA's power system will need to be upgraded to support the increasing number of GPUs. |
| @aleabitoreddit | $NVDA, $SIVE, $SOI | opinion | True | medium-term | NVIDIA's CEO has called out Silicon Photonics with memory, which is a bullish sign for the SiPH supply chain. |
| @spacanpanman | $SPCX | opinion | True | short-term | SpaceX getting more AI data center customers will help support its IPO valuation. |
| @amitisinvesting | $META, $GOOGL, $MSFT, $AMZN | news | True | short-term | Financial Times is reporting that META is thinking of raising tens of billions in a new share sale. |
| @amitisinvesting | $PLTR | opinion | False | none | Having sales calls with LLM companies is not as valuable as working with a company that cares about bringing value. |
| @venu_7_ | $QQQ | prediction | True | short-term | The anchored VWAP from April 29th is a key area for buyers to watch if QQQ loses the 21-day EMA. |
| @aleabitoreddit | $NVDA, $GOOGL, $AMZN, $MRVL, $LITE, $COHR, $INTC | opinion | True | long-term | Hyperscaler ASICs will eventually siphon off NVDA demand. |
| @aleabitoreddit | $NVDA, $MU, $PL, $AAOI | news | False | none | Market corrections are happening, with leaders like NVDA and MU experiencing losses. |
| @spacanpanman | $PL | other | False | none | none |
| @spacanpanman | $PL, $RKLB | opinion | False | none | The size of Planet Labs' ATM is too aggressive. |
| @spacanpanman | $SPCX | prediction | True | short-term | Investors who were selling positions to participate in the SPCX IPO will be left with unused funds. |
| @aleabitoreddit | $TSM | opinion | False | none | Xintec is an interesting investment opportunity due to its connection to TSMC. |
| @aleabitoreddit | $SIVE | opinion | True | short-term | The founding co-manager of a hedge fund quitting is a sign that the firm is going under. |
| @aleabitoreddit | $SIVE | opinion | True | short-term | A hedge fund is performing poorly due to its position on SIVE. |
| @venu_7_ | $FROG | opinion | True | long-term | JFrog is becoming an important piece of the Agentic AI stack. |
| @aleabitoreddit | $SIVE, $AAOI, $TSM, $NVDA, $TSEM, $SOI | opinion | False | none | The user is a fan of several companies, including SIVE and AAOI. |
| @aleabitoreddit | $AAOI | opinion | True | short-term | AAOI has large exposure to CPO. |
| @aleabitoreddit | $JBL, $SIVE, $NVDA | prediction | True | medium-term | Several companies, including SIVE, will be working on pluggable and CPO scale-up applications in the near future. |
| @venu_7_ | $CRDO | prediction | True | short-term | Credo's stock is forming a flag after breaking out of a 6-month base. |
| @aleabitoreddit | $SIVE, $GFS, $JBL | opinion | True | long-term | SIVE's CPO applications are not imaginary. |
| @venu_7_ | $QQQ | prediction | True | short-term | The Nasdaq is about to test its 21-day EMA, and a pullback could be an opportunity to buy. |
| @spacanpanman | $ASTS, $TE | other | False | none | none |
| @kaizen_investor | $PL | opinion | False | none | Planet Labs' ATM announcement may be painful for current shareholders but could be an entry point for new investors. |
| @spacanpanman | $ASTS | news | True | short-term | Short sellers are covering their positions in ASTS. |
| @aleabitoreddit | $GOOGL | opinion | False | none | Technical analysis is not as important as fundamentals. |
| @spacanpanman | $PL | news | False | none | Clear Street has raised its price target for Planet Labs to $53. |
| @spacanpanman | $MRLN | news | False | none | The real-time short interest in MRLN is 4.9M shares with a 37% borrow fee. |
| @michaelsikand | $KRKNF, $AVAV, $KTOS, $AVEX, $LASR, $EOS | opinion | False | none | The author's trading portfolio, which includes a subsea drone stock, has caught the attention of NYMag. |
| @spacanpanman | $ASTS | other | False | none | none |
| @spacanpanman | $TE | news | True | 2032 | Solar power will become the largest source of global electricity generation by 2032. |
| @venu_7_ | $FSLR, $ENPH, $SEDG, $NXT | other | False | none | none |
| @spacanpanman | $BAER | promotion | False | none | The author is encouraging investors to continue investing in BAER. |
| @spacanpanman | $TE | question | True | none | The increasing demand for data centers will require more power. |
| @kaizen_investor | $PL | prediction | True | short-term | The author expects PL's Q1 earnings to show 36% year-over-year growth. |
| @kaizen_investor | $AMZN, $ASTS | opinion | True | medium-term | The company's success in producing GaN V-band Amps will allow them to play a significant role in the market. |
| @venu_7_ | $TSLA, $MU, $NBIS | other | False | none | none |
| @michaelsikand | $CIEN | opinion | True | short-term | The stock price of CIEN is undervalued despite the company's strong earnings report. |
| @venu_7_ | $KLIC, $ACMR, $VIAV, $MCHP | opinion | True | medium-term | The High, Tight Flag chart pattern is a powerful indicator of stock performance. |
| @venu_7_ | $FPS | opinion | True | medium-term | The market is starting to understand the importance of power infrastructure for AI. |
| @amitisinvesting | $PLTR | news | False | none | Palantir's sales strategy is to let customers try other companies' products first. |
| @kawzinvests | $CIEN, $AAOI, $COHR, $LITE | news | True | short-term | CIEN's strong earnings report and revenue growth indicate a positive outlook for the company. |
| @venu_7_ | $RKLB | prediction | True | medium-term | Rocket Lab's stock price will reach $200. |
| @spacanpanman | $TE | opinion | True | long-term | The demand for polysilicon solar cell fab producers will increase due to AI. |
| @venu_7_ | $XBI | opinion | False | none | The biotech sector is too volatile for the author's investment portfolio. |
| @venu_7_ | $FSLR | prediction | True | medium-term | FSLR's stock price will increase due to the company's strong fundamentals. |
| @venu_7_ | $NBIS | prediction | True | medium-term | NBIS's stock price will reach $300. |
| @venu_7_ | $MRVL, $ALAB | question | False | none | The author is considering investing in either MRVL or ALAB. |
| @venu_7_ | $FROG, $SNOW, $DDOG, $BAND, $FIVN | other | False | none | none |
| @venu_7_ | $IONQ, $QNT | opinion | True | medium-term | The quantum theme is becoming increasingly popular, and IONQ's stock price will benefit from it. |
| @venu_7_ | $MU | opinion | False | none | The author has not trimmed their MU position since it reached $370. |
| @aleabitoreddit | $RDDT | opinion | True | short-term | RDDT's stock price is undervalued despite the company's strong earnings and revenue growth. |
| @venu_7_ | $MRVL | opinion | True | medium-term | MRVL's stock price has the potential to increase significantly. |
| @venu_7_ | $ONDS | opinion | True | short-term | Ondas is experiencing a healthy backtest of the 21-day EMA and ATH VWAP. |
| @venu_7_ | $INOD | opinion | True | medium-term | Innodata is well-positioned for a major Stage 2 uptrend due to its role in AI model training and evaluation. |
| @spacanpanman | $BCAR, $SHAZ | opinion | False | none | The user is long on $BCAR and $SHAZ. |
| @venu_7_ | $SNOW, $INOD, $ORCL, $DDOG, $TWLO, $FTNT, $BAND, $FIVN, $FROG, $DOCN, $AKAM, $RDDT, $NAVN, $CRWD, $PANW, $RBRK, $NET, $LOGI, $APP, $MDB | opinion | True | medium-term | The user believes the best risk/reward opportunities are shifting toward software and cybersecurity. |
| @spacanpanman | $TE | opinion | True | short-term | The BESS deal is bullish for T1 Energy. |
| @spacanpanman | $ASTS | other | False | none | none |
| @spacanpanman | $BRUN, $SHAZ, $BCAR | news | True | short-term | Boost Run is hitting on all cylinders and its price target has been raised to $45. |
| @spacanpanman | $TE | opinion | False | none | The user bought more $TE overnight. |
| @spacanpanman | $SRTA | news | True | short-term | LAKE STREET CAPITAL raised Strata's critical price target to $9.50 and reiterates a buy rating. |
| @aleabitoreddit | $SIVE | news | True | short-term | Origo's fund has lost substantial money shorting $SIVE. |
| @spacanpanman | $ASTS | other | False | none | none |
| @aleabitoreddit | $NVDA | news | True | short-term | Jensen Huang is meeting with Faker, a League of Legends player. |
| @aleabitoreddit | $SIVE, $IQE, $MTSI, $GFS, $JBL | opinion | True | medium-term | It's hard for major companies to acquire CHIPS act funded companies like $SIVE on a whim. |
| @aleabitoreddit | $SIVE | opinion | True | medium-term | Win Semi is confident in scaling up significant volume for $SIVE. |
| @aleabitoreddit | $SIVE | opinion | True | medium-term | The user is confident in their $SIVE thesis playing out. |
| @aleabitoreddit | $NVDA, $MU | opinion | True | short-term | Insider selling means literally nothing. |
| @aleabitoreddit | $SIVE | opinion | True | medium-term | Other pluggable players may create novel 1.6T architectures using $SIVE. |
| @aleabitoreddit | $SIVE, $LITE, $NVDA, $SNDK, $MRVL, $COHR, $AVGO, $MTSI, $JBL, $GFS, $AMD | opinion | True | medium-term | $SIVE looks like both a chokepoint and a bottleneck for CPO next year. |
| @aleabitoreddit | $SIVE, $NVDA | opinion | True | short-term | $SIVE was probably the most recent visible laser chokepoint that's still being rerated. |
| @venu_7_ | $SNOW | opinion | True | medium-term | Snowflake is becoming a key platform for Enterprise AI and Agentic AI. |
| @venu_7_ | $ALGM | opinion | True | medium-term | Allegro MicroSystems is a leader in magnetic sensors and power semiconductors used in EV's, industrial automation, robotics, and data centers. |
| @aleabitoreddit | $GOOGL, $META, $AMZN, $SIVE, $SOI | news | True | long-term | Goldman now expects a combined $5.3 trillion of capex spending for the four largest hyperscalers from 2025 to 2030. |
| @venu_7_ | $MU, $TSLA | other | False | none | none |
| @venu_7_ | $TSLA | prediction | True | short-term | A big move is brewing for $TSLA. |
| @aleabitoreddit | $IBIT, $ETHA, $HOOD, $COIN | opinion | False | none | The user bought $IBIT and $ETHA for swing trading. |
| @aleabitoreddit | $XFAB, $SIVE | news | False | none | Europe is releasing its Tech Sovereignty Package, which includes the CHIPS ACT 2.0 and highlights $XFAB and $SIVE in the Industry Policy Blueprints. |
| @amitisinvesting | $MRVL, $META, $NVDA, $TSLA, $AAPL, $MSFT, $GOOGL, $INTC, $NOK, $MSTR, $AMZN, $BTC, $PANW, $CRWV, $SPCX, $UBER, $GME, $SHOP | news | False | none | A lot of things happened in the stock market today, including Marvell's significant increase in market cap after Jensen Huang's comment. |
| @aleabitoreddit | $SIVE, $NVDA | opinion | False | none | Having $SIVE as the laser supplier to $NVDA nvlink fusion ecosystem is big news. |
| @aleabitoreddit | $TSM | opinion | True | none | Xintech, owned by TSMC, is probably the unknown $TSM COUPE supplier. |
| @aleabitoreddit | $LPK | opinion | False | none | There is no news aside from waiting for volume orders for $LPK and others in H1 2027. |
| @aleabitoreddit | $AEHR, $LPK | opinion | False | none | Good times with $AEHR, now with a market cap of ~$3.5B, waiting for volume orders. |
| @speculator_io | $BE, $GEV, $PWR, $AMPX, $VICR, $VST, $NVTS, $BWXT, $CEG, $UEC, $CCJ, $NVDA, $TSM, $INTC, $AVGO, $AMD, $ASML, $ARM, $MRVL, $AAOI, $AXTI, $COHR, $MU, $SNDK, $STX, $OPTX, $LITE, $ICHR, $AEHR, $WDC, $NBIS, $IREN, $CRWV, $APLD, $VRT, $DELL, $HPE, $ORCL, $GOOGL, $META, $AMZN, $TSLA, $NOW, $PLTR, $DOCN, $SNOW, $NET, $FSLY, $INOD | promotion | False | none | Jensen Huang's 5-Layer AI Cake investment strategy includes various stocks. |
| @spacanpanman | $BCAR, $BCARW | opinion | False | none | The user is long $BCAR $BCARW. |
| @michaelsikand | $BRUN, $NVDA, $NBIS | prediction | True | short-term | $BRUN will end up on Leopold's 13F due to its credibility and $471M take or pay from a top AI lab. |
| @venu_7_ | $FSLR | opinion | False | none | The $FSLR monthly chart is a beast. |
| @venu_7_ | $MRVL | opinion | False | none | $MRVL is officially a 3x bagger for the user. |
| @amitisinvesting | $SHOP | news | False | none | Shopify announces a $3B increase to its share buyback program, and Tobi thinks the stock is cheap. |
| @venu_7_ | $MRVL | other | False | none | none |
| @aleabitoreddit | $MRVL, $NBIS | opinion | True | long-term | Jensen Huang gave a $1T price target for $MRVL, which is a significant claim. |
| @spacanpanman | $ASTS | news | False | none | Another day, another $ASTS patent. |
| @spacanpanman | $ASTS | news | False | none | T-Mobile's response to a question about satellite service was defensive and directed towards Starlink. |
| @venu_7_ | $FPS | opinion | True | long-term | $FPS looks promising long-term. |
| @spacanpanman | $SHAZ | news | False | none | There is a short report from Bleecker on SharonAI, and Oak Tree is a reputable institutional investor. |
| @michaelsikand | $KRKNF | opinion | False | none | Everyone who has studied $KRKNF deeply has class and is patient. |
| @venu_7_ | $HBM, $FSLR | opinion | True | short-term | $HBM $FSLR are breaking out of a monster base. |
| @spacanpanman | $BCAR | opinion | True | short-term | $BCAR looks pretty interesting and could perform well post-merger. |
| @spacanpanman | $BCAR | opinion | False | none | The user is looking at $BCAR and thinks it could be interesting. |
| @spacanpanman | $TE, $LIFE | opinion | True | short-term | There is a coordinated hedge fund hit job on $TE. |
| @venu_7_ | $SEZL | opinion | True | short-term | $SEZL is quietly building a monster cup. |
| @spacanpanman | $ASTS, $RKLB | prediction | True | short-term | $ASTS could mean revert to $RKLB down to -$7.5 and could flip this week. |
| @spacanpanman | $ASTS | news | True | short-term | ULA Vulcan Centaur will return to service after July |
| @spacanpanman | $SHAZ | news | True | none | SharonAI has a market cap of $1.4B and has raised $350M in funding |
| @spacanpanman | $SHAZ | opinion | False | none | SharonAI is being researched by the author |
| @spacanpanman | $SHAZ, $NBIS, $IREN | opinion | True | long-term | SharonAI is undervalued compared to its peers |
| @amitisinvesting | $NVDA, $MRVL | opinion | True | short-term | Jensen's endorsement can significantly impact a company's stock price |
| @kaizen_investor | $PL, $RKLB | opinion | False | none | The author is considering the potential impact of the SpaceX IPO on their portfolio |
| @spacanpanman | $WLAC | other | False | none | The author forgot to follow a stock |
| @speculator_io | $CRWV, $NBIS, $IREN, $IBM, $CDNS, $J, $PCOR, $PTC, $SIE, $SU, $DSY, $VRT, $GEV, $TT, $ABBN, $CAT, $ETN, $ENGI, $DLR, $EQIX, $SIFY, $DELL, $HPE, $SMCI | news | True | none | Nvidia's AI Factory Ecosystem includes several companies |
| @spacanpanman | $TE | news | True | short-term | T1 Energy is making progress on its G2 plant construction |
| @spacanpanman | $TE | opinion | True | short-term | There is an arbitrage opportunity in T1 Energy's warrants and calls |
| @aleabitoreddit | $LITE, $SIVE | prediction | True | long-term | Sivers can replicate the success of LITE in the optical wave |
| @venu_7_ | $ETN | opinion | True | long-term | Eaton is a high-quality electrical infrastructure company with a strong backlog |
| @spacanpanman | $ASTS, $TE | opinion | True | short-term | Blue Origin's setback is an opportunity for AST SpaceMobile |
| @venu_7_ | $MP | other | False | none | The author is excited about their investment in MP |
| @aleabitoreddit | $SOI, $XFAB | opinion | False | none | The author is surprised by the market's reaction to SOI and XFAB's valuations |
| @venu_7_ | $FSLR | prediction | True | short-term | First Solar is setting up to break out of an 18-year base |
| @venu_7_ | $MP, $UAMY, $USAR, $REMX | prediction | True | short-term | Rare earth stocks are poised for a breakout |
| @spacanpanman | $ASTS | news | True | none | Short interest in AST SpaceMobile has decreased |
| @aleabitoreddit | $XFAB, $TSEM, $NVDA, $NOK | opinion | False | none | XFAB reminds the author of early TSEM |
| @spacanpanman | $TE | opinion | False | none | Solar is the future |
| @michaelsikand | $KRKNF, $HOOD | opinion | True | long-term | Owning the future of subsea defense with KRKNF feels undeniably asymmetrical |
| @venu_7_ | $MRVL | other | False | none | none |
| @venu_7_ | $MRVL | news | True | short-term | Marvell's stock price has increased significantly since the author's initial investment |
| @kaizen_investor | $SIVE, $POET | opinion | True | long-term | Using AI agents to search for stocks can be a successful strategy |
| @kaizen_investor | $NVDA, $FLNC, $MRVL, $SIVE | opinion | True | short-term | Jensen's endorsement can significantly impact a company's stock price |
| @venu_7_ | $NVDA, $AVGO | opinion | True | medium-term | NVDA and AVGO have much higher prices ahead. |
| @michaelsikand | $NOK | opinion | True | medium-term | The market still underestimates NOK. |
| @venu_7_ | $MU | question | False | none | The question is when to sell a winner like Micron. |
| @venu_7_ | $ARM | opinion | True | short-term | ARM bulls should be sitting on some fat gains. |
| @venu_7_ | $INOD | opinion | True | medium-term | INOD is one of the favorite AI software names and will reach $150. |
| @aleabitoreddit | $HPS | opinion | True | long-term | HPS.A is a good long-term investment due to its backlog and market share. |
| @aleabitoreddit | $SIVE | other | False | none | none |
| @aleabitoreddit | $AAOI, $SNDK | opinion | True | long-term | AAOI is the next SNDK and will have a massive inflection point in H1 2027. |
| @michaelsikand | $BRUN, $GLXY, $CRWV, $IREN, $NBIS, $NOK, $BE, $LASR, $CRCL, $AAOI, $MU, $PENG | opinion | True | medium-term | BRUN is surging and will continue to grow. |
| @aleabitoreddit | $ARM | other | False | none | none |
| @aleabitoreddit | $SOI | opinion | True | short-term | SOI is still doing well despite the 17% drop. |
| @aleabitoreddit | $ARM | opinion | False | none | ARM's growth is ridiculous and could have been more profitable with options. |
| @aleabitoreddit | $CRWV, $IREN, $NBIS | opinion | True | medium-term | NBIS is the best neocloud player due to its debt interest and upside potential. |
| @aleabitoreddit | $NBIS | other | False | none | NBIS has plot armor confirmed. |
| @aleabitoreddit | $EWY, $MU | news | True | medium-term | EWY leaps are up 485% due to IV expansion and directional memory longs. |
| @aleabitoreddit | $SIVE, $AAOI | opinion | False | none | It's disingenuous to conflate different architectures and timelines for SIVE. |
| @aleabitoreddit | $IQE, $LPK, $SOI, $XFAB, $ALRIB | opinion | True | long-term | IQE is a successful long-term investment. |
| @aleabitoreddit | $SIVE, $MRVL, $POET, $AAPL, $AVGO, $LITE, $COHR | opinion | False | none | The new SIVE short seller has no clue what they're talking about. |
| @venu_7_ | $NBIS | opinion | True | medium-term | NBIS is the best dip-buy name and will continue to grow. |
| @venu_7_ | $RKLB | prediction | True | medium-term | RKLB is heading toward $200. |
| @aleabitoreddit | $NVDA, $FLNC | news | True | short-term | FLNC is up 36% due to its reference power architectures for Vera Rubin N72. |
| @aleabitoreddit | $IREN | opinion | True | medium-term | IREN's infinite ATM dilution machine is a concern. |
| @aleabitoreddit | $NBIS | other | False | none | NBIS has the power of Plot Armor. |
| @aleabitoreddit | $NBIS, $IREN, $CIFR | prediction | True | long-term | NBIS will reach a $100B market cap. |
| @spacanpanman | $ASTS | news | True | short-term | ASTS has agreements in place with multiple launch providers. |
| @aleabitoreddit | $LITE | opinion | False | none | The sale of a hedge fund's positions does not impact the market. |
| @aleabitoreddit | $LITE, $AAOI, $SIVE, $JBL | opinion | True | long-term | The market is driven by extreme forward revenue growth. |
| @aleabitoreddit | $AAOI, $SIVE, $LITE, $AMD, $NVDA | opinion | True | short-term | The current selloff in photonics markets is due to algorithmic trading. |
| @aleabitoreddit | $SIVE | opinion | False | none | The stock would be 90% institutionally owned without individual investors. |
| @aleabitoreddit | $LITE, $COHR, $SIVE | opinion | True | long-term | There are few major pluggable players that do not vertically integrate lasers. |
| @aleabitoreddit | $SIVE | news | True | short-term | The company is working with new pluggable optical transceiver companies. |
| @aleabitoreddit | $SIVE | opinion | False | none | The cultural battle is just normal volatility. |
| @aleabitoreddit | $SIVE, $JBL | opinion | True | long-term | The stock is unlikely to reach certain levels again. |
| @aleabitoreddit | $SIVE, $JBL, $SOI | opinion | False | none | The cultural attitude in Sweden is to dislike anything special or growth-related. |
| @aleabitoreddit | $XFAB, $SOI | prediction | True | medium-term | The cyclical slump will occur in 2025. |
| @aleabitoreddit | $XFAB, $NVDA, $NVTS, $ON, $POWI, $GFS, $NOK, $INTC, $SOI | opinion | True | long-term | The company will benefit from the $NVDA push for GaN/SiC players. |
| @kawzinvests | $IBM | other | False | none | none |
| @kawzinvests | $NVDA, $NBIS, $ORCL, $CRWV, $DELL, $HPE, $SMCI, $SNX | news | False | none | NVIDIA Vera CPU partner list has been announced. |
| @kawzinvests | $NVDA, $TSM, $LITE, $COHR | news | False | none | NVIDIA Vera Rubin is ramping into full production. |
| @kawzinvests | $NVDA | news | False | none | Vera Rubin is in full production. |
| @venu_7_ | $MRVL, $FPS | other | False | none | none |
| @venu_7_ | $ARM | opinion | True | long-term | The conviction in $ARM is built when technicals, fundamentals, and themes align. |
| @amitisinvesting | $META | prediction | True | long-term | META is a screaming buy and will eventually be $1000. |
| @aleabitoreddit | $NVDA | prediction | True | short-term | The next AI bottleneck will be announced at the NVIDIA GTC/Computex in Taipei. |
| @aleabitoreddit | $AAOI | opinion | True | medium-term | The premiums on space sector or quantum will disappear if $AAOI hits $5.7B ARR. |
| @aleabitoreddit | $MSFT, $AAOI, $SNDK | opinion | False | none | Hypergrowth names require calculating their own forward P/E ratios. |
| @aleabitoreddit | $AAOI, $AMZN, $MSFT, $NVDA, $AMD | opinion | False | none | AAOI is the favorite photonics exposure in the US market. |
| @aleabitoreddit | $ARM, $NVDA | prediction | True | long-term | ARM will dominate AI ASIC servers. |
| @venu_7_ | $FSLR | opinion | True | long-term | FSLR is a beneficiary of America's push for energy independence and AI-driven power demand. |
| @spacanpanman | $BBC | other | False | none | none |

## Run summary

- Groq calls attempted: **22** (daily budget guard: 100)
- Groq calls succeeded: **0**
- Groq calls rate-limited (429): **22**
- Stage 1–2 are deterministic and always complete (no LLM).

_Read-only run. No database writes, no schema changes. Descriptive analysis only — not investment advice._
