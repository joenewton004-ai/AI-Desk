"""Performance statistics computed from a daily equity curve."""

from __future__ import annotations

import numpy as np
import pandas as pd

TRADING_DAYS = 252


def daily_rf(cash_rate, index: pd.DatetimeIndex) -> pd.Series | None:
    """T-bill return earned on each date in `index` (yesterday's annual rate / 252)."""
    if cash_rate is None:
        return None
    if not isinstance(cash_rate, pd.Series):
        return pd.Series(float(cash_rate) / TRADING_DAYS, index=index)
    return cash_rate.reindex(index).ffill().fillna(0.0).shift(1) / TRADING_DAYS


def max_drawdown(equity: pd.Series) -> float:
    """Largest peak-to-trough fall, as a negative fraction (e.g. -0.34)."""
    return float((equity / equity.cummax() - 1).min())


def summarize(equity: pd.Series, weights: pd.Series | None = None,
              n_trades: int | None = None, total_costs: float | None = None,
              rf_daily: pd.Series | None = None) -> dict:
    """rf_daily: the daily risk-free (T-bill) return. Sharpe and Sortino are
    measured on returns ABOVE it - earning T-bill interest isn't skill."""
    rets = equity.pct_change().dropna()
    excess = rets - (rf_daily.reindex(rets.index).fillna(0.0) if rf_daily is not None else 0.0)
    years = len(rets) / TRADING_DAYS
    total = equity.iloc[-1] / equity.iloc[0] - 1
    cagr = (equity.iloc[-1] / equity.iloc[0]) ** (1 / years) - 1 if years > 0 else np.nan
    vol = rets.std() * np.sqrt(TRADING_DAYS)
    downside = excess[excess < 0].std() * np.sqrt(TRADING_DAYS)
    mdd = max_drawdown(equity)
    out = {
        "start": equity.index[0].date().isoformat(),
        "end": equity.index[-1].date().isoformat(),
        "total_return": total,
        "cagr": cagr,
        "volatility": vol,
        # below 1e-9 the "volatility" is just floating-point rounding (e.g. a cash-only strategy)
        "sharpe": excess.mean() / excess.std() * np.sqrt(TRADING_DAYS) if excess.std() > 1e-9 else np.nan,
        "sortino": excess.mean() * TRADING_DAYS / downside if downside > 1e-9 else np.nan,
        "max_drawdown": mdd,
        "calmar": cagr / abs(mdd) if mdd < 0 else np.nan,
    }
    if weights is not None:
        out["time_in_market"] = float((weights.abs() > 1e-9).mean())
    if n_trades is not None:
        out["trades"] = n_trades
    if total_costs is not None:
        out["costs_pct_of_start"] = total_costs / equity.iloc[0]
    return out


PCT_KEYS = {"total_return", "cagr", "volatility", "max_drawdown", "time_in_market", "costs_pct_of_start"}


def format_table(rows: dict[str, dict]) -> str:
    """Render {label: metrics} as an aligned text table."""
    if not rows:
        return ""
    keys = list(next(iter(rows.values())).keys())
    labels = list(rows)
    width = max(len(k) for k in keys) + 2
    colw = max(14, *(len(l) + 2 for l in labels))

    def fmt(k, v):
        if isinstance(v, str):
            return v
        if v is None or (isinstance(v, float) and np.isnan(v)):
            return "n/a"
        if k in PCT_KEYS:
            return f"{v:.1%}"
        if k == "trades":
            return str(int(v))
        return f"{v:.2f}"

    lines = ["".ljust(width) + "".join(l.rjust(colw) for l in labels)]
    for k in keys:
        lines.append(k.ljust(width) + "".join(fmt(k, rows[l].get(k)).rjust(colw) for l in labels))
    return "\n".join(lines)
