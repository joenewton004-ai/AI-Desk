"""Daily backtester.

Timing (this is where most home-made backtests cheat by accident):
  1. At the close of day t the strategy sees prices up to t and picks a target.
  2. The trade is filled at the OPEN of day t+1, paying commission + slippage.
  3. Overnight (close t -> open t+1) you still hold the OLD position.

So a signal can never profit from the same bar it was computed on.

Simplification: the position is treated as a constant fraction of equity
(as if rebalanced daily for free). Costs are charged only when the target
weight changes by at least risk.rebalance_threshold (entries and full exits
always trade). This is fine for daily index strategies.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from ai_desk.metrics import summarize
from ai_desk.risk import RiskConfig
from ai_desk.strategies.base import Strategy


@dataclass
class CostModel:
    commission_bps: float = 1.0   # 1 bp = 0.01% of the traded amount
    slippage_bps: float = 2.0     # gap between the quoted price and your fill

    @property
    def rate(self) -> float:
        return (self.commission_bps + self.slippage_bps) / 10_000


@dataclass
class BacktestResult:
    strategy: str
    equity: pd.Series
    weights: pd.Series
    trades: pd.DataFrame
    metrics: dict = field(default_factory=dict)
    halted_on: pd.Timestamp | None = None


def run_backtest(prices: pd.DataFrame, strategy: Strategy, risk: RiskConfig | None = None,
                 costs: CostModel | None = None, start: str | pd.Timestamp | None = None,
                 initial_equity: float = 100_000.0) -> BacktestResult:
    """Simulate a strategy. Indicators see all history, but trading and scoring
    begin at `start` - this lets warm-up periods (e.g. a 200-day average) use
    earlier data without counting it as performance."""
    risk = risk or RiskConfig()
    costs = costs or CostModel()

    target = risk.size(strategy.target_exposure(prices), prices)
    begin = 0 if start is None else int(prices.index.searchsorted(pd.Timestamp(start)))
    if begin >= len(prices) - 1:
        raise ValueError("not enough data after the start date to run a backtest")

    opens = prices["open"].to_numpy()
    closes = prices["close"].to_numpy()
    tgt = np.nan_to_num(target.to_numpy())
    dates = prices.index

    equity, weight, peak = initial_equity, 0.0, initial_equity
    pending = 0.0
    halted_on = None
    eq_out, w_out, trades = [], [], []

    for i in range(begin, len(prices)):
        if i > begin:
            equity *= 1 + weight * (opens[i] / closes[i - 1] - 1)   # overnight, old position
            small = abs(pending - weight) < risk.rebalance_threshold and pending != 0 and weight != 0
            if pending != weight and not small:                     # fill at the open
                cost = abs(pending - weight) * equity * costs.rate
                equity -= cost
                trades.append({"date": dates[i], "price": opens[i], "from_weight": weight,
                               "to_weight": pending, "cost": cost})
                weight = pending
            equity *= 1 + weight * (closes[i] / opens[i] - 1)       # intraday, new position
        eq_out.append(equity)
        w_out.append(weight)

        # end of day: risk checks, then decide tomorrow's target
        peak = max(peak, equity)
        if (halted_on is None and risk.max_drawdown_halt is not None
                and equity / peak - 1 <= -risk.max_drawdown_halt):
            halted_on = dates[i]
        pending = 0.0 if halted_on is not None else float(tgt[i])

    idx = dates[begin:]
    eq = pd.Series(eq_out, index=idx, name="equity")
    w = pd.Series(w_out, index=idx, name="weight")
    tr = pd.DataFrame(trades, columns=["date", "price", "from_weight", "to_weight", "cost"])
    metrics = summarize(eq, w, n_trades=len(tr), total_costs=float(tr["cost"].sum()))
    return BacktestResult(strategy.describe(), eq, w, tr, metrics, halted_on)
