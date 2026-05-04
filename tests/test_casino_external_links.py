"""Tests for casino_dashboard.ui.external_links."""
from casino_dashboard.ui.external_links import build_external_links

EXPECTED_LABELS = {"Finviz", "Yahoo", "Stocktwits", "WSB", "Reddit", "SEC", "TradingView"}


def test_all_seven_sources_present():
    links = build_external_links("AAOI")
    labels = {label for label, _ in links}
    assert labels == EXPECTED_LABELS
    assert len(links) == 7


def test_ticker_substituted_correctly():
    for ticker in ("AAOI", "RKLB"):
        links = build_external_links(ticker)
        for label, url in links:
            assert ticker in url, f"{label} URL missing ticker {ticker!r}: {url}"


def test_all_urls_start_with_https():
    for ticker in ("AAOI", "RKLB"):
        for _, url in build_external_links(ticker):
            assert url.startswith("https://"), f"Non-HTTPS URL: {url}"
