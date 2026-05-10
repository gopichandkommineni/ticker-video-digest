"""Tests for the TradingView widget utility functions."""
from casino_dashboard.ui.components.tradingview import get_tradingview_symbol, render_tradingview_technicals


def test_get_tradingview_symbol_known_ticker():
    assert get_tradingview_symbol("AAOI") == "NASDAQ:AAOI"


def test_get_tradingview_symbol_nyse_ticker():
    assert get_tradingview_symbol("GLW") == "NYSE:GLW"


def test_get_tradingview_symbol_unknown_ticker():
    assert get_tradingview_symbol("ZZZZ") == "NASDAQ:ZZZZ"


def test_get_tradingview_symbol_lowercase():
    assert get_tradingview_symbol("aaoi") == "NASDAQ:AAOI"


def test_get_tradingview_symbol_with_whitespace():
    assert get_tradingview_symbol("  AAOI  ") == "NASDAQ:AAOI"


def test_render_tradingview_technicals_contains_symbol(monkeypatch):
    """render_tradingview_technicals builds HTML containing the correct symbol."""
    captured: list[str] = []

    def _fake_html(html: str, height: int = 0) -> None:
        captured.append(html)

    import streamlit.components.v1 as components_module
    monkeypatch.setattr(components_module, "html", _fake_html)

    render_tradingview_technicals("AAOI")

    assert len(captured) == 1
    assert "NASDAQ:AAOI" in captured[0]
