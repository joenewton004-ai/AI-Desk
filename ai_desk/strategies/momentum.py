from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from ai_desk.strategies.base import Strategy


@dataclass
class TimeSeriesMomentum(Strategy):
    """Hold the index while its trailing return is positive, else cash.

    Edge hypothesis: "time-series momentum" - assets that have risen over the
    past ~12 months tend to keep rising, and long bear markets show up as a
    negative 12-month return. Documented across asset classes back to the
    1880s (Moskowitz, Ooi & Pedersen 2012; Hurst, Ooi & Pedersen 2017).

    The signal is only checked on the first trading day of each month, so it
    trades rarely (low costs) and isn't whipsawed by daily noise.
    """

    name = "momentum"
    lookback: int = 252          # trading days (~12 months)
    skip: int = 0                # skip the most recent N days (some research skips 1 month)
    monthly: bool = True

    def target_exposure(self, prices: pd.DataFrame) -> pd.Series:
        close = prices["close"]
        past = close.shift(self.skip)
        ret = past / close.shift(self.lookback) - 1
        signal = (ret > 0).astype(float).where(ret.notna(), 0.0)
        if not self.monthly:
            return signal
        # only update on the first trading day of a month (known without peeking ahead)
        idx = prices.index
        new_month = pd.Series(idx.month, index=idx).diff().fillna(1) != 0
        return signal.where(new_month).ffill().fillna(0.0)
