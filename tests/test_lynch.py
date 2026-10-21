import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "research"))
import lynch  # noqa: E402


def test_growth_rate_needs_positive_ends():
    assert abs(lynch.growth_rate(pd.Series([100.0, 110, 121, 133.1])) - 0.10) < 1e-9
    assert np.isnan(lynch.growth_rate(pd.Series([-5.0, 10, 20, 30])))
    assert np.isnan(lynch.growth_rate(pd.Series([1.0, 2.0])))


def test_peg_and_lynch_ratio():
    ni = pd.Series([100.0, 110, 121, 133.1])                        # 10%/yr
    m = lynch.lynch_metrics(mcap=1331.0, ni=ni, revenue=pd.Series([1000.0, 1100]), dividends=26.62, debt=50,
                            cash=100, equity=500, inventory=pd.Series([100.0, 130]), shares_now=95, shares_1y=100)
    assert abs(m["pe"] - 10) < 1e-9 and abs(m["peg"] - 1.0) < 1e-9   # P/E 10 / growth 10
    assert abs(m["lynch_ratio"] - (10 + 2) / 10) < 1e-9             # 2% yield
    assert m["net_cash"] and abs(m["debt_equity"] - 0.1) < 1e-9
    assert abs(m["inv_gap"] - 0.20) < 1e-9                          # inventory +30% vs sales +10%
    assert abs(m["share_change"] + 0.05) < 1e-9


def test_rules_and_categories():
    f = pd.DataFrame({"peg": [0.4, 1.5], "lynch_ratio": [2.5, 0.8], "growth": [0.22, 0.05],
                      "debt_equity": [0.2, 2.0], "net_cash": [False, False], "inv_gap": [np.nan, 0.2],
                      "share_change": [-0.01, 0.03]}, index=["A", "B"])
    r = lynch.rules(f)
    assert list(r["PEG under 0.5"]) == [True, False] and list(r["fast grower (18-30%)"]) == [True, False]
    assert list(r["inventory not piling up"]) == [True, False] and list(r["strong balance sheet"]) == [True, False]
    assert lynch.category(0.22) == "fast grower" and lynch.category(0.4) == "hot grower (over 30%)"
    assert lynch.category(np.nan) == "no steady earnings"


def test_simulate_holds_cash_when_nothing_passes():
    idx = pd.to_datetime(["2020-03-31", "2020-04-30", "2020-05-31", "2020-06-30"])
    monthly = pd.DataFrame({"A": [np.nan, 0.10, 0.10, 0.10]}, index=idx)
    rf = pd.Series(0.001, index=idx)
    r = lynch.simulate({idx[0]: ["A"], idx[2]: []}, monthly, rf, cost=0.0)
    assert abs(r[idx[1]] - 0.10) < 1e-12 and abs(r[idx[3]] - 0.001) < 1e-12
