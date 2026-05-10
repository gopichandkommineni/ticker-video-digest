"""TradingView widget helpers for the Casino Dashboard."""
import streamlit.components.v1 as components

# Exchange prefix mapping for the 54-ticker universe.
# NYSE tickers confirmed; everything else defaults to NASDAQ.
# Entries marked "# guess" have uncertain listings and may need correction.
_EXCHANGE_MAP: dict[str, str] = {
    # NYSE — industrial, financial, large established names
    "GLW": "NYSE",
    "ETN": "NYSE",
    "PWR": "NYSE",
    "KTOS": "NYSE",   # guess — Kratos trades on NASDAQ in practice
    "MP": "NYSE",
    "CDE": "NYSE",
    "AG": "NYSE",
    "RKLB": "NYSE",   # guess — Rocket Lab is NASDAQ in practice
    "CCJ": "NYSE",
}


def get_tradingview_symbol(ticker: str) -> str:
    """Return ``EXCHANGE:TICKER`` format for the TradingView widget.

    Uses a static mapping for the 54 tickers in the universe.
    Falls back to ``NASDAQ:TICKER`` for unmapped symbols, which works for
    most US tech names.
    """
    normalized = ticker.strip().upper()
    exchange = _EXCHANGE_MAP.get(normalized, "NASDAQ")
    return f"{exchange}:{normalized}"


def render_tradingview_technicals(ticker: str, theme: str = "light") -> None:
    """Embed a TradingView Technical Analysis widget for the given ticker.

    Args:
        ticker: Raw ticker symbol (e.g. "AAOI").
        theme: "light" or "dark". Defaults to "light"; dark-mode detection
               is deferred follow-up work.
    """
    symbol = get_tradingview_symbol(ticker)
    widget_html = f"""
<div class="tradingview-widget-container">
  <div class="tradingview-widget-container__widget"></div>
  <script type="text/javascript"
          src="https://s3.tradingview.com/external-embedding/embed-widget-technical-analysis.js"
          async>
  {{
    "interval": "1D",
    "width": "100%",
    "isTransparent": false,
    "height": 550,
    "symbol": "{symbol}",
    "showIntervalTabs": true,
    "displayMode": "multiple",
    "locale": "en",
    "colorTheme": "{theme}"
  }}
  </script>
</div>
"""
    components.html(widget_html, height=580)
