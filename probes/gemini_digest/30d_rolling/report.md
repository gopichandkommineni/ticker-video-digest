# Gemini 30-Day Probe Report

**DESCRIPTIVE ANALYSIS ONLY — not investment advice.** This report
measures what handles are *posting*: volume, ticker frequency, and
sector concentration. It contains no buy signals, no ranking of tickers
by attractiveness, and no recommendations. The reader draws their own
conclusions from the concentration data.

- Database: `fintwit.db` · table `raw_tweets` (read-only)
- Window: last 30 days
- Model: `gemini-2.5-flash` (Stages 3 & 4 only)

## Stage 1 — Volume (free, no LLM)

| Metric | Count |
|---|---:|
| Total non-deleted tweets (last 30d) | 2971 |
| Ticker-bearing tweets (cashtag regex) | 741 |
| Ratio | 24.9% |

## Stage 2 — Per-handle ticker profile (free, no LLM)

Deterministic counts. Handles sorted by ticker-bearing tweet volume.

- **@aleabitoreddit** — 444 tweets, 279 ticker-bearing; $SIVE (95), $NVDA (61), $AAOI (38), $LITE (36), $MRVL (25), $NBIS (24), $JBL (24), $XFAB (24), $SOI (21), $GFS (18), $MU (14), $AMD (13), $IREN (13), $IQE (13), $TSM (13), $POET (12), $GOOGL (12), $AXTI (11), $TSEM (11), $SNDK (11), $RDDT (11), $COHR (11), $INTC (11), $SPCX (10), $EWY (9), $LPK (9), $NOK (8), $AVGO (8), $AMZN (6), $RKLB (6), $META (6), $MTSI (6), $HOOD (6), $ARM (6), $POWI (5), $RPI (5), $WOLF (5), $MSFT (5), $TSLA (4), $ALAB (4), $AEHR (4), $NVTS (4), $CRWV (4), $AOSL (3), $ALRIB (3), $ON (3), $CIFR (3), $BKKT (3), $ASTS (2), $CBRS (2), $AEVA (2), $WEN (2), $BABA (2), $AAPL (2), $ASML (2), $WYFI (2), $WULF (2), $ASX (2), $VICR (2), $IBIT (2), $CRCL (2), $VPG (2), $SLNH (2), $COIN (2), $GM (1), $EOS (1), $QQQ (1), $DRAM (1), $MXL (1), $KOSPI (1), $SPY (1), $TOWA (1), $CAMT (1), $ACMR (1), $VRT (1), $HUT (1), $HIMX (1), $NFLX (1), $LRCX (1), $KLAC (1), $FN (1), $CLS (1), $AMKR (1), $YSS (1), $INHD (1), $XLU (1), $IFNNY (1), $LFUS (1), $VSH (1), $ENPH (1), $BDC (1), $EOSE (1), $SEDG (1), $CWR (1), $AMSC (1), $HYLN (1), $FCEL (1), $ASYS (1), $RELL (1), $PAY (1), $IPWR (1), $SNAP (1), $AMAT (1), $SHMD (1), $PL (1), $ETHA (1), $QCOM (1), $BRK (1), $HPS (1), $FLNC (1), $ASPI (1)
- **@spacanpanman** — 666 tweets, 180 ticker-bearing; $ASTS (79), $TE (34), $SPCX (14), $SHAZ (13), $RKLB (9), $BAER (8), $MRLN (8), $BCAR (7), $PL (6), $SPKL (5), $SPKLW (3), $ECON (3), $BRUN (2), $SRTA (2), $T (2), $WLAC (2), $BCARW (2), $TMUS (1), $KRKNF (1), $PNG (1), $CEPT (1), $SECZ (1), $SPACE (1), $AUR (1), $NXT (1), $CSIQ (1), $HAWK (1), $LIFE (1), $NBIS (1), $IREN (1), $BBC (1), $NPA (1)
- **@venu_7_** — 765 tweets, 139 ticker-bearing; $MU (18), $MRVL (17), $FPS (10), $SNOW (8), $STM (8), $CRDO (7), $NBIS (7), $FROG (7), $FSLR (7), $APH (6), $VSH (6), $BAND (6), $ALAB (5), $MCHP (5), $ICHR (5), $AMBQ (5), $QQQ (5), $DDOG (5), $FIVN (5), $LRCX (4), $ALGM (4), $RKLB (4), $TWLO (4), $NVDA (4), $TSLA (4), $INOD (4), $ARM (4), $TVTX (3), $TGTX (3), $GH (3), $XBI (3), $TXN (3), $ADI (3), $MPWR (3), $ON (3), $NVTS (3), $POWI (3), $WOLF (3), $IFNNY (3), $VICR (3), $AEIS (3), $DIOD (3), $AOSL (3), $AIXA (3), $ENTG (3), $RNECF (3), $ROHCY (3), $AMAT (3), $SNDK (3), $ACMR (3), $MDB (3), $VIAV (3), $ONDS (3), $LQDA (2), $AMD (2), $PLTR (2), $ALKS (2), $TWST (2), $RVMD (2), $RDDT (2), $HNGE (2), $LLY (2), $TTMI (2), $UCTT (2), $UMC (2), $SEZL (2), $CAVA (2), $GLD (2), $UNH (2), $OSCR (2), $FTNT (2), $DOCN (2), $AKAM (2), $JBHT (2), $PANW (2), $ORCL (2), $MP (2), $ABCL (1), $JAZZ (1), $ARGX (1), $HUT (1), $CRS (1), $ASTH (1), $MIRM (1), $DY (1), $TER (1), $HOOD (1), $NKE (1), $NVO (1), $PYPL (1), $FLNC (1), $LPG (1), $RSI (1), $VVX (1), $VCYT (1), $KRYS (1), $ARW (1), $COCO (1), $NBIX (1), $LINC (1), $INCY (1), $DAVE (1), $VIRT (1), $EVR (1), $CUBI (1), $ATLC (1), $TKO (1), $TTD (1), $KLAC (1), $ASML (1), $STX (1), $INTC (1), $DELL (1), $WDC (1), $VSXY (1), $TEV (1), $CEVA (1), $VIX (1), $SPY (1), $SLV (1), $MSTR (1), $CVS (1), $AMKR (1), $SN (1), $KEYS (1), $KEEL (1), $MRK (1), $JNJ (1), $ENPH (1), $SEDG (1), $NXT (1), $KLIC (1), $IONQ (1), $QNT (1), $NAVN (1), $CRWD (1), $RBRK (1), $NET (1), $LOGI (1), $APP (1), $GRAB (1), $HBM (1), $ETN (1), $UAMY (1), $USAR (1), $REMX (1), $MUU (1), $AMR (1), $AVGO (1), $AEVA (1)
- **@amitisinvesting** — 240 tweets, 45 ticker-bearing; $NVDA (17), $SPCX (17), $MSFT (13), $MU (12), $AAPL (12), $AMZN (12), $META (12), $GOOGL (11), $PLTR (11), $TSLA (11), $HOOD (8), $INTC (6), $AMD (6), $MRVL (6), $QQQ (5), $ORCL (5), $NOK (5), $NFLX (4), $RDDT (3), $SPY (3), $ZETA (3), $F (3), $AVGO (3), $CRWD (3), $SHOP (3), $GME (2), $CBRS (2), $QCOM (2), $SOFI (2), $SPX (2), $CRWV (2), $SNDK (2), $BTC (2), $PANW (2), $NOW (2), $WEN (1), $VZ (1), $SMH (1), $ASTS (1), $EBAY (1), $INFQ (1), $QBTS (1), $IBM (1), $RGTI (1), $IONQ (1), $QNT (1), $CVX (1), $DRAM (1), $SPCH (1), $IBIT (1), $SNAP (1), $NBIS (1), $RKLB (1), $TER (1), $ALAB (1), $SMCI (1), $SOXS (1), $QLD (1), $SSO (1), $GLW (1), $IREN (1), $MSTR (1), $UBER (1), $CRM (1), $IGV (1), $DDOG (1), $SNOW (1)
- **@kaizen_investor** — 165 tweets, 35 ticker-bearing; $PL (19), $WOLF (5), $RKLB (5), $MRVL (4), $SIVE (3), $ASTS (3), $SPCX (2), $ASML (2), $ASM (2), $GOOGL (2), $OUST (2), $PLTR (2), $FLNC (2), $MU (1), $SAP (1), $NASA (1), $SPIR (1), $BKSY (1), $ENHA (1), $AMZN (1), $SATL (1), $FLY (1), $LUNR (1), $POET (1), $NVDA (1), $TMDX (1), $AMPX (1), $IREN (1), $HIMS (1)
- **@michaelsikand** — 180 tweets, 29 ticker-bearing; $NOK (5), $AAOI (4), $BRUN (4), $MRVL (3), $KRKNF (3), $NBIS (3), $SPCX (2), $SATS (2), $LITE (2), $SKM (2), $ZM (2), $SIVE (2), $PENG (2), $LASR (2), $NVDA (2), $WEN (1), $RDDT (1), $NYT (1), $COHR (1), $RKLB (1), $ASTS (1), $STCK (1), $CRM (1), $COKE (1), $DELL (1), $RCAT (1), $AVAV (1), $KTOS (1), $AVEX (1), $EOS (1), $CIEN (1), $SGOV (1), $MXL (1), $HOOD (1), $DRAM (1), $GLXY (1), $CRWV (1), $IREN (1), $BE (1), $CRCL (1), $MU (1)
- **@kawzinvests** — 76 tweets, 27 ticker-bearing; $NVDA (10), $AAOI (5), $SKM (5), $LITE (4), $COHR (4), $CIEN (3), $BRUN (3), $CRWV (3), $FN (2), $CSCO (2), $STM (2), $DELL (2), $NBIS (2), $NOK (1), $KXIAY (1), $MU (1), $SNDK (1), $MRVL (1), $RDDT (1), $ZM (1), $PENG (1), $CRDO (1), $SMTC (1), $MTSI (1), $VRT (1), $PWR (1), $IFX (1), $MPWR (1), $VICR (1), $NVTS (1), $ON (1), $TXN (1), $ADI (1), $POWI (1), $DIOD (1), $WOLF (1), $AOSL (1), $APLD (1), $IBM (1), $ORCL (1), $HPE (1), $SMCI (1), $SNX (1), $TSM (1)
- **@speculator_io** — 9 tweets, 6 ticker-bearing; $SNDK (4), $DELL (4), $NBIS (4), $MU (3), $STX (3), $WDC (3), $DOCN (3), $BE (3), $HUT (3), $IREN (3), $RXT (2), $HYLN (2), $VPG (2), $AMBQ (2), $INTC (2), $FLEX (2), $GEV (2), $AMPX (2), $VICR (2), $NVTS (2), $AMD (2), $ARM (2), $MRVL (2), $AAOI (2), $AXTI (2), $OPTX (2), $ICHR (2), $AEHR (2), $CRWV (2), $APLD (2), $VRT (2), $HPE (2), $ORCL (2), $STM (1), $MCHP (1), $IFX (1), $ON (1), $WOLF (1), $STRL (1), $SILC (1), $HIMX (1), $PWR (1), $VST (1), $BWXT (1), $CEG (1), $UEC (1), $CCJ (1), $NVDA (1), $TSM (1), $AVGO (1), $ASML (1), $COHR (1), $LITE (1), $GOOGL (1), $META (1), $AMZN (1), $TSLA (1), $NOW (1), $PLTR (1), $SNOW (1), $NET (1), $FSLY (1), $INOD (1), $IBM (1), $CDNS (1), $J (1), $PCOR (1), $PTC (1), $SIE (1), $SU (1), $DSY (1), $TT (1), $ABBN (1), $CAT (1), $ETN (1), $ENGI (1), $DLR (1), $EQIX (1), $SIFY (1), $SMCI (1), $DGXX (1), $HIVE (1), $WYFI (1), $BTDR (1), $RIOT (1), $CLSK (1), $CORZ (1), $CIFR (1), $CIEN (1), $ASX (1), $ENLT (1), $NOK (1), $GLW (1), $RKLB (1), $ALAB (1), $MXL (1), $VSH (1), $VIAV (1), $PL (1), $SEDG (1), $BLDP (1), $SATL (1), $MX (1), $SPIR (1), $CPSH (1), $FEL (1), $PURR (1), $PENG (1), $MRAM (1), $BKSY (1), $OSS (1), $UMAC (1), $USAR (1)
- **@zephyr_z9** — 426 tweets, 1 ticker-bearing; $TTM (1)

