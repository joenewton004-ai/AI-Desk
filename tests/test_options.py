import math

import pytest

from ai_desk.options import payoff
from ai_desk.options.black_scholes import greeks, implied_vol, price


def test_textbook_value():
    # Hull's classic example: S=K=100, T=1, r=5%, vol=20% -> call ~10.4506
    assert price("call", 100, 100, 1, 0.2, 0.05) == pytest.approx(10.4506, abs=1e-4)


def test_put_call_parity():
    S, K, t, v, r, q = 580, 600, 0.25, 0.2, 0.04, 0.013
    c, p = price("call", S, K, t, v, r, q), price("put", S, K, t, v, r, q)
    assert c - p == pytest.approx(S * math.exp(-q * t) - K * math.exp(-r * t), abs=1e-9)


@pytest.mark.parametrize("kind", ["call", "put"])
def test_delta_matches_finite_difference(kind):
    h = 0.01
    g = greeks(kind, 100, 105, 0.5, 0.25)
    num = (price(kind, 100 + h, 105, 0.5, 0.25) - price(kind, 100 - h, 105, 0.5, 0.25)) / (2 * h)
    assert g.delta == pytest.approx(num, rel=1e-5)


def test_implied_vol_round_trip():
    p = price("put", 580, 560, 30 / 365, 0.22)
    assert implied_vol("put", p, 580, 560, 30 / 365) == pytest.approx(0.22, abs=1e-5)


def test_iron_condor_profit_is_credit_and_loss_is_defined():
    legs = payoff.iron_condor(90, 0.5, 95, 1.5, 105, 1.5, 110, 0.5)
    stats = payoff.analyze(legs)
    assert stats["net_premium"] == pytest.approx(200)
    assert stats["max_profit"] == pytest.approx(200)
    assert stats["max_loss"] == pytest.approx(-300)
    assert stats["breakevens"] == pytest.approx([93.0, 107.0], abs=0.01)


def test_long_call_unlimited_upside():
    stats = payoff.analyze(payoff.long_call(100, 3))
    assert stats["max_profit"] == "unlimited"
    assert stats["max_loss"] == pytest.approx(-300)


def test_cash_secured_put_max_loss_bounded_at_zero():
    stats = payoff.analyze(payoff.cash_secured_put(100, 2))
    assert stats["max_loss"] == pytest.approx(-(100 - 2) * 100)
