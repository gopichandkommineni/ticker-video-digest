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
