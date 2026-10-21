import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "research"))
import near_misses as nm  # noqa: E402


def test_gap_stats_and_rank_corr():
    s = nm.gap_stats(pd.Series([0.01, 0.02, -0.01, 0.03]))
    assert s["n"] == 4 and s["picks_won"] == 0.75 and s["t"] > 0
    a = pd.Series(range(10), dtype=float)
    assert abs(nm.rank_corr(a, a ** 2) - 1) < 1e-12
    assert np.isnan(nm.rank_corr(a[:3], a[:3]))


def test_forward_return_uses_the_closes_at_both_ends_only():
    idx = pd.to_datetime(["2020-01-31", "2020-02-29", "2020-03-31"])
    adj = pd.DataFrame({"A": [100.0, 50.0, 110.0], "B": [10.0, 10.0, 40.0 * 10]}, index=idx)
    r = nm.forward_return(adj, idx[0], idx[2], ["A", "B", "C"])
    assert abs(r["A"] - 0.10) < 1e-12 and np.isnan(r["B"]) and "C" not in r     # a 39x jump is treated as bad data
