import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "research"))

import swing_etf as se  # noqa: E402


def bars(n=400, seed=1):
    rng = np.random.default_rng(seed)
    c = 100 * np.exp(np.cumsum(rng.normal(0.0004, 0.012, n)))
    o = c * np.exp(rng.normal(0, 0.003, n))
    idx = pd.bdate_range("2020-01-01", periods=n)
    return pd.DataFrame({"open": o, "high": np.maximum(o, c) * 1.004, "low": np.minimum(o, c) * 0.996, "close": c},
                        index=idx)


def test_no_lookahead_signals_ignore_later_bars():
    d = bars()
    cut = 300
    for rule in se.RULES:
        a, _ = se.signals(d, rule)
        later = d.copy()
        later.iloc[cut + 1:] *= 1.5                       # rewrite the future
        b, _ = se.signals(later, rule)
        k = cut - 1 if rule in ("down_week", "up_week", "turn_of_month") else cut   # calendar rules look at the week/month
        assert (a[:k] == b[:k]).all(), rule


def test_trades_enter_after_the_signal_and_exit_within_a_week():
    d = bars()
    checked = 0
    for rule in ("rsi2_dip", "ten_day_low", "three_down", "ibs_low", "breakout_20"):
        t = se.trades(d, rule, 0.0)
        sig, _ = se.signals(d, rule)
        if t.empty:
            continue
        checked += 1
        first = d.index[np.nonzero(sig)[0][0]]
        assert t["entry"].iloc[0] > first                 # bought at the next open
        assert (t["days"] <= se.HOLD).all() and (t["exit"] > t["entry"]).all()
    assert checked >= 2
