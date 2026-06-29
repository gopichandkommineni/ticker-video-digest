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
| Total non-deleted tweets (last 30d) | 3012 |
| Ticker-bearing tweets (cashtag regex) | 754 |
| Ratio | 25.0% |

## Stage 2 — Per-handle ticker profile (free, no LLM)

Deterministic counts. Handles sorted by ticker-bearing tweet volume.

- **@aleabitoreddit** — 458 tweets, 287 ticker-bearing; $SIVE (100), $NVDA (62), $AAOI (39), $LITE (37), $MRVL (26), $XFAB (26), $NBIS (24), $JBL (24), $SOI (22), $GFS (18), $MU (14), $IQE (14), $AMD (13), $IREN (13), $TSM (13), $POET (12), $GOOGL (12), $AXTI (12), $TSEM (11), $SNDK (11), $RDDT (11), $COHR (11), $INTC (11), $SPCX (10), $LPK (10), $EWY (9), $NOK (8), $AVGO (8), $AMZN (6), $RKLB (6), $META (6), $MTSI (6), $HOOD (6), $ARM (6), $POWI (5), $RPI (5), $WOLF (5), $MSFT (5), $TSLA (4), $ALAB (4), $AEHR (4), $NVTS (4), $CRWV (4), $AOSL (3), $ALRIB (3), $ON (3), $CIFR (3), $BKKT (3), $ASTS (2), $CBRS (2), $AEVA (2), $WEN (2), $BABA (2), $AAPL (2), $ASML (2), $WYFI (2), $VRT (2), $WULF (2), $ASX (2), $VICR (2), $IBIT (2), $CRCL (2), $VPG (2), $SLNH (2), $SNAP (2), $COIN (2), $GM (1), $EOS (1), $QQQ (1), $DRAM (1), $MXL (1), $KOSPI (1), $SPY (1), $TOWA (1), $CAMT (1), $ACMR (1), $HUT (1), $HIMX (1), $NFLX (1), $LRCX (1), $KLAC (1), $FN (1), $CLS (1), $AMKR (1), $YSS (1), $INHD (1), $XLU (1), $IFNNY (1), $LFUS (1), $VSH (1), $ENPH (1), $BDC (1), $EOSE (1), $SEDG (1), $CWR (1), $AMSC (1), $HYLN (1), $FCEL (1), $ASYS (1), $RELL (1), $PAY (1), $IPWR (1), $AMAT (1), $SHMD (1), $PL (1), $ETHA (1), $QCOM (1), $BRK (1), $HPS (1), $FLNC (1), $ASPI (1), $APH (1), $STM (1)
- **@spacanpanman** — 668 tweets, 180 ticker-bearing; $ASTS (79), $TE (34), $SPCX (14), $SHAZ (13), $RKLB (9), $BAER (8), $MRLN (8), $BCAR (7), $PL (6), $SPKL (5), $SPKLW (3), $ECON (3), $BRUN (2), $SRTA (2), $T (2), $WLAC (2), $BCARW (2), $TMUS (1), $KRKNF (1), $PNG (1), $CEPT (1), $SECZ (1), $SPACE (1), $AUR (1), $NXT (1), $CSIQ (1), $HAWK (1), $LIFE (1), $NBIS (1), $IREN (1), $BBC (1), $NPA (1)
- **@venu_7_** — 769 tweets, 139 ticker-bearing; $MU (18), $MRVL (17), $FPS (10), $SNOW (8), $STM (8), $CRDO (7), $NBIS (7), $FROG (7), $FSLR (7), $APH (6), $VSH (6), $BAND (6), $ALAB (5), $MCHP (5), $ICHR (5), $AMBQ (5), $QQQ (5), $DDOG (5), $FIVN (5), $LRCX (4), $ALGM (4), $RKLB (4), $TWLO (4), $NVDA (4), $TSLA (4), $INOD (4), $ARM (4), $TVTX (3), $TGTX (3), $GH (3), $XBI (3), $TXN (3), $ADI (3), $MPWR (3), $ON (3), $NVTS (3), $POWI (3), $WOLF (3), $IFNNY (3), $VICR (3), $AEIS (3), $DIOD (3), $AOSL (3), $AIXA (3), $ENTG (3), $RNECF (3), $ROHCY (3), $AMAT (3), $SNDK (3), $ACMR (3), $MDB (3), $VIAV (3), $ONDS (3), $LQDA (2), $AMD (2), $PLTR (2), $ALKS (2), $TWST (2), $RVMD (2), $RDDT (2), $HNGE (2), $LLY (2), $TTMI (2), $UCTT (2), $UMC (2), $SEZL (2), $CAVA (2), $GLD (2), $UNH (2), $OSCR (2), $FTNT (2), $DOCN (2), $AKAM (2), $JBHT (2), $PANW (2), $ORCL (2), $MP (2), $ABCL (1), $JAZZ (1), $ARGX (1), $HUT (1), $CRS (1), $ASTH (1), $MIRM (1), $DY (1), $TER (1), $HOOD (1), $NKE (1), $NVO (1), $PYPL (1), $FLNC (1), $LPG (1), $RSI (1), $VVX (1), $VCYT (1), $KRYS (1), $ARW (1), $COCO (1), $NBIX (1), $LINC (1), $INCY (1), $DAVE (1), $VIRT (1), $EVR (1), $CUBI (1), $ATLC (1), $TKO (1), $TTD (1), $KLAC (1), $ASML (1), $STX (1), $INTC (1), $DELL (1), $WDC (1), $VSXY (1), $TEV (1), $CEVA (1), $VIX (1), $SPY (1), $SLV (1), $MSTR (1), $CVS (1), $AMKR (1), $SN (1), $KEYS (1), $KEEL (1), $MRK (1), $JNJ (1), $ENPH (1), $SEDG (1), $NXT (1), $KLIC (1), $IONQ (1), $QNT (1), $NAVN (1), $CRWD (1), $RBRK (1), $NET (1), $LOGI (1), $APP (1), $GRAB (1), $HBM (1), $ETN (1), $UAMY (1), $USAR (1), $REMX (1), $MUU (1), $AMR (1), $AVGO (1), $AEVA (1)
- **@amitisinvesting** — 242 tweets, 45 ticker-bearing; $NVDA (17), $SPCX (17), $MSFT (13), $MU (12), $AAPL (12), $AMZN (12), $META (12), $GOOGL (11), $PLTR (11), $TSLA (11), $HOOD (8), $INTC (6), $AMD (6), $MRVL (6), $QQQ (5), $ORCL (5), $NOK (5), $NFLX (4), $RDDT (3), $SPY (3), $ZETA (3), $F (3), $AVGO (3), $CRWD (3), $SHOP (3), $GME (2), $CBRS (2), $QCOM (2), $SOFI (2), $SPX (2), $CRWV (2), $SNDK (2), $BTC (2), $PANW (2), $NOW (2), $WEN (1), $VZ (1), $SMH (1), $ASTS (1), $EBAY (1), $INFQ (1), $QBTS (1), $IBM (1), $RGTI (1), $IONQ (1), $QNT (1), $CVX (1), $DRAM (1), $SPCH (1), $IBIT (1), $SNAP (1), $NBIS (1), $RKLB (1), $TER (1), $ALAB (1), $SMCI (1), $SOXS (1), $QLD (1), $SSO (1), $GLW (1), $IREN (1), $MSTR (1), $UBER (1), $CRM (1), $IGV (1), $DDOG (1), $SNOW (1)
- **@kaizen_investor** — 165 tweets, 35 ticker-bearing; $PL (19), $WOLF (5), $RKLB (5), $MRVL (4), $SIVE (3), $ASTS (3), $SPCX (2), $ASML (2), $ASM (2), $GOOGL (2), $OUST (2), $PLTR (2), $FLNC (2), $MU (1), $SAP (1), $NASA (1), $SPIR (1), $BKSY (1), $ENHA (1), $AMZN (1), $SATL (1), $FLY (1), $LUNR (1), $POET (1), $NVDA (1), $TMDX (1), $AMPX (1), $IREN (1), $HIMS (1)
- **@kawzinvests** — 90 tweets, 31 ticker-bearing; $NVDA (10), $AAOI (5), $SKM (5), $LITE (4), $COHR (4), $CIEN (3), $BRUN (3), $CRWV (3), $FN (2), $CSCO (2), $PENG (2), $STM (2), $AOSL (2), $DELL (2), $NBIS (2), $NOK (1), $KXIAY (1), $MU (1), $SNDK (1), $MRVL (1), $RDDT (1), $ZM (1), $CRDO (1), $SMTC (1), $MTSI (1), $VRT (1), $PWR (1), $IFX (1), $MPWR (1), $VICR (1), $NVTS (1), $ON (1), $TXN (1), $ADI (1), $POWI (1), $DIOD (1), $WOLF (1), $APLD (1), $IBM (1), $ORCL (1), $HPE (1), $SMCI (1), $SNX (1), $TSM (1), $LASR (1), $EOS (1), $SMOL (1), $ENAFF (1), $MX (1)
- **@michaelsikand** — 181 tweets, 30 ticker-bearing; $NOK (5), $AAOI (4), $BRUN (4), $MRVL (3), $KRKNF (3), $NBIS (3), $SPCX (2), $SATS (2), $LITE (2), $SKM (2), $ZM (2), $SIVE (2), $PENG (2), $LASR (2), $NVDA (2), $WEN (1), $RDDT (1), $NYT (1), $COHR (1), $RKLB (1), $ASTS (1), $STCK (1), $CRM (1), $COKE (1), $DELL (1), $RCAT (1), $AVAV (1), $KTOS (1), $AVEX (1), $EOS (1), $CIEN (1), $SGOV (1), $MXL (1), $HOOD (1), $DRAM (1), $GLXY (1), $CRWV (1), $IREN (1), $BE (1), $CRCL (1), $MU (1), $SOI (1)
- **@speculator_io** — 9 tweets, 6 ticker-bearing; $SNDK (4), $DELL (4), $NBIS (4), $MU (3), $STX (3), $WDC (3), $DOCN (3), $BE (3), $HUT (3), $IREN (3), $RXT (2), $HYLN (2), $VPG (2), $AMBQ (2), $INTC (2), $FLEX (2), $GEV (2), $AMPX (2), $VICR (2), $NVTS (2), $AMD (2), $ARM (2), $MRVL (2), $AAOI (2), $AXTI (2), $OPTX (2), $ICHR (2), $AEHR (2), $CRWV (2), $APLD (2), $VRT (2), $HPE (2), $ORCL (2), $STM (1), $MCHP (1), $IFX (1), $ON (1), $WOLF (1), $STRL (1), $SILC (1), $HIMX (1), $PWR (1), $VST (1), $BWXT (1), $CEG (1), $UEC (1), $CCJ (1), $NVDA (1), $TSM (1), $AVGO (1), $ASML (1), $COHR (1), $LITE (1), $GOOGL (1), $META (1), $AMZN (1), $TSLA (1), $NOW (1), $PLTR (1), $SNOW (1), $NET (1), $FSLY (1), $INOD (1), $IBM (1), $CDNS (1), $J (1), $PCOR (1), $PTC (1), $SIE (1), $SU (1), $DSY (1), $TT (1), $ABBN (1), $CAT (1), $ETN (1), $ENGI (1), $DLR (1), $EQIX (1), $SIFY (1), $SMCI (1), $DGXX (1), $HIVE (1), $WYFI (1), $BTDR (1), $RIOT (1), $CLSK (1), $CORZ (1), $CIFR (1), $CIEN (1), $ASX (1), $ENLT (1), $NOK (1), $GLW (1), $RKLB (1), $ALAB (1), $MXL (1), $VSH (1), $VIAV (1), $PL (1), $SEDG (1), $BLDP (1), $SATL (1), $MX (1), $SPIR (1), $CPSH (1), $FEL (1), $PURR (1), $PENG (1), $MRAM (1), $BKSY (1), $OSS (1), $UMAC (1), $USAR (1)
- **@zephyr_z9** — 430 tweets, 1 ticker-bearing; $TTM (1)

## Stage 3 — Sector grouping (LLM, probe-only)

> ⚠️ **Probe-only.** Sectors below are assigned by a single Gemini call
> and the model can miscategorize. In production this would be replaced
> by a deterministic ticker→sector map.

Unique tickers across all handles: **357**


### Overall sector concentration (by total mentions)

