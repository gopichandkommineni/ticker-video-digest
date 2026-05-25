"""Reusable tile rendering components for the Casino Dashboard per-ticker page."""
import streamlit as st

from casino_dashboard.ui.components.colors import color_for_returns, color_to_hex

_TIER_PRIMARY_SIZE: dict[int, str] = {1: "1.75rem", 2: "1.35rem", 3: "1.1rem"}
_TIER_MIN_HEIGHT: dict[int, str] = {1: "130px", 2: "100px", 3: "90px"}
_PLACEHOLDER_COLOR = "var(--tile-subline-color)"

_TILE_CSS = """
<style>
:root {
  --tile-label-color: color-mix(in srgb, var(--text-color) 65%, transparent);
  --tile-subline-color: color-mix(in srgb, var(--text-color) 50%, transparent);
}
</style>
"""


def inject_tile_css() -> None:
    """Inject CSS custom properties for tile label and subline colors once per session."""
    if st.session_state.get("_tile_css_injected"):
        return
    st.markdown(_TILE_CSS, unsafe_allow_html=True)
    st.session_state["_tile_css_injected"] = True


def _safe_primary(primary: str | None) -> str:
    return primary if primary is not None else "—"


def _is_empty_note(value: object) -> bool:
    """Return True for values that should show the empty-state placeholder.

    Handles None, float NaN, empty string, and the literal strings 'nan' / 'none'
    that pandas produces when reading NULL from SQLite.
    """
    if value is None:
        return True
    if isinstance(value, float) and value != value:  # NaN: only value not equal to itself
        return True
    return str(value).strip().lower() in ("", "nan", "none")


def _tile_html(
    title: str,
    primary: str,
    sublines: list[str],
    color: str | None,
    tier: int,
    edit_mode: bool,
    min_height: str | None = None,
) -> str:
    hex_color = color_to_hex(color)
    # Gray/uncolored primaries use CSS var for readability in dark mode;
    # colored tier-1/2 primaries use the accent hex; tier-3 is always monochrome.
    if tier >= 3 or not color or color == "gray":
        primary_color = "var(--text-color)"
    else:
        primary_color = hex_color
    font_size = _TIER_PRIMARY_SIZE.get(tier, "1.35rem")

    if color and color != "gray":
        border_accent = f"border-left:3px solid {hex_color};"
    else:
        border_accent = "border-left:3px solid rgba(128,128,128,0.2);"

    edit_icon = " ✏️" if edit_mode else ""

    sublines_html = "".join(
        f'<div style="font-size:0.8rem;color:var(--tile-subline-color);margin-top:3px;line-height:1.4;">{s}</div>'
        for s in sublines
    )

    min_h = min_height or _TIER_MIN_HEIGHT.get(tier, "130px")
    return (
        f'<div style="border:1px solid rgba(128,128,128,0.2);{border_accent}'
        f"border-radius:8px;padding:16px 14px 14px;"
        f"background:var(--secondary-background-color);min-height:{min_h};\">"
        f'<div style="font-size:0.68rem;text-transform:uppercase;letter-spacing:0.08em;'
        f'color:var(--tile-label-color);font-weight:600;margin-bottom:10px;">{title}{edit_icon}</div>'
        f'<div style="font-size:{font_size};font-weight:700;color:{primary_color};line-height:1.15;">'
        f"{primary}</div>"
        f"{sublines_html}"
        f"</div>"
    )


def render_tile(
    title: str,
    primary: str | None,
    subline: str | None = None,
    color: str | None = None,
    tier: int = 2,
    edit_mode: bool = False,
    min_height: str | None = None,
) -> None:
    """Render one tile inside the current Streamlit container."""
    sublines = [subline] if subline else []
    html = _tile_html(title, _safe_primary(primary), sublines, color, tier, edit_mode, min_height)
    st.markdown(html, unsafe_allow_html=True)


def get_tile_html(
    title: str,
    primary: str | None,
    subline: str | None = None,
    color: str | None = None,
    tier: int = 2,
    edit_mode: bool = False,
) -> str:
    """Return tile HTML string for embedding in a CSS grid layout."""
    sublines = [subline] if subline else []
    return _tile_html(title, _safe_primary(primary), sublines, color, tier, edit_mode)


