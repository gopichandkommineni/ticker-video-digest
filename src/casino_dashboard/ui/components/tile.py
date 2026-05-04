"""Reusable tile rendering components for the Casino Dashboard per-ticker page."""
import streamlit as st

from casino_dashboard.ui.components.colors import color_for_returns, color_to_hex

_TIER_PRIMARY_SIZE: dict[int, str] = {1: "1.75rem", 2: "1.35rem", 3: "1.1rem"}
_PLACEHOLDER_COLOR = "#d1d5db"


def _safe_primary(primary: str | None) -> str:
    return primary if primary is not None else "—"


def _tile_html(
    title: str,
    primary: str,
    sublines: list[str],
    color: str | None,
    tier: int,
    edit_mode: bool,
) -> str:
    hex_color = color_to_hex(color)
    # Tier 3 is monochrome — primary text stays neutral
    primary_color = hex_color if tier < 3 else "#1f2937"
    font_size = _TIER_PRIMARY_SIZE.get(tier, "1.35rem")

    if tier == 1 and color and color != "gray":
        border_accent = f"border-left:3px solid {hex_color};"
    else:
        border_accent = "border-left:3px solid #e5e7eb;"

    edit_icon = " ✏️" if edit_mode else ""

    sublines_html = "".join(
        f'<div style="font-size:0.8rem;color:#6b7280;margin-top:3px;line-height:1.4;">{s}</div>'
        for s in sublines
    )

    return (
        f'<div style="border:1px solid #e5e7eb;{border_accent}'
        f"border-radius:8px;padding:16px 14px 14px;background:#fafafa;min-height:110px;\">"
        f'<div style="font-size:0.68rem;text-transform:uppercase;letter-spacing:0.08em;'
        f'color:#9ca3af;font-weight:700;margin-bottom:10px;">{title}{edit_icon}</div>'
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
) -> None:
    """Render one tile inside the current Streamlit container."""
    sublines = [subline] if subline else []
    html = _tile_html(title, _safe_primary(primary), sublines, color, tier, edit_mode)
    st.markdown(html, unsafe_allow_html=True)


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
    """Render a free-text catalyst or red-flag note tile."""
    if text:
        body_html = (
            f'<div style="font-size:0.95rem;color:#1f2937;line-height:1.55;">{text}</div>'
        )
    else:
        body_html = (
            f'<div style="font-size:0.9rem;color:{_PLACEHOLDER_COLOR};font-style:italic;">'
            f"{placeholder}</div>"
        )

    html = (
        f'<div style="border:1px solid #e5e7eb;border-left:3px solid #e5e7eb;'
        f"border-radius:8px;padding:16px 14px 14px;background:#fafafa;min-height:110px;\">"
        f'<div style="font-size:0.68rem;text-transform:uppercase;letter-spacing:0.08em;'
        f'color:#9ca3af;font-weight:700;margin-bottom:10px;">{title} ✏️</div>'
        f"{body_html}"
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
    """Render the 5-row Returns tile."""

    def _row(label: str, val: float | None) -> str:
        if val is None:
            return (
                f'<tr><td style="color:#6b7280;font-size:0.8rem;padding:2px 8px 2px 0;">{label}</td>'
                f'<td style="font-size:0.85rem;font-weight:600;color:#6b7280;">—</td></tr>'
            )
        c = color_to_hex(color_for_returns(val))
        pct = f"{val:+.1%}"
        return (
            f'<tr><td style="color:#6b7280;font-size:0.8rem;padding:2px 8px 2px 0;">{label}</td>'
            f'<td style="font-size:0.85rem;font-weight:600;color:{c};">{pct}</td></tr>'
        )

    rows = (
        _row("1d", return_1d)
        + _row("5d", return_5d)
        + _row("1M", return_1m)
        + _row("YTD", return_ytd)
        + _row("1Y", return_1y)
    )

    html = (
        f'<div style="border:1px solid #e5e7eb;border-left:3px solid #e5e7eb;'
        f"border-radius:8px;padding:16px 14px 14px;background:#fafafa;min-height:110px;\">"
        f'<div style="font-size:0.68rem;text-transform:uppercase;letter-spacing:0.08em;'
        f'color:#9ca3af;font-weight:700;margin-bottom:10px;">Returns</div>'
        f'<table style="width:100%;border-collapse:collapse;">{rows}</table>'
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
            f'<div style="position:relative;width:100%;height:4px;background:#e5e7eb;'
            f'border-radius:2px;margin:10px 0 6px;">'
            f'<div style="position:absolute;top:-4px;left:calc({dot_left:.1f}% - 6px);'
            f'width:12px;height:12px;background:#374151;border-radius:50%;"></div>'
            f"</div>"
        )
    else:
        bar_html = ""

    html = (
        f'<div style="border:1px solid #e5e7eb;border-left:3px solid #e5e7eb;'
        f"border-radius:8px;padding:16px 14px 14px;background:#fafafa;min-height:110px;\">"
        f'<div style="font-size:0.68rem;text-transform:uppercase;letter-spacing:0.08em;'
        f'color:#9ca3af;font-weight:700;margin-bottom:8px;">52-Week Range</div>'
        f'<div style="font-size:1.35rem;font-weight:700;color:#1f2937;">{price_str}</div>'
        f"{bar_html}"
        f'<div style="display:flex;justify-content:space-between;font-size:0.78rem;'
        f'color:#6b7280;margin-top:2px;">'
        f"<span>L: {low_str}{low_pct_html}</span>"
        f"<span>H: {high_str}{high_pct_html}</span>"
        f"</div>"
        f"</div>"
    )
    st.markdown(html, unsafe_allow_html=True)