| Sector | Mentions | Tickers |
|---|---:|---|
| semiconductors | 654 | $ACMR, $ADI, $AEHR, $ALGM, $AMAT, $AMBQ, $AMD, $AMKR, $AOSL, $ARM, $ASM, $ASML, $ASX, $ASYS, $AVGO, $AXTI, $CAMT, $CEVA, $CRDO, $DIOD, $ENTG, $GFS, $HIMX, $ICHR, $IFNNY, $IFX, $INTC, $IQE, $KLAC, $KLIC, $LRCX, $MCHP, $MPWR, $MRVL, $MTSI, $MX, $MXL, $NVDA, $NVTS, $ON, $POWI, $QCOM, $RNECF, $ROHCY, $SIVE, $SMTC, $SOI, $STM, $TER, $TOWA, $TSEM, $TSM, $TXN, $UCTT, $UMC, $VICR, $VSH, $WOLF, $XFAB |
| space | 160 | $ALAB, $ASTS, $BKSY, $LUNR, $NPA, $PL, $RKLB, $SATL, $SPIR, $STRL |
| optical/photonics | 137 | $AAOI, $COHR, $FN, $LASR, $LITE, $OPTX, $POET, $SMOL, $VIAV |
| software | 127 | $APP, $CDNS, $CRM, $CRWD, $DDOG, $DSY, $FIVN, $FROG, $FTNT, $KEEL, $MDB, $MSFT, $MSTR, $NOW, $ORCL, $PANW, $PCOR, $PLTR, $PTC, $RBRK, $SAP, $SHAZ, $SHOP, $SNOW, $TTD, $TWLO, $ZETA, $ZM |
| internet | 97 | $AKAM, $AMZN, $BABA, $EBAY, $FSLY, $GOOGL, $GRAB, $META, $NET, $RDDT, $SECZ, $SNAP, $UBER |
| etf | 91 | $ECON, $EWY, $GLD, $IBIT, $IGV, $QLD, $QQQ, $REMX, $SGOV, $SLV, $SMH, $SOXS, $SPCX, $SPY, $SSO, $VSXY, $XBI, $XLU |
| memory | 85 | $DRAM, $KXIAY, $MRAM, $MU, $MUU, $SNDK, $STX, $WDC |
| industrial technology | 69 | $ABBN, $AEIS, $AMSC, $APH, $BDC, $CWR, $ETN, $FEL, $GEV, $LFUS, $LPK, $SIE, $TE, $VPG |
| oil & gas | 49 | $CVX, $NBIS, $PENG, $SU |
| telecom | 46 | $BAND, $CIEN, $DY, $NOK, $ONDS, $SKM, $T, $TMUS, $VZ |
| biotech | 45 | $ABCL, $ALKS, $ARGX, $ASTH, $AVEX, $BBC, $BCAR, $BCARW, $CBRS, $GH, $INCY, $INHD, $JAZZ, $KRYS, $LIFE, $LQDA, $MIRM, $NBIX, $QBTS, $RVMD, $TGTX, $TVTX, $TWST, $VCYT, $VVX |
| cryptocurrency | 45 | $BTC, $BTDR, $CIFR, $CLSK, $COIN, $CORZ, $ETHA, $GLXY, $HIVE, $HUT, $IREN, $RIOT, $SLNH, $SPCH, $WULF |
| other | 35 | $AIXA, $CRWV, $DGXX, $ENAFF, $RPI, $SPKL, $SPKLW, $SRTA, $WYFI |
| automotive | 35 | $AEVA, $AUR, $CEPT, $F, $GM, $HYLN, $OUST, $TSLA, $TTM |
| electronics manufacturing services | 29 | $CLS, $FLEX, $JBL, $TTMI |
| fintech | 27 | $BKKT, $DAVE, $HAWK, $HOOD, $PAY, $PYPL, $SEZL, $SOFI |
| ai infrastructure | 17 | $APLD, $INOD, $OSS, $SMCI, $VRT |
| solar | 15 | $CSIQ, $ENPH, $FSLR, $NXT, $SEDG |
| consumer electronics | 14 | $AAPL |
| mining | 12 | $AMR, $CCJ, $CRCL, $HBM, $MP, $UAMY, $UEC, $USAR |
| aerospace & defense | 11 | $AVAV, $BAER, $KTOS, $RCAT |
| other (spac) | 11 | $ATLC, $MRLN, $WLAC |
| consumer discretionary | 11 | $BRUN, $NKE, $PURR |
| batteries | 11 | $AMPX, $EOS, $EOSE, $FLNC |
| other (historical tech) | 10 | $FPS |
| computer hardware | 8 | $DELL |
| entertainment | 7 | $NFLX, $TKO, $UMAC |
| healthcare | 7 | $CVS, $ENHA, $HIMS, $OSCR, $UNH |
| cloud computing | 7 | $DOCN, $RXT |
| utilities | 6 | $CEG, $ENGI, $PNG, $PWR, $VST |
| restaurants | 6 | $CAVA, $WEN |
| financial services | 6 | $ALRIB, $EVR, $NAVN, $VIRT |
| clean energy | 6 | $BE, $BLDP, $FCEL |
| materials science | 5 | $ASPI, $CPSH, $CRS, $GLW |
| quantum computing | 5 | $IONQ, $QNT, $RGTI |
| pharmaceuticals | 5 | $LLY, $MRK, $NVO, $TEV |
| marine technology | 4 | $KRKNF |
| other (index) | 4 | $KOSPI, $SPX, $VIX |
| industrial machinery | 4 | $CAT, $LINC, $SHMD, $TT |
| medical devices | 3 | $HPS, $INFQ, $TMDX |
| enterprise software & services | 3 | $IBM |
| it services | 3 | $RSI, $SIFY, $SN |
| networking equipment | 3 | $CSCO, $SILC |
| enterprise hardware | 3 | $HPE |
| electronics distribution | 2 | $ARW, $RELL |
| retail | 2 | $GME |
| digital health | 2 | $HNGE |
| consumer staples | 2 | $COCO, $COKE |
| logistics | 2 | $JBHT |
| satellite communications | 2 | $SATS |
| real estate | 2 | $DLR, $EQIX |
| other (generic space) | 1 | $SPACE |
| cannabis | 1 | $YSS |
| power electronics | 1 | $IPWR |
| other (conglomerate) | 1 | $BRK |
| shipping | 1 | $LPG |
| banking | 1 | $CUBI |
| test & measurement equipment | 1 | $KEYS |
| pharmaceuticals & medical devices | 1 | $JNJ |
| computer peripherals | 1 | $LOGI |
| media | 1 | $NYT |
| e-commerce | 1 | $STCK |
| other (space agency) | 1 | $NASA |
| aerospace | 1 | $FLY |
| it distribution | 1 | $SNX |
| nuclear technology | 1 | $BWXT |
| engineering & construction | 1 | $J |
| renewable energy | 1 | $ENLT |

### Per-handle sector concentration (by mentions)

- **@aleabitoreddit** — semiconductors (392), optical/photonics (100), internet (39), memory (26), electronics manufacturing services (25), etf (24), oil & gas (24), cryptocurrency (24), industrial technology (17), space (13), other (11), fintech (10), automotive (8), telecom (8), software (5), batteries (3), biotech (3), financial services (3), restaurants (2), consumer electronics (2), ai infrastructure (2), mining (2), solar (2), other (index) (1), entertainment (1), cannabis (1), clean energy (1), electronics distribution (1), power electronics (1), industrial machinery (1), other (conglomerate) (1), medical devices (1), materials science (1)
- **@spacanpanman** — space (95), industrial technology (34), etf (17), software (13), biotech (11), other (10), other (spac) (10), aerospace & defense (8), telecom (3), automotive (2), solar (2), consumer discretionary (2), marine technology (1), utilities (1), internet (1), other (generic space) (1), fintech (1), oil & gas (1), cryptocurrency (1)
- **@venu_7_** — semiconductors (131), software (46), biotech (27), memory (24), etf (14), telecom (10), other (historical tech) (10), industrial technology (10), solar (10), space (9), oil & gas (7), internet (6), mining (6), fintech (5), pharmaceuticals (5), healthcare (5), automotive (5), ai infrastructure (4), other (3), financial services (3), optical/photonics (3), digital health (2), it services (2), electronics manufacturing services (2), restaurants (2), cloud computing (2), logistics (2), quantum computing (2), cryptocurrency (1), materials science (1), consumer discretionary (1), batteries (1), shipping (1), electronics distribution (1), consumer staples (1), industrial machinery (1), banking (1), other (spac) (1), entertainment (1), computer hardware (1), other (index) (1), test & measurement equipment (1), pharmaceuticals & medical devices (1), computer peripherals (1)
- **@amitisinvesting** — software (46), semiconductors (41), internet (41), etf (31), memory (15), automotive (14), consumer electronics (12), fintech (10), telecom (6), entertainment (4), cryptocurrency (4), space (3), biotech (3), quantum computing (3), retail (2), oil & gas (2), other (index) (2), other (2), restaurants (1), medical devices (1), enterprise software & services (1), ai infrastructure (1), materials science (1)
- **@kaizen_investor** — space (31), semiconductors (17), software (3), internet (3), batteries (3), etf (2), healthcare (2), automotive (2), memory (1), other (space agency) (1), aerospace (1), optical/photonics (1), medical devices (1), cryptocurrency (1)
- **@kawzinvests** — semiconductors (30), optical/photonics (17), telecom (9), oil & gas (4), other (4), memory (3), ai infrastructure (3), consumer discretionary (3), networking equipment (2), software (2), computer hardware (2), internet (1), utilities (1), enterprise software & services (1), enterprise hardware (1), it distribution (1), batteries (1)
- **@michaelsikand** — semiconductors (9), optical/photonics (9), telecom (8), oil & gas (5), consumer discretionary (4), etf (3), software (3), aerospace & defense (3), marine technology (3), satellite communications (2), space (2), memory (2), cryptocurrency (2), restaurants (1), internet (1), media (1), e-commerce (1), consumer staples (1), computer hardware (1), biotech (1), batteries (1), fintech (1), other (1), clean energy (1), mining (1)
- **@speculator_io** — semiconductors (34), memory (14), cryptocurrency (12), software (9), industrial technology (8), space (7), optical/photonics (7), ai infrastructure (7), oil & gas (6), cloud computing (5), internet (5), computer hardware (4), clean energy (4), utilities (4), other (4), automotive (3), mining (3), electronics manufacturing services (2), batteries (2), enterprise hardware (2), industrial machinery (2), real estate (2), telecom (2), materials science (2), networking equipment (1), nuclear technology (1), enterprise software & services (1), engineering & construction (1), it services (1), renewable energy (1), solar (1), consumer discretionary (1), entertainment (1)
- **@zephyr_z9** — automotive (1)

## Stage 4 — Thesis extraction (LLM, ticker-bearing only)

Descriptive structure per tweet: thesis, whether the claim is
falsifiable, its horizon and a checkpoint, and the stance. No judgement
of whether the claim is *good*.

Tweets are batched **50 per Gemini call** so the full month
fits within the free-tier daily request cap (one per-tweet call would not).

_Batch 6 failed: TimeoutError: The read operation timed out_
_Batch 7 failed: HTTPError: HTTP Error 503: Service Unavailable_
_Batch 11 failed: HTTPError: HTTP Error 503: Service Unavailable_
_Batch 13 failed: TimeoutError: The read operation timed out_
_Batch 14 failed: HTTPError: HTTP Error 503: Service Unavailable_
_Batch 15 failed: TimeoutError: The read operation timed out_

Successful extractions: **454** of 754 tweets across 16 batched call(s).

Stance distribution: opinion (222), news (101), prediction (62), other (52), question (12), promotion (5)

