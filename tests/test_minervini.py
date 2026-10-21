import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "research"))
import minervini as mv  # noqa: E402


def _e(start, end, val, filed, form="10-Q"):
    return {"start": start, "end": end, "val": val, "filed": filed, "form": form}


def test_quarters_as_first_reported_with_q4_from_the_annual_report():
    entries = [
        _e("2024-01-01", "2024-03-31", 1.0, "2024-05-01"),
        _e("2024-01-01", "2024-03-31", 9.0, "2025-05-01"),             # restated a year later: ignored
        _e("2024-04-01", "2024-06-30", 2.0, "2024-08-01"),
        _e("2024-07-01", "2024-09-30", 3.0, "2024-11-01"),
        _e("2024-01-01", "2024-09-30", 6.0, "2024-11-01"),             # nine months: not a quarter
        _e("2024-01-01", "2024-12-31", 10.0, "2025-02-20", "10-K"),
    ]
    q = mv.quarters_from_filings(entries)
    assert list(q["val"]) == [1.0, 2.0, 3.0, 4.0]
    assert q.loc[pd.Timestamp("2024-12-31"), "filed"] == pd.Timestamp("2025-02-20")


def test_growth_only_against_a_positive_base():
    q = pd.DataFrame({"val": [1.0, -1.0, 1.5, 2.0], "filed": pd.NaT},
                     index=pd.to_datetime(["2023-03-31", "2023-06-30", "2024-03-31", "2024-06-30"]))
    g = mv.yoy_growth(q)
    assert g[pd.Timestamp("2024-03-31")] == pytest.approx(0.5)
    assert np.isnan(g[pd.Timestamp("2024-06-30")])                      # from a loss: no growth rate


def test_growth_usable_only_from_the_day_after_filing_and_goes_stale():
    dates = pd.bdate_range("2024-04-25", "2024-12-31")
    f = pd.DataFrame({"eps_g": [0.4], "rev_g": [0.3], "eps_g_prev": [0.1], "filed": [pd.Timestamp("2024-05-01")]},
                     index=[pd.Timestamp("2024-03-31")])
    ok = mv.growth_on_days({"A": f}, dates, ["A"])[:, 0]
    assert not ok[dates.get_loc(pd.Timestamp("2024-05-01"))]           # filing day: not yet
    assert ok[dates.get_loc(pd.Timestamp("2024-05-02"))]
    assert not ok[-1]                                                  # > STALE_DAYS after the quarter ended
    weak = mv.growth_on_days({"A": f.assign(rev_g=0.1)}, dates, ["A"])
    assert not weak.any()


def test_rs_rating_ranks_stronger_stocks_higher():
    idx = pd.bdate_range("2020-01-01", periods=300)
    c = pd.DataFrame({"UP": np.linspace(10, 30, 300), "FLAT": 10.0, "DOWN": np.linspace(30, 10, 300)}, index=idx)
    rs = mv.rs_rating(c, np.ones(c.shape, dtype=bool))
    assert rs[-1, 0] > rs[-1, 1] > rs[-1, 2]
    assert rs[100].sum() == 0                                          # under a year of history: no rating


def test_stops_fill_next_open_and_break_even_after_a_gain():
    n = 8
    dates = pd.bdate_range("2024-01-01", periods=n)
    o = np.full((n, 1), 100.0)
    c = np.array([[100], [100], [118], [99], [99], [99], [99], [99]], dtype=float)
    buy = np.zeros((n, 1), dtype=bool)
    buy[0] = True
    eq, t = mv.simulate(o, c, buy, None, np.ones((n, 1)), np.full((n, 1), np.nan), np.zeros(n), dates, ["A"])
    # bought at day 1's open; +18% on day 2 -> stop raised to the entry; day 3 closes below it -> sold day 4's open
    assert len(t) == 1 and t.iloc[0]["why"] == "break-even stop"
    assert t.iloc[0]["entry_date"] == dates[1] and t.iloc[0]["exit_date"] == dates[4]
    c2 = c.copy()
    c2[2] = 92.0                                                       # -8% before any gain: the 7.5% stop
    _, t2 = mv.simulate(o, c2, buy, None, np.ones((n, 1)), np.full((n, 1), np.nan), np.zeros(n), dates, ["A"])
    assert t2.iloc[0]["why"] == "stop" and t2.iloc[0]["exit_date"] == dates[3]


def test_rotation_sells_what_stops_qualifying():
    n = 6
    dates = pd.bdate_range("2024-01-01", periods=n)
    o = c = np.full((n, 1), 100.0)
    q = np.array([[True], [True], [True], [False], [False], [False]])
    _, t = mv.simulate(o, c, q, q, np.ones((n, 1)), np.full((n, 1), np.nan), np.zeros(n), dates, ["A"],
                       stop=None, breakeven_at=None, ma_exit=False)
    assert t.iloc[0]["why"] == "no longer qualifies" and t.iloc[0]["exit_date"] == dates[4]
