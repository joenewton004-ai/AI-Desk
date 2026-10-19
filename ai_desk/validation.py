"""Guarding against overfitting.

If you try 100 parameter combinations, one will look great by luck. These
tools check whether an edge survives on data it was NOT tuned on.

* split_test:   tune on the past (in-sample), check on later data (out-of-sample).
* walk_forward: repeat that through time - optimise on N years, trade the
                next year blind, slide forward. The stitched-together blind
                years are the most honest estimate you can get from history.
* param_sensitivity: a robust edge works across a RANGE of nearby
                parameters. If only lookback=187 works, it's noise.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass

import pandas as pd

from ai_desk.backtest import BacktestResult, CostModel, run_backtest
from ai_desk.metrics import daily_rf, summarize
from ai_desk.risk import RiskConfig
from ai_desk.strategies import get_strategy


def expand_grid(grid: dict[str, list]) -> list[dict]:
    keys = list(grid)
    return [dict(zip(keys, combo)) for combo in itertools.product(*(grid[k] for k in keys))]


def _score(result: BacktestResult, metric: str) -> float:
    v = result.metrics.get(metric)
    return float("-inf") if v is None or v != v else float(v)


def param_sensitivity(prices: pd.DataFrame, strategy_name: str, grid: dict[str, list],
                      risk: RiskConfig | None = None, costs: CostModel | None = None,
                      start=None, end=None, cash_rate=None) -> pd.DataFrame:
    """Backtest every parameter combination; returns one row per combination."""
    data = prices.loc[:end] if end is not None else prices
    rows = []
    for params in expand_grid(grid):
        res = run_backtest(data, get_strategy(strategy_name, **params), risk, costs, start=start, cash_rate=cash_rate)
        rows.append({**params, **{k: res.metrics[k] for k in ("cagr", "sharpe", "max_drawdown", "trades")}})
    return pd.DataFrame(rows)


def split_test(prices: pd.DataFrame, strategy_name: str, params: dict, split: str,
               risk: RiskConfig | None = None, costs: CostModel | None = None,
               start=None, cash_rate=None) -> dict[str, BacktestResult]:
    split_ts = pd.Timestamp(split)
    before = prices.loc[prices.index < split_ts]
    strat = get_strategy(strategy_name, **params)
    return {
        "in_sample": run_backtest(before, strat, risk, costs, start=start, cash_rate=cash_rate),
        "out_of_sample": run_backtest(prices, strat, risk, costs, start=split_ts, cash_rate=cash_rate),
    }


@dataclass
class WalkForwardResult:
    equity: pd.Series                 # stitched out-of-sample equity
    windows: pd.DataFrame             # chosen params + scores per window
    metrics: dict


def walk_forward(prices: pd.DataFrame, strategy_name: str, grid: dict[str, list],
                 train_years: int = 5, test_years: int = 1, metric: str = "sharpe",
                 risk: RiskConfig | None = None, costs: CostModel | None = None,
                 initial_equity: float = 100_000.0, warmup_days: int = 252,
                 cash_rate=None) -> WalkForwardResult:
    """warmup_days: bars at the start of the data excluded from scoring, so slow
    indicators (e.g. a 250-day average) aren't penalised for sitting in cash
    while they have no reading yet."""
    first, last = prices.index[0], prices.index[-1]
    earliest_score = prices.index[min(warmup_days, len(prices) - 1)]
    test_start = first + pd.DateOffset(years=train_years)
    equity, pieces, windows = initial_equity, [], []
    combos = expand_grid(grid)

    while test_start < last:
        test_end = min(test_start + pd.DateOffset(years=test_years), last + pd.Timedelta(days=1))
        train_start = max(test_start - pd.DateOffset(years=train_years), earliest_score)
        train = prices.loc[:test_start - pd.Timedelta(days=1)]

        best_params, best_score = None, float("-inf")
        for params in combos:
            res = run_backtest(train, get_strategy(strategy_name, **params), risk, costs, start=train_start,
                               cash_rate=cash_rate)
            s = _score(res, metric)
            if s > best_score:
                best_params, best_score = params, s

        # trade the next window blind with the chosen params (history up to window end only)
        # start on the last training day so the first test day's return is counted;
        # that bar's equity just repeats the previous window's final value
        window = prices.loc[:test_end - pd.Timedelta(days=1)]
        first_test = int(window.index.searchsorted(test_start))
        if first_test >= len(window):
            break
        res = run_backtest(window, get_strategy(strategy_name, **best_params), risk, costs,
                           start=window.index[first_test - 1], initial_equity=equity,
                           cash_rate=cash_rate)
        pieces.append(res.equity if not pieces else res.equity.iloc[1:])
        equity = float(res.equity.iloc[-1])
        windows.append({"test_start": window.index[first_test].date(),
                        "test_end": res.equity.index[-1].date(),
                        **best_params, f"train_{metric}": best_score,
                        "test_return": res.metrics["total_return"]})
        test_start = test_end

    if not pieces:
        raise ValueError("not enough data for walk-forward; reduce train_years or load more history")
    eq = pd.concat(pieces)
    return WalkForwardResult(eq, pd.DataFrame(windows), summarize(eq, rf_daily=daily_rf(cash_rate, eq.index)))
