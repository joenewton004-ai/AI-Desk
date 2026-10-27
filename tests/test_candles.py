import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "research"))
import alpaca_bars  # noqa: E402
import candles  # noqa: E402


def _minutes(days=3, seed=0):
    rng = np.random.default_rng(seed)
    idx = []
    for d in pd.bdate_range("2024-01-02", periods=days):
        idx += list(pd.date_range(d + pd.Timedelta(hours=9, minutes=30), periods=390, freq="min"))
    idx = pd.DatetimeIndex(idx)
    c = 100 * np.exp(np.cumsum(rng.normal(0, 0.0008, len(idx))))
    o = np.r_[c[0], c[:-1]]
    h = np.maximum(o, c) * (1 + rng.uniform(0, 0.0005, len(idx)))
    l = np.minimum(o, c) * (1 - rng.uniform(0, 0.0005, len(idx)))
    return pd.DataFrame({"open": o, "high": h, "low": l, "close": c, "volume": 1000.0, "vwap": c}, index=idx)


def test_regular_session_and_bars():
    m = _minutes(2)
    pre = m.iloc[:5].copy()
    pre.index = pre.index - pd.Timedelta(hours=1)
    assert len(alpaca_bars.regular_session(pd.concat([pre, m]))) == len(m)
    b = candles.to_bars(m)
    assert len(b) == 2 * 78 and b["day"].nunique() == 2
    first = m.iloc[:5]
    assert b["high"].iloc[0] == first["high"].max() and b["close"].iloc[0] == first["close"].iloc[-1]


def test_signals_use_only_the_past():
    b = candles.to_bars(_minutes(4))
    full = candles.candle_signals(b)
    cut = candles.candle_signals(b.iloc[:200])
    for k in full:
        assert (full[k].iloc[:200] == cut[k]).all(), k


def test_engulfing_and_hammer_definitions():
    idx = pd.date_range("2024-01-02 10:00", periods=2, freq="5min")
    b = pd.DataFrame({"open": [101, 99.5], "high": [101.2, 102], "low": [99.8, 99.4], "close": [100, 101.5],
                      "volume": 1.0, "vwap": 100.0, "tod": [600, 605], "day": 0}, index=idx)
    # the range filter needs history: check the raw shape rules through a long flat history
    flat = pd.DataFrame({"open": 100.0, "high": 100.1, "low": 99.9, "close": 100.0, "volume": 1.0, "vwap": 100.0,
                         "tod": np.arange(570, 570 + 5 * 20, 5), "day": 0},
                        index=pd.date_range("2024-01-02 09:30", periods=20, freq="5min"))
    b = pd.concat([flat, b.assign(tod=[670, 675])])
    s = candles.candle_signals(b)
    assert s["engulfing"].iloc[-1] == 1
    ham = b.iloc[[-1]].assign(open=101.0, close=101.2, high=101.25, low=99.0)
    s = candles.candle_signals(pd.concat([b.iloc[:-1], ham]))
    assert s["hammer / shooting star"].iloc[-1] == 1


def test_run_exit_stop_first_and_target():
    o = np.array([100, 100, 100.0]); h = np.array([101, 103, 100.5]); l = np.array([99, 99.5, 99.0]); c = np.array([100, 102, 100.0])
    r, k = candles.run_exit(o, h, l, c, 0, 2, 1, 100.0, 99.5, 102.0)
    assert k == 0 and np.isclose(r, -0.005)                         # stop and target both in candle 0: stop
    r, k = candles.run_exit(o, h, l, c, 1, 2, 1, 100.0, 99.0, 102.0)
    assert k == 1 and np.isclose(r, 0.02)
    r, k = candles.run_exit(o, h, l, c, 0, 2, -1, 100.0, None, None, hold=2)
    assert k == 1 and np.isclose(r, -0.02)


def test_trades_enter_after_the_signal_and_stay_in_the_day():
    b = candles.to_bars(_minutes(3, seed=3))
    for name, sig in candles.candle_signals(b).items():
        t = candles.candle_trades(b, sig, "stop/2R")
        sigpos = set(np.flatnonzero(sig.to_numpy()))
        assert all((p - 1) in sigpos for p in t["pos"])
    for t in (candles.inside_trades(b), candles.orb_trades(b, 15), candles.momentum_trades(b)):
        assert (t["time"].dt.hour * 60 + t["time"].dt.minute <= 15 * 60 + 55).all()
    orb = candles.orb_trades(b, 15)
    assert (orb["time"].dt.hour * 60 + orb["time"].dt.minute >= 9 * 60 + 45).all() and orb["time"].dt.date.is_unique
