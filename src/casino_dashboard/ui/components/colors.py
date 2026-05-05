"""Color classification helpers for Casino Dashboard tile rendering.

Color palette:
  green  — positive returns, breakout, high vol, oversold RSI, analyst upside, positive growth
  red    — negative returns, breakdown, analyst downside, negative margin
  yellow — earnings within 7 days, short% >15%, RSI 60-70 (approaching overbought)
  gray   — neutral / no data
"""
import math


def _is_null(x: object) -> bool:
    if x is None:
        return True
    try:
        return math.isnan(float(x))
    except (TypeError, ValueError):
        return True


def color_for_returns(x: float | None) -> str:
    """'green' for positive, 'red' for negative, 'gray' for None/zero."""
    if _is_null(x):
        return "gray"
    if x > 0:
        return "green"
    if x < 0:
        return "red"
    return "gray"


def color_for_setup(
    near_breakout: float | None, near_breakdown: float | None
) -> str:
    """'green' for breakout, 'red' for breakdown, 'gray' for neutral."""
    bo = float(near_breakout or 0)
    bd = float(near_breakdown or 0)
    if bo:
        return "green"
    if bd:
        return "red"
    return "gray"


def color_for_volume_ratio(x: float | None) -> str:
    """'green' if >1.5x, 'red' if <0.5x, 'gray' otherwise."""
    if _is_null(x):
        return "gray"
    if x > 1.5:
        return "green"
    if x < 0.5:
        return "red"
    return "gray"


def color_for_rsi(x: float | None) -> str:
    """'yellow' if >=60 (overbought/approaching), 'green' if <30 (oversold), 'gray' otherwise."""
    if _is_null(x):
        return "gray"
    if x >= 60:
        return "yellow"
    if x < 30:
        return "green"
    return "gray"


def color_for_short_pct(x: float | None) -> str:
    """'yellow' if short% > 15% (squeeze territory), 'gray' otherwise."""
    if _is_null(x):
        return "gray"
    return "yellow" if x > 0.15 else "gray"


def color_for_earnings_days(days: int | None) -> str:
    """'yellow' if fewer than 7 days until earnings, 'gray' otherwise."""
    if days is None:
        return "gray"
    return "yellow" if 0 <= days < 7 else "gray"


def color_for_analyst_upside(x: float | None) -> str:
    """'green' for positive upside, 'red' for downside, 'gray' for None/zero."""
    if _is_null(x):
        return "gray"
    if x > 0:
        return "green"
    if x < 0:
        return "red"
    return "gray"


def color_for_revenue_growth(x: float | None) -> str:
    """'green' for positive growth, 'red' for decline, 'gray' for None/zero."""
    if _is_null(x):
        return "gray"
    if x > 0:
        return "green"
    if x < 0:
        return "red"
    return "gray"


def color_for_profit_margin(x: float | None) -> str:
    """'green' for positive margin, 'red' for negative, 'gray' for None/zero."""
    if _is_null(x):
        return "gray"
    if x > 0:
        return "green"
    if x < 0:
        return "red"
    return "gray"


_COLOR_HEX_MAP: dict[str, str] = {
    "green": "#16a34a",
    "red": "#dc2626",
    "yellow": "#ca8a04",
    "gray": "#6b7280",
}


def color_to_hex(color: str | None) -> str:
    """Map a color name to its hex value."""
    return _COLOR_HEX_MAP.get(color or "gray", "#6b7280")
