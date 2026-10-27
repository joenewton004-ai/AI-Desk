import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "research"))
import desk_rsi  # noqa: E402


def test_book_caps_positions_and_prefers_the_lowest_rsi():
    days = pd.bdate_range("2024-01-01", periods=10)
    d = days
    trades = [("A", d[1], d[4]), ("B", d[1], d[3]), ("C", d[2], d[5])]
    rsi_at = {("A", d[1]): 25.0, ("B", d[1]): 20.0, ("C", d[2]): 10.0}
    w = desk_rsi.book(trades, rsi_at, days, 0.03, 1)
    assert w["B"].loc[d[1]:d[2]].eq(0.03).all() and w["B"].loc[d[3]] == 0      # B first (lower RSI), held to its exit
    assert w["A"].sum() == 0 and w["C"].sum() == 0                              # A and C found no free slot
    w2 = desk_rsi.book(trades, rsi_at, days, 0.03, 2)
    assert w2.sum(axis=1).max() <= 0.06 + 1e-12


def test_overlay_charges_costs_on_entry_days_only():
    days = pd.bdate_range("2024-01-01", periods=4)
    w = pd.DataFrame({"A": [0.0, 0.03, 0.03, 0.0]}, index=days)
    oo = pd.DataFrame({"A": [0.0, 0.01, 0.02, 0.0]}, index=days)
    r = desk_rsi.overlay_daily(w, oo, 0.001)
    assert np.isclose(r.iloc[1], 0.03 * 0.01 - 0.03 * 0.002) and np.isclose(r.iloc[2], 0.03 * 0.02)
