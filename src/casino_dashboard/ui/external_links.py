"""External research link builder for a given ticker symbol."""


def build_external_links(ticker: str) -> list[tuple[str, str]]:
    """Return [(label, url), ...] for the standard external sources."""
    return [
        ("Finviz", f"https://finviz.com/quote.ashx?t={ticker}"),
        ("Yahoo", f"https://finance.yahoo.com/quote/{ticker}"),
        ("Stocktwits", f"https://stocktwits.com/symbol/{ticker}"),
        ("WSB", f"https://www.reddit.com/r/wallstreetbets/search/?q={ticker}&restrict_sr=1&sort=new"),
        ("Reddit", f"https://www.reddit.com/search/?q=%24{ticker}&sort=new"),
        ("SEC", f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={ticker}&type=&dateb=&owner=include&count=40"),
        ("TradingView", f"https://www.tradingview.com/symbols/{ticker}"),
    ]
