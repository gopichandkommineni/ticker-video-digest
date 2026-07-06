"""FastMCP server exposing the casino dashboard databases to an MCP client.

Register with Claude Code / Claude Desktop (stdio transport):

    claude mcp add casino-data -- \
        uv run --project /path/to/ticker-video-digest --extra mcp \
        python -m casino_mcp.server

Databases are opened read-only (SQLite mode=ro). Override paths with the
CASINO_SNAPSHOTS_DB / CASINO_FINTWIT_DB environment variables.
"""
from mcp.server.fastmcp import FastMCP

from casino_mcp import queries
from casino_mcp.models import (
    CongressTradesResult,
    FintwitSearchResult,
    NewsResult,
    ResolvedTicker,
    SectorHeatResult,
    SignalsResult,
    SnapshotResult,
)

mcp = FastMCP(
    "casino-data",
    instructions=(
        "Read-only access to a casino-coherent momentum equity dashboard: "
        "daily price snapshots, 18 derived signals, sector heat metrics, "
        "curated fintwit tweets, congressional trades, and per-ticker news. "
        "Call resolve_ticker first to map user input to a tracked ticker. "
        "Every row carries a `provenance` object (db, table, natural row key) "
        "— cite it when quoting figures. An empty result means the database "
        "has no such rows; that is different from data you did not request. "
        "Never invent figures that a tool did not return."
    ),
)


@mcp.tool()
def resolve_ticker(query: str) -> ResolvedTicker:
    """Resolve a ticker symbol against the tracked universe (themes.yaml +
    user-added tickers). Returns a typed status code: `ok`, `no_data_yet`
    (in universe, no rows yet), `not_in_universe` (rows exist but the ticker
    was dropped/never added), or `unknown_ticker`. Call this before other
    per-ticker tools."""
    return queries.resolve_ticker(query)


@mcp.tool()
def get_snapshot(ticker: str) -> SnapshotResult:
    """Latest daily OHLCV snapshot plus fundamentals metadata (52-week range,
    short interest, analyst targets, market cap, earnings dates) for one
    ticker. `snapshot`/`metadata` are null when the database has no rows."""
    return queries.get_snapshot(ticker)


@mcp.tool()
def get_signals(ticker: str) -> SignalsResult:
    """All derived momentum/social signals for a ticker on its most recent
    signal date (returns, RSI, ATR, volume ratio, breakout proximity,
    ApeWisdom mention velocity, ...). Values are precomputed by the daily
    refresh — read them, never recompute."""
    return queries.get_signals(ticker)


@mcp.tool()
def get_sector_heat(sector: str | None = None) -> SectorHeatResult:
    """Latest sector-level heat metrics (ETF flow ratio, 30d deal-log volume,
    social velocity, news heat, aggregate returns, % above SMA50) for one
    sector id, or all sectors when omitted."""
    return queries.get_sector_heat(sector)


@mcp.tool()
def search_fintwit(
    query: str | None = None,
    ticker: str | None = None,
    handle: str | None = None,
    days: int = 30,
    limit: int = 25,
) -> FintwitSearchResult:
    """Search tweets from ~30 curated fintwit accounts. Provide at least one
    of: `query` (substring of tweet text), `ticker` (matches $TICKER cashtags
    and ticker labels), `handle` (exact account handle). `days` bounds the
    lookback window. `truncated=true` means more rows matched than `limit`
    allowed — narrow the search or raise the limit (max 100)."""
    return queries.search_fintwit(query, ticker, handle, days, limit)


@mcp.tool()
def get_congress_trades(
    ticker: str | None = None,
    member: str | None = None,
    days: int = 180,
    limit: int = 50,
) -> CongressTradesResult:
    """Congressional STOCK Act trade disclosures, filtered by ticker and/or
    member name substring, within a disclosure-date lookback window. Amounts
    are disclosed ranges (amount_low/amount_high), not exact figures."""
    return queries.get_congress_trades(ticker, member, days, limit)


@mcp.tool()
def get_news(ticker: str, days: int = 14, limit: int = 25) -> NewsResult:
    """Recent news headlines for a ticker (title, publisher, link), newest
    first, filtered by publication date. Cite the link when quoting a
    headline."""
    return queries.get_news(ticker, days, limit)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
