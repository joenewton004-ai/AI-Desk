import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "research"))
import cameron  # noqa: E402
import soros  # noqa: E402


def test_trend_weights_use_only_the_past_and_beat_cash():
    idx = pd.date_range("2020-01-31", periods=15, freq="ME")
    px = pd.DataFrame({"UP": np.linspace(100, 130, 15), "DOWN": np.linspace(100, 80, 15)}, index=idx)
    rf = pd.Series(0.001, index=idx)
    w = soros.trend_weights(px, rf)
    assert w.iloc[-1]["UP"] == 0.5 and w.iloc[-1]["DOWN"] == 0.0 and w.iloc[5].isna().all()
    ws = soros.trend_weights(px, rf, short=True)
    assert ws.iloc[-1]["DOWN"] == -0.5
    cut = soros.trend_weights(px.iloc[:13], rf.iloc[:13])           # no lookahead
    assert cut.iloc[-1].equals(w.iloc[12])


def test_book_holds_last_months_weights_and_pays_cash_on_the_rest():
    idx = pd.date_range("2020-01-31", periods=3, freq="ME")
    w = pd.DataFrame({"A": [0.5, 0.5, 0.5]}, index=idx)
    r = pd.DataFrame({"A": [0.0, 0.10, 0.10]}, index=idx)
    rf = pd.Series(0.01, index=idx)
    out = soros.book(w, r, rf, cost=0.0)
    assert out.iloc[1] == pytest.approx(0.5 * 0.10 + 0.5 * 0.01)


def test_gap_trades_take_open_to_close_on_gap_days_only():
    idx = pd.bdate_range("2024-01-01", periods=3)
    o = pd.DataFrame({"A": [100.0, 110.0, 100.0]}, index=idx)
    c = pd.DataFrame({"A": [100.0, 121.0, 100.0]}, index=idx)
    r = cameron.gap_trades(o, c, pd.DataFrame(True, index=idx, columns=["A"]), 0.05)
    assert len(r) == 1 and r.iloc[0] == pytest.approx(0.10 - 2 * cameron.COST)
