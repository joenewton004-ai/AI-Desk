import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "research"))
import lookbacks as lb  # noqa: E402


def test_daily_top_picks_the_best_eligible_each_day():
    idx = pd.bdate_range("2024-01-01", periods=2)
    score = pd.DataFrame({"A": [3.0, 1.0], "B": [2.0, 2.0], "C": [1.0, 3.0], "D": [np.nan, 9.0]}, index=idx)
    el = pd.DataFrame(True, index=idx, columns=score.columns)
    el.loc[idx[1], "D"] = False
    p = lb.daily_top(score, el, n=2)
    assert p.iloc[0].tolist() == [True, True, False, False]
    assert p.iloc[1].tolist() == [False, True, True, False]        # D not eligible that day
