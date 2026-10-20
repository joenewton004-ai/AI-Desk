import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "research"))
import weekly  # noqa: E402


def test_members_are_point_in_time():
    snaps = {pd.Timestamp("2020-03-31"): ["A"], pd.Timestamp("2020-06-30"): ["A", "B"]}
    assert weekly.members_at(snaps, pd.Timestamp("2020-05-01")) == ["A"]
    assert weekly.members_at(snaps, pd.Timestamp("2020-07-03")) == ["A", "B"]
    assert weekly.members_at(snaps, pd.Timestamp("2020-01-01")) == []


def test_pickers():
    r = pd.Series({"A": -0.10, "B": 0.05, "C": -0.02, "D": np.nan})
    assert weekly.pick_reversal(r, 2) == ["A", "C"]
    above = pd.Series({"A": False, "B": True, "C": True, "D": True})
    strength = pd.Series({"A": 0.9, "B": 0.1, "C": 0.8, "D": 0.7})
    assert weekly.pick_pullback(r, above, strength, 1) == ["C"]          # A is losing most but not in an uptrend
    assert weekly.pick_momentum(strength, above, 2) == ["C", "D"]


def test_simulate_earns_next_week_and_charges_turnover():
    idx = pd.date_range("2020-01-03", periods=4, freq="W-FRI")
    ret = pd.DataFrame({"A": [0, 0.10, 0.0, 0.0], "B": [0, 0.0, 0.20, 0.0]}, index=idx)
    picks = {idx[0]: ["A"], idx[1]: ["B"], idx[2]: ["B"], idx[3]: ["B"]}   # returns are earned between decisions
    r = weekly.simulate(picks, ret, cost=0.001)
    assert r[idx[1]] == 0.10 - 0.001                # bought A at the first close, earned A's next week
    assert abs(r[idx[2]] - (0.20 - 0.002)) < 1e-12  # swapped A for B: 200% turnover
    assert abs(r[idx[3]] - 0.0) < 1e-12 and len(r) == 3   # held B, no trade


def test_momentum_book_uses_only_the_past():
    rng = np.random.default_rng(2)
    idx = pd.date_range("2013-01-04", periods=150, freq="W-FRI")
    px = pd.DataFrame(100 * np.cumprod(1 + rng.normal(0.002, 0.04, (150, 6)), axis=0), index=idx, columns=list("ABCDEF"))
    snaps = {idx[0]: list("ABCDEF")}
    f = {"dates": idx[60:], "above": px > px.rolling(40, min_periods=40).mean()}
    base = weekly.momentum_book(px, snaps, f, lookback=26, n=2)
    future = px.copy()
    future.iloc[100:] *= np.linspace(0.3, 3, 50)[:, None] ** np.arange(1, 7)
    f2 = {"dates": idx[60:], "above": future > future.rolling(40, min_periods=40).mean()}
    changed = weekly.momentum_book(future, snaps, f2, lookback=26, n=2)
    assert all(base[d] == changed[d] for d in idx[60:100])