def get_empty_tile_html(title: str, message: str = "—") -> str:
    """Return empty-state tile HTML string for embedding in a CSS grid layout."""
    return _tile_html(title, message, [], None, 2, False)


def render_grid(tile_html_list: list[str], cols: int = 2) -> None:
    """Render a list of tile HTML strings in a CSS grid (always cols-per-row on mobile)."""
    cells = "".join(f"<div>{h}</div>" for h in tile_html_list)
    col_def = " ".join(["1fr"] * cols)
    st.markdown(
        f'<div style="display:grid;grid-template-columns:{col_def};gap:8px;">{cells}</div>',
        unsafe_allow_html=True,
    )


def render_empty_tile(title: str, message: str = "—") -> None:
    """Render a tile with empty/null data state."""
    html = _tile_html(title, message, [], None, 2, False)
    st.markdown(html, unsafe_allow_html=True)


def render_note_tile(
    title: str,
    text: str | None,
    placeholder: str = "+ Add note",
    tier: int = 1,
) -> None:
    """Render a free-text catalyst or red-flag note tile.

    Guards against pandas NaN / empty-string / literal 'nan' values that SQLite
    NULLs produce at read time, showing the empty-state placeholder instead.
    """
    if _is_empty_note(text):
        body_html = (
            f'<div style="font-size:0.9rem;color:{_PLACEHOLDER_COLOR};font-style:italic;">'
            f"{placeholder}</div>"
        )
    elif "\n" in str(text):
        items = [line.strip() for line in str(text).strip().split("\n") if line.strip()]
        bullets = "".join(
            f'<div style="font-size:0.88rem;color:var(--text-color);line-height:1.6;'
            f'margin-bottom:4px;display:flex;gap:6px;">'
            f'<span style="color:var(--tile-subline-color);flex-shrink:0;">•</span><span>{item}</span></div>'
            for item in items
        )
        body_html = f"<div>{bullets}</div>"
    else:
        body_html = (
            f'<div style="font-size:0.95rem;color:var(--text-color);line-height:1.55;">'
            f"{text}</div>"
        )

    html = (
        f'<div style="border:1px solid rgba(128,128,128,0.2);'
        f"border-left:3px solid rgba(128,128,128,0.2);"
        f"border-radius:8px;padding:16px 14px 14px;"
        f"background:var(--secondary-background-color);min-height:120px;height:auto;\">"
        f'<div style="font-size:0.68rem;text-transform:uppercase;letter-spacing:0.08em;'
        f'color:var(--tile-label-color);font-weight:600;margin-bottom:10px;">{title} ✏️</div>'
        f"{body_html}"
        f"</div>"
    )
    st.markdown(html, unsafe_allow_html=True)


