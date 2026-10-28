import numpy as np
import pandas as pd

from ai_desk import skill_desk as sd


def day_bars(path, start="2026-10-28 09:30", vol=1000.0):
    """5-minute bars from a list of (open, high, low, close)."""
    idx = pd.date_range(start, periods=len(path), freq="5min")
    o, h, l, c = zip(*path)
    return pd.DataFrame({"open": o, "high": h, "low": l, "close": c, "volume": vol}, index=idx)


def flat(n, px=100.0):
    return [(px, px + 0.1, px - 0.1, px)] * n


# range 99.9-101 (mid 100.45); 9:45 bar closes 101.2 above the high -> signal 9:50, fill at the 9:50 open
RANGE = [(100, 101, 99.9, 100.5), (100.5, 100.8, 100.2, 100.6), (100.6, 100.9, 100.3, 100.7)]


def test_breakout_fills_next_open_and_hits_target():
    path = RANGE + [(100.7, 101.3, 100.6, 101.2), (101.25, 101.5, 101.0, 101.4), (101.4, 102.9, 101.3, 102.8)] \
        + flat(70, 102.0)
    x = sd.breakout(day_bars(path))
    assert x["signal_time"] == "09:50" and x["entry"] == 101.25 and x["entry_time"] == "09:50"
    assert abs(x["stop"] - 100.45) < 1e-9 and abs(x["risk"] - 0.75) < 1e-9
    assert x["exit_why"] == "target" and abs(x["exit"] - (101.2 + 2 * 0.75)) < 1e-9


def test_stop_wins_when_a_bar_touches_both_and_flat_by_closes_the_rest():
    both = RANGE + [(100.7, 101.3, 100.6, 101.2), (101.25, 103.0, 100.0, 101.0)] + flat(70, 101.0)
    assert sd.breakout(day_bars(both))["exit_why"] == "stop"
    drift = RANGE + [(100.7, 101.3, 100.6, 101.2)] + flat(75, 101.3)
    x = sd.breakout(day_bars(drift))
    assert x["exit_why"] == "flat_by" and x["exit_time"] == "15:55"


def test_no_lookahead_later_bars_dont_change_the_signal():
    path = RANGE + [(100.7, 101.3, 100.6, 101.2), (101.25, 101.5, 101.0, 101.4)] + flat(70, 101.4)
    a = sd.breakout(day_bars(path))
    b = sd.breakout(day_bars(path[:5] + flat(70, 50.0)))
    assert (a["signal_time"], a["entry"], a["stop"], a["target"]) == (b["signal_time"], b["entry"], b["stop"], b["target"])


def test_missing_opening_bar_or_no_breakout_gives_nothing():
    assert sd.breakout(day_bars(RANGE + flat(70, 100.0))) is None
    assert sd.breakout(day_bars(RANGE[1:] + flat(70, 102.0), start="2026-10-28 09:35")) is None


def test_limits_size_by_max_loss_and_cap_trades_per_day():
    up = RANGE + [(100.7, 101.3, 100.6, 101.2), (101.25, 101.5, 101.0, 101.4)] + flat(70, 101.4)
    bars = {f"S{i}": day_bars(up, vol=1000.0 * (i + 1)) for i in range(5)}
    tr = sd.day_trades(bars, 5000.0)
    assert len(tr) <= 3
    assert tr[0]["symbol"] == "S4"                    # same minute: the most traded first
    for x in tr:
        assert x["shares"] <= 50 / x["risk"] and x["shares"] * x["plan_entry"] <= 4000
    assert sum(x["shares"] * x["entry"] for x in tr) <= 5000 * 0.9 + 1e-6


def test_daily_loss_limit_stops_new_entries():
    cfg = dict(sd.CONFIG, max_daily_loss_usd=30.0)   # A loses ~$31 (39 shares, $4,000 cap)
    loser = RANGE + [(100.7, 101.3, 100.6, 101.2), (101.25, 101.3, 100.0, 100.2)] + flat(70, 100.2)
    late = RANGE + flat(6, 100.5) + [(100.7, 101.3, 100.6, 101.2), (101.25, 101.5, 101.0, 101.4)] + flat(64, 101.4)
    tr = sd.day_trades({"A": day_bars(loser), "B": day_bars(late)}, 5000.0, cfg)
    assert [x["symbol"] for x in tr] == ["A"] and tr[0]["pnl"] < -30
    assert np.isfinite(tr[0]["R"])
