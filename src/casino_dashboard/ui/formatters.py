"""Number and currency formatting helpers for the per-ticker detail page.

Note: this module is separate from ui/formatting.py (which uses 1dp percentages for
the overview tables). These formatters use 2dp percentages matching the detail page spec.
"""
import math


def _is_null(x: object) -> bool:
    if x is None:
        return True
    try:
        return math.isnan(float(x))
    except (TypeError, ValueError):
        return True


def format_market_cap(x: float | None) -> str:
    """Format a raw market cap value as '$X.XXB' or '$X.XXM', e.g. '$13.97B'."""
    if _is_null(x):
        return "—"
    x = float(x)
    if abs(x) >= 1_000_000_000:
        return f"${x / 1_000_000_000:.2f}B"
    if abs(x) >= 1_000_000:
        return f"${x / 1_000_000:.2f}M"
    return f"${x:,.2f}"


def format_pct(x: float | None) -> str:
    """Format a decimal fraction as a 2dp percentage string, e.g. '+82.75%' or '—' for None/NaN.

    Signals are stored as decimals (0.8275 = 82.75%). Multiplies by 100 for display.
    """
    if _is_null(x):
        return "—"
    return f"{float(x):+.2%}"


def format_currency(x: float | None) -> str:
    """Format a float as a dollar amount, e.g. '$176.97' or '—'."""
    if _is_null(x):
        return "—"
    return f"${float(x):.2f}"
