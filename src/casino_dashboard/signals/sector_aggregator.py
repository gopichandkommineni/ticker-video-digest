"""
Sector heat aggregator — computes sector_heat rows from constituent signals.

Called daily after compute_and_save_all_signals(). One sector_heat row per
sector per day. Equal-weighted across constituents; skips constituents with
null data rather than treating null as zero.

Spec §3: three dimensions, seven sub-columns.
  Dimension 1 (Capital Flows): etf_flow_5d_30d_ratio, deal_log metrics
  Dimension 2 (Hype): agg_social_velocity, news_heat_ratio
  Dimension 3 (Growth): agg_return_30d, pct_above_sma50, agg_atr_pct_change_30d
"""
import logging
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

from casino_dashboard.db.repository import (
    get_deal_log_for_sector,
    get_deal_log_latest_date_per_sector,
    get_etf_flows,
    get_latest_signal_for_tickers,
    get_news_count_for_tickers,
    get_sector_etf_mapping,
    get_signal_for_ticker_on_date,
    save_sector_heat,
)
from casino_dashboard.data.etf_flows_fetcher import (
    ETFFlow,
    compute_etf_flow_ratio,
)
from casino_dashboard.universe import Universe

logger = logging.getLogger(__name__)


@dataclass
class SectorHeat:
    sector: str
    date: date
    etf_flow_5d_30d_ratio: float | None
    deal_log_30d_total_usd: float | None
    deal_log_30d_count: int
    days_since_last_deal: int | None
    agg_social_velocity: float | None
    news_heat_ratio: float | None
    agg_return_30d: float | None
    pct_above_sma50: float | None
    agg_atr_pct_change_30d: float | None
    constituent_count: int


def _equal_weighted_avg(values: dict[str, float]) -> float | None:
    """Return the equal-weighted mean across ticker values, or None if empty."""
    if not values:
        return None
    return sum(values.values()) / len(values)


def _compute_etf_flow_for_sector(
    sector: str,
    as_of: date,
    db_path: Path,
) -> float | None:
    """Aggregate ETF flow ratio across all ETFs mapped to the sector.

    Averages compute_etf_flow_ratio across sector ETFs. Returns None if no
    ETF data exists for the sector (e.g. Photonics).
    """
    mapping_df = get_sector_etf_mapping(db_path=db_path)
    if mapping_df.empty:
        return None

    sector_etfs = mapping_df[mapping_df["sector"] == sector]["etf_ticker"].tolist()
    if not sector_etfs:
        return None

    ratios = []
    for etf_ticker in sector_etfs:
        flows_df = get_etf_flows(etf_ticker, days=35, db_path=db_path)
        if flows_df.empty:
            continue
        flows = [
            ETFFlow(
                etf_ticker=etf_ticker,
                date=date.fromisoformat(row["date"]),
                net_flow_usd=row["net_flow_usd"],
                aum_usd=row["aum_usd"],
            )
            for _, row in flows_df.iterrows()
            if row["net_flow_usd"] is not None
        ]
        ratio = compute_etf_flow_ratio(flows, as_of)
        if ratio is not None:
            ratios.append(ratio)

    return sum(ratios) / len(ratios) if ratios else None


def _compute_deal_log_metrics(
    sector: str,
    as_of: date,
    db_path: Path,
) -> tuple[float | None, int, int | None]:
    """Return (total_usd_30d, count_30d, days_since_last_deal)."""
    deals_df = get_deal_log_for_sector(sector, days=30, db_path=db_path)

    total_usd: float | None = None
    count = len(deals_df)

    if not deals_df.empty:
        amounts = deals_df["amount_usd"].dropna()
        if not amounts.empty:
            total_usd = float(amounts.sum())

    latest_dates = get_deal_log_latest_date_per_sector(db_path=db_path)
    days_since: int | None = None
    if sector in latest_dates and latest_dates[sector]:
        latest = date.fromisoformat(latest_dates[sector])
        days_since = (as_of - latest).days

    return total_usd, count, days_since


def _compute_news_heat_ratio(
    tickers: list[str],
    db_path: Path,
) -> float | None:
    """7-day news count / (30-day count / (30 / 7)).

    Returns None if there are no news in the 30-day window.
    """
    count_7d = get_news_count_for_tickers(tickers, days=7, db_path=db_path)
    count_30d = get_news_count_for_tickers(tickers, days=30, db_path=db_path)

    if count_30d == 0:
        return None

    avg_7d_rate = count_30d / (30 / 7)  # expected count per 7-day window
    if avg_7d_rate == 0:
        return None

    return count_7d / avg_7d_rate