def render_analyst_target_tile(
    target_mean: float | None,
    target_high: float | None,
    target_low: float | None,
    analyst_count: int | None,
    current_price: float | None,
) -> None:
    """Render the Analyst Target tile with a min/avg/max range bar."""
    from casino_dashboard.ui.formatters import format_currency

    green_hex = color_to_hex("green")
    red_hex = color_to_hex("red")

    # ── fallback: no data ──────────────────────────────────────────────────────
    if target_mean is None:
        st.markdown(
            _tile_html("Analyst Target", "—", [], None, 3, False),
            unsafe_allow_html=True,
        )
        return

    # ── upside / downside vs current ──────────────────────────────────────────
    if current_price and current_price > 0:
        upside = (target_mean - current_price) / current_price
        upside_color = green_hex if upside >= 0 else red_hex
        upside_label = f"{upside:+.2%} upside" if upside >= 0 else f"{upside:.2%} from current"
    else:
        upside_color = "#9ca3af"
        upside_label = ""

    # ── analyst count badge ────────────────────────────────────────────────────
    count_html = (
        f'<span style="font-size:0.72rem;color:var(--tile-subline-color);background:rgba(128,128,128,0.1);'
        f'padding:2px 8px;border-radius:10px;">'
        f"{int(analyst_count)} analyst{'s' if int(analyst_count) != 1 else ''}</span>"
        if analyst_count is not None
        else ""
    )

    # ── range bar with current-price dot and avg-target marker ────────────────
    range_html = ""
    if target_low is not None and target_high is not None and target_high > target_low:
        span = target_high - target_low

        def _pos(val: float) -> float:
            return max(0.0, min(100.0, (val - target_low) / span * 100))

        avg_pos = _pos(target_mean)
        cur_pos = _pos(current_price) if current_price else None

        avg_pct_from_low = (target_mean - target_low) / target_low if target_low else None
        high_pct = (target_high - current_price) / current_price if current_price and current_price > 0 else None
        low_pct = (target_low - current_price) / current_price if current_price and current_price > 0 else None

        high_pct_html = (
            f'<span style="color:{green_hex};font-size:0.7rem;"> ({high_pct:+.1%})</span>'
            if high_pct is not None else ""
        )
        low_pct_html = (
            f'<span style="color:{red_hex};font-size:0.7rem;"> ({low_pct:+.1%})</span>'
            if low_pct is not None else ""
        )

        # Current price dot (dark circle)
        dot_html = (
            f'<div style="position:absolute;top:-5px;left:calc({cur_pos:.1f}% - 6px);'
            f'width:12px;height:12px;background:var(--text-color);border-radius:50%;'
            f'border:2px solid var(--secondary-background-color);opacity:0.8;z-index:2;"></div>'
            if cur_pos is not None else ""
        )
        # Avg target tick (colored vertical bar)
        avg_tick_html = (
            f'<div style="position:absolute;top:-4px;left:calc({avg_pos:.1f}% - 1px);'
            f'width:2px;height:10px;background:{upside_color};opacity:0.9;z-index:1;"></div>'
        )

        range_html = f"""
<div style="margin:12px 0 6px;">
  <div style="position:relative;width:100%;height:4px;
              background:rgba(128,128,128,0.18);border-radius:2px;">
    {dot_html}{avg_tick_html}
  </div>
  <div style="display:flex;justify-content:space-between;margin-top:8px;font-size:0.75rem;">
    <div>
      <div style="color:var(--tile-subline-color);margin-bottom:2px;">Low</div>
      <div style="font-weight:600;color:var(--text-color);">{format_currency(target_low)}</div>
      <div>{low_pct_html}</div>
    </div>
    <div style="text-align:right;">
      <div style="color:var(--tile-subline-color);margin-bottom:2px;">High</div>
      <div style="font-weight:600;color:var(--text-color);">{format_currency(target_high)}</div>
      <div>{high_pct_html}</div>
    </div>
  </div>
</div>
"""

    html = (
        f'<div style="border:1px solid rgba(128,128,128,0.2);'
        f"border-left:3px solid {upside_color};"
        f"border-radius:8px;padding:16px 14px 14px;"
        f"background:var(--secondary-background-color);\">"
        # title row
        f'<div style="display:flex;justify-content:space-between;align-items:center;'
        f'margin-bottom:10px;">'
        f'<div style="font-size:0.68rem;text-transform:uppercase;letter-spacing:0.08em;'
        f'color:var(--tile-label-color);font-weight:600;">Analyst Target</div>'
        f"{count_html}"
        f"</div>"
        # primary: avg price + upside
        f'<div style="display:flex;align-items:baseline;gap:8px;margin-bottom:2px;">'
        f'<div style="font-size:1.35rem;font-weight:700;color:var(--text-color);">'
        f"{format_currency(target_mean)}</div>"
        f'<div style="font-size:0.85rem;font-weight:600;color:{upside_color};">'
        f"{upside_label}</div>"
        f"</div>"
        f'<div style="font-size:0.72rem;color:var(--tile-subline-color);margin-bottom:0;">avg 1-year target</div>'
        # range bar
        f"{range_html}"
        f"</div>"
    )
    st.markdown(html, unsafe_allow_html=True)


