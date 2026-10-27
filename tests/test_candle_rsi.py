import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "research"))
import candle_rsi as cr  # noqa: E402


def _daily(n=300, seed=0):
    rng = np.random.default_rng(seed)
    c = 100 * np.exp(np.cumsum(rng.normal(0.0003, 0.012, n)))
    o = np.r_[c[0], c[:-1]] * (1 + rng.normal(0, 0.002, n))
    h = np.maximum(o, c) * (1 + rng.uniform(0, 0.01, n))
    l = np.minimum(o, c) * (1 - rng.uniform(0, 0.01, n))
    return pd.DataFrame({"open": o, "high": h, "low": l, "close": c}, index=pd.bdate_range("2020-01-01", periods=n))


def test_features_use_only_the_past():
    d = _daily()
    full, cut = cr.features(d), cr.features(d.iloc[:250])
    cols = ["T1", "T2", "R1", "R2", "C1", "C2", "C3"]
    assert (full[cols].iloc[:250] == cut[cols]).all().all()


def test_candle_definitions():
    idx = pd.bdate_range("2024-01-01", periods=2)
    d = pd.DataFrame({"open": [101.0, 99.0], "high": [101.5, 102.0], "low": [99.8, 98.5], "close": [100.0, 101.8]},
                     index=idx)
    f = cr.features(d)
    assert f["C2"].iloc[1] and f["C3"].iloc[1]          # engulfing, and a lower low closing near the high
    ham = d.copy()
    ham.iloc[1] = [101.0, 101.2, 98.0, 101.1]            # long lower wick, tiny upper wick
    assert cr.features(ham)["C1"].iloc[1]


def test_trades_enter_next_open_exit_after_condition_one_at_a_time():
    d = _daily(40, seed=3)
    sig = np.zeros(40, bool)
    sig[[5, 6, 20]] = True
    tr = cr.trades(d, sig, np.full(40, np.inf), "E2")    # hold 5 days
    assert tr[0] == (6, 11)                              # bought at 6's open, sold at 11's open
    assert all(e == 21 for e, _ in tr[1:])               # signal 6 skipped (already holding); 20 -> entry 21
    sma5 = np.full(40, -np.inf)                          # close always above SMA5: exit the day after entry
    tr = cr.trades(d, sig, sma5, "E1")
    assert tr[0] == (6, 7) and tr[1] == (7, 8)           # the next entry can be at the exit's open
