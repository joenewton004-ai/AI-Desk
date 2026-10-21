import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "research"))
import overnight as ov  # noqa: E402


def test_split_returns_and_annualising():
    idx = pd.date_range("2026-01-05", periods=3, freq="B")
    o = pd.DataFrame({"A": [100.0, 102, 99]}, index=idx)
    c = pd.DataFrame({"A": [101.0, 100, 103]}, index=idx)
    on, day = ov.split_returns(o, c)
    assert np.isnan(on.iloc[0, 0]) and abs(on.iloc[1, 0] - (102 / 101 - 1)) < 1e-12
    assert abs(day.iloc[2, 0] - (103 / 99 - 1)) < 1e-12
    assert abs(ov.ann(0.0) - 0.0) < 1e-12 and ov.ann(0.001) > 0.28


def test_monthly_picks_only_use_scores_from_an_earlier_month_end():
    idx = pd.bdate_range("2026-01-26", "2026-02-27")
    score = pd.DataFrame({"A": 1.0, "B": 2.0}, index=idx)
    score.loc["2026-02-02":, "A"] = 5.0                   # A becomes best in February...
    elig = pd.DataFrame(True, index=idx, columns=["A", "B"])
    pick = ov.monthly_picks(score, elig, 1)
    assert not pick.loc[:"2026-01-30"].any().any()        # nothing held before the first month-end
    assert pick.loc["2026-02-02":"2026-02-27", "B"].all()  # ...but February holds January's pick (B)
    assert not pick.loc["2026-02-02":, "A"].any()
