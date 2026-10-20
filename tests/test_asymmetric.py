import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "research"))
import asymmetric as a  # noqa: E402


def _setup():
    idx = pd.date_range("2020-01-31", periods=14, freq="ME")
    px = pd.DataFrame({"A": np.r_[np.linspace(100, 200, 12), 120, 125],      # hot industry, 40% off its high
                       "B": np.linspace(100, 130, 14),                          # same industry, near its high
                       "C": np.linspace(100, 90, 14)}, index=idx)               # cold industry
    snap = pd.DataFrame({"sic2": [36, 36, 20], "market_cap": [10e9, 40e9, 5e9], "revenue_$bn": [5, 4, 5],
                         "rev_growth_recent": [0.6, 0.3, 0.05]}, index=["A", "B", "C"])
    return px, snap, idx


def test_features_use_only_the_past_and_compare_with_peers():
    px, snap, idx = _setup()
    f = a.features(snap, px, idx[-1])
    assert abs(f.loc["A", "off_high"] - (125 / 200 - 1)) < 1e-12
    assert f.loc["A", "ps_vs_peers"] < 1 < f.loc["B", "ps_vs_peers"]        # A is cheaper than its peer B
    future = px.copy()
    future.loc[idx[-1] + pd.offsets.MonthEnd(1)] = [1, 1, 1]
    pd.testing.assert_frame_equal(f, a.features(snap, future, idx[-1]))


def test_pick_applies_the_rules():
    px, snap, idx = _setup()
    f = a.features(snap, px, idx[-1])
    f["theme"] = f["sic2"] == 36
    assert a.pick(f, n=5) == ["A"]                         # fast, cheaper than peers, off its high, hot industry
    assert "B" in a.pick(f, n=5, off_high=None, discount=False)
    assert a.latest_snapshot({pd.Timestamp("2020-03-31"): snap}, pd.Timestamp("2020-02-29")) is None
