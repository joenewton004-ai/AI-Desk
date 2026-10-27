import pandas as pd

from ai_desk import nvda_orb


def _day(rows):
    idx = pd.date_range("2026-10-26 09:30", periods=len(rows), freq="5min")
    return pd.DataFrame(rows, columns=["open", "high", "low", "close"], index=idx)


def test_breakout_then_close_and_stop():
    flat = [[100, 101, 99, 100]] * 3                       # 9:30-9:45 range 99-101
    rest = [[100.5, 102, 100.2, 101.5]] + [[101.5, 102, 101, 101.8]] * 72
    r = nvda_orb.evaluate(_day(flat + rest))
    assert r["status"] == "traded" and r["entry"] == 101 and r["exit_why"] == "close" and r["entry_time"] == "09:45"
    assert abs(r["gross"] - (101.8 / 101 - 1)) < 1e-6 and r["net"] < r["gross"]
    stop = [[100.5, 102, 100.2, 101.5], [101, 101.2, 98.5, 99]] + [[99, 99.5, 98, 99]] * 71
    r = nvda_orb.evaluate(_day(flat + stop))
    assert r["exit_why"] == "stop" and r["exit"] == 99 and r["R"] == -1.0


def test_no_breakout_and_summary():
    flat = [[100, 101, 99, 100]] * 78
    assert nvda_orb.evaluate(_day(flat))["status"] == "no breakout"
    s = nvda_orb.summary([{"status": "traded", "net": 0.01}, {"status": "traded", "net": -0.005},
                          {"status": "no breakout"}])
    assert s["trades"] == 2 and s["days"] == 3 and s["win_rate"] == 0.5 and abs(s["avg_net"] - 0.0025) < 1e-12
