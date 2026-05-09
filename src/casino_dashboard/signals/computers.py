from datetime import date

import pandas as pd

from casino_dashboard.models import TickerSnapshot


def compute_vol_ratio_30d(history: list[TickerSnapshot]) -> float | None:
    """Most recent volume / mean of prior days' volumes (up to 30 prior days)."""
    if len(history) < 2:
        return None

    latest = history[-1]
    prior = history[-31:-1] if len(history) > 31 else history[:-1]

    if len(prior) < 10:
        return None

    mean_vol = sum(s.volume for s in prior) / len(prior)
    if mean_vol == 0:
        return None

    return latest.volume / mean_vol


def compute_return(history: list[TickerSnapshot], days: int) -> float | None:
    """(latest_close - close_n_days_ago) / close_n_days_ago."""
    if len(history) < days + 1:
        return None

    latest_close = history[-1].close
    prior_close = history[-(days + 1)].close

    if prior_close == 0:
        return None

    return (latest_close - prior_close) / prior_close


def compute_dist_from_extreme(
    history: list[TickerSnapshot], days: int, kind: str
) -> float | None:
    """
    kind='high': (close - max_close_over_N_days) / max_close_over_N_days
    kind='low':  (close - min_close_over_N_days) / min_close_over_N_days
    """
    if len(history) < days:
        return None

    window = history[-days:]
    latest_close = history[-1].close
    closes = [s.close for s in window]

    if kind == "high":
        extreme = max(closes)
        if extreme == 0:
            return None
        return (latest_close - extreme) / extreme
    elif kind == "low":
        extreme = min(closes)
        if extreme == 0:
            return None
        return (latest_close - extreme) / extreme
    else:
        raise ValueError(f"kind must be 'high' or 'low', got {kind!r}")


def compute_return_1m(history: list[TickerSnapshot]) -> float | None:
    """21-trading-day return convenience wrapper."""
    return compute_return(history, 21)


def compute_return_ytd(history: list[TickerSnapshot]) -> float | None:
    """Return from the first trading day of the current calendar year to the latest close.

    Returns None if history doesn't span back to before January 1 of the current year
    (i.e., no pre-Jan-1 reference point exists in the data).
    """
    if not history:
        return None

    current_year = date.today().year
    jan1 = date(current_year, 1, 1)

    # History must contain at least one entry from before the current year
    # so we can anchor the YTD start at the first trading day of the year.
    if history[0].date >= jan1:
        return None

    year_start_snap: TickerSnapshot | None = None
    for snap in history:
        if snap.date >= jan1:
            year_start_snap = snap
            break

    if year_start_snap is None:
        return None

    latest_close = history[-1].close
    start_close = year_start_snap.close

    if start_close == 0:
        return None

    return (latest_close - start_close) / start_close


def compute_return_1y(history: list[TickerSnapshot]) -> float | None:
    """252-trading-day return convenience wrapper."""
    return compute_return(history, 252)


def compute_rsi_14(history: list[TickerSnapshot]) -> float | None:
    """14-day RSI using Wilder's smoothing.

    Standard formula: 100 - (100 / (1 + RS))
    where RS = average_gain / average_loss over 14 periods.

    Returns None if fewer than 15 days of history.
    Returns 100 if no losses in window (all gains).
    Returns 0 if no gains in window (all losses).
    """
    if len(history) < 15:
        return None

    closes = [s.close for s in history]
    changes = [closes[i] - closes[i - 1] for i in range(1, len(closes))]

    # Use the last 14 changes
    window = changes[-14:]

    gains = [c for c in window if c > 0]
    losses = [abs(c) for c in window if c < 0]

    avg_gain = sum(gains) / 14
    avg_loss = sum(losses) / 14

    if avg_loss == 0:
        return 100.0
    if avg_gain == 0:
        return 0.0

    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def compute_apewisdom_velocity_24h(
    mentions: int, mentions_24h_ago: int | None
) -> float | None:
    """Return mentions / mentions_24h_ago, or None if denominator is None or 0."""
    if mentions_24h_ago is None or mentions_24h_ago == 0:
        return None
    return mentions / mentions_24h_ago


def compute_mention_velocity_7d(history: pd.DataFrame) -> float | None:
    """Return latest_count / mean(prior 7 days count).

    history: DataFrame with columns [date, mention_count] sorted newest-first.
    Requires at least 8 rows (today + 7 prior days). Returns None if insufficient.
    NaN mention_count values are dropped before computing the mean.
    """
    if history.empty or len(history) < 8:
        return None
    latest = history["mention_count"].iloc[0]
    prior = history["mention_count"].iloc[1:8].dropna()
    if prior.empty:
        return None
    mean_prior = prior.mean()
    if mean_prior == 0:
        return None
    return float(latest) / float(mean_prior)
