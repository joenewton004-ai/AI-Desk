import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "research"))
import alpaca_bars  # noqa: E402
import ict_long  # noqa: E402
import tjr_long  # noqa: E402


def _five(day="2024-01-02", start="09:30", n=78):
    idx = pd.date_range(f"{day} {start}", periods=n, freq="5min")
    c = np.linspace(100, 101, n)
    return pd.DataFrame({"open": c, "high": c + 0.1, "low": c - 0.1, "close": c, "volume": 1.0}, index=idx)


def test_extended_session_keeps_4am_to_8pm():
    b = _five(start="03:00", n=17 * 12 + 12)            # 3:00 to 20:55
    e = alpaca_bars.extended_session(b)
    assert e.index[0].strftime("%H:%M") == "04:00" and e.index[-1].strftime("%H:%M") == "19:55"
    r = alpaca_bars.regular_session(b)
    assert r.index[0].strftime("%H:%M") == "09:30" and r.index[-1].strftime("%H:%M") == "15:55"


def test_hourly_candles_start_at_half_past():
    h = ict_long.hourly(_five())
    assert [t.strftime("%H:%M") for t in h.index] == ["09:30", "10:30", "11:30", "12:30", "13:30", "14:30", "15:30"]
    b = _five()
    assert h["high"].iloc[0] == b["high"].iloc[:12].max() and h["close"].iloc[-1] == b["close"].iloc[-1]


def test_stock_levels_drop_asia_and_london():
    idx = pd.date_range("2024-01-02 04:00", "2024-01-03 09:25", freq="5min")
    idx = idx[(idx.hour >= 4) & (idx.hour < 20)]
    b = pd.DataFrame({"Open": 100.0, "High": 101.0, "Low": 99.0, "Close": 100.0}, index=idx)
    lv = tjr_long.stock_levels(b, pd.Timestamp("2024-01-03"))
    assert set(lv) == {"prior day high", "prior day low", "overnight high", "overnight low"}


def test_members_use_filings_45_days_after_the_quarter():
    snap = pd.DataFrame({"market_cap": [3.0, 2.0, 1.0]}, index=["A", "B", "C"])
    snaps = {pd.Timestamp("2024-03-31"): snap}
    days = pd.DatetimeIndex(["2024-05-14", "2024-05-15"])
    m = ict_long.members_by_day(snaps, days)
    assert pd.Timestamp("2024-05-14") not in m and m[pd.Timestamp("2024-05-15")][1] == {"A", "B", "C"}
