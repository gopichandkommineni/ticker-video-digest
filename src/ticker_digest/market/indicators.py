"""Indicator fetchers for the broader-market dashboard.

Each indicator function returns a `MarketIndicator` populated with the latest
value, a 5y rolling z-score, and a small history slice for sparklines. Any
network or data error is caught and surfaced via the indicator's `error`
field so the rest of the dashboard keeps rendering.
"""
from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone

import pandas as pd

from ticker_digest import cache, config
from ticker_digest.market import fred_client
from ticker_digest.models import IndicatorBucket, IndicatorSource, MarketIndicator, MarketSnapshot

log = logging.getLogger(__name__)

_SPARKLINE_POINTS = 60
_ZSCORE_WINDOW_YEARS = 5


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _z_score(series: pd.Series, value: float) -> float | None:
    if series.empty:
        return None
    cutoff = series.index.max() - pd.Timedelta(days=365 * _ZSCORE_WINDOW_YEARS)
    window = series[series.index >= cutoff]
    if len(window) < 12:
        window = series  # fall back to whole history if 5y window is sparse
    std = float(window.std())
    if std == 0 or pd.isna(std):
        return None
    mean = float(window.mean())
    return (value - mean) / std


def _sparkline(series: pd.Series) -> dict[str, float]:
    if series.empty:
        return {}
    tail = series.tail(_SPARKLINE_POINTS)
    return {ts.strftime("%Y-%m-%d"): float(v) for ts, v in tail.items()}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _build(
    name: str,
    series_id: str,
    source: IndicatorSource,
    bucket: IndicatorBucket,
    series: pd.Series,
) -> MarketIndicator:
    series = series.dropna().sort_index()
    if series.empty:
        return MarketIndicator(
            name=name,
            series_id=series_id,
            source=source,
            bucket=bucket,
            error="empty series",
        )
    latest = float(series.iloc[-1])
    return MarketIndicator(
        name=name,
        series_id=series_id,
        source=source,
        bucket=bucket,
        value=latest,
        z_score=_z_score(series, latest),
        as_of=series.index[-1].to_pydatetime().replace(tzinfo=timezone.utc),
        history=_sparkline(series),
    )


def _error(name: str, series_id: str, source: IndicatorSource, bucket: IndicatorBucket, exc: Exception) -> MarketIndicator:
    return MarketIndicator(
        name=name,
        series_id=series_id,
        source=source,
        bucket=bucket,
        error=f"{type(exc).__name__}: {exc}",
    )


# ---------------------------------------------------------------------------
# Indicator fetchers
# ---------------------------------------------------------------------------


def _yf_history(ticker: str, period: str = "10y", interval: str = "1d") -> pd.Series:
    import yfinance as yf

    df = yf.Ticker(ticker).history(period=period, interval=interval, auto_adjust=False)
    if df.empty or "Close" not in df.columns:
        return pd.Series(dtype=float)
    series = df["Close"].dropna()
    series.index = pd.DatetimeIndex(series.index).tz_localize(None)
    return series


def fetch_vix() -> MarketIndicator:
    name, sid = "VIX", "VIX"
    try:
        return _build(name, sid, "yfinance", "context", _yf_history("^VIX", period="10y"))
    except Exception as exc:  # noqa: BLE001
        log.warning("VIX fetch failed: %s", exc)
        return _error(name, sid, "yfinance", "context", exc)


def fetch_buffett_indicator() -> MarketIndicator:
    name, sid = "Buffett Indicator (Mkt Cap / GDP)", "BUFFETT"
    try:
        wilshire = fred_client.fetch_series("WILL5000PRFC")
        gdp = fred_client.fetch_series("GDP")
        if wilshire.empty or gdp.empty:
            raise ValueError("missing component series")
        # Resample wilshire to GDP's quarterly frequency (last value of quarter).
        wq = wilshire.resample("QE").last().dropna()
        gq = gdp.reindex(wq.index, method="ffill").dropna()
        ratio = (wq / gq).dropna()
        return _build(name, sid, "computed", "market", ratio)
    except Exception as exc:  # noqa: BLE001
        log.warning("Buffett indicator failed: %s", exc)
        return _error(name, sid, "computed", "market", exc)


def fetch_cape() -> MarketIndicator:
    name, sid = "Shiller CAPE (approx.)", "CAPE"
    try:
        # Approximation: S&P 500 monthly real price / 10y trailing avg of real S&P earnings proxy.
        # Without an earnings series we proxy via real S&P price / 10y rolling avg of real price.
        # This is a "real-price-stretch" measure — directionally equivalent to CAPE for our purpose.
        sp = _yf_history("^GSPC", period="max", interval="1mo")
        cpi = fred_client.fetch_series("CPIAUCSL")
        if sp.empty or cpi.empty:
            raise ValueError("missing component series")
        cpi = cpi.reindex(sp.index, method="ffill")
        latest_cpi = float(cpi.iloc[-1])
        real_price = sp * (latest_cpi / cpi)
        rolling = real_price.rolling(window=120, min_periods=60).mean()
        cape = (real_price / rolling).dropna()
        return _build(name, sid, "computed", "market", cape)
    except Exception as exc:  # noqa: BLE001
        log.warning("CAPE proxy failed: %s", exc)
        return _error(name, sid, "computed", "market", exc)