## Stage 3 — Sector grouping (LLM, probe-only)

> ⚠️ **Probe-only.** Sectors below are assigned by a single Gemini call
> and the model can miscategorize. In production this would be replaced
> by a deterministic ticker→sector map.

Unique tickers across all handles: **355**


### Overall sector concentration (by total mentions)

| Sector | Mentions | Tickers |
|---|---:|---|
| semiconductors | 657 | $ACMR, $ADI, $AEHR, $AEIS, $AIXA, $ALAB, $ALGM, $AMAT, $AMBQ, $AMD, $AMKR, $AOSL, $ARM, $ASM, $ASML, $ASX, $ASYS, $AVGO, $AXTI, $CAMT, $CEVA, $CRDO, $DIOD, $ENTG, $GFS, $HIMX, $ICHR, $IFNNY, $IFX, $INTC, $IQE, $KLAC, $KLIC, $LFUS, $LRCX, $MCHP, $MPWR, $MRVL, $MTSI, $MX, $MXL, $NAVN, $NVDA, $NVTS, $ON, $POWI, $QCOM, $RNECF, $ROHCY, $SIVE, $SMTC, $SOI, $STM, $TER, $TOWA, $TSEM, $TSM, $TXN, $UCTT, $UMC, $VICR, $VSH, $WOLF, $XFAB |
| other | 496 | $AAPL, $ABBN, $ALRIB, $AMPX, $AMR, $AMSC, $APH, $ARW, $ATLC, $AVAV, $AVEX, $BAER, $BBC, $BDC, $BE, $BKKT, $BLDP, $BRK, $BRUN, $BTC, $BTDR, $BWXT, $CAT, $CAVA, $CBRS, $CCJ, $CEG, $CIFR, $CLS, $CLSK, $COCO, $COIN, $COKE, $CORZ, $CPSH, $CRCL, $CRS, $CRWV, $CSIQ, $CUBI, $CVS, $CVX, $DAVE, $DELL, $DGXX, $DRAM, $ECON, $ENGI, $ENHA, $ENLT, $ENPH, $EOS, $EOSE, $ETHA, $ETN, $EVR, $FCEL, $FEL, $FLEX, $FLNC, $FLY, $FPS, $FSLR, $GEV, $GLXY, $GME, $HAWK, $HBM, $HIMS, $HIVE, $HNGE, $HOOD, $HPS, $HUT, $INFQ, $IONQ, $IPWR, $IREN, $J, $JBHT, $JBL, $JNJ, $KEEL, $KEYS, $KOSPI, $KRKNF, $KTOS, $LINC, $LLY, $LOGI, $LPG, $LPK, $MP, $MRK, $MRLN, $MUU, $NASA, $NBIS, $NKE, $NPA, $NVO, $NXT, $NYT, $OPTX, $OSCR, $PAY, $PENG, $PNG, $PURR, $PWR, $PYPL, $QNT, $RCAT, $RELL, $RGTI, $RIOT, $RPI, $RSI, $SECZ, $SEDG, $SEZL, $SHAZ, $SHMD, $SIE, $SIFY, $SLNH, $SN, $SNDK, $SNX, $SOFI, $SPACE, $SPCH, $SPKL, $SPKLW, $SPX, $SRTA, $STCK, $STRL, $STX, $SU, $TE, $TEV, $TKO, $TMDX, $TT, $TTMI, $UAMY, $UEC, $UMAC, $UNH, $USAR, $VIRT, $VIX, $VPG, $VST, $VSXY, $VVX, $WDC, $WEN, $WLAC, $WULF, $WYFI, $YSS |
| space | 147 | $ASTS, $BKSY, $LUNR, $PL, $RKLB, $SATL, $SPIR |
| optical/photonics | 133 | $AAOI, $COHR, $FN, $GLW, $LASR, $LITE, $POET, $VIAV |
| software | 117 | $APP, $ASPI, $CDNS, $CRM, $CRWD, $DDOG, $DOCN, $DSY, $FIVN, $FROG, $FTNT, $MDB, $MSFT, $MSTR, $NOW, $ORCL, $PANW, $PCOR, $PLTR, $PTC, $RBRK, $RXT, $SAP, $SNOW, $TWLO, $ZETA, $ZM |
| internet | 104 | $AKAM, $AMZN, $BABA, $EBAY, $FSLY, $GOOGL, $GRAB, $META, $NET, $NFLX, $RDDT, $SHOP, $SNAP, $TTD, $UBER |
| etf | 87 | $EWY, $GLD, $IBIT, $IGV, $QLD, $QQQ, $REMX, $SGOV, $SLV, $SMH, $SOXS, $SPCX, $SPY, $SSO, $XBI, $XLU |
| memory | 52 | $KXIAY, $MRAM, $MU |
| telecom | 51 | $BAND, $CIEN, $CSCO, $DY, $NOK, $ONDS, $SATS, $SILC, $SKM, $T, $TMUS, $VZ |
| biotech | 39 | $ABCL, $ALKS, $ARGX, $ASTH, $BCAR, $BCARW, $CWR, $GH, $INCY, $INHD, $JAZZ, $KRYS, $LIFE, $LQDA, $MIRM, $NBIX, $QBTS, $RVMD, $TGTX, $TVTX, $TWST, $VCYT |
| automotive | 35 | $AEVA, $AUR, $CEPT, $F, $GM, $HYLN, $OUST, $TSLA, $TTM |
| ai infrastructure | 24 | $APLD, $DLR, $EQIX, $HPE, $IBM, $INOD, $OSS, $SMCI, $VRT |

