import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "research"))
import overnight_safety as osf  # noqa: E402


def test_earnings_nights_follow_the_release_time():
    dates = pd.bdate_range("2026-10-19", periods=10)                       # Mon 19th ...
    acc = pd.Series(pd.to_datetime(["2026-10-20 16:05", "2026-10-21 07:00", "2026-10-21 12:00",
                                    "2026-10-24 10:00"]))                   # after close, pre-open, midday, Saturday
    n = osf.earnings_nights(acc, dates)
    assert list(n.strftime("%m-%d")) == ["10-21", "10-21", "10-26"]


def test_daily_capped_limits_each_group():
    idx = pd.bdate_range("2026-01-01", periods=2)
    score = pd.DataFrame([[5, 4, 3, 2, 1]] * 2, index=idx, columns=list("ABCDE"), dtype=float)
    elig = pd.DataFrame(True, index=idx, columns=score.columns)
    group = pd.Series({"A": 1, "B": 1, "C": 1, "D": 2, "E": 3})
    out = osf.daily_capped(score, elig, group, 3, 2)
    assert list(out.columns[out.iloc[0]]) == ["A", "B", "D"]
