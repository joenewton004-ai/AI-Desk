import numpy as np
import pandas as pd
import pytest

from ai_desk.fundamentals.screen_backtest import _simulate, excluded_sic, momentum


def test_equal_weight_drift_and_costs():
    idx = pd.date_range("2020-01-31", periods=4, freq="ME")
    monthly = pd.DataFrame({"A": [np.nan, 0.10, 0.10, 0.0], "B": [np.nan, 0.0, 0.0, 0.0]}, index=idx)
    r = _simulate({idx[0]: ["A", "B"]}, monthly, idx[-1], cost=0.001)
    assert r.iloc[0] == pytest.approx(0.5 * 0.10 - 0.001)              # buy-in cost on 100% turnover
    w_a = 0.5 * 1.1 / (0.5 * 1.1 + 0.5)                                 # A's weight drifted up
    assert r.iloc[1] == pytest.approx(w_a * 0.10)


def test_missing_return_is_cash_not_a_crash():
    idx = pd.date_range("2020-01-31", periods=3, freq="ME")
    monthly = pd.DataFrame({"A": [np.nan, np.nan, 0.05], "B": [np.nan, 0.02, 0.02]}, index=idx)
    r = _simulate({idx[0]: ["A", "B"]}, monthly, idx[-1], cost=0.0)
    assert r.iloc[0] == pytest.approx(0.5 * 0.02)


def test_financials_excluded_by_sic():
    assert excluded_sic(6021) and excluded_sic(6798) and not excluded_sic(7389) and not excluded_sic(None)


def test_momentum_skips_latest_month():
    idx = pd.date_range("2019-01-31", periods=14, freq="ME")
    px = pd.Series(np.arange(100, 114, dtype=float), index=idx)
    # price 12 months ago (101) to 1 month ago (112); the latest month (113) is skipped
    assert momentum(px, idx[-1]) == pytest.approx(112 / 101 - 1)
