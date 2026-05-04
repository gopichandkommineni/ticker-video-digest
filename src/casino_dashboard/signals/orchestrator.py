import logging
from datetime import date
from pathlib import Path

from casino_dashboard.db.repository import get_history, save_signal
from casino_dashboard.signals.computers import (
    compute_dist_from_extreme,
    compute_return,
    compute_vol_ratio_30d,
)
from casino_dashboard.universe import Universe

logger = logging.getLogger(__name__)


def compute_signals_for_ticker(ticker: str, db_path: Path) -> dict[str, float]:
    history = get_history(ticker, 60, db_path)
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
    _store("dist_from_30d_high_pct", compute_dist_from_extreme(history, 30, "high"))
    _store("dist_from_30d_low_pct", compute_dist_from_extreme(history, 30, "low"))

    # Derived flags
    if "dist_from_30d_high_pct" in results:
        results["near_breakout"] = 1.0 if results["dist_from_30d_high_pct"] > -0.02 else 0.0
    if "dist_from_30d_low_pct" in results:
        results["near_breakdown"] = 1.0 if results["dist_from_30d_low_pct"] < 0.02 else 0.0

    return results


def compute_and_save_all_signals(universe: Universe, db_path: Path) -> None:
    today = date.today()
    tickers = universe.all_tickers()
    computed = 0

    for ticker in sorted(tickers):
        signals = compute_signals_for_ticker(ticker, db_path)
        for signal_name, value in signals.items():
            save_signal(ticker, today, signal_name, value, db_path)
        logger.info("Signals computed for %s: %d signals", ticker, len(signals))
        computed += 1

    logger.info("Signals computed for %d tickers", computed)