def fetch_aaii() -> MarketIndicator:
    name, sid = "AAII Bull-Bear Spread", "AAII"
    # AAII publishes weekly survey results; absent a stable free CSV endpoint
    # we mark this as not-available rather than scrape brittle HTML. Users can
    # populate it later via a custom hook.
    return MarketIndicator(
        name=name,
        series_id=sid,
        source="scrape",
        bucket="market",
        error="AAII feed not configured (see README for manual setup)",
    )


def fetch_margin_debt() -> MarketIndicator:
    name, sid = "Margin Debt YoY", "MARGIN_DEBT"
    try:
        # FRED mirrors FINRA margin debt as BOGZ1FL663067003Q (Securities credit, brokers/dealers).
        series = fred_client.fetch_series("BOGZ1FL663067003Q")
        if series.empty:
            raise ValueError("empty series")
        yoy = (series.pct_change(periods=4) * 100).dropna()
        return _build(name, sid, "fred", "market", yoy)
    except Exception as exc:  # noqa: BLE001
        log.warning("Margin debt failed: %s", exc)
        return _error(name, sid, "fred", "market", exc)


def fetch_put_call() -> MarketIndicator:
    name, sid = "CBOE Put/Call Ratio", "PUT_CALL"
    # ^CPC was delisted on Yahoo Finance; ^CPCE (equity-only) is the closest
    # available substitute. Fall back gracefully if that also disappears.
    for symbol in ("^CPCE", "^CPC"):
        try:
            data = _yf_history(symbol, period="5y")
            if data is not None and not data.empty:
                return _build(name, sid, "yfinance", "market", data)
        except Exception:  # noqa: BLE001
            continue
    exc = ValueError("No put/call data available from Yahoo Finance (^CPCE, ^CPC both failed)")
    log.warning("Put/Call failed: %s", exc)
    return _error(name, sid, "yfinance", "market", exc)


def fetch_mag7_concentration() -> MarketIndicator:
    name, sid = "Mag-7 Share of S&P 500 (price proxy)", "MAG7_CONCENTRATION"
    try:
        import yfinance as yf

        mag7 = ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA"]
        # yfinance multi-ticker download
        df = yf.download(
            mag7 + ["^GSPC"],
            period="5y",
            interval="1wk",
            auto_adjust=False,
            progress=False,
            group_by="ticker",
        )
        # Pull each ticker's close
        closes: dict[str, pd.Series] = {}
        for tkr in mag7 + ["^GSPC"]:
            try:
                closes[tkr] = df[tkr]["Close"].dropna()
            except (KeyError, AttributeError):
                continue
        if "^GSPC" not in closes or len(closes) < 5:
            raise ValueError("insufficient ticker data")
        # Equal-weighted rebased basket vs S&P 500 — proxy for relative dominance.
        spx = closes.pop("^GSPC")
        basket = pd.concat(closes.values(), axis=1).mean(axis=1).dropna()
        common = basket.index.intersection(spx.index)
        ratio = (basket.loc[common] / spx.loc[common]).dropna()
        ratio = ratio / ratio.iloc[0]  # rebase to 1.0 at start
        return _build(name, sid, "computed", "market", ratio)
    except Exception as exc:  # noqa: BLE001
        log.warning("Mag-7 concentration failed: %s", exc)
        return _error(name, sid, "computed", "market", exc)


def fetch_breadth_rsp_spy() -> MarketIndicator:
    name, sid = "Breadth (RSP / SPY)", "BREADTH_RSP_SPY"
    try:
        rsp = _yf_history("RSP", period="10y")
        spy = _yf_history("SPY", period="10y")
        if rsp.empty or spy.empty:
            raise ValueError("missing component")
        common = rsp.index.intersection(spy.index)
        ratio = (rsp.loc[common] / spy.loc[common]).dropna()
        return _build(name, sid, "computed", "market", ratio)
    except Exception as exc:  # noqa: BLE001
        log.warning("Breadth ratio failed: %s", exc)
        return _error(name, sid, "computed", "market", exc)


def fetch_t10y2y() -> MarketIndicator:
    name, sid = "10Y - 2Y Treasury Spread", "T10Y2Y"
    try:
        return _build(name, sid, "fred", "economy", fred_client.fetch_series("T10Y2Y"))
    except Exception as exc:  # noqa: BLE001
        log.warning("T10Y2Y failed: %s", exc)
        return _error(name, sid, "fred", "economy", exc)


