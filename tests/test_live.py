from ai_desk.live import plan_order
from ai_desk.risk import RiskConfig
from ai_desk.strategies import get_strategy


def test_plan_buys_from_flat(prices):
    plan = plan_order(prices, get_strategy("buy_hold"), RiskConfig(), "SPY",
                      equity=100_000, current_qty=0, max_order_notional=1e9)
    expected = int(100_000 // prices["close"].iloc[-1])
    assert plan.side == "buy" and plan.order_qty == expected == plan.target_qty


def test_plan_blocks_oversized_order(prices):
    plan = plan_order(prices, get_strategy("buy_hold"), RiskConfig(), "SPY",
                      equity=100_000, current_qty=0, max_order_notional=1_000)
    assert plan.side is None and plan.order_qty == 0 and "BLOCKED" in plan.reason


def test_plan_skips_tiny_rebalance(prices):
    price = prices["close"].iloc[-1]
    target = int(100_000 // price)
    plan = plan_order(prices, get_strategy("buy_hold"), RiskConfig(), "SPY",
                      equity=100_000, current_qty=target - 1, max_order_notional=1e9)
    assert plan.side is None


def test_plan_sells_to_flat(prices):
    class Flat(type(get_strategy("buy_hold"))):
        def target_exposure(self, p):
            return super().target_exposure(p) * 0

    plan = plan_order(prices, Flat(), RiskConfig(), "SPY",
                      equity=100_000, current_qty=50, max_order_notional=1e9)
    assert plan.side == "sell" and plan.order_qty == 50
