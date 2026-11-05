import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "research"))

import overnight_timing as ot  # noqa: E402


def _nights(n=400, seed=0):
    idx = pd.bdate_range("2020-01-01", periods=n)
    return pd.Series(np.random.default_rng(seed).normal(0.001, 0.01, n), index=idx)


def test_own_trend_and_vol_scale_ignore_the_night_they_size():
    r = _nights()
    t0, s0 = ot.own_trend(r), ot.vol_scale(r)
    r2 = r.copy()
    r2.iloc[300:] = -0.5                                   # wreck night 300 onward
    t1, s1 = ot.own_trend(r2), ot.vol_scale(r2)
    assert np.allclose(t0.iloc[:301].fillna(0), t1.iloc[:301].fillna(0))   # night 300 itself not used
    assert np.allclose(s0.iloc[:301], s1.iloc[:301])
    assert (s0 <= 1).all() and (s0 > 0).all()


def test_breadth_and_weekend():
    idx = pd.bdate_range("2024-01-01", periods=60)
    close = pd.DataFrame({"A": np.linspace(1, 2, 60), "B": np.linspace(2, 1, 60)}, index=idx)
    b = ot.breadth(close, pd.DataFrame(True, index=idx, columns=["A", "B"]))
    assert b.iloc[-1] == 0.5
    w = ot.weekend(idx)
    assert w[pd.Timestamp("2024-01-08")] and not w[pd.Timestamp("2024-01-09")]
