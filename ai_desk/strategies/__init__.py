"""Strategy registry. Add your own strategy class here to use it from the CLI."""

from __future__ import annotations

from ai_desk.strategies.base import Strategy
from ai_desk.strategies.buy_hold import BuyAndHold
from ai_desk.strategies.mean_reversion import RSIMeanReversion
from ai_desk.strategies.trend import TrendFollowing

STRATEGIES: dict[str, type[Strategy]] = {
    BuyAndHold.name: BuyAndHold,
    TrendFollowing.name: TrendFollowing,
    RSIMeanReversion.name: RSIMeanReversion,
}


def get_strategy(name: str, **params) -> Strategy:
    try:
        cls = STRATEGIES[name]
    except KeyError:
        raise ValueError(f"unknown strategy '{name}'. Choose from: {', '.join(STRATEGIES)}") from None
    return cls(**params)


__all__ = ["STRATEGIES", "Strategy", "get_strategy"]