def fetch_indpro() -> MarketIndicator:
    name, sid = "Industrial Production YoY %", "INDPRO"
    try:
        series = fred_client.fetch_series("INDPRO")
        if series.empty:
            raise ValueError("empty series")
        yoy = (series.pct_change(periods=12) * 100).dropna()
        return _build(name, sid, "fred", "economy", yoy)
    except Exception as exc:  # noqa: BLE001
        log.warning("INDPRO failed: %s", exc)
        return _error(name, sid, "fred", "economy", exc)


def fetch_unrate() -> MarketIndicator:
    name, sid = "Unemployment Rate", "UNRATE"
    try:
        return _build(name, sid, "fred", "economy", fred_client.fetch_series("UNRATE"))
    except Exception as exc:  # noqa: BLE001
        log.warning("UNRATE failed: %s", exc)
        return _error(name, sid, "fred", "economy", exc)


def fetch_icsa() -> MarketIndicator:
    name, sid = "Initial Jobless Claims", "ICSA"
    try:
        return _build(name, sid, "fred", "economy", fred_client.fetch_series("ICSA"))
    except Exception as exc:  # noqa: BLE001
        log.warning("ICSA failed: %s", exc)
        return _error(name, sid, "fred", "economy", exc)


def fetch_core_cpi_yoy() -> MarketIndicator:
    name, sid = "Core CPI YoY %", "CORE_CPI_YOY"
    try:
        series = fred_client.fetch_series("CPILFESL")
        if series.empty:
            raise ValueError("empty series")
        yoy = (series.pct_change(periods=12) * 100).dropna()
        return _build(name, sid, "fred", "economy", yoy)
    except Exception as exc:  # noqa: BLE001
        log.warning("Core CPI failed: %s", exc)
        return _error(name, sid, "fred", "economy", exc)


def fetch_real_retail_sales() -> MarketIndicator:
    name, sid = "Real Retail Sales YoY %", "REAL_RETAIL_SALES"
    try:
        series = fred_client.fetch_series("RRSFS")
        if series.empty:
            raise ValueError("empty series")
        yoy = (series.pct_change(periods=12) * 100).dropna()
        return _build(name, sid, "fred", "economy", yoy)
    except Exception as exc:  # noqa: BLE001
        log.warning("Real retail sales failed: %s", exc)
        return _error(name, sid, "fred", "economy", exc)


def fetch_m2_yoy() -> MarketIndicator:
    name, sid = "M2 YoY %", "M2_YOY"
    try:
        series = fred_client.fetch_series("M2SL")
        if series.empty:
            raise ValueError("empty series")
        yoy = (series.pct_change(periods=12) * 100).dropna()
        return _build(name, sid, "fred", "economy", yoy)
    except Exception as exc:  # noqa: BLE001
        log.warning("M2 failed: %s", exc)
        return _error(name, sid, "fred", "economy", exc)


# ---------------------------------------------------------------------------
# Registry & snapshot
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _Spec:
    fetcher: Callable[[], MarketIndicator]


INDICATOR_REGISTRY: dict[str, _Spec] = {
    "VIX": _Spec(fetch_vix),
    "BUFFETT": _Spec(fetch_buffett_indicator),
    "CAPE": _Spec(fetch_cape),
    "AAII": _Spec(fetch_aaii),
    "MARGIN_DEBT": _Spec(fetch_margin_debt),
    "PUT_CALL": _Spec(fetch_put_call),
    "MAG7_CONCENTRATION": _Spec(fetch_mag7_concentration),
    "BREADTH_RSP_SPY": _Spec(fetch_breadth_rsp_spy),
    "T10Y2Y": _Spec(fetch_t10y2y),
    "INDPRO": _Spec(fetch_indpro),
    "UNRATE": _Spec(fetch_unrate),
    "ICSA": _Spec(fetch_icsa),
    "CORE_CPI_YOY": _Spec(fetch_core_cpi_yoy),
    "REAL_RETAIL_SALES": _Spec(fetch_real_retail_sales),
    "M2_YOY": _Spec(fetch_m2_yoy),
}


def get_indicator(series_id: str, force: bool = False) -> MarketIndicator:
    if not force:
        cached = cache.get_indicator(series_id)
        if cached is not None:
            return cached
    spec = INDICATOR_REGISTRY[series_id]
    indicator = spec.fetcher()
    ttl = config.INDICATOR_TTLS.get(series_id, 21600)
    # Only cache successful fetches; errors should retry next call.
    if indicator.error is None:
        cache.set_indicator(series_id, indicator, ttl)
    return indicator


def get_snapshot(force: bool = False) -> MarketSnapshot:
    indicators: dict[str, MarketIndicator] = {}
    for series_id in INDICATOR_REGISTRY:
        indicators[series_id] = get_indicator(series_id, force=force)
    return MarketSnapshot(generated_at=_now(), indicators=indicators)
