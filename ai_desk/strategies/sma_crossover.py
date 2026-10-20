from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from ai_desk.indicators import sma
from ai_desk.strategies.base import Strategy


@dataclass
class SMACrossover(Strategy):
    """Hold while the fast moving average is above the slow one ("golden
    cross"), go to cash when it falls below ("death cross").

    Edge hypothesis: the same as trend following - long declines happen
    below the long average - but comparing two averages instead of price vs
    one average reacts more slowly, so it trades less (fewer whipsaws) at
    the cost of later exits and re-entries. 50/200 is the classic pair.
    """

    name = "sma_crossover"
    fast: int = 50
    slow: int = 200

    def __post_init__(self):
        if self.fast >= self.slow:
            raise ValueError("fast must be shorter than slow")

    def target_exposure(self, prices: pd.DataFrame) -> pd.Series:
        close = prices["close"]
        f, s = sma(close, self.fast), sma(close, self.slow)
        return (f > s).astype(float).where(s.notna(), 0.0)
