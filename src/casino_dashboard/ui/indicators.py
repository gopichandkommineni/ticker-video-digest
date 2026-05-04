"""Pure functions for computing technical indicators from a price Series."""
import pandas as pd


def compute_sma(prices: pd.Series, window: int) -> pd.Series:
    """Simple moving average. First (window-1) values are NaN."""
    return prices.rolling(window=window, min_periods=window).mean()


def compute_rsi(prices: pd.Series, window: int = 14) -> pd.Series:
    """14-day RSI using Wilder's smoothing (exponential with alpha=1/window).

    First `window` values are NaN. Returns values in [0, 100].
    A flat series (zero delta everywhere) returns NaN (RS is 0/0).
    """
    delta = prices.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)

    # Wilder's smoothing: first value is SMA, then exponential
    avg_gain = gain.ewm(alpha=1 / window, min_periods=window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / window, min_periods=window, adjust=False).mean()

    # Replace zero avg_loss with NaN to avoid divide-by-zero; we'll fix pure-bull after
    rs = avg_gain / avg_loss.replace(0.0, float("nan"))
    rsi = 100.0 - (100.0 / (1.0 + rs))

    # avg_loss==0 and avg_gain>0 → all gains → RSI=100
    rsi[(avg_loss == 0) & (avg_gain > 0)] = 100.0
    # avg_loss==0 and avg_gain==0 → flat → RSI=NaN (already NaN from above)
    return rsi


def compute_bollinger(
    prices: pd.Series, window: int = 20, num_std: float = 2.0
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Bollinger Bands. Returns (middle, upper, lower) — all same length as input."""
    middle = compute_sma(prices, window)
    rolling_std = prices.rolling(window=window, min_periods=window).std()
    upper = middle + num_std * rolling_std
    lower = middle - num_std * rolling_std
    return middle, upper, lower
