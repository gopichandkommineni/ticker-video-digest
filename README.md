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

Not investment advice.
