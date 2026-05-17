"""Tests for tile CSS variable injection and readability improvements."""
import pytest


def test_inject_tile_css_contains_label_color(mocker):
    """inject_tile_css must emit a style block with --tile-label-color defined."""
    calls = []
    mocker.patch("streamlit.markdown", side_effect=lambda html, **kw: calls.append(html))
    mocker.patch("streamlit.session_state", {})
    from casino_dashboard.ui.components.tile import inject_tile_css

    inject_tile_css()
    assert calls, "st.markdown should have been called"
    combined = " ".join(calls)
    assert "--tile-label-color" in combined


def test_inject_tile_css_contains_subline_color(mocker):
    """inject_tile_css must emit a style block with --tile-subline-color defined."""
    calls = []
    mocker.patch("streamlit.markdown", side_effect=lambda html, **kw: calls.append(html))
    mocker.patch("streamlit.session_state", {})
    from casino_dashboard.ui.components.tile import inject_tile_css

    inject_tile_css()
    combined = " ".join(calls)
    assert "--tile-subline-color" in combined


def test_inject_tile_css_contains_dark_media_query(mocker):
    """inject_tile_css must include a prefers-color-scheme: dark media query."""
    calls = []
    mocker.patch("streamlit.markdown", side_effect=lambda html, **kw: calls.append(html))
    mocker.patch("streamlit.session_state", {})
    from casino_dashboard.ui.components.tile import inject_tile_css

    inject_tile_css()
    combined = " ".join(calls)
    assert "prefers-color-scheme: dark" in combined or "prefers-color-scheme:dark" in combined


def test_inject_tile_css_contains_style_tag(mocker):
    """inject_tile_css output must be wrapped in a <style> tag."""
    calls = []
    mocker.patch("streamlit.markdown", side_effect=lambda html, **kw: calls.append(html))
    mocker.patch("streamlit.session_state", {})
    from casino_dashboard.ui.components.tile import inject_tile_css

    inject_tile_css()
    combined = " ".join(calls)
    assert "<style>" in combined


def test_inject_tile_css_deduplication(mocker):
    """inject_tile_css must not call st.markdown a second time if already injected."""
    calls = []
    mocker.patch("streamlit.markdown", side_effect=lambda html, **kw: calls.append(html))
    session = {}
    mocker.patch("streamlit.session_state", session)
    from casino_dashboard.ui.components.tile import inject_tile_css

    inject_tile_css()
    first_count = len(calls)
    inject_tile_css()
    assert len(calls) == first_count, "inject_tile_css should not re-inject on second call"


def test_get_tile_html_uses_label_color_var(mocker):
    """get_tile_html must use var(--tile-label-color) for the tile title."""
    from casino_dashboard.ui.components.tile import get_tile_html

    html = get_tile_html("RETURNS", "8.4%")
    assert "var(--tile-label-color)" in html


def test_get_tile_html_uses_subline_color_var(mocker):
    """get_tile_html must use var(--tile-subline-color) for subline text."""
    from casino_dashboard.ui.components.tile import get_tile_html

    html = get_tile_html("VOLUME", "8.4M", subline="Today: 8.4M / 30d avg: 12.6M")
    assert "var(--tile-subline-color)" in html


def test_tile_html_no_hardcoded_gray_label_color():
    """The literal #9ca3af must not appear as a label or subline color in tile output."""
    from casino_dashboard.ui.components.tile import get_tile_html

    html = get_tile_html("SHORT INTEREST", "18%", subline="0.84 days to cover")
    assert "#9ca3af" not in html


def test_tile_html_title_font_weight_600():
    """Tile title must use font-weight:600, not 700."""
    from casino_dashboard.ui.components.tile import get_tile_html

    html = get_tile_html("RSI (14)", "68")
    assert "font-weight:600" in html
