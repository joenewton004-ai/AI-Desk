import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "research"))
import tjr  # noqa: E402


def test_levels_use_only_bars_before_the_open():
    idx = pd.date_range("2026-10-01 18:00", "2026-10-02 12:00", freq="5min")
    b = pd.DataFrame({"Open": 100.0, "High": 101.0, "Low": 99.0, "Close": 100.0, "Volume": 1}, index=idx)
    b.loc["2026-10-02 03:00", "High"] = 120.0           # London high
    b.loc["2026-10-02 10:00", "High"] = 200.0           # after the open: must not count
    lv = tjr.levels(b, pd.Timestamp("2026-10-02"))
    assert lv["London high"] == 120.0 and lv["overnight high"] == 120.0 and max(lv.values()) < 200


def test_sweep_then_break_of_structure_gives_a_short():
    # bars: run up, sweep above 105 and close back below, then a close under the swing low (99)
    h = np.array([100, 101, 102, 106, 103, 101, 98], float)
    lo = np.array([99, 99.5, 100, 103, 100, 98.5, 96], float)
    c = np.array([100.5, 101, 101.5, 104, 101, 98.8, 97], float)
    o = c.copy()
    s = tjr.find_setup(o, h, lo, c, {"prior day high": 105.0, "prior day low": 90.0}, 3, 7, 3)
    assert s["side"] == -1 and s["sweep_bar"] == 3 and s["confirm_bar"] == 5 and s["extreme"] == 106


def test_no_setup_when_the_bar_closes_beyond_the_level():
    h = np.array([100, 101, 102, 106, 107], float)
    lo = np.array([99, 99.5, 100, 103, 105], float)
    c = np.array([100.5, 101, 101.5, 105.5, 106], float)      # closed above 105: a breakout, not a sweep
    assert tjr.find_setup(c, h, lo, c, {"prior day high": 105.0}, 3, 5, 3) is None


def test_opposite_target_is_the_nearest_level_at_least_1r_away():
    lv = {"a low": 95.0, "b low": 98.5, "c low": 90.0}
    assert tjr.opposite_target(lv, -1, 100.0, 2.0) == 95.0      # 98.5 is under 1R away
