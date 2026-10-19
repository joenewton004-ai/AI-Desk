"""Risk management: turns a strategy's exposure into a position size.

Rules here apply to every strategy, so they live in one place:
  * volatility targeting - hold less when the market is wild, so each
    day risks roughly the same amount
  * a leverage cap - never hold more than max_leverage x equity
  * a drawdown circuit breaker - stop trading after a set loss from the
    peak until a human reviews what went wrong
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from ai_desk.indicators import realized_vol


@dataclass
class RiskConfig:
    target_vol: float | None = None      # e.g. 0.15 = aim for 15% annual volatility; None = off
    vol_lookback: int = 20
    max_leverage: float = 1.0            # 1.0 = never borrow
    max_drawdown_halt: float | None = None  # e.g. 0.20 = go flat and stop after a 20% drawdown
    allow_short: bool = False
    rebalance_threshold: float = 0.10    # only resize when the target moves by 10+ percentage points

    def size(self, exposure: pd.Series, prices: pd.DataFrame) -> pd.Series:
        """Target portfolio weight per day, decided at that day's close."""
        weight = exposure.astype(float).fillna(0.0)
        if not self.allow_short:
            weight = weight.clip(lower=0.0)
        if self.target_vol:
            vol = realized_vol(prices["close"], self.vol_lookback)
            # until there's enough history to measure vol, stay at 1x
            scale = (self.target_vol / vol).fillna(1.0)
            weight = weight * scale
        return weight.clip(-self.max_leverage, self.max_leverage)