| Handle | Tickers | Stance | Falsifiable | Horizon | Thesis |
|---|---|---|---|---|---|
| @spacanpanman | $RKLB | news | True | Long-term | Rocket Lab is acquiring Iridium, which will create a vertically integrated space powerhouse poised for growth. |
| @aleabitoreddit | $ASTS, $SPCX | news | True | Medium to long-term | Rakuten and ASTS are forming a joint venture to build LEO satellite networks in Japan, seen as a strategic response to Starlink's influence. |
| @spacanpanman | $ASTS | prediction | True | Short-term | AST SpaceMobile and Rakuten are expected to win the J-LEO project. |
| @spacanpanman | $ASTS | opinion | True | Medium-term | The formal confirmation of the J-LEO project award for AST SpaceMobile in Japan will bring several significant benefits, including commercial approval, expanded partnerships, a multi-launch agreement, and substantial government funding. |
| @spacanpanman | $ASTS | news | True | Short-term | The Nikkei reports that Japan's Ministry of Internal Affairs and Communications is expected to select Rakuten and AST SpaceMobile for the $1 billion J-LEO project, which will provide 150 billion yen over three years for satellite communication development. |
| @aleabitoreddit | $GM, $NVDA, $AMZN | opinion | True | Medium-term | GM's worker cuts and robot replacements, along with a potential deal with Nvidia for factory robotics, validate the robotics industry by demonstrating increased operational efficiency and margin potential through automation. |
| @amitisinvesting | $MU, $NVDA, $AAPL | news | True | Short-term | Micron has become a top 10 holding in the S&P 500 with a 1.9% weighting, indicating a shift in institutional money towards new players like Micron, while the weightings of Nvidia and Apple have decreased. |
| @aleabitoreddit | $POET | opinion | True | Medium to long-term | Insights from the POET AGM transcript suggest that major laser suppliers are sold out for the next two years, indicating a thematic laser bottleneck likely extending into 2029. |
| @aleabitoreddit | $POET, $LITE, $SIVE, $AAOI | opinion | True | Medium to long-term | Notes from the POET AGM and optical market analysis indicate a laser shortage extending into 2029, and POET's new NRE customer for high-power external light sources is likely using Sivers as the laser supplier. |
| @aleabitoreddit | $RKLB, $SPCX, $EOS, $LITE, $TSLA | prediction | True | Long-term | The decade from 2020-2030 is predicted to be historically significant due to advancements in reusable rockets, artificial super intelligence, humanoid robotics, laser technology, self-driving cars, and quantum commercialization. |
| @venu_7_ | $ABCL, $JAZZ | prediction | True | Short-term | If ABCL closes weekly above its IPO VWAP, it appears ready for a significant upward movement, and JAZZ also looks promising. |
| @venu_7_ | $MU, $ALAB, $ARGX, $TVTX, $LQDA, $HUT, $CRDO, $AMD, $TGTX, $CRS, $ASTH, $GH, $MIRM, $LRCX, $DY | news | True | Short-term | The IBD Top 15 list for this week indicates a strong institutional money flow into AI infrastructure, semiconductors, and healthcare sectors. |
| @venu_7_ | $PLTR | prediction | True | Short-term | PLTR is at an interesting technical level, specifically its VWAP, which has historically acted as strong support, suggesting it might form a base here. |
| @venu_7_ | $TER | opinion | True | Long-term | This stock is a hidden robotics play that feels like TER in its early stages. |
| @venu_7_ | $SNOW | prediction | True | Medium-term | SNOW has held key support levels and shows strong volume, suggesting it is ready to begin a Stage 2 uptrend and could become a software leader this cycle. |
| @aleabitoreddit | $META, $NBIS, $GOOGL | opinion | True | Medium-term | Google's reported compute restraints on Meta and its own cloud backlog suggest a strong demand for AI data center capex buildout, which is positive for companies involved in that sector. |
| @spacanpanman | $TE | other | False | none | none |
| @aleabitoreddit | $CBRS | opinion | False | none | CBRS is currently a cautionary position due to the rapidly evolving nature of the AI space and various market factors. |
| @aleabitoreddit | $CBRS, $JBL | opinion | True | Short to medium-term | OpenAI's launch of its frontier model on Cerebras (CBRS) at high performance validates Cerebras' technology, though the stock might be overvalued compared to profitable peers, but benefits from an OpenAI exposure premium. |
| @aleabitoreddit | $SIVE | opinion | True | Medium-term | Following SpaceX's acquisition of Mesh, Sivers (SIVE) is likely to benefit due to its history of collaborating with early-stage startups. |
| @spacanpanman | $ASTS | opinion | True | Long-term | T-Mobile's partnership with Starlink appears to be a strategic mistake because it inadvertently helped SpaceX overcome regulatory and spectrum validation hurdles for its Direct-to-Cell technology, allowing SpaceX to expand beyond a passive infrastructure role. |
| @aleabitoreddit | $SPCX, $SIVE, $POET, $LITE, $MTSI | opinion | True | Medium-term | SpaceX's acquisition of Mesh, an optical networking startup, is positive for the industry, and Sivers (SIVE) is a plausible merchant supplier for Mesh's CW DFB lasers given its history with startups. |
| @aleabitoreddit | $SIVE | news | True | Short-term | Sivers (SIVE) dropped the employee incentive program from its meeting agenda, but its NASDAQ listing is still in process, with the shareholder meeting passing necessary authorizations for share issuance and new board members for dual listing liquidity. |
| @aleabitoreddit | $NBIS | other | False | none | none |
| @aleabitoreddit | $SIVE, $JBL, $GFS, $AMD, $NVDA, $POET, $AEVA, $MRVL | opinion | True | Medium to long-term | Sivers (SIVE) is undervalued based on its market cap relative to forward revenue potential, supported by recent positive developments including partnerships with JBL, GFS, Ayar (part of Nvidia ecosystem), and AlChip's Amazon connection. |
| @aleabitoreddit | $SIVE, $EWY, $NBIS, $IREN, $QQQ, $LITE | opinion | False | none | none |
| @aleabitoreddit | $SIVE, $AAOI | prediction | True | Long-term | The user is confident that Sivers (SIVE) and AAOI will experience a revenue ramp with lasers by 2027. |
| @aleabitoreddit | $MU | news | True | Short to medium-term | Elon Musk is highlighting massive demand and price hikes for memory from Micron, SK Hynix, and Samsung due to supply constraints, suggesting a significant memory bottleneck. |
| @aleabitoreddit | $SOI, $RKLB | opinion | True | Short-term to medium-term | There is a global market correction underway, with major indexes like Kospi, Nikkei, and TWSE experiencing significant drops, and high beta stocks are typically hit harder but tend to recover earlier. |
| @aleabitoreddit | $AXTI, $AAOI, $TSEM, $LITE, $MU, $SNDK, $EWY, $SIVE, $IQE, $SOI | opinion | True | Short-term to long-term | The user previously shared successful investment ideas for several stocks, and despite a recent macro-driven correction, most of these ideas are still significantly up, with CPO names being early-stage investments expected to recover. |
| @aleabitoreddit | $JBL, $SIVE | other | False | none | none |
| @aleabitoreddit | $AAOI, $AMD | opinion | True | Medium-term | The selloff in AAOI is attributed to a photonics theme selloff combined with a macro market drop, but the user remains confident due to AMD's CW LTA reports and next year's $471M/month projections. |
| @aleabitoreddit | $AOSL, $POWI | opinion | True | Short to medium-term | Power semiconductor companies are initiating price hikes, driven by demand from AI data centers and other sectors, which is a bullish thematic indicator for US power semiconductor stocks before the full impact of the 800V DC shift. |
| @spacanpanman | $BAER | other | False | none | none |
| @michaelsikand | $WEN | opinion | True | Short-term | The current market is characterized by a trillion-dollar company outperforming a meme stock in pre-market trading. |
| @kaizen_investor | $MU | news | True | Short-term | SK Hynix is up 14% due to strong earnings from Micron (MU). |
| @aleabitoreddit | $WEN, $RDDT | news | True | Short-term | Wendy's (WEN) stock has risen approximately 50% due to meme trading, gaining global media attention, which is impressive despite the user's AI memory/optical portfolio underperforming it. |
| @aleabitoreddit | $MU, $TSM, $TSLA | prediction | True | Long-term | Micron's CEO predicts a multi-decade memory demand cycle, starting before 2030, driven by humanoid robots requiring significantly more memory than autonomous vehicles, and further supported by on-device AI and pent-up unit replacement demand. |
| @kawzinvests | $NOK | opinion | True | Medium to long-term | The Infinera acquisition was a massive turning point for Nokia (NOK). |
| @kawzinvests | $KXIAY, $MU, $SNDK | news | True | Long-term | Kioxia has announced the availability of US depositary shares around April or May 2027. |
| @aleabitoreddit | $AXTI, $SOI, $AAOI | opinion | False | none | The user's investment strategy has resulted in recent losses, particularly in photonics and CPO-related stocks due to overconcentration, but they disagree with negative institutional reports on Soitec. |
| @venu_7_ | $MU | opinion | True | Short to medium-term | Micron's (MU) current price action and strong fundamentals, including $33B in operating profit, 85% gross margins, and guidance for $50B next quarter revenue and $210B operating profit over five quarters, suggest it is not cyclical, and the user will maintain this view as long as it holds above its 50-day moving average. |
| @aleabitoreddit | $DRAM, $MU, $SNDK | opinion | True | Medium-term | The DRAM ETF is a positive investment option due to its exposure to key memory companies like SK Hynix, Samsung, Micron (MU), and SanDisk (SNDK). |
| @aleabitoreddit | $BABA | opinion | True | Medium-term | If Alibaba's Qwen AI increases market share by effectively distilling Anthropic models without penalties, the rewards outweigh the risks, and the lack of enforcement from the US side is concerning. |
| @aleabitoreddit | $BABA | news | True | Short-term | Anthropic has accused Alibaba's Qwen AI lab of distilling its frontier AI models through extensive fake accounts and exchanges, a situation that is widely known but has not yet resulted in penalties. |
| @michaelsikand | $NOK | news | True | Short to medium-term | Nokia (NOK) is now considered a "Trump stock" after Trump publicly praised its $30M investment in US domestic manufacturing, which is expected to create thousands of jobs. |
| @aleabitoreddit | $JBL, $SIVE, $MRVL, $MXL, $TSEM | opinion | True | Medium-term | OpenLight, a private company, is growing, and investors can gain exposure to its ecosystem through public equities like JBL (a Sivers partner), Marvell, MaxLinear, and TSMC, due to the interconnected nature of optical players. |
| @aleabitoreddit | $AMZN, $TSLA, $GOOGL | opinion | True | Long-term | Hyperscaler capital expenditure, exemplified by Amazon's investment in LLM-driven workforce automation, physical AI (self-driving, robotics), and AWS compute buildout, is intended to drive massive future revenue and margin increases, not merely siphon off funds. |
| @amitisinvesting | $RDDT | other | False | none | none |
| @amitisinvesting | $MU | opinion | True | Short-term | The current market trend involves investors who missed the semiconductor rally turning random stocks, like Wendy's, into their own versions of successful plays like Micron (MU). |
| @venu_7_ | $HOOD | prediction | True | next few months | Robinhood ($HOOD) is showing strong bullish signals, including decoupling from Bitcoin, reclaiming its 200-day SMA, and significant institutional accumulation. |
| @amitisinvesting | $WEN | news | False | none | Wendy's ($WEN) stock is up 20% overnight due to a viral campaign on r/WallStreetBets aiming to prevent the company's bankruptcy. |
| @venu_7_ | $TGTX, $TVTX, $ALKS, $TWST, $RVMD, $LQDA, $XBI | opinion | True | next few months | Several biotech stocks ($TGTX, $TVTX, $ALKS, $TWST, $RVMD, $LQDA) and the $XBI ETF look promising. |
| @aleabitoreddit | $RDDT, $WEN | question | True | next few days/weeks | A viral campaign on Reddit ($RDDT) to "save" Wendy's ($WEN) has caused its stock price to rise 20% overnight, and the author wonders about its future effectiveness. |
| @venu_7_ | $MU, $NKE, $NVO, $PYPL | opinion | True | next few quarters | Micron ($MU) is a strong beneficiary of the HBM and AI memory cycle with dramatically improving earnings, and dismissing its potential by predicting a crash is dangerous. |
| @spacanpanman | $BAER | other | False | none | none |
| @amitisinvesting | $SPY, $SPCX, $MU, $GOOGL, $VZ, $AMZN, $AAPL, $MSFT, $NVDA, $META, $SMH, $PLTR, $ZETA, $ASTS, $GME, $EBAY, $CBRS | news | False | none | Global markets, including the S&P ($SPY) and U.S. memory stocks, were under pressure due to a sharp selloff in South Korea's KOSPI, fears of new taxes, retail leverage, and renewed rate-hike concerns. |
| @amitisinvesting | $MU | question | False | none | none |
| @venu_7_ | $GH | opinion | True | next few months | Guardant Health ($GH) showed leadership qualities by finding support at its 200-day SMA during a recent pullback. |
| @aleabitoreddit | $KOSPI, $EWY | opinion | True | long term | Bank of America's market calls, such as predicting an extreme bubble in $KOSPI/$EWY and three rate hikes in 2026, have been inaccurate and harmful to retail investors. |
| @aleabitoreddit | $SIVE, $AAPL | opinion | True | short term | A recent PR regarding $SIVE and $AAPL is likely a defensive move to counter false short-seller claims about their relationship, rather than indicating a new market entry. |
| @spacanpanman | $BAER | prediction | True | this summer | $BAER is fully deployed in anticipation of what is predicted to be the busiest firefighting summer on record. |
| @aleabitoreddit | $LITE, $COHR | opinion | False | none | Investing in certain ETFs is illogical because they contain easily accessible stocks like $LITE and $COHR, incur management fees, and include companies not directly related to AI data centers. |
| @aleabitoreddit | $LITE, $NVDA, $AMD, $AAOI, $SIVE, $SOI, $TSEM | prediction | True | next few years | The photonics theme, particularly CW laser chokepoints, is highly promising due to current EML bottlenecks and the shift to 1.6T/CPO, mirroring past growth seen in $LITE driven by $NVDA. |
| @aleabitoreddit | $ALAB, $MRVL | news | False | none | The optimal time to invest in CXL for memory pooling was four months ago, as evidenced by the significant price increases of $ALAB and $MRVL since then. |
| @amitisinvesting | $SPCX, $NVDA, $PLTR, $TSLA, $AMZN, $AAPL, $GOOGL, $MSFT, $NFLX, $INTC, $QCOM, $INFQ, $QBTS, $IBM, $RGTI, $IONQ, $QNT, $MU, $CVX | news | True | short term | Global markets could experience a significant end-of-Q2 rebalancing wave, with institutional investors potentially selling up to $165B in equities and buying bonds, as estimated by JPMorgan. |
| @aleabitoreddit | $TSM | opinion | False | none | The author's M&A ideas are compelling, as one of the Japanese $TSM suppliers they previously identified was fully acquired by Apollo. |
| @aleabitoreddit | $IREN, $NBIS | opinion | False | none | Selling $IREN due to dilution and a GPU pivot, and investing in $NBIS instead, was the correct investment decision. |
| @aleabitoreddit | $IREN, $NBIS | opinion | False | none | $IREN performed poorly last year, while $NBIS compounded significantly, despite negative sentiment towards $NBIS. |
| @aleabitoreddit | $NBIS, $IREN | opinion | False | none | Investors holding $IREN are missing out on the AI supercycle run, which includes sectors like photonics, memory, and Neoclouds like $NBIS. |
| @kawzinvests | $MRVL | news | False | none | $MRVL has officially been included in the S&P 500 index today. |
| @spacanpanman | $SHAZ | news | True | short term | Sharon AI ($SHAZ) is initiating the process for an IPO on the Australian Stock Exchange in 2H July, with an expected size of $200M or more, led by Macquarie and Canaccord. |
| @kaizen_investor | $SAP | opinion | True | next few years | While $SAP is excellent for data storage, its AI layer is lacking, leading many companies to build their own AI solutions on top of SAP data, which is eroding SAP's "complete package" moat. |
| @michaelsikand | $MRVL | opinion | True | next few years | Jensen Huang (Nvidia CEO) believes $MRVL can quadruple in value from its current price. |
| @aleabitoreddit | $LPK, $AEHR | prediction | True | next 1-2 years | $LPK could reach a market capitalization of $3B-$5B upon full volume ramp, as it has customers for glass substrates, but its growth might be capped by its niche as a small machine supplier. |
| @venu_7_ | $RDDT | prediction | True | long term | Reddit ($RDDT) is projected to experience significant growth, with revenue increasing nearly 20x and EPS inflecting positively within a decade. |
| @venu_7_ | $MCHP | opinion | True | next few months | Microchip Technology ($MCHP) is a strong company in the analog semiconductor sector, showing a 24-month base with significant accumulation. |
| @venu_7_ | $FLNC | opinion | True | next few weeks/months | Fluence Energy ($FLNC) presents an interesting setup in the power infrastructure theme, exhibiting constructive technical patterns like a daily flag and a solid monthly base. |
| @aleabitoreddit | $SIVE | prediction | True | short term | Japan is expected to defeat Sweden in the World Cup tomorrow, possibly by a score of 4-0, influenced by how Swedish media treated $SIVE. |
| @aleabitoreddit | $NVDA, $TSM | prediction | True | next few quarters/years | FOCI will remain a bottleneck for FAU and passive components within the $NVDA $TSM ecosystem as COUPE scales up. |
| @aleabitoreddit | $SPY | prediction | True | short term | $SPY is expected to be green tomorrow because the US won 2-0. |
| @venu_7_ | $HNGE | opinion | True | next few years | Hinge Health ($HNGE) is a promising recent IPO with strong revenue growth, technicals, AI software exposure, and healthcare-like margins, validated by expanding access from employers and insurers. |
| @venu_7_ | $MU, $NBIS, $MRVL, $FPS | opinion | False | none | The author believes in the power semiconductor theme and holds a diversified portfolio including $MU, $NBIS, $MRVL, and $FPS, with specific allocation rules. |
| @venu_7_ | $TXN, $ADI, $MCHP, $APH, $MPWR, $ON, $STM, $NVTS, $POWI, $WOLF, $IFNNY, $VICR, $AEIS, $VSH, $ALGM, $DIOD, $AOSL, $AIXA, $ENTG, $ICHR, $AMBQ, $RNECF, $ROHCY | promotion | True | next 18 months | Investing across the entire power semiconductor supply chain, rather than focusing on single companies, is a strategic playbook for the next 18 months, with 25 identified names, including 12 NVIDIA 800V partners. |
| @venu_7_ | $RNECF, $ROHCY | news | False | none | $RNECF and $ROHCY are international IDMs with meaningful AI-DC content, with $RNECF being on NVIDIA's 800V list and $ROHCY's MOSFET endorsed by NVIDIA for AI servers. |
| @venu_7_ | $AIXA, $ENTG, $ICHR, $AMBQ | opinion | True | next few years | Companies like $AIXA, $ENTG, $ICHR, and $AMBQ are "picks and shovels" in the equipment, materials, and edge AI sector, offering lower beta and structural exposure to the growing semiconductor supply chain. |
| @venu_7_ | $VSH, $ALGM, $DIOD, $AOSL | opinion | True | next few quarters | Companies like $VSH, $ALGM, $DIOD, and $AOSL are key players in the discrete, sensing, and passives sector, benefiting from a broad cycle recovery with lower beta and diverse exposure across various applications. |
| @venu_7_ | $VICR, $AEIS | opinion | True | next few years | Companies like $VICR and $AEIS are direct beneficiaries of 800V HVDC, serving as crucial links between WBG silicon and the rack in power modules and system-level conversion. |
| @venu_7_ | $ON, $STM, $NVTS, $POWI, $WOLF, $IFNNY | opinion | True | next few years | Wide-bandgap device makers like $ON, $STM, $NVTS, and $POWI are at the technological core of SiC and GaN switches, offering high structural growth and benefiting from NVIDIA's 800V initiatives. |
| @venu_7_ | $TXN, $ADI, $APH, $MCHP, $MPWR, $MRVL, $FPS | opinion | True | next few quarters | Companies like $TXN, $ADI, $APH, and $MCHP are high-quality names in broad analog and power management, benefiting from accelerating AI-DC mix and a cycle inflection. |
| @venu_7_ | $TXN, $ADI, $MCHP, $APH, $MPWR, $ON, $STM, $NVTS, $POWI, $WOLF, $IFNNY, $VICR, $AEIS, $VSH, $ALGM, $DIOD, $AOSL, $AIXA, $ENTG, $ICHR, $AMBQ, $RNECF, $ROHCY | news | False | none | This tweet provides a categorized list of 25 top power semiconductor companies, including 12 named NVIDIA 800V silicon partners. |
| @venu_7_ | $GH | opinion | True | next few weeks | Guardant Health ($GH) is currently in a massive Stage 2 uptrend. |
| @venu_7_ | $XBI, $TGTX, $TVTX, $ALKS, $TWST, $RVMD | opinion | True | next few months | The Biotech ETF ($XBI) is in a massive Stage 2 uptrend with institutional accumulation, indicating that the biotech sector is becoming constructive after years of underperformance. |
| @venu_7_ | $STM | opinion | True | next few quarters/years | STMicroelectronics ($STM) is one of the best-looking semiconductor stocks, having broken out of a 26-year base with strong institutional accumulation. |
| @aleabitoreddit | $LITE, $SIVE | prediction | True | next 2 years | $SIVE has the potential for significant market cap growth, similar to $LITE's past performance, given its current starting point. |
| @aleabitoreddit | $JBL, $SIVE, $NVDA | prediction | True | next few months | The partnership between $JBL and $SIVE was known before an official PR, and a more confident mapping to the $NVDA CPO ecosystem would lead to a significant rerating of $SIVE. |
| @aleabitoreddit | $POET, $GFS | other | False | none | The author's investment thesis is derived from combining various data points, including conference insights, annual reports, press releases, and historical investor decks related to CPO startups. |
| @aleabitoreddit | $SIVE, $JBL, $POET, $MRVL, $GFS | opinion | True | next few years | $SIVE is a crucial laser supplier for next-generation optical architectures, including 1.6T pluggable transceivers developed with $JBL, which creates a significant moat by addressing EML bottlenecks. |
| @aleabitoreddit | $COHR, $LITE, $NVDA, $AMD | news | True | next few quarters | The industry is facing a significant bottleneck in EMLs and CW lasers, with companies like $COHR and $LITE struggling to meet demand, which impacts supply for major players like $NVDA and $AMD. |
| @aleabitoreddit | $SNDK | opinion | False | none | Nittobo (3110), despite its near-monopoly in glass fiber cloth, is frustrating due to its refusal to significantly raise T-Glass ASP, which prevents its valuation from tripling, largely due to Japanese business culture. |
| @aleabitoreddit | $LITE, $COHR | opinion | True | Short to medium term | Korea is behind in laser technology, specifically 100G EML, which is dominated by US/Japan, but OE Solutions is the first/only in Korea to produce it, making its IP valuable. |
| @aleabitoreddit | $AAOI, $COHR, $LITE, $SIVE, $JBL, $GFS | opinion | True | Current/Short term | OE Solutions is a small Korean optical transceiver company that has become one of the few global players in 100G EML lasers, with scarce capacity for high-speed transceivers, and is expanding into full transceiver and CPO products. |
| @aleabitoreddit | $SNDK | opinion | True | Short term | Gym enthusiasts are causing supply bottlenecks and price hikes in whey protein, similar to past tech trends, and creatine might be next. |
| @aleabitoreddit | $HOOD | opinion | False | none | The user is confused why people mistake fake accounts for them despite a clear bio, and states that Robinhood ($HOOD) not supporting EU/TW assets indicates it's a scam. |
| @venu_7_ | $MU | opinion | False | none | Technical analysis (TA) was instrumental in entering a memory trade with $MU and will likely guide the exit, and successful investing requires combining multiple metrics like fundamentals, technicals, sentiment, and risk management rather than relying on a single indicator. |
| @aleabitoreddit | $ASML, $TOWA, $LPK | opinion | True | Medium to long term | The key to winning trade wars lies in controlling frontier supply chains (Quantum, AI, Robotics) rather than traditional exports, as critical monopolies and chokepoints are held by countries outside the US, making tariffs on partners a poor strategy, though it's not too late to change. |
| @spacanpanman | $SHAZ, $BCAR | other | False | none | none |
| @aleabitoreddit | $CAMT, $WYFI, $SIVE, $ACMR | opinion | True | Short to medium term | Priortech appears to be a holding company due to its large stake in $CAMT, Bit Digital's NAV discount is not clean due to dilution, and Wistron (3231) is a strong company with significant Q1 revenue growth and a valuable stake in Wiwynn, which is expected to continue growing. |
| @aleabitoreddit | $RPI | opinion | False | none | The user prefers to do their own forecast modeling for non-Mag7 companies because institutional reports for retail are often inaccurate, and their own models, like for $RPI, tend to be more accurate. |
| @aleabitoreddit | $EWY | opinion | True | Short to medium term | The user is long on Samsung via $EWY and believes it is currently undervalued based on operating income forecasts. |
| @aleabitoreddit | $XFAB | prediction | True | Short to long term | $XFAB is a long-term investment for 2027/2028 but is expected to recover in the second half of the current year, independent of silicon photonics, as it emerges from an automotive slump. |
| @aleabitoreddit | $AAOI | opinion | True | Short to medium term | Bears are mistaken about the industry when it is laser/capacity constrained, especially as $AAOI projects significant revenue with independent, US-based supply. |
| @michaelsikand | $RDDT, $NYT | prediction | True | Medium to long term | The internet and stock market media are filled with low-quality content due to outdated search/SEO, and the beneficiaries of a shift towards quality will be platforms like $RDDT, publishers with legitimate news teams ($NYT, News Corp) who will secure lucrative deals from LLMs and win lawsuits, and human-curated content on X and Substack. |
| @aleabitoreddit | $INTC | opinion | True | Short to medium term | $INTC is strategically acquiring or partnering with various entities, metaphorically 'assembling the Avengers.' |
| @aleabitoreddit | $ASML | question | False | none | The user questions how China could smuggle large equipment from $ASML, implying a significant and potentially illicit operation. |
| @spacanpanman | $ASTS | news | True | Short to medium term | SpaceX has criticized the EU's proposed rules for satellite spectrum distribution, arguing that they risk leaving the bloc without functional satellite services and impacting Starlink's growth plans. |
| @kaizen_investor | $WOLF | opinion | True | Short to medium term | $WOLF is a highly volatile stock but is currently one of the most undervalued AI stocks. |
| @kaizen_investor | $SIVE | opinion | False | none | The user acknowledges a past investment mistake with $SIVE at 8SEK, implying it was a poor entry point. |
| @kaizen_investor | $MRVL | opinion | True | Short term | $MRVL has reached new all-time highs, and the user believes they bought it just before its significant rise, attributing its success to being a great company with many tailwinds. |
| @aleabitoreddit | $AAOI, $SIVE, $COHR | prediction | True | Medium to long term | Laser companies like $AAOI and $SIVE are favored investments due to their potential to expand revenue beyond just lasers into full optical modules and components, or even vertically integrate like $COHR, and the photonics sector is still in its very early stages with most significant revenue growth expected in H1-H2 2027. |
| @aleabitoreddit | $ALRIB | news | True | Short term | $ALRIB's general meeting notes indicate positive developments, including the imminent delivery of a second ROSIE System to a US quantum computing player and intensified business development for photonics products with strong interest, reinforcing its position as an MBE duopoly with quantum exposure. |
| @spacanpanman | $ASTS | news | True | Short to medium term | New Street Research has published a report on the policy issues and implications of a joint venture involving AT&T, Verizon, and T-Mobile, with key implications for $ASTS, and the user's view aligns with the report's assessment of the JV's impact on $ASTS. |
| @amitisinvesting | $AMD, $HOOD, $AAPL, $SPCX, $NVDA, $GOOGL, $META, $SPY, $QQQ, $AMZN, $MSFT, $TSLA, $SOFI, $MU, $DRAM | news | True | Short term | The Federal Reserve did not cut rates at its recent meeting, with "rigorous debate" among policymakers, and Kevin Warsh emphasized that markets perform best by reacting to data and that financial market prices are crucial information for central bankers. |
| @aleabitoreddit | $RDDT | opinion | True | Short term | The user speculates on the likely financial status of $RDDT users, suggesting a majority have significant credit card debt or have lost money on options, with a very small percentage being wealthy. |
| @spacanpanman | $BAER | other | False | none | none |
| @spacanpanman | $ASTS | news | True | Short to medium term | $ASTS is entering a "catalyst season" with several upcoming events, including a $1B Japan project decision, multiple BlueBird satellite deliveries and launches, and the achievement of 200Mbps performance for Block-2 satellites. |
| @spacanpanman | $ASTS | other | False | none | none |
| @spacanpanman | $ASTS | opinion | False | none | The user feels compelled to re-engage with $ASTS due to a significant "call to action." |
| @spacanpanman | $SHAZ | news | True | Short term | Cantor has upgraded its price target for $SHAZ, as reported by Bloomberg. |
| @spacanpanman | $ASTS | news | True | Short term | AST SpaceMobile has successfully launched BlueBird satellites 8, 9, and 10, which are the largest commercial communications arrays in LEO, and satellites 11, 12, and 13 are being prepared for shipment, with the BlueBird satellites designed for nearly 200 Mbps data speeds to smartphones. |
| @kaizen_investor | $PL, $RKLB | opinion | False | none | The user is not worried about $PL's 50% drop because there are no fundamental issues with the company, and their diversified investment strategy across various "investment waves" (space, memory, LiDAR, drones, photonics, datacenters, energy) provides resilience against downturns in any single sector. |
| @spacanpanman | $ASTS | promotion | False | none | none |
| @spacanpanman | $ASTS | news | True | Short term | SpaceX successfully delivered AST SpaceMobile's BlueBird8-10 satellites to orbit in a flawless mission, marking their third such mission for AST SpaceMobile. |
| @spacanpanman | $ASTS | news | True | Short term | The deployment of $ASTS assets has been successfully confirmed. |
| @spacanpanman | $ASTS | other | False | none | none |
| @aleabitoreddit | $SIVE | opinion | False | none | The perception of an investment in $SIVE differs significantly based on whether it's attributed to a formal entity like "Serenity Research" versus an informal "Serenity," with the latter being perceived as a retail meme. |
| @spacanpanman | $ASTS | other | False | none | none |
| @spacanpanman | $ASTS | other | False | none | none |
| @aleabitoreddit | $INTC | opinion | True | Past | The user previously criticized a $36 price target for $INTC as a "troll" report in January, and Intel subsequently saw triple-digit gains. |
| @aleabitoreddit | $INTC | opinion | True | Short to medium term | Bernstein is an incompetent analyst firm, evidenced by their call for a 50% crash in Kioxia and a $36 price target for $INTC in January which subsequently rose to $118, serving as a lesson to disregard institutional reports aimed at retail investors as they are not intended to be helpful. |
| @aleabitoreddit | $AEHR, $AAOI | opinion | True | Short term | There has not been much news or debate surrounding $AEHR, unlike $AAOI, with only a few comments suggesting $AEHR would drop to $25. |
| @amitisinvesting | $SPCH, $IBIT, $SPCX, $SPX, $TSLA, $NVDA, $AAPL, $INTC, $NFLX, $MU, $AMZN, $MSFT, $SOFI, $HOOD, $SNAP | news | True | Short term | Tomorrow's FOMC meeting, led by Kevin Warsh as Fed Chair, will be closely watched for his stance on inflation, rates, and potential cuts, with falling oil prices ($77 today) acting as a tailwind by easing inflation pressure and potentially influencing Warsh's acknowledgment of the improving inflation picture. |
| @aleabitoreddit | $AAOI, $AMD, $NVDA, $LITE, $NBIS | opinion | True | Short to medium term | The user maintains a high conviction long position on $AAOI, believing bearish views are incorrect, because the company possesses scarce laser capacity sought by hyperscalers like $AMD, operates a US-based transceiver supply chain for high-speed production, and benefits from demand far exceeding supply in an industry bottlenecked by $NVDA. |
| @spacanpanman | $ASTS | other | False | none | none |
| @spacanpanman | $ASTS | other | False | none | none |
| @michaelsikand | $SPCX, $SATS | prediction | True | Long term | In 50 years, $SPCX will be worth $100T, while some investors will still be waiting for $SATS to re-rate to its Net Asset Value (NAV). |
| @kaizen_investor | $NASA | opinion | False | none | There are good space ETFs available, such as $NASA. |
| @kaizen_investor | $PL | opinion | True | Short to medium term | $PL is down almost 50% due to a poorly timed ATM announcement and capital outflow to SpaceX, but its fundamentals and projects remain strong, suggesting it's not a time to panic and it could recover like IREN did. |
| @spacanpanman | $ASTS, $RKLB, $PL, $SPCX | prediction | True | Medium term | The space sector is entering its "AI moment," where initial investment focus on large players like SpaceX will shift to smaller, higher-leverage pure-play leaders with direct exposure to the space economy, similar to how AI investments moved beyond Nvidia. |
| @spacanpanman | $ASTS | opinion | False | none | The @thekookreport space has significantly increased the user's bullish sentiment towards $ASTS. |
| @spacanpanman | $RKLB | news | True | 12-18 months | KeyBanc upgraded Rocket Lab (RKLB) to Overweight with a $135 price target due to compelling opportunities in the space sector, accelerating NASA activity, and constrained launch supply. |
| @aleabitoreddit | $SIVE | other | False | none | none |
| @aleabitoreddit | $IQE | other | False | none | none |
| @aleabitoreddit | $IQE, $TSEM, $MTSI | news | False | none | IQE has signed a multi-year InP epiwafer deal with Tower Semi, reinforcing its importance to Western optical supply chains. |
| @aleabitoreddit | $WOLF | opinion | True | short-term | WOLF, as a core part of American supply chains, might perform well ("go brrr") with more market support and subsidies, despite current financial toxicity. |
| @aleabitoreddit | $SIVE, $LITE | opinion | True | short-term | The user is bullish on SIVE due to positive EU macro, the laser group's performance from InP bottleneck easing, and a possible Nasdaq listing timeline announcement today. |
| @aleabitoreddit | $WOLF, $LITE, $SPCX | opinion | True | short-term | It is foolish to be bearish because Trump is boosting markets, specific sectors like power semi (WOLF) and optical (LITE) will benefit from technological advancements and easing bottlenecks, the SPCX IPO increases risk appetite, and macro conditions are improving. |
| @aleabitoreddit | $POET | opinion | True | medium-term | POET has a significant cash reserve (~$1B) after a $400M private placement, which provides a strategic advantage for acquisitions even if their core technology doesn't succeed with hyperscalers. |
| @aleabitoreddit | $AXTI, $IQE, $AAOI, $LITE, $SIVE | news | True | short-term | China easing InP substrate exports is expected to relieve mass production bottlenecks in the photonics market, benefiting optical companies like AXTI, IQE, AAOI, LITE, SIVE, VPEC, and Landmark. |
| @aleabitoreddit | $NVTS, $POWI, $ON, $WOLF, $AOSL, $XFAB | prediction | True | short-term | Companies with power semiconductor exposure, such as NVTS, POWI, ON, WOLF, AOSL, and XFAB, will likely see a stock price bump due to a Q3 pull forward. |
| @aleabitoreddit | $NVDA, $GOOGL, $VRT | news | True | medium-term | Nvidia and Google are leading the adoption of 800V DC technology ahead of schedule, with small volume shipments starting in Q3 2026, benefiting companies like Delta Electronics, VRT, Song Chuan Precision, Schneider Electric, Eaton, and Siemens. |
| @amitisinvesting | $SPCX | opinion | True | medium-term | If Elon Musk's statement (implied from the context of the conversation) is correct, then SPCX is currently undervalued. |
| @kaizen_investor | $WOLF | opinion | True | short-term | WOLF is a stock worth considering for investment because it has not experienced significant recent price appreciation. |
| @michaelsikand | $AAOI, $LITE, $COHR | opinion | True | long-term | AAOI is still an asymmetrical investment opportunity, with management projecting $471M in monthly transceiver revenue by Q2 2027. |
| @aleabitoreddit | $SPCX, $SIVE, $SOI | opinion | False | none | Different regions exhibit distinct market behaviors and investment focuses, with China being short-term focused, America bullish on futuristic tech like SPCX regardless of valuation, Europe prioritizing sustainability over AI, and Korea showing high volatility. |
| @aleabitoreddit | $SIVE | opinion | True | medium-term | The discussed event (implied from context) is positive for SIVE as it relates to Nasdaq listing liquidity requirements and M&A, which could lead to SIVE trading on US markets. |
| @aleabitoreddit | $SIVE, $SNDK | opinion | True | long-term | SIVE is a good long-term investment, similar to past compounders like SNDK, as it is important to AI and the market is at the beginning of a new supercycle. |
| @kawzinvests | $LITE, $AAOI, $FN, $CIEN, $CSCO | news | True | long-term | Demand for 800G and 1.6T components significantly outstrips supply, with LITE having sold all its lasers through 2027 and AAOI's expanded capacity still being outrun by demand through mid-2027. |
| @spacanpanman | $ASTS | news | True | short-term | ASTS is preparing for the loading of Batch-2 BlueBird satellites (11, 12, 13) soon. |
| @kawzinvests | $RDDT | opinion | False | none | RDDT is fundamentally a very unique company. |
| @spacanpanman | $ASTS | opinion | False | none | ASTS possesses the most revolutionary technology, according to an unnamed source from Seal Team 6. |
| @kaizen_investor | $PL | opinion | True | medium-term | PL is currently the best space investment, based on its historical performance and the user's extensive research. |
| @spacanpanman | $ASTS | opinion | False | none | AST SpaceMobile has an impressive roadmap that led Verizon to partner with them over Starlink. |
| @aleabitoreddit | $TSM | prediction | True | short-term | Foosung is expected to be a massive beneficiary soon due to China's export control on Japan's WF₆ supply, which creates a significant bottleneck for major chip manufacturers like SK Hynix, Samsung, and TSM. |
| @aleabitoreddit | $AXTI | opinion | True | long-term | The "AI supremacy Wars" and resulting upstream supply chain bottlenecks (e.g., AXTI) will create interesting investment opportunities, and actions to keep advanced AI models within the US will help preserve American dominance. |
| @spacanpanman | $ASTS | other | False | none | none |
| @spacanpanman | $ASTS | other | False | none | none |
| @spacanpanman | $ASTS | opinion | False | none | The significant drawdown in ASTS stock today was surprising, and despite various theories, the user loaded heavily on upside. |
| @amitisinvesting | $SPCX | news | False | none | SpaceX (SPCX) traded 380M shares in its first 3 hours, setting a new record for the largest intraday IPO trading volume. |
| @spacanpanman | $SHAZ | news | True | short-term | An S-1 registration for $350M convertible notes, allowing ~11.2M shares to be sold, is likely causing pressure on SHAZ stock today. |
| @spacanpanman | $SPCX, $ASTS | other | False | none | none |
| @amitisinvesting | $SPCX | news | False | none | SpaceX (SPCX) opened up 20%, making Elon Musk the world's first trillionaire. |
| @aleabitoreddit | $SPCX | news | False | none | SpaceX (SPCX) is now trading with a market cap over $2.15T. |
| @kaizen_investor | $SPCX, $PL, $ASTS, $RKLB | prediction | True | short-term | The trading of SPCX has created a liquidity vacuum effect on other space stocks, which will be followed by a halo effect, making companies like PL, ASTS, and RKLB buying opportunities. |
| @aleabitoreddit | $SIVE | other | False | none | none |
| @spacanpanman | $TE | opinion | True | medium-term | The transition for TE to become fully independent after acquiring operating assets will take time. |
| @spacanpanman | $SHAZ | prediction | True | short-term | SHAZ is expected to rebound after the market processes the volatility from the SpaceX IPO. |
| @aleabitoreddit | $SNDK, $SPCX | opinion | False | none | SNDK short sellers have been wiped out as the stock approaches $2000, and the market is currently focused on the upcoming SPCX IPO. |
| @spacanpanman | $ASTS | other | False | none | none |
| @spacanpanman | $SPKL | promotion | False | none | none |
| @kaizen_investor | $SPIR, $BKSY | opinion | True | medium-term | SPIR has a limited total addressable market despite a monopoly in commercial satellite weather data, which is a concern, while BKSY is a competitor to Planet Labs focused on on-demand monitoring. |
| @amitisinvesting | $SPCX, $HOOD | opinion | False | none | Robinhood (HOOD) is commendable for providing retail investors access to the SpaceX (SPCX) IPO, which is the largest in history. |
| @spacanpanman | $SPCX | question | False | none | none |
| @venu_7_ | $RKLB | prediction | True | short-term | RKLB's stock price will reach $200 or more before the end of the year. |
| @spacanpanman | $SPCX | news | False | none | none |
| @spacanpanman | $SHAZ | opinion | True | long-term | The collaboration between SHAZ and Nvidia, involving product credit and revenue-sharing, appears to be an attractive and efficient model for Sharon AI to serve the Australian market. |
| @spacanpanman | $SHAZ | news | False | none | Sharon AI (SHAZ) has announced a six-year strategic compute collaboration with Nvidia to deploy a 72MW AI factory with up to 40,000 Grace Blackwell GB300 GPUs in Australia, significantly expanding its AI factory capacity. |
| @kaizen_investor | $PL | news | True | long-term | Planet Labs (PL) CEO expects commercial revenue to surpass defense and intelligence revenue in a couple of years, with Agentic Geospatial AI & LLM Integration being the biggest factor for revenue growth in the next 5 years. |
| @spacanpanman | $SPCX | news | False | none | SpaceX (SPCX) IPO will begin quoting at 9:50 AM ET and be eligible for trading at 10 AM ET on NASDAQ. |
| @spacanpanman | $BAER | promotion | False | none | none |
| @spacanpanman | $ASTS | other | False | none | none |
| @kaizen_investor | $ASML | opinion | True | short to medium term | SK Hynix (implied) still has room to grow due to its low forward P/E and strong financial metrics compared to ASML. |
| @aleabitoreddit | $IQE, $XFAB | opinion | True | long term | IQE and XFAB are critical to western supply chains and likely have a long way to go in terms of recognition or growth. |
| @aleabitoreddit | $IQE, $MTSI | news | True | short to medium term | VPEC's price hikes on Epiwafers indicate strong demand and pricing power for companies like IQE and Landmark, highlighting their critical role in supply chains. |
| @aleabitoreddit | $AXTI | opinion | True | medium to long term | CPO (Co-Packaged Optics) related investment ideas should not be judged over a short one-month timeframe, as similar bottlenecks took many months to be confirmed and play out. |
| @aleabitoreddit | $RDDT | other | False | none | none |
| @aleabitoreddit | $ALAB, $LITE, $AAOI, $NBIS, $RKLB, $TSM, $SIVE, $AXTI | other | False | none | The author's high-conviction investment ideas from 2025, including ALAB, LITE, AAOI, NBIS, RKLB, and TSM, performed very well, with some growing significantly in market cap. |
| @aleabitoreddit | $NBIS | prediction | True | long term | NBIS has the potential to become the next hyperscaler. |
| @aleabitoreddit | $ALAB | other | False | none | none |
| @aleabitoreddit | $NBIS, $ALAB, $RKLB | news | False | none | NBIS, ALAB, and RKLB have been added to the Nasdaq 100, signifying their growth from small companies into large ones on Nasdaq. |
| @michaelsikand | $SPCX | opinion | False | none | Market sentiment regarding SPCX and space-related stocks has shifted from skepticism to strong desire. |
| @spacanpanman | $RKLB | other | False | none | none |
| @amitisinvesting | $QQQ, $NBIS, $RKLB, $CRWV, $TER, $ALAB | news | False | none | NBIS, RKLB, CRWV, TER, and ALAB have been announced as new additions to the Nasdaq 100 index. |
| @spacanpanman | $SPKLW | opinion | True | short to medium term | SPKLW is probably worth picking up if there is a pullback. |
| @spacanpanman | $SPCX | question | False | none | none |
| @venu_7_ | $NBIS, $RKLB | other | False | none | none |
| @spacanpanman | $TE | opinion | False | long term | American energy independence and AI supremacy are rooted in Texas, implying TE plays a role. |
| @venu_7_ | $MRVL | opinion | True | short term | Marvell Technology ($MRVL) looks good and is holding up its gap. |
| @spacanpanman | $ASTS | opinion | True | short to medium term | AST SpaceMobile ($ASTS) has entered a period of strong performance or growth. |
| @spacanpanman | $TE | other | False | none | none |
| @venu_7_ | $QQQ | prediction | True | short to medium term | The Nasdaq 100 ($QQQ) could reach new All-Time Highs (ATHs) if Tuesday's lows hold, despite recent bearish sentiment. |
| @venu_7_ | $MU | prediction | True | medium term | Micron ($MU) is breaking out of a flag pattern after pulling back to its 21-day EMA, suggesting it could reach $1,200+. |
| @spacanpanman | $TE | prediction | True | short to medium term | Following a negative report from Fuzzy Panda Short, T1 Energy ($TE) is poised for a significant upside run of 100% to 150%, potentially reaching $15 or $20, similar to a previous instance. |
| @kawzinvests | $SKM | opinion | True | long term | SK Telecom's ($SKM) management demonstrates long-term conviction by focusing on Anthropic's implications for their business over the next decade rather than cashing out at IPO. |
| @aleabitoreddit | $SNDK, $MRVL, $LITE | news | False | none | The current green market, including indexes and specific stocks like SNDK, MRVL, and LITE, is a direct result of Trump cancelling attacks on Iran. |
| @kawzinvests | $ZM | other | False | none | none |
| @spacanpanman | $ASTS | news | False | none | SpaceX is scheduled to launch 3 AST SpaceMobile Block-2 BlueBird satellites on June 17th, and ASTS stock previously rose above $100 towards $120 in anticipation of this launch before being impacted by the Iranian conflict. |
| @spacanpanman | $TE | news | True | medium term | Roth Capital has reiterated a Buy rating and $10 price target for TE, refuting Fuzzy Panda Research's report which mistakenly assumes TE is a FEOC based on sales invoices. |
| @venu_7_ | $CRDO, $LPG, $RSI, $VVX, $LLY, $VCYT, $KRYS, $ARW, $COCO, $TTMI, $NBIX, $LINC, $INCY, $DAVE, $VIRT, $EVR, $CUBI, $ATLC, $TKO, $LRCX | opinion | False | none | The listed CANSLIM Top 20 leaders exhibit characteristics of explosive EPS growth, strong revenue growth, exceptional relative strength, and trading near 52-week highs. |
| @aleabitoreddit | $WULF, $CIFR, $WYFI, $HUT | opinion | True | medium term | New Anthropic news, specifically its pursuit of data center leases, is a potential tailwind for the Neocloud colocation sector, benefiting companies like WULF, CIFR, WYFI, and HUT. |
| @kawzinvests | $SKM | prediction | True | long term | Anthropic has the potential to become one of the biggest companies globally by 2030, and SKM could be one of its biggest beneficiaries. |
| @kawzinvests | $SKM, $NVDA, $PENG | opinion | True | medium to long term | SKM is strategically building a comprehensive AI ecosystem by partnering with Anthropic for models, NVDA for compute, and PENG for AI factory infrastructure. |
| @venu_7_ | $MRVL | opinion | True | short term | Marvell Technology ($MRVL) is demonstrating strong technical characteristics by holding its earnings gap, backtesting the 9-day EMA, and forming a tight flag, which are signs of a leader preparing for a breakout. |
| @kawzinvests | $SKM, $NVDA | news | False | none | SKM is a critical component of Korea's AI ecosystem, as evidenced by Jensen Huang's statement, its increased investment in Anthropic with no intention to sell before IPO, and its inclusion in Anthropic's exclusive Project Glasswing. |
| @michaelsikand | $SKM, $ZM | opinion | True | medium to long term | SKM has significant exposure to Anthropic, confirmed by its CEO, and its core telco business is undervalued, suggesting substantial upside if telecom becomes critical AI infrastructure as Jensen Huang predicts. |
| @aleabitoreddit | $NVDA | opinion | True | medium to long term | The author's investment themes, including 800V DC and CPO, are focused on investing in NVIDIA and securing its supply chains by supporting critical companies with capital expenditure to overcome technological difficulties and bottlenecks. |
| @aleabitoreddit | $NVDA | prediction | True | medium term | Lightmatter/Ayar-type companies, being part of the NVIDIA NVLink CPO ecosystem with strong backers, are likely to achieve market valuations higher than $5 billion if they IPO. |
| @aleabitoreddit | $AAOI, $INTC, $IQE, $XFAB, $MU, $WOLF, $SOI, $SIVE | opinion | True | medium to long term | Markets should support domestic champions like AAOI and other listed companies because they are critical to US AI infrastructure and supply chains, and are receiving subsidies for securing Western supply chains. |
| @spacanpanman | $SPKL | news | False | none | ZincFive ($SPKL) has strong key statistics, including a $752M Enterprise Value, projected revenue growth through 2026, significant contracted backlog, deployed capacity, and numerous patents. |
| @venu_7_ | $TTD | opinion | False | none | TTD serves as a correct example of a bear flag pattern, characterized by distribution and a loss of the 50-day moving average. |
| @venu_7_ | $KLAC, $LRCX, $AMAT, $ASML, $ICHR, $UCTT | prediction | True | medium term | While major semi equipment stocks are rising, ICHR and UCTT, which sell to AMAT and LRCX and are tied to the Wafer Fab Equipment (WFE) cycle, are expected to outperform when the cycle expands. |
| @venu_7_ | $MU | opinion | True | short term | Marvell Technology ($MRVL) is holding its gap-up candle low, which is a strong support level, and Micron ($MU) still looks great. |
| @kaizen_investor | $SPCX | prediction | True | short term | The SPCX IPO has three effects on other space tickers: a halo effect, vacuum pressure, and capital outflow; the halo effect and capital outflow have already occurred, and vacuum pressure might manifest tomorrow. |
| @venu_7_ | $UMC | other | False | none | none |
| @venu_7_ | $SNDK, $MU, $STX, $INTC, $DELL, $WDC, $AMD, $AMAT, $LRCX | opinion | True | medium to long term | Despite recent pullbacks, the market is still having a phenomenal year, with many S&P 500 leaders showing significant gains, and bull markets typically experience corrections before continuing higher. |
| @aleabitoreddit | $META, $MSFT, $SPCX | question | False | none | none |
| @venu_7_ | $SNDK, $MU | question | False | none | none |
| @michaelsikand | $SATS, $RKLB, $ASTS, $STCK, $ZM, $CRM, $SKM | opinion | True | medium term | Anthropic is the next major investment opportunity after SpaceX, with a potential $1T+ IPO, but retail investors face challenges in finding a straightforward proxy trade due to its private nature and lack of direct public competitors. |
| @aleabitoreddit | $AAOI | opinion | True | medium term | If AAOI can achieve $471M/month revenue by the end of H1 2027, its potential seems high given its current $13.4B valuation, though optical names are volatile. |
| @venu_7_ | $VSXY | opinion | True | short to medium term | Victoria's Secret ($VSXY) is unexpectedly breaking out of a 4-year base in an AI bull market, supported by a PEG candle, a 90% EPS beat, and nearly doubled EPS estimates for 2026 vs 2025. |
| @aleabitoreddit | $ASX, $JBL, $VICR, $GFS, $AAOI, $TSEM, $FN, $CLS, $NBIS, $NOK, $AMKR, $LITE, $COHR, $ARM, $MRVL | opinion | True | next few quarters | AI-exposed companies in the $10-100B range likely offer compelling ROI right now compared to indexes or already-run stocks like ARM and MRVL. |
| @spacanpanman | $ASTS | news | True | immediate | AST SpaceMobile's Block-2 BlueBird satellites (BB8, BB9, BB10) can fit in a Falcon-9 fairing, contrary to previous claims. |
| @spacanpanman | $ASTS | news | True | June 17 @ 2:39 AM EST | SpaceX is scheduled to launch AST SpaceMobile BlueBirds 8, 9, and 10 on Wednesday, June 17, at 2:39 AM EST from Cape Canaveral aboard a Falcon-9 rocket. |
| @aleabitoreddit | $GFS, $JBL, $SIVE | opinion | False | none | GFS, JBL, and other companies tied to SIVE are liked, but they are large and have less chance to triple, though Jabil would be a hedge fund pick. |
| @aleabitoreddit | $IREN, $BKKT | opinion | True | immediate/ongoing | Criticizing IREN or BKKT in the US leads to attacks from bots/influencers, which is a worldwide phenomenon related to jealousy and lies when one gains popularity. |
| @aleabitoreddit | $IREN | other | True | ongoing | The author does not engage in paid promotions, paid marketing, or accept outside gifts, and any online content suggesting otherwise is fabricated or a scam. |
| @aleabitoreddit | $NVDA, $JBL, $GFS, $AEVA, $POET | opinion | True | medium to long term | Sivers is a compelling photonics company, funded by the CHIPS Act, involved in major hyperscaler supply chains (NVDA, JBL, GFS), with potential future ramps with AEVA/POET and a US NASDAQ listing, while institutions are trying to buy up its float against retail investor interests. |
| @aleabitoreddit | $SIVE, $YSS, $MRVL | news | True | immediate and medium term | Sivers announced $8.2M volume orders for Space applications, implying it now powers a larger defense prime (YSS) which typically leads to more follow-up orders and volume contracts. |
| @aleabitoreddit | $JBL, $SIVE, $INTC, $AAOI | opinion | True | medium to long term | JBL is a compelling long idea at $38B because markets have not yet priced in its 1.6T LRO pluggable transceiver business, with SIVE potentially being a bottleneck by H1 2027, and its supply chains are already established. |
| @aleabitoreddit | $SIVE, $RPI | other | False | none | The author's priority is helping retail investors, and they are accustomed to media skirmishes, continuing to share ideas as long as retail followers benefit. |
| @aleabitoreddit | $GOOGL, $MSFT, $AXTI | opinion | True | long term | The author hopes their picks, like LeaderDrive, will demonstrate that certain equities can be good long-term holds, citing Innolight's triple-digit gain, and their ideas are based on Western institutional research and US hyperscaler requirements, considering geopolitical tensions. |
| @venu_7_ | $NVDA | opinion | False | none | NVIDIA is still the dominant company in its sector. |
| @venu_7_ | $NVDA | opinion | False | none | NVIDIA is one of the greatest profit-generating companies Wall Street has ever seen. |
| @amitisinvesting | $NVDA, $INTC, $AAPL, $TSLA, $MSFT, $AMZN, $MU, $GOOGL, $META, $NOK, $AMD, $NFLX, $HOOD, $PLTR, $F, $GLW, $SPCX, $SNDK | news | True | medium to long term | NVIDIA CEO Jensen Huang stated that NVIDIA is at the beginning of the AI supercycle, market weakness is a buying opportunity, and AI will become global infrastructure. |
| @aleabitoreddit | $INHD | question | False | none | none |
| @aleabitoreddit | $RDDT | opinion | True | short to medium term | Jim Cramer's recommendations are inversely correlated with stock performance, as evidenced by Reddit's flat performance despite Cramer's bullish stance since February, while the author has been bullish since $140. |
| @aleabitoreddit | $EWY | opinion | True | past event | Bank of America's past negative call on Korean memory equities (EWY/KOSPI) in March, which was followed by a rally after retail investors sold, suggests that institutional advice can be misleading and work against retail interests. |
| @spacanpanman | $ASTS | opinion | True | ongoing/future | Starlink is pursuing direct-to-consumer mobile services globally, which explains why MNOs are partnering with AST SpaceMobile, highlighting AST SpaceMobile's strategic value as the only true space-based cellular broadband solution. |
| @spacanpanman | $ASTS, $SPCX | news | True | next 2 years | SpaceX CFO Bret Johnsen discussed plans for Starlink Mobile to roll out globally within the next two years, competing with MNOs by attacking terrestrial markets from space, making comparable solutions 'table stakes' in a $1.6 trillion TAM. |
| @venu_7_ | $TSLA | opinion | False | none | Tesla's stock still looks good to the author. |
| @venu_7_ | $FROG | opinion | True | ongoing | While many focus on AI agents, few recognize the importance of the infrastructure managing them, which is where FROG plays a role. |
| @amitisinvesting | $AAPL, $GOOGL, $NVDA | news | True | immediate/ongoing | Apple, Google, and NVIDIA are collaborating to enhance Apple's AI capabilities, with Apple's Private Cloud Compute utilizing Google Cloud infrastructure and its largest AI model, AFM Cloud Pro, running on Google Cloud. |
| @amitisinvesting | $F | news | True | past event | Robinhood provided millions of new users with a free share of Ford (F) between 2018-2020, leading many to hold the stock. |
| @amitisinvesting | $AMD, $NFLX, $HOOD, $META, $GOOGL, $AMZN, $MSFT, $NVDA, $PLTR, $F, $TSLA | news | True | immediate and past | AMD has replaced Netflix in Robinhood's top 10 most held investments for June, reflecting its 118% YTD gain and status as a significant winner for retail investors. |
| @venu_7_ | $KEEL | prediction | True | medium term | KEEL is forming a 'monster cup' technical pattern, indicating it could become a new small-cap leader. |
| @amitisinvesting | $MRVL | opinion | True | past event | Jensen (presumably Jensen Huang) did not predict a $1 trillion valuation for the current topic, unlike his past prediction for Marvell (MRVL). |
| @spacanpanman | $TE | prediction | True | long term | A Section 232 ruling on polysilicon and solar derivatives is expected by late June 2026, with potential tariffs effective in early July, which could significantly benefit T1 Energy by raising the value of US-made solar supply and becoming a major 2026 EBITDA catalyst. |
| @venu_7_ | $MU | prediction | True | medium term | People are underestimating Micron's operating profit, as it is expected to generate approximately $155 billion in operating profit over the next five quarters, potentially becoming a $1 trillion company. |
| @venu_7_ | $LLY, $MRK, $UNH, $JNJ | opinion | False | none | As the AI investment theme becomes crowded, legacy healthcare companies like LLY, MRK, UNH, and JNJ are worth watching as alternative investment options. |
| @spacanpanman | $SPCX | news | True | immediate | SpaceX's initial public offering is reportedly well oversubscribed, with institutional investor orders closing on Wednesday, indicating high demand for a potentially record-setting debut. |
| @venu_7_ | $STM | prediction | True | short term | STM appears ready for its next upward movement in stock price. |
| @kaizen_investor | $PL, $GOOGL | opinion | True | ongoing | Planet's partnership with Google is a significant bullish advantage, as its entire operational pipeline is built on Google Cloud Platform, addressing a major data storage hurdle for competitors. |
| @amitisinvesting | $QCOM | news | True | immediate | Jensen (presumably Jensen Huang) recommends buying Qualcomm (QCOM) stock. |
| @spacanpanman | $ASTS | opinion | True | ongoing | Russia is capable of jamming GPS and China's BeiDou, making AST SpaceMobile's PNT (Positioning, Navigation, and Timing) capabilities critical for national security. |
| @amitisinvesting | $MU, $NVDA, $TSLA, $SNDK, $AMD | news | True | past event | Micron (MU), NVIDIA (NVDA), Tesla (TSLA), SanDisk (SNDK), and AMD experienced the largest retail single stock net inflows for the month of May. |
| @venu_7_ | $MRVL | prediction | True | short to medium term | Marvell (MRVL) exhibits characteristics of a William O'Neil High Tight Flag pattern, suggesting a potential for a significant upward movement if the pattern resolves higher. |
| @venu_7_ | $OSCR | prediction | True | short to medium term | OSCR has potential to reach $36. |
| @aleabitoreddit | $XFAB | opinion | False | none | XFAB is a European company that the author likes, believing the markets are currently underestimating it. |
| @spacanpanman | $ASTS, $TE | news | True | immediate/short term | The author covered their short ASTS calls and increased their position in TE, anticipating a strategic financing package for TE soon. |
| @spacanpanman | $CEPT, $SECZ | news | True | immediate | Securitized (CEPT) announced on 6/5 that its merger proxy is effective, with a vote date set for 6/29, after which it will trade as SECZ. |
| @venu_7_ | $JBHT, $VIAV | other | False | none | none |
| @venu_7_ | $SNOW | prediction | True | short to medium term | Snowflake (SNOW) is finding support at its 9-day EMA and PEG low, suggesting it is at the beginning of a Stage 2 advance, based on historical observations of PEG lows. |
| @aleabitoreddit | $MRVL, $ARM, $AAOI | opinion | True | past and medium to long term | Marvell (MRVL) and Arm (ARM) have seen significant price increases from their past levels, and the author believes other stocks like AAOI still have substantial room for growth. |
| @aleabitoreddit | $IBIT, $XLU, $META, $CRCL, $HOOD, $NBIS | opinion | True | past | Out of 30 mentioned stocks, only IBIT, XLU, META, and CRCL are down, with 1-2 flat like HOOD, while 25, including NBIS, are up, many by triple digits, which is solid on an equal-weighted basis. |
| @venu_7_ | $VSH, $STM, $FSLR | opinion | True | long term | VSH, STM, and FSLR are three companies with multi-decade bases, approaching Dot-Com and 2008 highs, and are significant players in robotics, edge AI/industrial semis, and the power revolution, respectively. |
| @spacanpanman | $TE | news | True | immediate and future | Microsoft announced land acquisition in Vaasa, Finland for a data center, and previously took over the Stargate 230MW Data Center project from OpenAI near T1 Energy's facility, which will be monetized. |
| @aleabitoreddit | $MRVL, $ARM, $INTC | opinion | False | none | The author's previous list of US equities, including Marvell (MRVL), Arm (ARM), and Intel (INTC), was excellent, serving as a recap of their preferred US stocks. |
| @kaizen_investor | $WOLF | news | True | ongoing | NVIDIA's new 800V HVDC architecture for next-generation AI factories requires SiC technology to address the bottleneck of power delivery from the utility grid to data centers, as detailed in a WOLF white paper. |
| @aleabitoreddit | $SIVE, $GFS, $JBL, $NVDA, $MRVL, $AMD | opinion | True | ongoing/medium term | Sivers (SIVE) is a very compelling long idea due to its involvement as a reference laser for GFS, its 1.6T LRO laser with JBL and other pluggable players, and its likely integration with Ayar/NVIDIA NVLink, Lightmatter/Marvell Celestial/NVIDIA NVLink, and AMD CPO ecosystem. |
| @aleabitoreddit | $SIVE | news | True | immediate | The recent development is primarily new news of US institutional accumulation of over 5% of the company (SIVE), possibly by JPM asset management or hedge funds using JPM, due to US retail's lack of synthetic exposure to SIVE. |
| @aleabitoreddit | $SIVE | prediction | True | Short to medium term | The implications of JP Morgan buying over 5.25% of SIVE are greater than perceived, signaling further institutional interest and potential for a short squeeze. |
| @aleabitoreddit | $NVDA | other | False | none | none |
| @kaizen_investor | $PL | opinion | False | none | none |
| @aleabitoreddit | $SIVE | opinion | True | Short to medium term | JP Morgan's 5%+ ownership of Sivers is the first major signal of institutional buying, and the current 3.36% price increase is surprisingly low given this news. |
| @aleabitoreddit | $IFNNY, $ON, $VICR, $LFUS, $VSH, $ENPH, $NVTS, $POWI, $BDC, $EOSE, $SEDG, $AEHR, $WOLF, $CWR, $AMSC, $XFAB, $AOSL, $HYLN, $FCEL, $IQE, $ASYS, $RELL, $PAY, $IPWR, $POET | other | False | none | none |
| @aleabitoreddit | $TSLA, $VPG | opinion | True | Medium to long term | LeaderDrive (688017) is China's standout component leader in the robotics sector due to its unique position, high technology barriers, and ability to capture high value. |
| @spacanpanman | $BAER | promotion | True | Medium term | Bridger Aerospace ($BAER) is undervalued and will be rerated higher to a $5 price target. |
| @aleabitoreddit | $MRVL | opinion | True | Long term | LeaderDrive (688017) holds a dominant position in global supply chains for robotics components and is currently very undervalued long term. |
| @spacanpanman | $ASTS | other | False | none | none |
| @kawzinvests | $NVDA | other | False | none | none |
| @amitisinvesting | $SPCX | news | True | Short term | SpaceX's IPO ($SPCX) is already 2x oversubscribed. |
| @amitisinvesting | $QQQ, $SPCX, $AVGO, $META | opinion | True | Short term | The -4% drop in Nasdaq ($QQQ) last Friday was likely due to a strong jobs report reducing the chances of a rate cut, leading to concerns about inflation. |
| @michaelsikand | $MRVL | news | True | Short term | The 'Inverse Cramer' portfolio, followed by over 20,000 Americans, has seen a 246% gain on its $MRVL position since Cramer's bearish call. |
| @kaizen_investor | $PL | opinion | True | Long term | Planet ($PL) possesses a unique competitive moat that other companies lack. |
| @kaizen_investor | $PL | other | False | none | none |
| @kawzinvests | $VRT, $PWR | opinion | True | Medium term | $VRT and $PWR are foundational 'picks and shovels' companies within their respective industries. |
| @kawzinvests | $STM | prediction | True | Medium term | $STM holders will benefit significantly when Kyber ramps up. |
| @kawzinvests | $NVDA, $IFX, $MPWR, $VICR, $NVTS, $STM, $ON, $TXN, $ADI, $POWI, $DIOD, $WOLF, $AOSL | news | True | Medium term | NVIDIA's Rubin Ultra architecture in 2027 will necessitate a fundamental change in power system design due to the increased power demands of 576 GPU dies per rack. |
| @aleabitoreddit | $NVDA, $SIVE, $SOI | opinion | True | Medium to long term | NVIDIA CEO's comments on requiring 'supply volumes beyond imagination' for Silicon Photonics (SiPH) are a bullish signal for the SiPH supply chain, including companies like $SIVE and $SOI. |
| @aleabitoreddit | $NVDA, $MU, $EWY | opinion | True | Long term | NVIDIA CEO's warning of a multi-year memory shortage due to AI demand suggests that current operating profit projections for memory companies like $MU and those represented by $EWY (Samsung/SK Hynix) may not be overly optimistic. |
| @kaizen_investor | $PL | other | False | none | none |
| @aleabitoreddit | $AAOI, $SIVE, $IQE, $MTSI, $IREN, $SLNH, $BKKT | opinion | True | Medium to long term | Dilution can be accretive if structured for strategic growth (e.g., $AAOI for fab capacity, $SIVE for M&A) or debt reduction (e.g., $IQE, $MTSI), but can be detrimental if excessive and used for continuous selling (e.g., $IREN). |
| @aleabitoreddit | $IREN, $NBIS, $NVDA, $CRWV, $SLNH, $BKKT, $SNAP | opinion | True | Medium to long term | Toxic financing structures and float dynamics, such as excessive dilution ($IREN) or high-interest debt ($CRWV), are detrimental, while optimal structures ($NBIS) lead to strong performance. |
| @aleabitoreddit | $AXTI, $RPI, $SIVE, $IQE, $LITE, $XFAB, $NVDA, $TSEM, $AAOI, $JBL, $TSM, $INTC, $MRVL | opinion | True | Long term | The investor's personal style involves discretionary investing based on identifying unstructured relationships and market unknowns, exemplified by the unexpected AI growth potential of Raspberry Pis ($RPI). |
| @aleabitoreddit | $TSM | opinion | True | Long term | Investing in $TSM is likely to yield a better return on investment than owning a depreciating car. |
| @aleabitoreddit | $AMAT, $AMD, $AVGO, $INTC, $TSM, $SHMD, $LPK | news | True | Medium to long term | Key timelines for glass substrate adoption are H2 2026 for SKC Absolics (AMD customers) and H2 2027 for Samsung Electromechanics (Apple/AVGO/hyperscalers), with $TSM's CoWoS timeline proving accurate. |
| @kawzinvests | $NVDA | news | True | Medium term | NVIDIA's Rubin Ultra AI Factory rack will feature a 31x increase in power semiconductor value compared to Hopper racks, driven by a complete architectural overhaul to manage significantly higher power demands. |
| @michaelsikand | $SIVE, $LITE | opinion | True | Long term | The most asymmetric returns in the AI era will come from launching ventures with minimal resources, rather than from stock investments like $SIVE or $LITE. |
| @kaizen_investor | $PL, $WOLF, $OUST | other | False | none | none |
| @kaizen_investor | $PL, $PLTR, $MRVL | opinion | True | Long term | Despite personal investment setbacks, individuals today have advantages like AI for research and access to knowledgeable people, making it easier to build investment conviction. |
| @aleabitoreddit | $SIVE, $AAOI | other | True | Short term | The user generates significant impressions, uses profits from stock investments like $SIVE and $AAOI for dog rescues, and avoids monetizing followers through paywalls or ads. |
| @spacanpanman | $ASTS | opinion | True | Medium term | $ASTS possesses a compelling dual-use case. |
| @aleabitoreddit | $XFAB | prediction | True | Long term | $XFAB, as a de-risked foundry, has compelling upside potential from CPO if they successfully execute their plans in H2 2027/2028, representing an opportunity to frontrun institutions. |
| @aleabitoreddit | $XFAB, $TSEM, $ASX, $NVDA, $NOK | prediction | True | Long term | $XFAB has the potential to become the next $TSEM, positioned to compete for the H2 2027 CPO scale-up inflection point with its next-gen integration IP, despite current yield challenges. |
| @aleabitoreddit | $NOK, $NVDA | other | False | none | none |
| @aleabitoreddit | $RDDT, $AAOI, $MRVL | opinion | True | Medium to long term | Short-term timing can significantly impact returns, and holding high-beta individual stocks like $AAOI or $MRVL for longer periods can be more effective than reacting to short-term drops. |
| @spacanpanman | $ASTS | opinion | True | Short to medium term | $ASTS is relevant to the Space Development Agency (SDA). |
| @aleabitoreddit | $SIVE | prediction | True | Short to medium term | Swedish hedge funds should not short $SIVE because US institutions and hyperscalers can easily acquire its float due to its importance in photonics. |
| @aleabitoreddit | $SIVE | opinion | True | Short term | US institutions are attempting to acquire $SIVE shares, and JP Morgan's 5%+ stake may have resulted from retail investor capitulation. |
| @aleabitoreddit | $SIVE | news | True | Short term | Despite warnings about $SIVE's importance to CPO, retail investors were shaken out, allowing JP Morgan to significantly increase its institutional stake from 0.4% to over 5% in one month. |
| @venu_7_ | $MRVL | opinion | False | none | none |
| @venu_7_ | $FROG, $DDOG, $PANW | opinion | True | Short to medium term | Software and cybersecurity stocks like $FROG, $DDOG, and $PANW are showing relative strength and accumulation, making them better investment focuses than weaker stocks below their 200-day SMA. |
| @venu_7_ | $QQQ | prediction | True | Short to medium term | Software, cybersecurity, data infrastructure, and Agentic AI stocks are showing relative strength and institutional accumulation, indicating they could lead the next market rally. |
| @michaelsikand | $COKE | other | False | none | none |
| @spacanpanman | $SPCX | news | True | Medium term | SpaceX ($SPCX) is acquiring more AI data center customers, which will support its IPO valuation. |
| @amitisinvesting | $META, $GOOGL, $MSFT, $AMZN | news | True | Short to medium term | Financial Times reports that $META is considering a multi-billion dollar share sale, suggesting a new paradigm where other 'Magnificent 7' companies like $MSFT and $AMZN may also issue new equity to fund AI buildouts. |
| @amitisinvesting | $PLTR | opinion | True | Medium term | $PLTR FDEs are perceived as more genuinely focused on delivering value to customers compared to LLM companies, a sentiment widely shared among industry professionals. |
| @venu_7_ | $QQQ | prediction | True | Short term | The anchored VWAP from April 29th is a critical support level for $QQQ, and if the 21-day EMA is lost, this VWAP could serve as the next key area for buyers. |
| @aleabitoreddit | $NVDA, $GOOGL, $AMZN, $MRVL, $LITE, $COHR, $INTC | opinion | True | Long term | Upstream chokepoint companies are preferable to $NVDA long-term because they have greater re-rating potential, and hyperscaler ASICs will eventually siphon off $NVDA demand, impacting its exponential revenue growth. |
| @aleabitoreddit | $NVDA, $MU, $PL, $AAOI | opinion | True | Short term | Recent market corrections, including drops in $NVDA, $MU, and $PL, are primarily driven by increased rate hike probabilities, not by media-fabricated narratives like Broadcom casting a shadow over chip stocks, as the AI buildout remains unchanged. |
| @spacanpanman | $PL | opinion | False | none | none |
| @spacanpanman | $PL, $RKLB | opinion | True | short-term to medium-term | Planet Labs' $1.5B At-The-Market (ATM) offering is too aggressive given its market cap, implying excessive dilution. |
| @spacanpanman | $SPCX | question | True | short-term | Investors selling positions to participate in the $SPCX IPO will have excess capital if they only receive a small allocation. |
| @aleabitoreddit | $TSM | opinion | True | medium-term to long-term | Xintec is an interesting investment idea due to its potential to benefit from $TSM's vertical integration and CPO opportunities, despite limited public data. |
| @aleabitoreddit | $SIVE | opinion | True | short-term to medium-term | The founding co-manager of a hedge fund quitting is a strong indicator that the firm is failing due to $SIVE's stock performance. |
| @aleabitoreddit | $SIVE | opinion | True | short-term to medium-term | The hedge fund is likely failing due to its year-to-date -31.02% performance, attributed to $SIVE. |
| @venu_7_ | $FROG | opinion | True | medium-term to long-term | JFrog ($FROG) is becoming a crucial component of the Agentic AI stack, showing strong fundamental growth while its stock price is only now approaching 2021 highs, suggesting potential for further appreciation. |
| @aleabitoreddit | $SIVE, $AAOI, $TSM, $NVDA, $TSEM, $SOI | opinion | False | none | The author lists several companies, including $SIVE and $AAOI, that they generally favor due to their involvement in CPO, photonics, and related technologies. |
| @aleabitoreddit | $AAOI | opinion | False | none | $AAOI has primary exposure to pluggable technology but also significant exposure to CPO, and FOCI is the author's second favorite pure-play CPO exposure. |
| @aleabitoreddit | $JBL, $SIVE, $NVDA | prediction | True | medium-term | 1.6T pluggable players like $JBL will be relevant in H1 2027, and main CPO scale-up applications from $NVDA's NVLink CPO ecosystem players like Ayar will be relevant in H2 2027. |
| @venu_7_ | $CRDO | opinion | True | short-term to medium-term | Credo ($CRDO) is showing technical strength and fundamental relevance, suggesting potential for continued positive performance as AI clusters grow. |
| @aleabitoreddit | $SIVE, $GFS, $JBL | opinion | True | medium-term to long-term | $SIVE is a favored CPO/photonics stock, and a hedge fund's claim that its CPO applications are imaginary is refuted by $GFS making $SIVE its reference laser, highlighting a misunderstanding of forward growth by some Swedish investors. |
| @venu_7_ | $QQQ | prediction | True | short-term | The Nasdaq ($QQQ) is in a strong uptrend, and a potential test of its 21-day EMA or a mini flag/base formation would be a healthy consolidation before a further move higher, contrary to bearish sentiment. |
| @spacanpanman | $ASTS, $TE | opinion | True | short-term to medium-term | The author is adding to positions in $ASTS and $TE, expecting upside. |
| @kaizen_investor | $PL | opinion | True | short-term to medium-term | Planet Labs' ($PL) $1.5B ATM announcement, despite analyst price target raises and a strong balance sheet, is surprising and painful for current shareholders but could be an entry point for new investors, as the company is aggressively pursuing AI. |
| @spacanpanman | $ASTS | news | True | short-term | Short sellers in $ASTS are steadily covering their positions, with approximately 20 million shares remaining to be covered to reach February/March levels. |
| @aleabitoreddit | $GOOGL | opinion | False | none | Technical analysis is often meaningless, as fundamentals are the most important factor in stock performance. |
| @spacanpanman | $PL | news | False | none | Clear Street raised its price target for Planet Labs ($PL) to $53 from $34 and maintained a Buy rating, citing strong Q1F27 results and the company's position as a key beneficiary of AI due to its proprietary data. |
| @spacanpanman | $MRLN | news | False | none | Real-time short interest for $MRLN is 4.9 million shares with a 37% borrow fee as of June 4th. |
| @spacanpanman | $PL | news | False | none | Multiple research firms have upgraded their price targets for Planet Labs ($PL) following strong Q1 results that exceeded revenue and earnings estimates, with Needham specifically citing robust growth in the Defense & Intelligence segment. |
| @spacanpanman | $SPCX | news | True | long-term | Morgan Stanley projects SpaceX's revenue could reach $3.4 trillion by 2040, supporting its target IPO valuation, with xAI expected to ramp growth, possibly through leasing data center capacity. |
| @spacanpanman | $ASTS, $RKLB, $PL, $SPACE | other | False | none | The author plans to take notes or record information related to $ASTS, $RKLB, $PL, and $SPACE. |
| @spacanpanman | $AUR | news | False | none | Craig Hallum initiated research coverage of Aurora Innovation ($AUR) with a Buy rating and an $18 price target. |
| @spacanpanman | $RKLB | news | False | none | Stifel raised Rocket Lab's ($RKLB) price target to $132 from $110 and maintained a Buy rating on June 4th. |
| @aleabitoreddit | $AAOI, $JBL, $SIVE, $RDDT, $MRVL | opinion | True | medium-term | $AAOI is the author's favorite US long, and they expect $JBL to perform well once its 1.6T LRO goes into mass production with $SIVE in H1 2027. |
| @aleabitoreddit | $XFAB, $NVDA, $NOK, $TSEM | opinion | True | long-term | $XFAB's silicon photonics platform with $NVDA and $NOK is expected to scale in H2 2027/2028, making it a derisked precommercial long with potential to be the next $TSEM, offering upside from SiC/GaN. |
| @aleabitoreddit | $SOI, $RPI, $SIVE | opinion | False | none | The author's opponents consistently challenge their views on stocks like $SOI, $RPI, and $SIVE, only to be repeatedly proven wrong. |
| @zephyr_z9 | $TTM | news | True | medium-term to long-term | The "Protecting Circuit Boards and Substrates Act" in the U.S. Congress, offering a 25% tax credit and $3 billion in subsidies for domestic PCB manufacturing, is beneficial for companies like $TTM Technologies and Sanmina, which are expanding U.S. capacity. |
| @aleabitoreddit | $RPI | opinion | False | none | $RPI's stock price increased significantly (247%) since the author's thesis post, demonstrating that the company, previously labeled a "memestock" with no fundamentals, was actually supported by strong AI-related revenue growth. |
| @spacanpanman | $TE | prediction | True | short-term to medium-term | Santander, JP Morgan, HSBC, and Societe Generale, having worked on T1 Energy's ($TE) April convert, are expected to initiate research coverage in the coming weeks/months, adding to existing coverage by BTIG, Roth, and Johnson Rice. |
| @spacanpanman | $MRLN | prediction | True | short-term to medium-term | TD Cowen initiated coverage on $MRLN with a Buy rating and $11 price target, and Roth Capital has a Buy rating with a $15 price target, with a good chance both will raise their targets upon completion of USSOCOM CDR. |
| @spacanpanman | $TE, $NXT | opinion | True | medium-term | T1 Energy's ($TE) acquisition of KORE NRI for $41.6M, contributing $15-20M to 2027 EBITDA at a 2.4x multiple, is a financially smarter and more strategic deal compared to $NXT Nextpower's acquisition of Prevalon at a 6.6x multiple. |
| @aleabitoreddit | $AAOI, $AMD, $NVDA, $LITE | opinion | True | short-term to medium-term | $AAOI is expected to double or triple in value if it executes well, driven by high demand for 800g/1.6T optical transceivers and its focus on large capacity and vertical integration, further supported by demand from sovereign and T2 AI data centers. |
| @spacanpanman | $MRLN | other | False | none | none |
| @spacanpanman | $MRLN | news | False | none | Ryan O'Connor from Crossroads Capital will discuss Merlin's ($MRLN) US Special Operations Command CDR Approval on June 5th at 1 PM ET. |
| @michaelsikand | $DELL, $MRVL | question | True | none | There is a $3.6 billion entity that works with both $DELL and $MRVL, which are favored by Trump and Jensen, respectively. |
| @michaelsikand | $RCAT | opinion | True | short-term to medium-term | The author is unsure if $RCAT will become the next trending stock. |
| @michaelsikand | $PENG | opinion | False | none | $PENG continues to be popular and widely discussed, having performed exceptionally well. |
| @spacanpanman | $MRLN | question | True | short-term | The author questions if $MRLN's stock price will return to the $15-17 range. |
| @kaizen_investor | $PL | other | False | none | The author finished the $PL earnings call, found many ongoing projects, and plans to create a detailed thread or article tomorrow to explain the updates, noting it was another strong quarter. |
| @speculator_io | $SNDK, $RXT, $HYLN, $WOLF, $DOCN, $DELL, $VPG, $BE, $STRL, $AMBQ, $INTC, $SILC, $HIMX, $HUT, $FLEX | opinion | False | none | Identifying stocks with blowout earnings, such as the listed Q1 winners, is an effective strategy for finding future successful investments. |
| @spacanpanman | $MRLN | news | False | none | Real-time short interest for $MRLN is at an all-time high, accompanied by a high borrow rate. |
| @spacanpanman | $MRLN | other | False | none | none |
| @kaizen_investor | $PL | prediction | True | short-term | Despite $PL being down 8% after reporting a record quarter with a double beat, gross profit margin beat, and raised guidance, the author expects the stock to be up tomorrow due to strong execution, massive revenue beat, and increased backlog. |
| @michaelsikand | $KRKNF, $AVAV, $KTOS, $AVEX, $LASR, $EOS | other | False | none | The author's trading, particularly an investment in $KRKNF (a subsea drone stock that doubled due to a mispriced connection with Anduril), attracted attention from NYMag for an article on the "drone stock bubble" and its appeal to young male retail investors. |
| @spacanpanman | $ASTS | opinion | False | none | none |
| @spacanpanman | $TE | news | True | long-term | BloombergNEF predicts that solar power will become the largest source of global electricity generation by 2032, surpassing coal, despite a minor dip in installations in 2026, due to its cost-effectiveness. |
| @venu_7_ | $FSLR, $ENPH, $SEDG, $NXT | other | False | none | none |
| @spacanpanman | $BAER | other | False | none | The author encourages continued positive performance for $BAER and provides a link to an updated June 2026 presentation. |
| @spacanpanman | $TE | news | False | none | The increasing scarcity of compute power, exemplified by Jane Street's plans for a new data center, highlights a critical need for power solutions, implying an opportunity for companies like $TE. |
| @amitisinvesting | $CRWD, $SPCX | opinion | True | short-term | The S&P's recent red close felt healthy despite chaos, and future market direction depends on bull resilience, with high valuations, oil prices, and the SpaceX IPO being contributing factors. |
| @kawzinvests | $BRUN | prediction | True | soon | $BRUN will recover soon because its recent dip was due to a mechanical event, not a fundamental thesis issue. |
| @michaelsikand | $BRUN, $SGOV | opinion | True | this week (~June 5-9) | There is a significant lock-up expiry risk for $BRUN this week, potentially releasing a large number of shares, leading to a decision to sell for now. |
| @kawzinvests | $BRUN, $CRWV | opinion | True | this week (~June 5-9) for trigger, 30-60 days for price impact | Selling $BRUN due to an impending lock-up expiry risk this week, which could release a large number of shares and historically leads to significant stock price drops for de-SPAC companies. |
| @spacanpanman | $ASTS, $T | news | True | long-term | Oppenheimer warns that investors are underestimating the disruptive risk posed by SpaceX's satellite ambitions to traditional telecommunications companies like AT&T. |
| @spacanpanman | $CSIQ | opinion | False | none | $CSIQ has a high enterprise value of $8.7B due to $7.8B in debt and $1.4B in minority interest. |
| @michaelsikand | $NOK, $SIVE, $MXL | news | True | medium-term | Northland's analyst Tim Savageux, known for accurately predicting photonics trends, has raised his price target for $NOK to $20. |
| @michaelsikand | $NBIS, $BRUN, $NVDA | opinion | True | FY26 | $NBIS is a strong company, evidenced by its contract with $BRUN, exemplar status with $NVDA, and projected 1,233% ARR expansion to over $400M by FY26. |
| @spacanpanman | $ASTS | other | False | none | none |
| @michaelsikand | $AAOI | opinion | True | long-term | $AAOI's CEO, Dr. Thompson Lin, is strategically positioning the company to become the 'Intel of Optics' through significant investments like onshore laser fabs, driven by his ambition to become a billionaire. |
| @spacanpanman | $ASTS | prediction | True | short-term | Reloading $ASTS due to potential upside ahead of the target date announcement for the SpaceX Falcon-9 launch of BlueBird 8, 9, and 10. |
| @spacanpanman | $ASTS, $T | opinion | True | medium-term | Oppenheimer downgraded AT&T due to Starlink's competition in fixed wireless, but the analyst's note is incorrect regarding mobile competition, as AT&T, Verizon, and T-Mobile are partners with AST SpaceMobile, not competitors. |
| @kawzinvests | $BRUN, $NVDA, $DELL, $CRWV, $NBIS, $APLD | opinion | True | FY26 year-end | $BRUN is projecting massive ARR growth to over $400M by FY26, supported by a rapidly increasing Total Contract Value (TCV) and strong partnerships with key suppliers and verified customers. |
| @kaizen_investor | $PL, $RKLB, $SATL, $ASTS, $FLY, $LUNR | opinion | True | medium-term | Despite recent drops, several space stocks have reached new highs in institutional ownership, indicating that the SpaceX IPO will boost the entire space sector rather than hinder other companies. |
| @spacanpanman | $TE | prediction | True | month end | T1 Energy ($TE) will close above $15 by the end of the month. |
| @aleabitoreddit | $SOI, $SIVE | opinion | True | long-term | Europe cannot compete with the US in the AI race but can strengthen its position by focusing on niche monopolies and supply chain resilience, recognizing the critical role of companies like $SOI and $SIVE in photonics for AI data centers. |
| @spacanpanman | $WLAC, $BRUN, $BCAR, $BCARW | opinion | True | Q3 for deal close, medium-term for Exascale's performance | Building a position in $BCAR, a SPAC merging with Exascale, an Asia/Pacific GPU-as-a-service provider, with the deal now expected to close in Q3. |
| @aleabitoreddit | $SIVE, $XFAB, $SOI | news | True | long-term | The EU CHIPS Act 2.0 proposal includes photonics as a new structural addition, which is thematically bullish for the EU photonics sector. |
| @spacanpanman | $HAWK | opinion | True | short-term for the bounce, medium-term for PT | Picked up $HAWK for a post-IPO pullback bounce, supported by research analysts initiating coverage with an average $39 price target. |
| @spacanpanman | $TE | prediction | True | short-term to medium-term | The seller of T1 Energy ($TE) warrants yesterday will regret their decision. |
| @spacanpanman | $SRTA | news | False | none | Strata ($SRTA) completed a highly accretive acquisition of Louisville Perfusion Services for $16M upfront plus $4M earnout, adding $10M revenue and $3M EBITDA, boosting pro forma EBITDA by ~10%. |
| @aleabitoreddit | $XFAB | news | False | none | The EU CHIPS Act 2.0, which includes photonics, has just been published, and $XFAB is mentioned in some related reports. |
| @spacanpanman | $TE | news | False | none | none |
| @aleabitoreddit | $XFAB | question | True | short-term | $XFAB's 7% rise might be linked to mentions in recent transcripts, which are currently being reviewed. |
| @aleabitoreddit | $POET, $XFAB, $NVDA, $NOK, $NVTS, $POWI | opinion | True | 2027/2028 | $XFAB, with a lower market cap than $POET, is a superior investment due to its diverse foundry capabilities, backing from EU/US CHIPS Acts, direct evaluations from major players like $NVDA and $NOK, and its role in scaling Europe's photonic supply chains, with volume ramping in 2027/2028. |
| @spacanpanman | $TE | opinion | True | short-term | Buying $TE premarket due to the KORE NRI acquisition. |
| @spacanpanman | $TE | opinion | False | none | T1 Energy's ($TE) recent M&A hire and Peter Matrai's contract extension now make sense in light of recent events. |
| @spacanpanman | $TE | news | True | end of the year for cell production, medium-term for price target | Northland Securities initiated coverage on T1 Energy ($TE) with an Outperform rating and a $16 price target, highlighting its role in establishing a US solar supply chain and its competitive advantage from domestic content bonuses. |
| @spacanpanman | $TE | opinion | True | medium-term | T1 Energy's ($TE) acquisition of KORE Power's NRI division for $32M is a highly accretive and game-changing strategic fit, enabling T1 Energy to offer end-to-end solar + battery solutions. |
| @aleabitoreddit | $NBIS | opinion | False | none | none |
| @aleabitoreddit | $NVDA, $MRVL | opinion | True | medium-term | While an $NVDA partnership with $MRVL was unexpected, Marvell was already considered a compelling investment due to its upcoming ASIC/connectivity revenue opportunities. |
| @aleabitoreddit | $CRWV, $IREN, $NBIS | opinion | True | medium-term | $NBIS is a superior investment compared to $CRWV and $IREN due to its favorable financing structure, sum-of-parts valuation from subsidiaries, and lack of excessive debt or equity dilution. |
| @aleabitoreddit | $NBIS, $IREN, $CRWV | opinion | False | none | The Neocloud sector has become a major theme, and $NBIS, identified as the top pick, has validated this thesis with its significant stock price increase from $84 to $260. |
| @aleabitoreddit | $SIVE, $JBL | prediction | True | over time | Short sellers of $SIVE will eventually be 'wrecked' as the company is co-developing with more pluggable transceiver partners and is likely to make further positive announcements. |
| @aleabitoreddit | $NVDA, $SIVE | opinion | True | medium-term | $SIVE appears to be the laser supplier to all ASIC/merchant NVLink CPO ecosystem partners, distinct from $NVDA's direct involvement. |
| @aleabitoreddit | $NVDA, $AMD, $GFS, $SIVE, $INTC, $GOOGL | prediction | True | soon | Based on investments in Ayar by $NVDA, $AMD, Mediatek, and $INTC, and $SIVE's connection through Ayar, it is likely that $SIVE will soon announce involvement in $GOOGL's supply chains. |
| @aleabitoreddit | $SIVE, $NVDA, $LITE, $COHR | opinion | True | gen-1 | While Celestial and Lightmatter are expected to multi-source, $SIVE is likely the sole or primary laser source for the first generation of the $NVDA CPO NVLink ecosystem, despite Nvidia's direct programs with $LITE and $COHR. |
| @aleabitoreddit | $SIVE | prediction | True | medium-term | $SIVE is undervalued at its current Swedish exchange listing, and a NASDAQ listing would likely close the valuation gap, potentially leading to a $6-8B market capitalization. |
| @aleabitoreddit | $NVDA, $MRVL, $SIVE, $GFS | opinion | True | short-term | $SIVE is the laser supplier to the entire $NVDA NVLink CPO ecosystem, including $MRVL, Lightmatter, and Ayar, with Ayar's recent joining providing the clearest confirmation of $SIVE's connection to $NVDA. |
| @aleabitoreddit | $SIVE | opinion | True | medium-term | With Ayar joining Nvidia's NVLink fusion, $SIVE is now likely the laser source for the entire Nvidia NVLink CPO supply chain ecosystem, establishing itself as a structural photonics laser chokepoint. |
| @aleabitoreddit | $NVDA | opinion | True | medium-term | Extremely transformative news released today positions a specific photonics company as the effective upstream laser chokepoint for the $NVDA NVLink fusion CPO ecosystem, with its lasers now in Nvidia's optical infrastructure supply chains. |
| @aleabitoreddit | $EWY | opinion | False | none | My investment thesis on memory, developed earlier this year, is being validated by market performance, similar to the 480% gain on $EWY longs. |
| @aleabitoreddit | $SIVE | news | True | short-term | There is even more significant news for $SIVE today than the EU CHIPS Act policy framework announcements. |
| @aleabitoreddit | $SOI, $NOK, $SIVE, $XFAB | opinion | True | medium to long-term | The EU CHIPS Act proposals, offering €30-500M in funding and incentives, are better suited for pre-volume production players like $SIVE and $XFAB than for established companies like $SOI and $NOK, aiming to bridge them to high-volume manufacturing. |
| @aleabitoreddit | $XFAB, $SIVE | news | True | medium to long-term | Europe's Tech Sovereignty Package, including CHIPS Act 2.0, will prioritize photonics and provide €30-500M in financing and incentives, making $XFAB and $SIVE large beneficiaries as they are highlighted in policy blueprints to bridge to volume production. |
| @amitisinvesting | $MRVL, $META, $NVDA, $TSLA, $AAPL, $MSFT, $GOOGL, $INTC, $NOK, $MSTR, $AMZN, $BTC, $PANW, $CRWV, $SPCX, $UBER, $GME, $SHOP | news | False | none | Today's stock market saw significant events, including $MRVL's 50% surge after Jensen Huang's 'next trillion-dollar company' comment, and OpenAI Codex reaching 5M+ weekly users with expanding applications. |
| @aleabitoreddit | $SIVE, $NVDA | opinion | True | medium-term | The news of $SIVE being the laser supplier to the $NVDA NVLink fusion ecosystem is significant, potentially leading to market cap growth similar to $MRVL's after its involvement. |
| @aleabitoreddit | $TSM | opinion | True | none | Xintech (3374) is likely the unknown $TSM COUPE supplier and is owned by TSMC. |
| @aleabitoreddit | $LPK | prediction | True | H1 2027 | Volume orders for glass core substrates with $LPK are expected in H1 2027, with no new developments until then. |
| @aleabitoreddit | $AEHR, $LPK | opinion | True | medium-term | $AEHR has performed well, reaching a ~$3.5B market cap, and the next significant catalyst for it and similar companies like $LPK will be volume orders. |
| @kawzinvests | $PENG, $AOSL, $ENAFF | opinion | False | none | none |
| @kawzinvests | $MX | opinion | False | none | none |
| @aleabitoreddit | $AAOI, $XFAB, $MRVL | news | False | none | none |
| @aleabitoreddit | $NVDA, $APH, $VRT, $STM | news | False | none | none |

## Run summary

- Gemini calls succeeded: **11**
- Gemini calls rate-limited (429): **0**
- Stage 1–2 are deterministic and always complete (no LLM).

_Read-only run. No database writes, no schema changes. Descriptive analysis only — not investment advice._