### Per-handle sector concentration (by mentions)

- **@aleabitoreddit** — semiconductors (384), other (143), optical/photonics (98), internet (39), etf (24), memory (14), space (9), automotive (8), telecom (8), software (6), biotech (2), ai infrastructure (1)
- **@spacanpanman** — space (94), other (91), etf (14), biotech (10), telecom (3), automotive (2)
- **@venu_7_** — semiconductors (143), other (94), software (46), biotech (26), memory (18), etf (13), telecom (10), internet (7), automotive (5), space (4), ai infrastructure (4), optical/photonics (3)
- **@amitisinvesting** — internet (48), other (44), software (43), semiconductors (42), etf (31), automotive (14), memory (12), telecom (6), space (2), ai infrastructure (2), biotech (1), optical/photonics (1)
- **@kaizen_investor** — space (31), semiconductors (17), other (9), software (3), internet (3), etf (2), automotive (2), memory (1), optical/photonics (1)
- **@michaelsikand** — other (29), telecom (10), optical/photonics (9), semiconductors (8), etf (3), software (3), space (2), internet (1), memory (1)
- **@kawzinvests** — semiconductors (28), optical/photonics (15), other (14), telecom (11), ai infrastructure (5), memory (2), software (2), internet (1)
- **@speculator_io** — other (72), semiconductors (35), software (14), ai infrastructure (12), optical/photonics (6), internet (5), space (5), memory (4), automotive (3), telecom (3)
- **@zephyr_z9** — automotive (1)

