import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "research"))
import circuit_breaker as cb  # noqa: E402
import swing  # noqa: E402


def _prices(n=320, seed=1):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2020-01-01", periods=n)
    c = pd.DataFrame(100 * np.exp(np.cumsum(rng.normal(0.001, 0.02, (n, 3)), axis=0)), index=idx, columns=list("ABC"))
    o = c.shift(1).fillna(c) * (1 + rng.normal(0, 0.003, c.shape))
    h, lo = np.maximum(o, c) * 1.01, np.minimum(o, c) * 0.99
    v = pd.DataFrame(rng.uniform(1e6, 3e6, c.shape), index=idx, columns=c.columns)
    return o, h, lo, c, v


def test_signals_use_only_data_up_to_the_close():
    o, h, lo, c, v = _prices()
    full = swing.signals(o, h, lo, c, v)
    cut = 250
    part = swing.signals(o.iloc[:cut], h.iloc[:cut], lo.iloc[:cut], c.iloc[:cut], v.iloc[:cut])
    for k in ("trend", "setup", "ma50"):
        pd.testing.assert_frame_equal(full[k].iloc[:cut], part[k], check_freq=False)


def _book(n=6):
    dates = pd.bdate_range("2021-01-01", periods=n)
    o = np.full((n, 1), 100.0)
    c = np.full((n, 1), 100.0)
    return dates, o, c


def test_simulate_buys_at_the_next_open_and_stops_out_at_the_open_after():
    dates, o, c = _book()
    o[1, 0] = 101.0                      # signal on day 0 -> bought at day 1's open
    c[2, 0] = 90.0                       # day 2 closes 10.9% below entry -> stop decided
    o[3, 0] = 85.0                       # ... and filled at day 3's open, after a gap
    setup = np.zeros((6, 1), dtype=bool)
    setup[0, 0] = True
    eq, t = swing.simulate(o, c, setup, np.ones((6, 1)), np.full((6, 1), np.nan), np.zeros(6), dates, ["A"],
                           slots=1, cost=0.0)
    assert len(t) == 1
    assert t.iloc[0]["entry"] == 101.0 and t.iloc[0]["exit"] == 85.0 and t.iloc[0]["why"] == "stop"
    assert t.iloc[0]["entry_date"] == dates[1] and t.iloc[0]["exit_date"] == dates[3]
    assert abs(eq.iloc[-1] - 85 / 101) < 1e-12


def test_membership_follows_the_latest_quarter_end():
    dates = pd.bdate_range("2021-03-25", "2021-04-05")
    snaps = {pd.Timestamp("2020-12-31"): ["A"], pd.Timestamp("2021-03-31"): ["B"]}
    m = swing.membership(snaps, dates, ["A", "B"])
    before = dates < pd.Timestamp("2021-03-31")
    assert m[before, 0].all() and not m[before, 1].any()
    assert m[~before, 1].all() and not m[~before, 0].any()


def test_breaker_halts_from_the_next_period_and_freeze_never_adds():
    dates = pd.date_range("2021-01-01", periods=6, freq="W-FRI")
    ret = pd.DataFrame({"X": [0, -0.10, 0.05, 0.05, 0.05, 0.05]}, index=dates)
    rf = pd.Series(0.0, index=dates)
    targets = [{"X": 0.5}, {"X": 1.0}, {"X": 1.0}, {"X": 1.0}, {"X": 1.0}, {"X": 1.0}]
    r, halted = cb.run_breaker(targets, ret, rf, week_limit=0.05, month_limit=None, cost=0.0)
    assert not halted.iloc[0]                       # the -5% week itself is earned unhalted
    assert halted.iloc[1]                           # the next week is halted...
    assert abs(r.iloc[1] - 0.5 * 0.05) < 1e-12      # ...and the increase to 100% is refused
    rc, _ = cb.run_breaker(targets, ret, rf, week_limit=0.05, month_limit=None, mode="cash", cost=0.0)
    assert rc.iloc[1] == 0.0                        # cash mode holds nothing while halted
    rn, hn = cb.run_breaker(targets, ret, rf, week_limit=None, month_limit=None, cost=0.0)
    assert not hn.any() and abs(rn.iloc[1] - 0.05) < 1e-12
