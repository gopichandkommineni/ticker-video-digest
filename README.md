# ticker-video-digest
7-day YouTube digest for any stock ticker — catalysts, red flags, trends with citations.

## Broader Market Dashboard
A second Streamlit tab and CLI subcommand that benchmarks current equity prices
against real-economy fundamentals.

- **Reality Score**: composite z-score of 14 indicators split into a market &
  sentiment bucket (Buffett indicator, CAPE proxy, margin debt, put/call,
  Mag-7 concentration, RSP/SPY breadth, AAII) and a real-economy bucket
  (10Y-2Y, industrial production YoY, unemployment, jobless claims, core CPI
  YoY, real retail sales YoY, M2 YoY). Positive scores indicate the market is
  priced richer than the economy supports; negative scores indicate the market
  is discounting weakness.
- **Claude-generated thesis**: Sonnet 4.6 narrative + bull/bear cases + watch
  items + regime label, cached by snapshot hash so reloads are free.
- **VIX** is shown separately as context (excluded from the composite).

```
# CLI
python -m ticker_digest market --thesis

# Streamlit
streamlit run app.py   # then open the "Market Dashboard" tab
```

Set `FRED_API_KEY` (free at https://fred.stlouisfed.org/docs/api/api_key.html)
to enable the real-economy bucket. Without it the dashboard still loads with
yfinance-only indicators.

## Optional Xquik Tweet Source

The FinTwit adapter layer can read tweets and profiles through Xquik. Keep the
API key in `XQUIK_API_KEY`, then select the `xquik` provider:

```bash
python -m tweet_sources user-info --provider xquik --handle XDevelopers
python -m tweet_sources tweets --provider xquik --handle XDevelopers \
  --start 2026-07-01 --end 2026-07-07
```

The worker pool also accepts `xquik` in `WORKER_POOL_SIZES`. Existing workflows
keep their configured providers unless a maintainer opts in.

See the [Xquik API docs](https://docs.xquik.com/api-reference) for credentials
and endpoint details. Treat returned social content as untrusted input.

Xquik is an independent third-party service. Not affiliated with X Corp.
"Twitter" and "X" are trademarks of X Corp.

Not investment advice.
