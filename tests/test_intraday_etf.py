import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "research"))

import intraday_etf as ie  # noqa: E402

N = ie.N


def make(paths):
    """A grid from one close path per day (open = previous minute's close, high/low = +-0.01)."""
    c = np.array(paths, dtype=float)
    o = np.c_[c[:, :1], c[:, :-1]]
    return {"open": o, "high": np.maximum(o, c) + 0.01, "low": np.minimum(o, c) - 0.01, "close": c,
            "volume": np.ones_like(c), "days": pd.bdate_range("2026-01-05", periods=len(c))}


def test_momentum_10am_trades_the_last_half_hour_in_the_morning_direction():
    day1 = np.full(N, 100.0)
    day2 = np.full(N, 100.0)
    day2[29:] = 101.0                                  # up by 10:00
    day2[359:] = 101.0
    day2[N - 1] = 102.0                                # the last half hour rises
    t = ie.trades(make([day1, day2]), "momentum_10am", 0.0)
    assert list(t["dir"]) == [1.0] and abs(t["net"].iloc[0] - (102 / 101 - 1)) < 1e-12


def test_gap_fade_exits_at_yesterdays_close_when_the_gap_fills():
    day1 = np.full(N, 100.0)
    day2 = np.full(N, 100.5)                           # opens +0.5%
    day2[0] = 100.5
    day2[30:] = 99.9                                   # falls back through yesterday's close
    g = make([day1, day2])
    g["open"][1, 0] = 100.5
    t = ie.trades(g, "gap_fade", 0.0)
    assert list(t["dir"]) == [-1.0]
    assert abs(t["net"].iloc[0] - (-(100.0 / 100.5 - 1))) < 1e-12      # short at 100.5, covered at 100.0


def test_orb_both_mirrors_the_short_side():
    up = np.r_[np.full(15, 100.0), np.linspace(100.0, 103.0, N - 15)]
    down = np.r_[np.full(15, 100.0), np.linspace(100.0, 97.0, N - 15)]
    gu, gd = make([up]), make([down])
    for g in (gu, gd):                                  # a realistic opening range: 99.9-100.1
        g["high"][:, :15], g["low"][:, :15] = 100.1, 99.9
    tu = ie.trades(gu, "orb_both", 0.0)
    td = ie.trades(gd, "orb_both", 0.0)
    assert list(tu["dir"]) == [1] and list(td["dir"]) == [-1]
    assert abs(tu["net"].iloc[0] - td["net"].iloc[0]) < 2e-3            # same size of move, both profitable
    assert tu["net"].iloc[0] > 0 and td["net"].iloc[0] > 0


def test_costs_are_charged_both_ways():
    day = np.r_[np.full(N - 1, 100.0), 101.0]
    a = ie.trades(make([day]), "long_day", 0.0)["net"].iloc[0]
    b = ie.trades(make([day]), "long_day", 0.001)["net"].iloc[0]
    assert abs((a - b) - 0.002) < 1e-12
