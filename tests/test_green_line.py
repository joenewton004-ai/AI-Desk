import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "research"))
import green_line as gl  # noqa: E402


def test_above_with_band_keeps_state_between_the_lines():
    idx = pd.date_range("2024-01-01", periods=6)
    line = pd.Series([np.nan, 100, 100, 100, 100, 100.0], index=idx)
    close = pd.Series([99, 101, 103, 101, 97, 99.0], index=idx)
    assert gl.above(close, line).tolist() == [False, True, True, True, False, False]
    assert gl.above(close, line, band=0.02).tolist() == [False, False, True, True, False, False]


def test_signal_uses_only_the_past():
    rng = np.random.default_rng(1)
    c = pd.Series(100 * np.exp(np.cumsum(rng.normal(0, 0.01, 600))), index=pd.bdate_range("2020-01-01", periods=600))
    full = gl.rules(c)
    cut = gl.rules(c.iloc[:400])
    for k, s in full.items():
        if s is not None:
            assert (s.iloc[:399] == cut[k].iloc[:399]).all(), k        # month-end rule: the last day may not be final


def test_book_switches_at_the_next_open():
    idx = pd.bdate_range("2024-01-01", periods=4)
    o = pd.Series([100, 100, 110, 121.0], index=idx)
    c = pd.Series([100, 110, 121, 121.0], index=idx)
    sig = pd.Series([True, False, False, False], index=idx)
    r = gl.book(o, c, pd.Series(0.0, index=idx), sig, cost=0.0)
    # in from day 1's open (+10% open->close); out at day 2's open, but day 2's overnight gap (0%) is still held
    assert np.allclose(r.tolist(), [0.0, 0.10, 0.0, 0.0])


def test_mag7_basket_is_the_daily_equal_weight():
    import green_line_tech as glt
    r = pd.DataFrame({"A": [0.1, -0.1], "B": [0.0, 0.1]})
    assert list(glt.basket(r).round(10)) == [0.05, 0.0]


def test_why_helpers_find_spells_falls_and_trend():
    import green_line_why as gw
    idx = pd.bdate_range("2020-01-01", periods=6)
    sig = pd.Series([False, True, False, False, True, False], index=idx)
    assert gw.spells(sig) == [(idx[2], idx[4]), (idx[5], idx[5])]
    c = pd.Series([100, 80, 60, 90, 110, 70.0], index=idx)
    dd = gw.drawdowns(c)
    assert len(dd) == 2 and abs(dd[0]["depth"] + 0.4) < 1e-12 and dd[0]["days_down"] == 2 and dd[0]["days_back"] == 2
    assert dd[1]["days_back"] is None
    m = pd.bdate_range("2000-01-01", periods=3000)
    trend = pd.Series(np.exp(np.cumsum(np.full(3000, 0.001))), index=m)
    noise = pd.Series(np.exp(np.cumsum(np.random.default_rng(1).normal(0, 0.01, 3000))), index=m)
    assert abs(gw.variance_ratio(noise) - 1) < 0.5
