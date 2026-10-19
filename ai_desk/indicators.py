"""Technical indicators. Each value at date t uses only data up to and including t."""

from __future__ import annotations

import numpy as np
import pandas as pd

TRADING_DAYS = 252


def sma(series: pd.Series, window: int) -> pd.Series:
    return series.rolling(window, min_periods=window).mean()


def rsi(series: pd.Series, window: int = 14) -> pd.Series:
    """Wilder's Relative Strength Index, 0-100."""
    delta = series.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / window, adjust=False, min_periods=window).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / window, adjust=False, min_periods=window).mean()
    rs = gain / loss.replace(0, np.nan)
    out = 100 - 100 / (1 + rs)
    return out.where(loss != 0, 100.0).where(gain.notna())


def realized_vol(close: pd.Series, window: int = 20) -> pd.Series:
    """Annualised volatility of daily log returns over a rolling window."""
    log_ret = np.log(close).diff()
    return log_ret.rolling(window, min_periods=window).std() * np.sqrt(TRADING_DAYS)
