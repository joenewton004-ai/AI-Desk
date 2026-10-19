from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from ai_desk.strategies.base import Strategy


@dataclass
class BuyAndHold(Strategy):
    """The benchmark. Any strategy worth running must beat this after costs,
    or deliver similar returns with clearly lower risk."""

    name = "buy_hold"

    def target_exposure(self, prices: pd.DataFrame) -> pd.Series:
        return pd.Series(1.0, index=prices.index)
