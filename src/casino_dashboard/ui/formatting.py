"""Number and percentage formatting helpers for the Casino Dashboard UI."""
import math


def format_pct(x: float | None) -> str:
    """Format a float as a percentage string, e.g. '+12.3%' or '—' for None/NaN."""
    if x is None:
        return "—"
    try:
        if math.isnan(float(x)):
            return "—"
    except (TypeError, ValueError):
        return "—"
    sign = "+" if x > 0 else ""
    return f"{sign}{x:.1f}%"


def format_ratio(x: float | None) -> str:
    """Format a float as a ratio string, e.g. '1.52x' or '—' for None/NaN."""
    if x is None:
        return "—"
    try:
        if math.isnan(float(x)):
            return "—"
    except (TypeError, ValueError):
        return "—"
    return f"{x:.2f}x"


def format_money(x: float | None) -> str:
    """Format a float as a dollar amount, e.g. '$26.33' or '$1,234.56' or '—'."""
    if x is None:
        return "—"
    try:
        if math.isnan(float(x)):
            return "—"
    except (TypeError, ValueError):
        return "—"
    return f"${x:,.2f}"


def color_for_return(x: float | None) -> str:
    """Return 'green', 'red', or 'gray' based on the sign of x."""
    if x is None:
        return "gray"
    try:
        if math.isnan(float(x)):
            return "gray"
    except (TypeError, ValueError):
        return "gray"
    if x > 0:
        return "green"
    if x < 0:
        return "red"
    return "gray"
