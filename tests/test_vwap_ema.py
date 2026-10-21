import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "research"))
import vwap_ema as ve  # noqa: E402


def test_vwap_resets_each_day_and_ema_tracks():
    h = np.array([11.0, 12, 21, 22]); lo = np.array([9.0, 10, 19, 20]); c = np.array([10.0, 11, 20, 21])
    v = np.array([1.0, 3, 1, 1])
    vw = ve.vwap(h, lo, c, v, np.array([True, False, True, False]))
    assert vw[0] == 10 and abs(vw[1] - (10 + 3 * 11) / 4) < 1e-12 and vw[2] == 20     # day 2 starts afresh
    e = ve.ema(np.array([1.0, 1, 1, 10]), 3)
    assert e[2] == 1 and 1 < e[3] < 10


def test_crossover_enters_at_the_next_open_and_never_holds_overnight():
    o = np.array([10, 10, 11, 12, 13, 14.0]); h = o + 0.5; lo = o - 0.5; c = o + 0.2
    e9 = np.array([9, 9, 11, 12, 13, 14.0]); vw = np.full(6, 10.5)
    day = np.array([1, 1, 1, 1, 1, 1])
    t = ve.crossover_trades(o, h, lo, c, e9, vw, day, min_bar=1)
    assert len(t) == 1 and t[0]["entry"] == 12.0 and t[0]["why"] == "close" and t[0]["exit"] == c[-1]


def test_tmc_signal_needs_all_four_conditions():
    c = np.array([100.0, 103]); v = np.array([1.0, 3.0])
    e20, e50, vw = np.array([1.0, 2.0]), np.array([0.5, 1.0]), np.array([99.0, 101.0])
    assert ve.tmc_signal(c, v, e20, e50, vw, pdh=102.0, orh=104.0, k=1, avg_vol=1.5)
    assert not ve.tmc_signal(c, v, e20, e50, vw, pdh=102.0, orh=104.0, k=1, avg_vol=2.5)   # volume too low
    assert not ve.tmc_signal(c, v, e50, e20, vw, pdh=102.0, orh=104.0, k=1, avg_vol=1.5)   # EMAs inverted