def render_returns_tile(
    return_1d: float | None,
    return_5d: float | None,
    return_1m: float | None,
    return_ytd: float | None,
    return_1y: float | None,
) -> None:
    """Render the Returns tile as a horizontally scrollable period card strip."""
    periods = [
        ("1d", return_1d),
        ("5d", return_5d),
        ("1M", return_1m),
        ("YTD", return_ytd),
        ("1Y", return_1y),
    ]

    def _card(label: str, val: float | None) -> str:
        hex_color = color_to_hex(color_for_returns(val))
        pct = f"{val:+.1%}" if val is not None else "—"
        return (
            f'<div style="flex:0 0 auto;text-align:center;min-width:52px;">'
            f'<div style="font-size:0.72rem;color:var(--tile-subline-color);margin-bottom:5px;">{label}</div>'
            f'<div style="font-size:1.15rem;font-weight:700;color:{hex_color};">{pct}</div>'
            f"</div>"
        )

    cards_html = "".join(_card(label, val) for label, val in periods)

    html = (
        f'<div style="border:1px solid rgba(128,128,128,0.2);'
        f"border-left:3px solid rgba(128,128,128,0.2);"
        f"border-radius:8px;padding:16px 14px 14px;"
        f"background:var(--secondary-background-color);min-height:110px;\">"
        f'<div style="font-size:0.68rem;text-transform:uppercase;letter-spacing:0.08em;'
        f'color:var(--tile-label-color);font-weight:600;margin-bottom:10px;">Returns</div>'
        f'<div style="display:flex;gap:16px;overflow-x:auto;padding-bottom:4px;">'
        f"{cards_html}"
        f"</div>"
        f"</div>"
    )
    st.markdown(html, unsafe_allow_html=True)


def render_range_tile(
    current: float | None,
    high_52w: float | None,
    low_52w: float | None,
) -> None:
    """Render the 52-week range tile with a position dot on a track bar."""
    from casino_dashboard.ui.formatters import format_currency

    def _pct(a: float | None, b: float | None) -> float | None:
        if a is None or b is None or b == 0:
            return None
        return (a - b) / b

    pct_from_high = _pct(current, high_52w)
    pct_from_low = _pct(current, low_52w)

    if (
        current is not None
        and high_52w is not None
        and low_52w is not None
        and high_52w != low_52w
    ):
        pos = max(0.0, min(1.0, (current - low_52w) / (high_52w - low_52w)))
    else:
        pos = None

    price_str = format_currency(current)
    high_str = format_currency(high_52w)
    low_str = format_currency(low_52w)

    green_hex = color_to_hex("green")
    red_hex = color_to_hex("red")

    high_pct_html = (
        f'<span style="color:{red_hex};font-size:0.75rem;"> ({pct_from_high:+.1%})</span>'
        if pct_from_high is not None
        else ""
    )
    low_pct_html = (
        f'<span style="color:{green_hex};font-size:0.75rem;"> ({pct_from_low:+.1%})</span>'
        if pct_from_low is not None
        else ""
    )

    if pos is not None:
        dot_left = pos * 100
        bar_html = (
            f'<div style="position:relative;width:100%;height:4px;'
            f'background:rgba(128,128,128,0.2);border-radius:2px;margin:10px 0 6px;">'
            f'<div style="position:absolute;top:-4px;left:calc({dot_left:.1f}% - 6px);'
            f'width:12px;height:12px;background:var(--text-color);border-radius:50%;opacity:0.7;"></div>'
            f"</div>"
        )
    else:
        bar_html = ""

    html = (
        f'<div style="border:1px solid rgba(128,128,128,0.2);'
        f"border-left:3px solid rgba(128,128,128,0.2);"
        f"border-radius:8px;padding:16px 14px 14px;"
        f"background:var(--secondary-background-color);min-height:140px;\">"
        f'<div style="font-size:0.68rem;text-transform:uppercase;letter-spacing:0.08em;'
        f'color:var(--tile-label-color);font-weight:600;margin-bottom:8px;">52-Week Range</div>'
        f'<div style="font-size:1.35rem;font-weight:700;color:var(--text-color);">{price_str}</div>'
        f"{bar_html}"
        f'<div style="display:flex;justify-content:space-between;font-size:0.78rem;'
        f'color:var(--tile-subline-color);margin-top:2px;">'
        f"<span>L: {low_str}{low_pct_html}</span>"
        f"<span>H: {high_str}{high_pct_html}</span>"
        f"</div>"
        f"</div>"
    )
    st.markdown(html, unsafe_allow_html=True)
