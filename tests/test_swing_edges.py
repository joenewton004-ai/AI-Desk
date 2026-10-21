import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "research"))
import swing_edges as se  # noqa: E402


def test_week_ends_marks_the_last_trading_day_of_each_week():
    d = pd.to_datetime(["2026-10-12", "2026-10-13", "2026-10-16", "2026-10-19", "2026-10-22"])
    assert list(se.week_ends(pd.DatetimeIndex(d))) == [False, False, True, False, True]


def test_sue_uses_only_earlier_quarters_spread():
    idx = pd.date_range("2020-03-31", periods=14, freq="QE")
    ni = pd.Series([10, 11, 12, 13, 11, 13, 12, 15, 13, 12, 15, 14, 16, 30.0], index=idx)
    q = se.sue(pd.DataFrame({"net_income": ni, "filed": idx}))
    spread_before = q["yoy"].iloc[:-1].tail(8).std()
    assert abs(q["sue"].iloc[-1] - (30 - ni.iloc[-5]) / spread_before) < 1e-9     # last quarter's own change isn't in its spread
    assert q["sue"].iloc[:8].isna().all()


def test_overnight_split_multiplies_back_to_close_to_close():
    o = pd.Series([100.0, 102, 101])
    c = pd.Series([101.0, 103, 100])
    on, day = se.overnight_split(o, c)
    total = (1 + on) * (1 + day) - 1
    assert np.allclose(total.iloc[1:], (c / c.shift(1) - 1).iloc[1:])


def test_orb_long_after_an_up_first_bar_with_worst_and_best_case_stops():
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "research"))
    import orb
    idx = pd.date_range("2026-10-01 09:30", periods=8, freq="5min")
    day = pd.DataFrame({"open": [100, 101, 102, 103, 104, 105, 106, 107],
                        "high": [101, 102.5, 103, 104, 105, 106, 107, 108],
                        "low": [99.5, 99.0, 101.5, 102.5, 103.5, 104.5, 105.5, 106.5],
                        "close": [100.8, 102, 102.8, 103.8, 104.8, 105.8, 106.8, 107.8]}, index=idx, dtype=float)
    worst = orb.orb_trade(day, atr=10.0)                  # stop 1.0 below the 101 entry; bar 1 dips to 99
    assert worst["side"] == 1 and worst["entry"] == 101.0 and worst["why"] == "stop"
    best = orb.orb_trade(day, atr=10.0, optimistic=True)  # the stop is only checked from the next bar
    assert best["why"] == "close" and abs(best["R"] - (107.8 - 101) / 1.0) < 1e-9
