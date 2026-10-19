from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from ai_desk.strategies.base import Strategy


@dataclass
class VixFilter(Strategy):
    """Hold the index while the VIX "fear gauge" is calm, step aside when it spikes.

    Edge hypothesis: high-volatility regimes have worse risk-adjusted returns
    (volatility clusters, crashes happen in high-vol regimes). Exit when VIX
    closes above `exit_above`, re-enter once it calms below `enter_below`.
    The gap between them stops it flipping in and out every day.

    Caution: the best rebound days also happen when VIX is high, so this can
    miss recoveries. That's exactly what the backtest has to settle.
    """

    name = "vix_filter"
    requires = ("vix",)
    exit_above: float = 30.0
    enter_below: float = 22.0

    def target_exposure(self, prices: pd.DataFrame) -> pd.Series:
        vix = prices["vix"].ffill().to_numpy()
        out, held = [], 0.0
        for v in vix:
            if v != v:
                held = 0.0
            elif held == 0.0 and v < self.enter_below:
                held = 1.0
            elif held == 1.0 and v > self.exit_above:
                held = 0.0
            out.append(held)
        return pd.Series(out, index=prices.index)
