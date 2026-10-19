"""Option strategy payoffs at expiry.

A position is a list of legs. Quantity is in CONTRACTS for options (1
contract = 100 shares) and SHARES for stock. Positive = long, negative = short.
Premium is per share (as quoted on the chain).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

MULTIPLIER = 100


@dataclass
class Leg:
    kind: str          # "call", "put" or "stock"
    qty: float
    strike: float = 0.0   # for stock: the purchase price
    premium: float = 0.0  # per share, paid (long) or received (short)

    def payoff(self, prices: np.ndarray) -> np.ndarray:
        if self.kind == "stock":
            return self.qty * (prices - self.strike)
        intrinsic = np.maximum(prices - self.strike, 0) if self.kind == "call" \
            else np.maximum(self.strike - prices, 0)
        return self.qty * MULTIPLIER * (intrinsic - self.premium)


def position_payoff(legs: list[Leg], prices: np.ndarray) -> np.ndarray:
    return sum(leg.payoff(prices) for leg in legs)


def analyze(legs: list[Leg], hi: float | None = None, steps: int = 6001) -> dict:
    """Max profit/loss and breakevens at expiry, for prices from 0 to `hi`.

    The price can't go below 0, so the downside is always bounded. If P&L is
    still rising/falling at `hi` (e.g. a long call) it is reported as unlimited.
    """
    hi = hi or 3 * max(leg.strike for leg in legs)
    grid = np.linspace(0, hi, steps)
    pnl = position_payoff(legs, grid)
    sign = np.sign(pnl)
    breakevens = []
    for i in np.where(np.diff(sign) != 0)[0]:
        x0, x1, y0, y1 = grid[i], grid[i + 1], pnl[i], pnl[i + 1]
        if y0 != y1:
            breakevens.append(round(float(x0 - y0 * (x1 - x0) / (y1 - y0)), 2))
    slope_at_hi = pnl[-1] - pnl[-2]
    net_premium = -sum(leg.qty * MULTIPLIER * leg.premium for leg in legs if leg.kind != "stock")
    return {
        "net_premium": float(net_premium),   # + = credit received, - = debit paid
        "max_profit": "unlimited" if slope_at_hi > 1e-9 else float(pnl.max()),
        "max_loss": "unlimited" if slope_at_hi < -1e-9 else float(pnl.min()),
        "breakevens": sorted(set(breakevens)),
    }


# ---- common strategies ---------------------------------------------------

def long_call(strike, premium):
    return [Leg("call", 1, strike, premium)]


def long_put(strike, premium):
    return [Leg("put", 1, strike, premium)]


def covered_call(stock_price, call_strike, call_premium):
    """Own 100 shares, sell 1 call: collect income, cap upside."""
    return [Leg("stock", 100, stock_price), Leg("call", -1, call_strike, call_premium)]


def cash_secured_put(strike, premium):
    """Sell a put with cash set aside to buy the shares if assigned."""
    return [Leg("put", -1, strike, premium)]


def bull_call_spread(low_strike, low_premium, high_strike, high_premium):
    """Buy a call, sell a higher call: cheaper bullish bet with capped profit and loss."""
    return [Leg("call", 1, low_strike, low_premium), Leg("call", -1, high_strike, high_premium)]


def bull_put_spread(short_strike, short_premium, long_strike, long_premium):
    """Sell a put, buy a lower put: collect a credit, defined max loss."""
    return [Leg("put", -1, short_strike, short_premium), Leg("put", 1, long_strike, long_premium)]


def iron_condor(put_long, put_long_prem, put_short, put_short_prem,
                call_short, call_short_prem, call_long, call_long_prem):
    """Bet the price stays in a range: short put spread + short call spread."""
    return [Leg("put", 1, put_long, put_long_prem), Leg("put", -1, put_short, put_short_prem),
            Leg("call", -1, call_short, call_short_prem), Leg("call", 1, call_long, call_long_prem)]
