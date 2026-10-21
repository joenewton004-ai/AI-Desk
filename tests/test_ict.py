import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "research"))
import ict  # noqa: E402


def test_fvg_detects_three_bar_gaps():
    h = np.array([10.0, 12.0, 14.0])
    lo = np.array([9.0, 10.5, 11.0])
    assert ict.fvg(h, lo, 2) == 1                     # bar 3's low (11) above bar 1's high (10)
    assert ict.fvg(-lo, -h, 2) == -1                  # the mirror image is bearish
    assert ict.fvg(h, lo, 1) == 0


def test_run_trade_assumes_the_stop_when_a_bar_touches_both():
    o = np.array([100.0, 100.0])
    h = np.array([100.5, 104.0])
    lo = np.array([99.5, 97.0])
    c = np.array([100.0, 101.0])
    tr = ict.run_trade(o, h, lo, c, 1, 1, 100.0, 98.0, 104.0, limit=False)
    assert tr["why"] == "stop" and tr["R"] == -1.0


def test_limit_entry_waits_for_the_price_and_expires():
    o = np.array([105.0, 104.0, 103.0, 102.0])
    h = o + 0.5
    lo = o - 0.5
    c = o.copy()
    assert ict.run_trade(o, h, lo, c, 0, 1, 100.0, 98.0, 106.0, limit=True, fill_by=3) is None
    tr = ict.run_trade(o, h, lo, c, 0, 1, 103.0, 101.0, 107.0, limit=True, fill_by=3)
    assert tr["bar_in"] == 2 and tr["entry"] == 103.0     # bar 1's low is 103.5; bar 2 reaches down to 102.5

def test_judas_fades_a_first_hour_sweep_that_closes_back_inside():
    idx = pd.date_range("2026-01-05 09:30", periods=4, freq="h")
    day = pd.DataFrame({"open": [100, 99, 98, 97], "high": [103, 99.5, 98.5, 97.5], "low": [99, 98, 97, 96],
                        "close": [99.5, 98, 97, 96.5]}, index=idx, dtype=float)
    tr = ict.judas(day, pdh=102.0, pdl=95.0)
    assert tr["side"] == -1 and tr["entry"] == 99.0       # short at the 10:30 open, stop at the sweep high (103)
    assert ict.judas(day, pdh=104.0, pdl=95.0) is None    # no sweep, no trade
