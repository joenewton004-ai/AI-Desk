"""Daily backtest for multi-asset portfolio methods.

Same rules as the single-asset engine (ai_desk/backtest.py):
  * weights decided at the close of day t, traded at the open of day t+1
  * overnight (close t -> open t+1) the OLD weights apply
  * costs on every change in weight; weights below `rebalance_threshold`
    of change are left alone (entries and full exits always trade)
  * uninvested cash earns the T-bill rate; shorts pay a borrow fee
Simplification: like the single-asset engine, weights are treated as
constant fractions of equity between trades (as if rebalanced for free).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from ai_desk.backtest import CostModel
from ai_desk.metrics import daily_rf, summarize
from ai_desk.portfolio.methods import Method


@dataclass
class PortfolioResult:
    method: str
    equity: pd.Series
    weights: pd.DataFrame          # weights actually held each day
    trades: pd.DataFrame
    metrics: dict


def run_portfolio_backtest(method: Method, prices: dict[str, pd.DataFrame], costs: CostModel | None = None,
                           cash_rate: pd.Series | float | None = None, start=None,
                           borrow_fee: float = 0.005, rebalance_threshold: float = 0.02,
                           initial_equity: float = 100_000.0) -> PortfolioResult:
    if not method.backtestable:
        raise ValueError(f"{method.name} can't be backtested from prices alone "
                         "(the stock screen's history needs research/screen_backtest.py)")
    costs = costs or CostModel()
    opens, closes = prices["open"], prices["close"]
    target = method.weights(closes).reindex(index=closes.index, columns=closes.columns).fillna(0.0)
    if not method.can_short and (target < -1e-12).any().any():
        raise ValueError(f"{method.name} produced short weights but is long-only")

    dates = closes.index
    begin = 0 if start is None else int(dates.searchsorted(pd.Timestamp(start)))
    o, c, t = opens.to_numpy(), closes.to_numpy(), target.to_numpy()
    if isinstance(cash_rate, pd.Series):
        rate = cash_rate.reindex(dates).ffill().fillna(0.0).to_numpy()
    else:
        rate = np.full(len(dates), float(cash_rate or 0.0))

    equity = initial_equity
    w = np.zeros(c.shape[1])
    pending = w.copy()
    eq_out, w_out, trades = [], [], []
    for i in range(begin, len(dates)):
        if i > begin:
            cash = 1 - w.sum()                                   # shorts add cash (their proceeds)
            equity *= 1 + cash * rate[i - 1] / 252 - np.abs(np.minimum(w, 0)).sum() * borrow_fee / 252
            equity *= 1 + (w * (o[i] / c[i - 1] - 1)).sum()       # overnight, old weights
            change = pending - w
            trade = (change != 0) & ((np.abs(change) >= rebalance_threshold) | (pending == 0) | (w == 0))
            if trade.any():
                new_w = np.where(trade, pending, w)
                turnover = np.abs(new_w - w).sum()
                cost = turnover * equity * costs.rate
                equity -= cost
                for j in np.flatnonzero(trade):
                    trades.append({"date": dates[i], "symbol": closes.columns[j], "from": w[j], "to": new_w[j]})
                w = new_w
            equity *= 1 + (w * (c[i] / o[i] - 1)).sum()          # intraday, new weights
        eq_out.append(equity)
        w_out.append(w.copy())
        pending = np.nan_to_num(t[i])

    idx = dates[begin:]
    eq = pd.Series(eq_out, index=idx, name="equity")
    held = pd.DataFrame(w_out, index=idx, columns=closes.columns)
    tr = pd.DataFrame(trades, columns=["date", "symbol", "from", "to"])
    m = summarize(eq, held.abs().sum(axis=1), n_trades=len(tr),
                  rf_daily=daily_rf(cash_rate, idx) if cash_rate is not None else None)
    m["avg_gross_exposure"] = float(held.abs().sum(axis=1).mean())
    m["avg_net_exposure"] = float(held.sum(axis=1).mean())
    return PortfolioResult(method.describe(), eq, held, tr, m)


def buy_and_hold(symbols: list[str], prices: dict[str, pd.DataFrame], **kw) -> PortfolioResult:
    """Benchmark: equal weight in every symbol, always invested."""
    from ai_desk.portfolio.methods import Method

    class _EqualWeight(Method):
        name = "buy_hold_equal_weight"

        def symbols(self):
            return symbols

        def weights(self, closes):
            return pd.DataFrame(1 / len(symbols), index=closes.index, columns=symbols)

        def describe(self):
            return f"equal-weight buy & hold of {', '.join(symbols)}"

    return run_portfolio_backtest(_EqualWeight(), prices, **kw)
