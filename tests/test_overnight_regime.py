import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "research"))
import overnight_regime as orr  # noqa: E402


def test_capped_picks_limits_one_industry():
    idx = pd.bdate_range("2024-01-29", periods=4)                 # includes the Jan month-end
    score = pd.DataFrame([[5, 4, 3, 2, 1]] * 4, index=idx, columns=list("ABCDE"), dtype=float)
    el = pd.DataFrame(True, index=idx, columns=score.columns)
    grp = pd.Series({"A": 36, "B": 36, "C": 36, "D": 49, "E": 20})
    p = orr.capped_picks(score, el, grp, n=3, cap=2)
    assert not p.iloc[0].any()                                     # nothing held before the first month-end
    assert p.iloc[-1][["A", "B", "D"]].all() and not p.iloc[-1]["C"]   # C would be a third from industry 36


def test_switch_uses_the_alternative_only_on_signal_nights():
    idx = pd.bdate_range("2024-01-01", periods=3)
    base, alt = pd.Series([0.01, 0.02, 0.03], idx), pd.Series([0.0, 0.0, 0.0], idx)
    out = orr.switch(base, alt, pd.Series([False, True, np.nan], idx))
    assert list(out) == [0.01, 0.0, 0.03]


def test_nightly_charges_both_sides_only_when_invested():
    idx = pd.bdate_range("2024-01-01", periods=2)
    on = pd.DataFrame({"A": [0.01, 0.02]}, index=idx)
    pick = pd.DataFrame({"A": [True, False]}, index=idx)
    r = orr.nightly(on, pick, 0.0002)
    assert abs(r.iloc[0] - 0.0096) < 1e-12 and r.iloc[1] == 0.0
