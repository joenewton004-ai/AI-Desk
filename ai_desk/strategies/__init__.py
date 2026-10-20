"""Strategy registry. Add your own strategy class here to use it from the CLI."""

from __future__ import annotations

from ai_desk.strategies.base import Strategy
from ai_desk.strategies.buy_hold import BuyAndHold
from ai_desk.strategies.mean_reversion import RSIMeanReversion
from ai_desk.strategies.momentum import TimeSeriesMomentum
from ai_desk.strategies.seasonal import TurnOfMonth
from ai_desk.strategies.sma_crossover import SMACrossover
from ai_desk.strategies.trend import TrendFollowing
from ai_desk.strategies.vix_filter import VixFilter

STRATEGIES: dict[str, type[Strategy]] = {
    BuyAndHold.name: BuyAndHold,
    TrendFollowing.name: TrendFollowing,
    RSIMeanReversion.name: RSIMeanReversion,
    TimeSeriesMomentum.name: TimeSeriesMomentum,
    VixFilter.name: VixFilter,
    TurnOfMonth.name: TurnOfMonth,
    SMACrossover.name: SMACrossover,
}


def get_strategy(name: str, **params) -> Strategy:
    try:
        cls = STRATEGIES[name]
    except KeyError:
        raise ValueError(f"unknown strategy '{name}'. Choose from: {', '.join(STRATEGIES)}") from None
    return cls(**params)


__all__ = ["STRATEGIES", "Strategy", "get_strategy"]
