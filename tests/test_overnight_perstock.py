import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "research"))
import overnight_perstock as ops  # noqa: E402


def _data():
    idx = pd.bdate_range("2024-01-01", periods=2)
    on = pd.DataFrame({"A": [0.01, 0.02], "B": [-0.02, 0.0]}, index=idx)
    held = pd.DataFrame(True, index=idx, columns=["A", "B"])
    rf = pd.Series(0.0001, index=idx)
    return on, held, rf


def test_skipped_slices_earn_cash_or_are_spread():
    on, held, rf = _data()
    skip = pd.DataFrame({"A": [False, False], "B": [True, False]}, index=on.index)
    cash = ops.book_night(on, held, skip, rf, spread=False, cost=0.0)
    spread = ops.book_night(on, held, skip, rf, spread=True, cost=0.0)
    assert cash.iloc[0] == pytest.approx((0.01 + 0.0001) / 2) and spread.iloc[0] == pytest.approx(0.01)
    assert cash.iloc[1] == pytest.approx(0.01)                         # nothing skipped: the plain average


def test_everything_skipped_earns_t_bills():
    on, held, rf = _data()
    r = ops.book_night(on, held, held.copy(), rf, spread=True, cost=0.0002)
    assert np.allclose(r, 0.0001)
