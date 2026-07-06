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

## MCP server (chat over the dashboard data)

`casino_mcp` exposes `data/snapshots.db` and `data/fintwit.db` to any MCP
client (Claude Code / Claude Desktop) as seven read-only tools:
`resolve_ticker`, `get_snapshot`, `get_signals`, `get_sector_heat`,
`search_fintwit`, `get_congress_trades`, `get_news`. Every row carries
structural provenance (db, table, natural row key) for citations. SQLite is
opened with `mode=ro`, so the server can never write to production data.

```
# Register with Claude Code
claude mcp add casino-data -- \
    uv run --project /path/to/ticker-video-digest --extra mcp \
    python -m casino_mcp.server
```

Override database locations with `CASINO_SNAPSHOTS_DB` / `CASINO_FINTWIT_DB`.
Reference architecture: `docs/ai-research-layer-reference-v1.md` (§8).

Not investment advice.
