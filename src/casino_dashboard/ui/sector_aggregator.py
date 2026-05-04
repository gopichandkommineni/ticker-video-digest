"""Pure functions for aggregating per-ticker signals into sector-level rollups."""
import math

import pandas as pd

from casino_dashboard.universe import Universe

# Thresholds for sector health classification
_HOT_RETURN_5D = 0.05       # avg 5d return > 5%
_HOT_BREAKOUT = 0.30        # % near breakout > 30%
_COLD_RETURN_5D = -0.05     # avg 5d return < -5%
_COLD_BREAKDOWN = 0.30      # % near breakdown > 30%
_MIXED_BREAKOUT = 0.20      # both > 20% = divergent sector
_MIXED_BREAKDOWN = 0.20


def _safe_mean(series: pd.Series) -> float | None:
    """Return mean of non-NaN values, or None if all are NaN."""
    valid = series.dropna()
    if valid.empty:
        return None
    return float(valid.mean())


def aggregate_signals_by_sector(
    signals_df: pd.DataFrame,
    universe: Universe,
) -> pd.DataFrame:
    """
    Returns wide-format DataFrame indexed by sector_id, with columns:
    display_name, n_tickers, avg_return_1d, avg_return_5d, avg_return_20d,
    pct_near_breakout, pct_near_breakdown, avg_vol_ratio,
    avg_apewisdom_velocity, sector_health.

    Tickers with multi-sector membership (e.g. RKLB in space and
    drones_defense) are counted in BOTH sector aggregates.

    NaN handling: sector aggregate ignores NaN values — apewisdom_velocity
    is NaN for tickers ApeWisdom doesn't track; the average is computed
    over the tickers that DO have data.

    Returns empty DataFrame if signals_df is empty.
    """
    if signals_df.empty:
        return pd.DataFrame()

    records: list[dict] = []

    for sector_id, sector in universe.sectors.items():
        tickers = sector.tickers
        n_total = len(tickers)

        # Filter signals to tickers in this sector
        present = [t for t in tickers if t in signals_df.index]
        if not present:
            sector_df = pd.DataFrame()
        else:
            sector_df = signals_df.loc[present]

        def _col(name: str) -> pd.Series:
            if sector_df.empty or name not in sector_df.columns:
                return pd.Series(dtype=float)
            return sector_df[name]

        avg_return_1d = _safe_mean(_col("return_1d"))
        avg_return_5d = _safe_mean(_col("return_5d"))
        avg_return_20d = _safe_mean(_col("return_20d"))
        avg_vol_ratio = _safe_mean(_col("vol_ratio_30d"))
        avg_apewisdom_velocity = _safe_mean(_col("apewisdom_velocity_24h"))

        # pct_near_breakout / breakdown: fraction of tickers where flag > 0
        bo_series = _col("near_breakout")
        bd_series = _col("near_breakdown")

        if bo_series.empty:
            pct_near_breakout = None
        else:
            valid_bo = bo_series.dropna()
            pct_near_breakout = float((valid_bo > 0).mean()) if not valid_bo.empty else None

        if bd_series.empty:
            pct_near_breakdown = None
        else:
            valid_bd = bd_series.dropna()
            pct_near_breakdown = float((valid_bd > 0).mean()) if not valid_bd.empty else None

        row = pd.Series(
            {
                "avg_return_5d": avg_return_5d,
                "pct_near_breakout": pct_near_breakout,
                "pct_near_breakdown": pct_near_breakdown,
            }
        )
        health = classify_sector_health(row)

        records.append(
            {
                "sector_id": sector_id,
                "display_name": sector.display_name,
                "n_tickers": n_total,
                "avg_return_1d": avg_return_1d,
                "avg_return_5d": avg_return_5d,
                "avg_return_20d": avg_return_20d,
                "pct_near_breakout": pct_near_breakout,
                "pct_near_breakdown": pct_near_breakdown,
                "avg_vol_ratio": avg_vol_ratio,
                "avg_apewisdom_velocity": avg_apewisdom_velocity,
                "sector_health": health,
            }
        )

    return pd.DataFrame(records).set_index("sector_id")


def classify_sector_health(row: pd.Series) -> str:
    """
    Returns one of: 'hot', 'mixed', 'cold', 'quiet'.

    Rules (in priority order):
      Hot:   avg_return_5d > 5%  AND pct_near_breakout  > 30%
      Cold:  avg_return_5d < -5% AND pct_near_breakdown  > 30%
      Mixed: pct_near_breakout > 20% AND pct_near_breakdown > 20%
      Quiet: everything else

    Pure function, no side effects. NaN values are treated as not meeting
    any threshold (i.e., they fall through to Quiet).
    """

    def _val(key: str) -> float:
        v = row.get(key)
        if v is None:
            return float("nan")
        try:
            f = float(v)
            return f if not math.isnan(f) else float("nan")
        except (TypeError, ValueError):
            return float("nan")

    avg_5d = _val("avg_return_5d")
    pct_bo = _val("pct_near_breakout")
    pct_bd = _val("pct_near_breakdown")

    # Hot
    if not math.isnan(avg_5d) and not math.isnan(pct_bo):
        if avg_5d > _HOT_RETURN_5D and pct_bo > _HOT_BREAKOUT:
            return "hot"

    # Cold
    if not math.isnan(avg_5d) and not math.isnan(pct_bd):
        if avg_5d < _COLD_RETURN_5D and pct_bd > _COLD_BREAKDOWN:
            return "cold"

    # Mixed
    if not math.isnan(pct_bo) and not math.isnan(pct_bd):
        if pct_bo > _MIXED_BREAKOUT and pct_bd > _MIXED_BREAKDOWN:
            return "mixed"

    return "quiet"


_HEALTH_LABEL: dict[str, str] = {
    "hot": "🟢 Hot",
    "cold": "🔴 Cold",
    "mixed": "🟡 Mixed",
    "quiet": "⚪ Quiet",
}


def health_label(health: str) -> str:
    """Return the display label for a sector health value."""
    return _HEALTH_LABEL.get(health, "⚪ Quiet")
