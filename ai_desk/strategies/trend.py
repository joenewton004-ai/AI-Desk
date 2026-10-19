from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from ai_desk.indicators import sma
from ai_desk.strategies.base import Strategy


@dataclass
class TrendFollowing(Strategy):
    """Hold the index while it trades above its long moving average, else cash.

    Edge hypothesis: markets trend, and the worst crashes (2000-02, 2008)
    tend to happen below the 200-day average. The aim is not to beat
    buy & hold in a bull market - it usually lags - but to cut the deepest
    drawdowns. `band` adds a buffer around the average so small wiggles
    across the line don't trigger trades (fewer whipsaws, lower costs).
    """

    name = "trend"
    lookback: int = 200
    band: float = 0.01

    def target_exposure(self, prices: pd.DataFrame) -> pd.Series:
        close = prices["close"]
        avg = sma(close, self.lookback)
        out, held = [], 0.0
        for c, a in zip(close.to_numpy(), avg.to_numpy()):
            if a != a:  # NaN during warm-up
                held = 0.0
            elif held == 0.0 and c > a * (1 + self.band):
                held = 1.0
            elif held == 1.0 and c < a * (1 - self.band):
                held = 0.0
            out.append(held)
        return pd.Series(out, index=prices.index)
