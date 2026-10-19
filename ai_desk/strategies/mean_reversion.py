from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from ai_desk.indicators import rsi, sma
from ai_desk.strategies.base import Strategy


@dataclass
class RSIMeanReversion(Strategy):
    """Buy short, sharp pullbacks inside an uptrend; sell the bounce.

    Edge hypothesis: in a long-term uptrend, indices tend to rebound after a
    few days of heavy selling (short-term overreaction). Enter when the
    short RSI is very low and price is above the trend average; exit when
    price closes back above a short average, or the trend breaks.

    It's in the market only a fraction of the time, so it pairs well with
    other strategies - but its edge is known and has weakened over time.
    """

    name = "rsi_reversion"
    rsi_window: int = 2
    entry_rsi: float = 10.0
    exit_sma: int = 5
    trend_sma: int = 200

    def target_exposure(self, prices: pd.DataFrame) -> pd.Series:
        close = prices["close"]
        r = rsi(close, self.rsi_window)
        exit_avg = sma(close, self.exit_sma)
        trend_avg = sma(close, self.trend_sma)
        out, held = [], 0.0
        for c, ri, ea, ta in zip(close.to_numpy(), r.to_numpy(),
                                 exit_avg.to_numpy(), trend_avg.to_numpy()):
            if ta != ta or ri != ri or ea != ea:
                held = 0.0
            elif held == 0.0 and ri < self.entry_rsi and c > ta:
                held = 1.0
            elif held == 1.0 and (c > ea or c < ta):
                held = 0.0
            out.append(held)
        return pd.Series(out, index=prices.index)
