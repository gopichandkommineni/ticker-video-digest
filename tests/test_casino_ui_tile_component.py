"""Tests for casino_dashboard.ui.components.tile — tile rendering functions."""
import pytest


# ── render_tile ───────────────────────────────────────────────────────────────

def test_render_tile_basic_does_not_raise(mocker):
    """render_tile with standard inputs should not raise."""
    mocker.patch("streamlit.markdown")
    from casino_dashboard.ui.components.tile import render_tile

    render_tile("Setup", "NEUTRAL")


def test_render_tile_with_all_params_does_not_raise(mocker):
    """render_tile accepts all optional params without raising."""
    mocker.patch("streamlit.markdown")
    from casino_dashboard.ui.components.tile import render_tile

    render_tile(
        title="Earnings",
        primary="3 days",
        subline="May 7, 2026 · AMC",
        color="yellow",
        tier=1,
        edit_mode=False,
    )


def test_render_tile_tier3_does_not_raise(mocker):
    mocker.patch("streamlit.markdown")
    from casino_dashboard.ui.components.tile import render_tile

    render_tile("RSI (14)", "68", subline="Approaching overbought", tier=3)


def test_render_tile_none_primary_renders_em_dash(mocker):
    """When primary is None, the rendered HTML should contain an em-dash."""
    calls = []
    mocker.patch("streamlit.markdown", side_effect=lambda html, **kw: calls.append(html))
    from casino_dashboard.ui.components.tile import render_tile

    render_tile("Volume", None)
    assert calls, "st.markdown should have been called"
    assert "—" in calls[0], "Em-dash should appear in HTML when primary is None"


def test_render_tile_green_color_does_not_raise(mocker):
    mocker.patch("streamlit.markdown")
    from casino_dashboard.ui.components.tile import render_tile

    render_tile("Vol Ratio", "2.31x", color="green", tier=2)


def test_render_tile_red_color_does_not_raise(mocker):
    mocker.patch("streamlit.markdown")
    from casino_dashboard.ui.components.tile import render_tile

    render_tile("Returns", "-8.39%", color="red", tier=2)


def test_render_tile_edit_mode_does_not_raise(mocker):
    mocker.patch("streamlit.markdown")
    from casino_dashboard.ui.components.tile import render_tile

    render_tile("Catalyst", "Some text", edit_mode=True, tier=1)


def test_render_tile_tier1_colored_border_in_html(mocker):
    """Tier-1 tile with non-gray color should include the color hex in HTML."""
    calls = []
    mocker.patch("streamlit.markdown", side_effect=lambda html, **kw: calls.append(html))
    from casino_dashboard.ui.components.tile import render_tile

    render_tile("Setup", "BREAKOUT", color="green", tier=1)
    assert calls
    # Green hex should appear for the border accent
    assert "#16a34a" in calls[0]


def test_render_tile_tier3_monochrome_no_color_in_primary(mocker):
    """Tier-3 tiles are monochrome; primary text uses neutral color regardless of color param."""
    calls = []
    mocker.patch("streamlit.markdown", side_effect=lambda html, **kw: calls.append(html))
    from casino_dashboard.ui.components.tile import render_tile

    render_tile("RSI (14)", "68", color="yellow", tier=3)
    assert calls
    html = calls[0]
    # Neutral primary color should appear (not yellow hex) for the primary value
    assert "#1f2937" in html


# ── render_empty_tile ─────────────────────────────────────────────────────────

def test_render_empty_tile_default_message(mocker):
    """render_empty_tile should render an em-dash by default."""
    calls = []
    mocker.patch("streamlit.markdown", side_effect=lambda html, **kw: calls.append(html))
    from casino_dashboard.ui.components.tile import render_empty_tile

    render_empty_tile("Short Interest")
    assert calls
    assert "—" in calls[0]


def test_render_empty_tile_custom_message(mocker):
    """render_empty_tile should show the custom message."""
    calls = []
    mocker.patch("streamlit.markdown", side_effect=lambda html, **kw: calls.append(html))
    from casino_dashboard.ui.components.tile import render_empty_tile

    render_empty_tile("Social", "Not tracked")
    assert calls
    assert "Not tracked" in calls[0]


def test_render_empty_tile_does_not_raise(mocker):
    mocker.patch("streamlit.markdown")
    from casino_dashboard.ui.components.tile import render_empty_tile

    render_empty_tile("Ownership")


def test_render_empty_tile_none_primary_shows_em_dash(mocker):
    """Confirm em-dash appears even when title is unusual."""
    calls = []
    mocker.patch("streamlit.markdown", side_effect=lambda html, **kw: calls.append(html))
    from casino_dashboard.ui.components.tile import render_empty_tile

    render_empty_tile("Analyst Target")
    assert "—" in calls[0]


# ── color logic applied in render_tile ───────────────────────────────────────

def test_render_tile_yellow_color_in_html(mocker):
    """Yellow color hex should appear for a yellow-colored tile."""
    calls = []
    mocker.patch("streamlit.markdown", side_effect=lambda html, **kw: calls.append(html))
    from casino_dashboard.ui.components.tile import render_tile

    render_tile("Earnings", "3 days", color="yellow", tier=1)
    assert calls
    assert "#ca8a04" in calls[0]