def _compute_atr_pct_change_30d(
    tickers: list[str],
    as_of: date,
    db_path: Path,
) -> float | None:
    """Change in aggregate atr14_pct over trailing 30 days.

    Equal-weighted average of current atr14_pct minus equal-weighted average
    of atr14_pct 30 days ago. Requires constituents with both data points.
    """
    date_30d_ago = as_of - timedelta(days=30)

    current_vals = get_latest_signal_for_tickers(tickers, "atr14_pct", db_path=db_path)

    past_vals: dict[str, float] = {}
    for ticker in tickers:
        val = get_signal_for_ticker_on_date(ticker, "atr14_pct", date_30d_ago, db_path=db_path)
        if val is not None:
            past_vals[ticker] = val

    # Only use tickers that have both data points
    common = set(current_vals) & set(past_vals)
    if not common:
        return None

    avg_current = sum(current_vals[t] for t in common) / len(common)
    avg_past = sum(past_vals[t] for t in common) / len(common)

    return avg_current - avg_past


def compute_sector_heat(
    sector: str,
    constituents: list[str],
    as_of: date,
    db_path: Path,
) -> SectorHeat:
    """Compute all sector_heat fields for one sector as of the given date.

    Equal-weighted across constituents; skips constituents with null data.
    Errors in sub-computations are caught per-dimension so a failure in one
    dimension does not blank the others.
    """
    # --- Dimension 1: Capital Flows ---
    etf_flow_ratio: float | None = None
    try:
        etf_flow_ratio = _compute_etf_flow_for_sector(sector, as_of, db_path)
    except Exception as exc:
        logger.warning("ETF flow computation failed for %s: %s", sector, exc)

    deal_total: float | None = None
    deal_count = 0
    days_since_deal: int | None = None
    try:
        deal_total, deal_count, days_since_deal = _compute_deal_log_metrics(sector, as_of, db_path)
    except Exception as exc:
        logger.warning("Deal log metrics failed for %s: %s", sector, exc)

    # --- Dimension 2: Hype ---
    social_velocity: float | None = None
    try:
        social_vals = get_latest_signal_for_tickers(constituents, "apewisdom_velocity_24h", db_path=db_path)
        social_velocity = _equal_weighted_avg(social_vals)
    except Exception as exc:
        logger.warning("Social velocity computation failed for %s: %s", sector, exc)

    news_heat: float | None = None
    try:
        news_heat = _compute_news_heat_ratio(constituents, db_path)
    except Exception as exc:
        logger.warning("News heat computation failed for %s: %s", sector, exc)

    # --- Dimension 3: Growth ---
    agg_return: float | None = None
    try:
        return_vals = get_latest_signal_for_tickers(constituents, "return_1m", db_path=db_path)
        agg_return = _equal_weighted_avg(return_vals)
    except Exception as exc:
        logger.warning("Return aggregation failed for %s: %s", sector, exc)

    breadth: float | None = None
    try:
        sma_vals = get_latest_signal_for_tickers(constituents, "pct_above_sma50", db_path=db_path)
        breadth = _equal_weighted_avg(sma_vals)
    except Exception as exc:
        logger.warning("Breadth computation failed for %s: %s", sector, exc)

    atr_change: float | None = None
    try:
        atr_change = _compute_atr_pct_change_30d(constituents, as_of, db_path)
    except Exception as exc:
        logger.warning("ATR pct change computation failed for %s: %s", sector, exc)

    return SectorHeat(
        sector=sector,
        date=as_of,
        etf_flow_5d_30d_ratio=etf_flow_ratio,
        deal_log_30d_total_usd=deal_total,
        deal_log_30d_count=deal_count,
        days_since_last_deal=days_since_deal,
        agg_social_velocity=social_velocity,
        news_heat_ratio=news_heat,
        agg_return_30d=agg_return,
        pct_above_sma50=breadth,
        agg_atr_pct_change_30d=atr_change,
        constituent_count=len(constituents),
    )


def compute_and_save_all_sector_heat(universe: Universe, db_path: Path) -> None:
    """Compute and persist sector_heat for all sectors as of today.

    Called from daily_refresh.py after compute_and_save_all_signals().
    Sector-level failures log and continue — never abort the run.
    """
    today = date.today()
    for sector_id, sector in universe.sectors.items():
        try:
            heat = compute_sector_heat(
                sector=sector_id,
                constituents=sector.tickers,
                as_of=today,
                db_path=db_path,
            )
            save_sector_heat(
                sector=heat.sector,
                heat_date=heat.date,
                etf_flow_5d_30d_ratio=heat.etf_flow_5d_30d_ratio,
                deal_log_30d_total_usd=heat.deal_log_30d_total_usd,
                deal_log_30d_count=heat.deal_log_30d_count,
                days_since_last_deal=heat.days_since_last_deal,
                agg_social_velocity=heat.agg_social_velocity,
                news_heat_ratio=heat.news_heat_ratio,
                agg_return_30d=heat.agg_return_30d,
                pct_above_sma50=heat.pct_above_sma50,
                agg_atr_pct_change_30d=heat.agg_atr_pct_change_30d,
                constituent_count=heat.constituent_count,
                db_path=db_path,
            )
            logger.info(
                "Sector heat saved for %s: return=%.1f%%, breadth=%.0f%%, social=%.2f",
                sector_id,
                (heat.agg_return_30d or 0) * 100,
                (heat.pct_above_sma50 or 0) * 100,
                heat.agg_social_velocity or 0,
            )
        except Exception as exc:
            logger.error("Sector heat failed for %s (continuing): %s", sector_id, exc)
