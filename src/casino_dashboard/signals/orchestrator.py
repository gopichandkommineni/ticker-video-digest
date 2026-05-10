import logging
from datetime import date
from pathlib import Path

import pandas as pd

from casino_dashboard.db.repository import (
    get_history,
    get_social_history,
    save_signal,
)
from casino_dashboard.signals.computers import (
    compute_apewisdom_velocity_24h,
    compute_atr14_pct,
    compute_dist_from_extreme,
    compute_mention_velocity_7d,
    compute_pct_above_sma50,
    compute_return,
    compute_return_1m,
    compute_return_1y,
    compute_return_ytd,
    compute_rsi_14,
    compute_vol_ratio_30d,
    compute_vol_rsi_14,
)
from casino_dashboard.universe import Universe

logger = logging.getLogger(__name__)


def compute_signals_for_ticker(ticker: str, db_path: Path) -> dict[str, float]:
    history = get_history(ticker, 300, db_path)
    # get_history returns newest-first; reverse to oldest-first for computers
    history = list(reversed(history))

    results: dict[str, float] = {}

    def _store(name: str, value: float | None) -> None:
        if value is not None:
            results[name] = value

    _store("vol_ratio_30d", compute_vol_ratio_30d(history))
    _store("return_1d", compute_return(history, 1))
    _store("return_5d", compute_return(history, 5))
    _store("return_20d", compute_return(history, 20))
    _store("return_1m", compute_return_1m(history))
    _store("return_ytd", compute_return_ytd(history))
    _store("return_1y", compute_return_1y(history))
    _store("rsi_14", compute_rsi_14(history))
    _store("vol_rsi_14", compute_vol_rsi_14(history))
    _store("dist_from_30d_high_pct", compute_dist_from_extreme(history, 30, "high"))
    _store("dist_from_30d_low_pct", compute_dist_from_extreme(history, 30, "low"))
    _store("atr14_pct", compute_atr14_pct(history))
    _store("pct_above_sma50", compute_pct_above_sma50(history))

    # Derived flags
    if "dist_from_30d_high_pct" in results:
        results["near_breakout"] = 1.0 if results["dist_from_30d_high_pct"] > -0.02 else 0.0
    if "dist_from_30d_low_pct" in results:
        results["near_breakdown"] = 1.0 if results["dist_from_30d_low_pct"] < 0.02 else 0.0

    return results


def compute_social_signals_for_ticker(ticker: str, db_path: Path) -> dict[str, float]:
    """Compute ApeWisdom social signals from accumulated DB history."""
    results: dict[str, float] = {}

    social_hist = get_social_history(ticker, "apewisdom", 30, db_path)
    if social_hist.empty:
        return results

    # Latest row carries today's mention_count and mentions_24h_ago from the API
    latest_row = social_hist.iloc[0]
    if pd.isna(latest_row["mention_count"]):
        return results
    mentions_today = int(latest_row["mention_count"])
    mentions_24h_ago = (
        int(latest_row["mentions_24h_ago"])
        if not pd.isna(latest_row["mentions_24h_ago"])
        else None
    )

    results["apewisdom_mentions_today"] = float(mentions_today)

    v24h = compute_apewisdom_velocity_24h(mentions_today, mentions_24h_ago)
    if v24h is not None:
        results["apewisdom_velocity_24h"] = v24h

    v7d = compute_mention_velocity_7d(social_hist)
    if v7d is not None:
        results["apewisdom_velocity_7d"] = v7d

    return results


def compute_and_save_all_signals(universe: Universe, db_path: Path) -> None:
    today = date.today()
    tickers = universe.all_tickers()
    computed = 0

    for ticker in sorted(tickers):
        signals = compute_signals_for_ticker(ticker, db_path)
        social_signals = compute_social_signals_for_ticker(ticker, db_path)
        signals.update(social_signals)

        for signal_name, value in signals.items():
            save_signal(ticker, today, signal_name, value, db_path)
        logger.info("Signals computed for %s: %d signals", ticker, len(signals))
        computed += 1

    logger.info("Signals computed for %d tickers", computed)
