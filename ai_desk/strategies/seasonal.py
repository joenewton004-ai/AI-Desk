from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from pandas.tseries.offsets import BDay

from ai_desk.strategies.base import Strategy


@dataclass
class TurnOfMonth(Strategy):
    """Hold the index only around the turn of each month, cash otherwise.

    Edge hypothesis: a large share of stock returns has historically come in
    the last trading day and first few trading days of the month (pay-day and
    pension inflows, month-end window dressing). Ariel 1987; Lakonishok &
    Smidt 1988; McConnell & Xu 2008.

    Uses the business-day calendar only (known in advance), never the price
    data's own future dates. Holidays are ignored, so it's off by a day now
    and then - fine for testing the idea.
    """

    name = "turn_of_month"
    days_before: int = 1    # last N trading days of the month
    days_after: int = 3     # first N trading days of the next month

    def target_exposure(self, prices: pd.DataFrame) -> pd.Series:
        # exposure decided at close t applies to the next business day
        nxt = (prices.index + BDay(1)).values.astype("datetime64[D]")
        month_start = nxt.astype("datetime64[M]").astype("datetime64[D]")
        next_month = (nxt.astype("datetime64[M]") + np.timedelta64(1, "M")).astype("datetime64[D]")
        day_of_month = np.busday_count(month_start, nxt) + 1    # 1 = first trading day
        days_left = np.busday_count(nxt, next_month)           # 1 = last trading day
        hold = (day_of_month <= self.days_after) | (days_left <= self.days_before)
        return pd.Series(hold.astype(float), index=prices.index)
