import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "research"))
import leveraged as lv  # noqa: E402


def test_trend_signal_has_hysteresis_and_no_lookahead():
    c = pd.Series([100.0] * 5 + [102, 100.5, 99.5, 98.0], index=pd.bdate_range("2020-01-01", periods=9))
    s = lv.trend_signal(c, n=5, band=0.01)
    assert list(s) == [0, 0, 0, 0, 0, 1, 1, 1, 0]               # in above +1%, out only below -1%
    full = lv.trend_signal(pd.concat([c, pd.Series([200.0], index=[pd.Timestamp("2020-01-14")])]), n=5)
    assert list(full.iloc[:9]) == list(s)


def test_simulate_fills_at_the_next_open_and_charges_leverage_costs():
    idx = pd.bdate_range("2021-01-04", periods=4)
    o = pd.Series([100.0, 100, 110, 110], index=idx)
    c = pd.Series([100.0, 100, 110, 110], index=idx)
    rf = pd.Series(0.0, index=idx)
    lev = pd.Series([3.0, 3.0, 3.0, 3.0], index=idx)
    eq, w = lv.simulate(o, c, lev, rf, 3, cost=0.0)
    assert w.iloc[0] == 0 and w.iloc[1] == 3                    # decided at day 0's close, held from day 1's open
    gross = 1 + 3 * 0.10                                        # day 2's 10% gap overnight, at 3x
    assert eq.iloc[2] < gross and eq.iloc[2] > gross - 0.001    # minus a little fee drag


def test_stop_exits_and_waits_for_the_reentry_signal():
    idx = pd.bdate_range("2021-01-04", periods=6)
    o = pd.Series([100.0, 100, 95, 95, 95, 95], index=idx)
    c = o.copy()
    rf = pd.Series(0.0, index=idx)
    lev = pd.Series(3.0, index=idx)
    re = pd.Series([False, False, False, False, True, True], index=idx)
    eq, w = lv.simulate(o, c, lev, rf, 3, cost=0.0, stop=0.10, reentry=re)
    assert list(w) == [0, 3, 3, 0, 0, 3]                        # -15% on day 2 -> out from day 3; back after re-entry