## Stage 4 — Thesis extraction (LLM, ticker-bearing only)

Descriptive structure per tweet: thesis, whether the claim is
falsifiable, its horizon and a checkpoint, and the stance. No judgement
of whether the claim is *good*.

Tweets are batched **50 per Gemini call** so the full month
fits within the free-tier daily request cap (one per-tweet call would not).

_Ledger (`thesis.jsonl`): 100 tweet(s) already extracted; **641** remaining this run._

_Batch 1 rate-limited (HTTP 429): { "error": { "code": 429, "message": "You exceeded your current quota, please check your plan and billing details. For m_
_Batch 2 rate-limited (HTTP 429): { "error": { "code": 429, "message": "You exceeded your current quota, please check your plan and billing details. For m_
_Batch 3 rate-limited (HTTP 429): { "error": { "code": 429, "message": "You exceeded your current quota, please check your plan and billing details. For m_
_Batch 4 rate-limited (HTTP 429): { "error": { "code": 429, "message": "You exceeded your current quota, please check your plan and billing details. For m_
_Batch 5 rate-limited (HTTP 429): { "error": { "code": 429, "message": "You exceeded your current quota, please check your plan and billing details. For m_
_Batch 6 rate-limited (HTTP 429): { "error": { "code": 429, "message": "You exceeded your current quota, please check your plan and billing details. For m_
_Batch 7 rate-limited (HTTP 429): { "error": { "code": 429, "message": "You exceeded your current quota, please check your plan and billing details. For m_
_Batch 8 rate-limited (HTTP 429): { "error": { "code": 429, "message": "You exceeded your current quota, please check your plan and billing details. For m_
_Batch 9 rate-limited (HTTP 429): { "error": { "code": 429, "message": "You exceeded your current quota, please check your plan and billing details. For m_
_Batch 10 rate-limited (HTTP 429): { "error": { "code": 429, "message": "You exceeded your current quota, please check your plan and billing details. For m_
_Batch 11 rate-limited (HTTP 429): { "error": { "code": 429, "message": "You exceeded your current quota, please check your plan and billing details. For m_
_Batch 12 rate-limited (HTTP 429): { "error": { "code": 429, "message": "You exceeded your current quota, please check your plan and billing details. For m_
_Batch 13 rate-limited (HTTP 429): { "error": { "code": 429, "message": "You exceeded your current quota, please check your plan and billing details. For m_
_Retrying 13 failed batch(es) (transient timeout/5xx); 5 calls of daily budget remain._

_Batch 1 rate-limited (HTTP 429): { "error": { "code": 429, "message": "You exceeded your current quota, please check your plan and billing details. For m_
_Batch 2 rate-limited (HTTP 429): { "error": { "code": 429, "message": "You exceeded your current quota, please check your plan and billing details. For m_
_Batch 3 rate-limited (HTTP 429): { "error": { "code": 429, "message": "You exceeded your current quota, please check your plan and billing details. For m_
_Batch 4 rate-limited (HTTP 429): { "error": { "code": 429, "message": "You exceeded your current quota, please check your plan and billing details. For m_
_Batch 5 rate-limited (HTTP 429): { "error": { "code": 429, "message": "You exceeded your current quota, please check your plan and billing details. For m_
_Note: 13 batch(es) (~641 tweets) not recovered this run (transient errors / budget); the ledger lets a later run pick them up._


Thesis ledger now holds **100** of 741 ticker-bearing tweets (**+0** this run).

Stance distribution: opinion (45), news (29), prediction (12), other (9), promotion (3), question (2)

| Handle | Tickers | Stance | Falsifiable | Horizon | Thesis |
|---|---|---|---|---|---|
| @venu_7_ | $HOOD | prediction | True | medium-term | Robinhood ($HOOD) is showing strong positive signals, including decoupling from Bitcoin, reclaiming its 200-day SMA, and significant institutional accumulation, suggesting a positive future performance. |
| @amitisinvesting | $WEN | news | False | none | Wendy's stock ($WEN) is up 20% overnight due to a viral campaign on r/WallStreetBets, which is motivated by a desire to prevent the company's bankruptcy. |
| @venu_7_ | $TGTX, $TVTX, $ALKS, $TWST, $RVMD, $LQDA, $XBI | opinion | True | medium-term | Specific biotech stocks ($TGTX, $TVTX, $ALKS, $TWST, $RVMD, $LQDA) and the $XBI ETF look promising. |
| @aleabitoreddit | $RDDT, $WEN | news | False | none | It is interesting that Reddit users are campaigning to save Wendy's ($WEN), leading to a 20% overnight stock price increase, and Wendy's has a meme status related to financial losses. |
| @venu_7_ | $MU, $NKE, $NVO, $PYPL | opinion | True | medium-term | Micron ($MU) is a significant beneficiary of the HBM and AI memory cycle, with dramatically increasing earnings power, and is not just a speculative stock, although a pullback is possible. |
| @spacanpanman | $BAER | opinion | False | none | The user appreciates educational videos related to $BAER. |
| @amitisinvesting | $SPY, $SPCX, $MU, $GOOGL, $VZ, $AMZN, $AAPL, $MSFT, $NVDA, $META, $SMH, $PLTR, $ZETA, $ASTS, $GME, $EBAY, $CBRS | news | False | none | Markets were under pressure today, with the S&P 500 ($SPY) down ~1.5%, primarily due to a 9.9% selloff in South Korea's KOSPI, driven by fears of potential taxes on unrealized stock gains. |
| @amitisinvesting | $MU | question | False | none | none |
| @venu_7_ | $GH | opinion | True | medium-term | $GH, despite being tricky to trade, showed positive price action by finding support at its 200-day SMA during a pullback, which is characteristic of a market leader. |
| @aleabitoreddit | $KOSPI, $EWY | opinion | False | none | Bank of America's negative calls on $KOSPI/$EWY proved incorrect, as the index doubled and hit all-time highs after their "extreme bubble" warning, suggesting their analysis is detrimental to retail investors. |
| @aleabitoreddit | $SIVE, $AAPL | opinion | True | short-term to medium-term | A recent PR regarding $SIVE and $AAPL is probably a defensive move to counter short seller claims about a terminated relationship, rather than indicating a new market entry, as they likely have a long-standing collaboration. |
| @spacanpanman | $BAER | prediction | True | short-term | $BAER is fully deployed in anticipation of what is predicted to be the busiest firefighting summer ever. |
| @aleabitoreddit | $LITE, $COHR | opinion | False | none | The user does not understand why people invest in certain ETFs because they contain easily purchasable, heavily weighted stocks like $LITE and $COHR, incur management fees, and include names not directly related to AI data centers. |
| @aleabitoreddit | $LITE, $NVDA, $AMD, $AAOI, $SIVE, $SOI, $TSEM | opinion | True | medium-term | The photonics theme and CW laser chokepoint are highly valuable, as markets seem to be forgetting the massive growth of $LITE due to EML bottlenecks caused by $NVDA, and a similar situation is now occurring with CW lasers. |
| @aleabitoreddit | $ALAB, $MRVL | news | False | none | The optimal time to invest in CXL for memory pooling was four months ago, as evidenced by the significant gains in $ALAB and $MRVL since then. |
| @amitisinvesting | $SPCX, $NVDA, $PLTR, $TSLA, $AMZN, $AAPL, $GOOGL, $MSFT, $NFLX, $INTC, $QCOM, $INFQ, $QBTS, $IBM, $RGTI, $IONQ, $QNT, $MU, $CVX | news | True | short-term | A significant end-of-Q2 rebalancing wave is anticipated, with JPMorgan estimating institutional investors could sell up to $165B in equities and buy an equal amount of bonds by quarter-end, representing the largest rebalance in history. |
| @aleabitoreddit | $TSM | opinion | False | none | The user's M&A ideas are compelling, as Apollo recently acquired one of the Japanese $TSM suppliers that the user had previously identified. |
| @aleabitoreddit | $IREN, $NBIS | opinion | False | none | The user's decision to sell $IREN due to dilution and a GPU pivot, and instead invest in $NBIS, was correct, as evidenced by the subsequent performance. |
| @aleabitoreddit | $IREN, $NBIS | news | False | none | $IREN's performance was poor last year, while $NBIS compounded 3-4x despite negative sentiment. |
| @aleabitoreddit | $NBIS, $IREN | opinion | False | none | Investors who held $IREN, which has experienced significant dilution, likely missed out on the AI supercycle gains seen in sectors like photonics, memory, and stocks like $NBIS. |
| @kawzinvests | $MRVL | news | False | none | $MRVL has officially been added to the S&P 500 index today. |
| @spacanpanman | $SHAZ | news | True | short-term | Sharon AI ($SHAZ) is initiating the process to list shares on the Australian Stock Exchange in the second half of July, with an expected IPO size of $200M or more, led by Macquarie and Canaccord. |
| @kaizen_investor | $SAP | opinion | False | none | $SAP is a best-in-class ERP system for data storage but is clumsy to use, and its AI layer is underdeveloped, leading many companies to build their own AI solutions on top of SAP data. |
| @michaelsikand | $MRVL | promotion | True | medium-term | Jensen (likely Jensen Huang of NVIDIA) has stated that $MRVL could quadruple from its current price, implying that doubting its potential is misguided. |
| @aleabitoreddit | $LPK, $AEHR | opinion | True | long-term | $LPK could reasonably reach a $3B-$5B valuation upon full volume ramp due to its customer base for glass substrates, presenting an asymmetrical opportunity, though small machine suppliers typically have TAM limitations. |
| @venu_7_ | $RDDT | prediction | True | long-term | $RDDT is projected to experience massive revenue growth (nearly 20x to $5.3B) and a significant EPS inflection (from -$1.23 to $8.28) within a decade. |
| @venu_7_ | $MCHP | opinion | True | medium-term | Microchip Technology ($MCHP) is a clean name in analog semiconductors, showing a 24-month base with strong accumulation, indicating potential for positive performance. |
| @venu_7_ | $FLNC | opinion | True | short-term to medium-term | Fluence Energy ($FLNC), a provider of battery storage systems, is showing a constructive flag on its daily chart and a solid monthly base, indicating an interesting setup within the power infrastructure theme. |
| @aleabitoreddit | $SIVE | prediction | True | short-term | Japan is expected to defeat Sweden in the World Cup tomorrow, possibly by a score of 4-0, influenced by how Swedish media treated $SIVE. |
| @aleabitoreddit | $NVDA, $TSM | prediction | True | medium-term to long-term | FOCI will remain a bottleneck contributor with FAU and passive components within the $NVDA $TSM ecosystem as COUPE technology scales up. |
| @aleabitoreddit | $SPY | prediction | True | short-term | $SPY is expected to be green tomorrow because the US won 2-0 (presumably in a sports event). |
| @venu_7_ | $HNGE | opinion | True | long-term | $HNGE is a rare recent IPO with strong fundamentals (40%+ revenue growth, AI software, healthcare-like margins) and positive technicals, with expanding access validating its product and long-term growth story. |
| @venu_7_ | $MU, $NBIS, $MRVL, $FPS | opinion | False | none | The user believes that investing in a single power semiconductor stock can justify exposure to that theme, and mentions holding other stocks like $MU, $NBIS, $MRVL, and $FPS, which constitute 50% of their portfolio, following specific allocation rules. |
| @venu_7_ | $TXN, $ADI, $MCHP, $APH, $MPWR, $ON, $STM, $NVTS, $POWI, $WOLF, $IFNNY, $VICR, $AEIS, $VSH, $ALGM, $DIOD, $AOSL, $AIXA, $ENTG, $ICHR, $AMBQ, $RNECF, $ROHCY | opinion | False | none | Investors should own the entire supply chain rather than individual components, and a diversified portfolio across various semiconductor sub-sectors (broad analog, WBG, modules, discrete, picks & shovels, international IDMs) is recommended. |
| @venu_7_ | $RNECF, $ROHCY | news | False | none | $RNECF and $ROHCY are international IDMs with significant AI-DC content, with $RNECF having acquired Transphorm GaN and being on NVIDIA's 800V list, and $ROHCY's MOSFET being endorsed by NVIDIA for AI servers. |
| @venu_7_ | $AIXA, $ENTG, $ICHR, $AMBQ | news | False | none | Companies like $AIXA and $ENTG represent "picks and shovels" in the equipment, materials, and edge AI sector, offering lower beta and structural exposure to the growing supply chain, with $AIXA specializing in MOCVD reactors and $ENTG in advanced materials. |
| @venu_7_ | $VSH, $ALGM, $DIOD, $AOSL | news | False | none | Companies like $VSH and $ALGM in the discrete, sensing, and passives sector are benefiting from a broad cycle recovery, offering lower beta and ubiquitous presence in bills of materials without binary WBG technology risk. |
| @venu_7_ | $VICR, $AEIS | news | False | none | Companies like $VICR and $AEIS in power modules and system-level conversion act as a bridge between WBG silicon and the rack, directly benefiting from 800V HVDC, with $VICR offering a unique power architecture and $AEIS providing high-power solutions. |
| @venu_7_ | $ON, $STM, $NVTS, $POWI, $WOLF, $IFNNY | news | False | none | Wide-bandgap device makers like $ON and $STM are at the technology core with SiC and GaN switches, experiencing high structural growth and pricing-cycle volatility, with $ON being a top SiC supplier and collaborating with NVIDIA, and $STM being a major auto SiC volume producer. |
| @venu_7_ | $TXN, $ADI, $APH, $MCHP, $MPWR, $MRVL, $FPS | news | False | none | Companies like $TXN and $ADI in broad analog and power management are high-quality names with less binary risk, deeper backlogs, and an accelerating AI-DC mix, positioning them well for a cycle inflection, with $TXN being an NVIDIA 800V partner and $ADI providing high-performance power solutions. |
| @venu_7_ | $TXN, $ADI, $MCHP, $APH, $MPWR, $ON, $STM, $NVTS, $POWI, $WOLF, $IFNNY, $VICR, $AEIS, $VSH, $ALGM, $DIOD, $AOSL, $AIXA, $ENTG, $ICHR, $AMBQ, $RNECF, $ROHCY | other | False | none | This tweet presents a list of the top 25 power semiconductor companies, categorized by sub-sector, including broad analog/power management, WBG devices, power modules/conversion, and discrete/sensing/passives. |
| @venu_7_ | $GH | opinion | True | short-term | $GH is currently in a massive Stage 2 uptrend. |
| @venu_7_ | $XBI, $TGTX, $TVTX, $ALKS, $TWST, $RVMD | opinion | True | medium-term | The $XBI Biotech ETF is in a massive Stage 2 uptrend with institutional accumulation, and the biotech sector, after years of underperformance, is beginning to look constructive. |
| @venu_7_ | $STM | opinion | True | medium-term | STMicroelectronics ($STM) is a leading semiconductor company with a 26-year massive base breakout and strong institutional accumulation, making it one of the most attractive semiconductor stocks currently. |
| @aleabitoreddit | $LITE, $SIVE | opinion | True | medium-term | While not providing a specific price target, the user notes that $SIVE is currently at a similar starting point as $LITE was before its significant market cap increase from $2.88B to $67B in two years, implying similar potential for $SIVE. |
| @aleabitoreddit | $JBL, $SIVE, $NVDA | opinion | True | short-term to medium-term | The collaboration between $JBL and $SIVE was known informally before an official PR, and a more confident mapping to the $NVDA CPO ecosystem would likely lead to a significant rerating of the stock. |
| @aleabitoreddit | $POET, $GFS | other | False | none | The user is describing a process of synthesizing information from various sources, including JP Morgan conferences, Sivers' annual reports, and old investor decks, to form a comprehensive understanding of market dynamics. |
| @aleabitoreddit | $SIVE, $JBL, $POET, $MRVL, $GFS | news | False | none | It is a misconception that $SIVE is only for CPO scale-up; it is a laser supplier for various next-gen architectures, and Sivers and $JBL have developed 1.6T optical transceivers with CW lasers, bypassing EML bottlenecks. |
| @aleabitoreddit | $COHR, $LITE, $NVDA, $AMD | news | False | none | The industry is experiencing a significant EML bottleneck, and now CW lasers are also facing bottlenecks, leading to companies like $COHR buying EMLs from $LITE, and $LITE, being focused on EMLs, is buying CW lasers from competitors. |
| @aleabitoreddit | $SNDK | opinion | True | medium-term | Nittobo (3110) is a frustrating Japanese company with a near-monopoly in glass fiber cloth that refuses to significantly raise T-Glass ASP, despite having the potential to triple its valuation if it adopted more aggressive pricing strategies. |
| @spacanpanman | $RKLB | news | True | medium-term | KeyBanc upgraded Rocket Lab to Overweight with a $135 price target, seeing compelling opportunities in the space sector after the SpaceX IPO related selloff. |
| @aleabitoreddit | $SIVE | other | False | none | none |
| @aleabitoreddit | $IQE | other | False | none | none |
| @aleabitoreddit | $IQE, $TSEM, $MTSI | news | False | none | IQE and Tower Semi have signed a multi-year InP epiwafer deal, reinforcing IQE's critical importance to Western optical supply chains. |
| @aleabitoreddit | $WOLF | opinion | True | medium-term | WOLF is a core part of American supply chains, and with more market support and subsidies, its stock might perform well despite current financial toxicity. |
| @aleabitoreddit | $SIVE, $LITE | opinion | True | short-term | The user is bullish on SIVE due to positive EU macro trends, easing InP bottlenecks benefiting the laser group, and a possible Nasdaq listing timeline announcement today. |
| @aleabitoreddit | $WOLF, $LITE, $SPCX | opinion | True | short-to-medium term | It is foolish to be bearish because Trump is boosting markets before midterms, WOLF and LITE related sectors are expected to perform well due to technological advancements, and the successful SpaceX IPO increases risk appetite. |
| @aleabitoreddit | $POET | opinion | False | none | POET has a large cash reserve of approximately $1B after a $400M private placement, which provides a strategic option for acquisitions even if their core technology doesn't succeed with hyperscalers. |
| @aleabitoreddit | $AXTI, $IQE, $AAOI, $LITE, $SIVE | news | True | short-to-medium term | China has eased InP substrate exports, which is expected to relieve mass production bottlenecks in the photonics market, positively impacting optical positions like AXTI, IQE, AAOI, LITE, and SIVE. |
| @aleabitoreddit | $NVTS, $POWI, $ON, $WOLF, $AOSL, $XFAB | prediction | True | short-term | Companies with power semiconductor exposure, including NVTS, POWI, ON, WOLF, AOSL, and XFAB, will likely see a stock price bump due to a Q3 pull forward. |
| @aleabitoreddit | $NVDA, $GOOGL, $VRT | news | True | medium-to-long term | NVDA and GOOGL are leading 800V DC development ahead of schedule, with small volume shipments starting in Q3 2026, and several companies including Delta Electronics and VRT are flagged as beneficiaries. |
| @amitisinvesting | $SPCX | opinion | True | medium-term | If the premise of the preceding conversation is correct, then SpaceX (SPCX) is currently undervalued. |
| @kaizen_investor | $WOLF | opinion | False | none | WOLF is a stock to consider for investment if one is looking for a company that has not yet experienced significant price appreciation. |
| @michaelsikand | $AAOI, $LITE, $COHR | opinion | False | none | AAOI is a controversial stock that has seen significant price appreciation since the user went long, and the user finds this interesting. |
| @aleabitoreddit | $SPCX, $SIVE, $SOI | opinion | False | none | Different regions exhibit distinct market behaviors and investment preferences, with America being bullish on futuristic companies like SpaceX regardless of valuation, and Europe focusing on specific sectors like water. |
| @aleabitoreddit | $SIVE | opinion | False | none | The mentioned action is for Nasdaq listing liquidity requirements and M&A, which is a positive development for SIVE as the user desires to see it trade on US markets. |
| @aleabitoreddit | $SIVE, $SNDK | opinion | True | long-term | The user likes SIVE and believes it will continue to compound like SNDK if it's important to AI, as they perceive the market to be at the beginning of a new supercycle. |
| @kawzinvests | $LITE, $AAOI, $FN, $CIEN, $CSCO | news | False | none | Analysis of the 800G and 1.6T supply chain indicates significant undersupply relative to demand, as evidenced by LITE's CEO stating they are significantly under-shipping demand. |
| @spacanpanman | $ASTS | prediction | True | short-term | ASTS's Batch-2 satellites (BlueBird 11, 12, 13) are expected to be loaded soon. |
| @kawzinvests | $RDDT | opinion | False | none | Fundamentally, RDDT is a very unique company. |
| @spacanpanman | $ASTS | opinion | False | none | A source claims that ASTS's technology is the most revolutionary they have ever seen. |
| @kaizen_investor | $PL | opinion | True | long-term | The user observes increased interest in PL from other investors and, based on extensive past analysis and observation of its volatile history, still considers it the best space investment. |
| @spacanpanman | $ASTS | opinion | False | none | AST SpaceMobile has an impressive roadmap that has successfully attracted Verizon as a partner over Starlink. |
| @aleabitoreddit | $TSM | prediction | True | short-term | Foosung is expected to be a massive beneficiary soon due to China's export control on Japan, which has disrupted the WF₆ supply chain critical for companies like SK Hynix, Samsung, and TSM. |
| @aleabitoreddit | $AXTI | opinion | True | short-to-medium term | The "AI supremacy Wars" are beginning, and resulting upstream supply chain bottlenecks caused by export controls should create interesting investment opportunities in the near future. |
| @spacanpanman | $ASTS | other | False | none | none |
| @spacanpanman | $ASTS | other | False | none | none |
| @spacanpanman | $ASTS | opinion | False | none | The user is surprised by the magnitude of ASTS's drawdown today, which exceeded the expected pullback, and finds the various theories for the move unconvincing. |
| @amitisinvesting | $SPCX | news | False | none | SpaceX (SPCX) traded 380 million shares in its first three hours, setting a new record for the largest intraday trading volume for an IPO. |
| @spacanpanman | $SHAZ | news | True | short-term | An S-1 registration for $350M convertible notes from Oaktree went effective yesterday, allowing ~11.2M SHAZ shares to be sold, which is likely causing current stock pressure. |
| @spacanpanman | $SPCX, $ASTS | other | False | none | none |
| @amitisinvesting | $SPCX | news | False | none | SpaceX (SPCX) opened up 20%, leading to Elon Musk becoming the world's first trillionaire. |
| @aleabitoreddit | $SPCX | news | False | none | SpaceX (SPCX) is now trading and has a market capitalization exceeding $2.15 trillion. |
| @kaizen_investor | $SPCX, $PL, $ASTS, $RKLB | prediction | True | short-to-medium term | The trading of SpaceX (SPCX) is creating a liquidity vacuum effect on other space stocks, which will be followed by a halo effect, making companies like PL, ASTS, and RKLB buying opportunities at their current levels. |
| @aleabitoreddit | $SIVE | other | False | none | none |
| @spacanpanman | $TE | opinion | False | none | none |
| @spacanpanman | $SHAZ | prediction | True | short-term | The user bought the dip in SHAZ and expects the stock to rebound after the market processes the volatility from the SpaceX IPO. |
| @aleabitoreddit | $SNDK, $SPCX | opinion | False | none | SNDK short sellers have been wiped out as the stock approaches $2000, and the market currently feels like it's waiting for the SpaceX (SPCX) IPO. |
| @spacanpanman | $ASTS | other | False | none | none |
| @spacanpanman | $SPKL | promotion | False | none | none |
| @kaizen_investor | $SPIR, $BKSY | opinion | True | long-term | SPIR focuses on radio frequency and space-based weather data analytics, holding a monopoly in commercial satellite weather data, but the user believes its total addressable market is very limited. |
| @amitisinvesting | $SPCX, $HOOD | opinion | False | none | The user is grateful to Robinhood for providing retail investor access to the SpaceX (SPCX) IPO, which is expected to be the largest in history today. |
| @spacanpanman | $SPCX | question | False | none | none |
| @venu_7_ | $RKLB | prediction | True | short-term | RKLB's stock price will reach $200 or more before the end of the year. |
| @spacanpanman | $SPCX | news | False | none | A small trade for SpaceX (SPCX) was observed in the Europe Tier-2 market at $181.83. |
| @spacanpanman | $SHAZ | opinion | True | medium-to-long term | The collaboration between Nvidia and Sharon AI, where Nvidia provides product credit for a portion of ongoing economics, appears to be an attractive and efficient model for Sharon AI to serve the Australian market. |
| @spacanpanman | $SHAZ | news | False | none | Sharon AI has announced a six-year strategic compute collaboration with Nvidia to deploy a 72MW AI factory with up to 40,000 Grace Blackwell GB300 GPUs in Australia. |
| @kaizen_investor | $PL | news | True | medium-term | Planet Labs' CEO expects commercial revenue to surpass defense and intelligence revenue within a couple of years, a shift from the current 61% D&I revenue share. |
| @spacanpanman | $SPCX | news | False | none | SpaceX (SPCX) IPO is scheduled to begin quoting at 9:50 AM ET and trading at 10 AM ET on NASDAQ. |
| @spacanpanman | $BAER | promotion | False | none | none |

## Run summary

- Gemini calls attempted: **19** (daily free-tier budget: 19)
- Gemini calls succeeded: **1**
- Gemini calls rate-limited (429): **18**
- Stage 1–2 are deterministic and always complete (no LLM).

_Read-only run. No database writes, no schema changes. Descriptive analysis only — not investment advice._
