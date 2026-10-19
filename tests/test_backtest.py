import numpy as np
import pandas as pd
import pytest

from ai_desk.backtest import CostModel, run_backtest
from ai_desk.metrics import max_drawdown
from ai_desk.risk import RiskConfig
from ai_desk.strategies import STRATEGIES, get_strategy
from ai_desk.strategies.base import Strategy


@pytest.mark.parametrize("name", list(STRATEGIES))
def test_no_lookahead(prices, name):
    """Changing future prices must not change any past result."""
    cut = 1000
    future = prices.copy()
    future.iloc[cut:, :4] *= np.linspace(0.5, 2.0, len(prices) - cut)[:, None]
    strat = get_strategy(name)
    a = run_backtest(prices, strat, RiskConfig(target_vol=0.15))
    b = run_backtest(future, strat, RiskConfig(target_vol=0.15))
    pd.testing.assert_series_equal(a.equity.iloc[:cut], b.equity.iloc[:cut])
    pd.testing.assert_series_equal(a.weights.iloc[:cut], b.weights.iloc[:cut])


def test_buy_and_hold_matches_asset(prices):
    """Buy at day-1 open, hold to the end: equity should track the price, minus one cost."""
    costs = CostModel(commission_bps=1, slippage_bps=2)
    res = run_backtest(prices, get_strategy("buy_hold"), costs=costs, initial_equity=1.0)
    expected = prices["close"].iloc[-1] / prices["open"].iloc[1] * (1 - costs.rate)
    assert res.equity.iloc[-1] == pytest.approx(expected, rel=1e-9)
    assert len(res.trades) == 1


def test_costs_reduce_returns(prices):
    strat = get_strategy("trend")
    free = run_backtest(prices, strat, costs=CostModel(0, 0))
    paid = run_backtest(prices, strat, costs=CostModel(5, 10))
    assert paid.equity.iloc[-1] < free.equity.iloc[-1]


class _AlwaysFlat(Strategy):
    name = "flat"

    def target_exposure(self, prices):
        return pd.Series(0.0, index=prices.index)


def test_flat_strategy_keeps_capital(prices):
    res = run_backtest(prices, _AlwaysFlat(), initial_equity=1000)
    assert (res.equity == 1000).all()
    assert res.trades.empty


def test_drawdown_halt_goes_flat_and_stays_flat(prices):
    res = run_backtest(prices, get_strategy("buy_hold"), RiskConfig(max_drawdown_halt=0.10))
    assert res.halted_on is not None
    after = res.weights.loc[res.halted_on:].iloc[2:]
    assert (after == 0).all()


def test_leverage_cap(prices):
    res = run_backtest(prices, get_strategy("buy_hold"), RiskConfig(target_vol=1.0, max_leverage=1.0))
    assert res.weights.max() <= 1.0


def test_start_date_skips_warmup(prices):
    start = prices.index[300]
    res = run_backtest(prices, get_strategy("trend"), start=start)
    assert res.equity.index[0] == start


def test_max_drawdown():
    eq = pd.Series([100, 120, 90, 110, 60, 130])
    assert max_drawdown(eq) == pytest.approx(60 / 120 - 1)


def test_cash_earns_interest(prices):
    """A strategy that stays in cash should grow at the T-bill rate."""
    res = run_backtest(prices, _AlwaysFlat(), initial_equity=1.0, cash_rate=0.05)
    years = (len(res.equity) - 1) / 252
    assert res.equity.iloc[-1] == pytest.approx((1 + 0.05 / 252) ** (252 * years), rel=1e-9)
    # earning the risk-free rate is not skill: there is no excess return to rate
    assert np.isnan(res.metrics["sharpe"])


def test_turn_of_month_calendar():
    idx = pd.bdate_range("2026-08-24", "2026-09-11")
    prices = pd.DataFrame({"open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0, "volume": 1}, index=idx)
    exp = get_strategy("turn_of_month", days_before=1, days_after=3).target_exposure(prices)
    # decided at these closes -> held on Aug 31 (last day) and Sep 1-3 (first three)
    assert list(exp[exp > 0].index.strftime("%m-%d")) == ["08-28", "08-31", "09-01", "09-02"]


def test_momentum_only_changes_at_month_start(prices):
    exp = get_strategy("momentum").target_exposure(prices)
    changes = exp.index[exp.diff().fillna(0) != 0]
    prev = [prices.index[prices.index.get_loc(d) - 1] for d in changes]
    assert all(d.month != p.month for d, p in zip(changes, prev))
