"""Black-Scholes pricing for European options (SPX index options are European;
SPY options are American, but for calls on non-dividend payers and most
practical purposes the numbers are close enough for learning).

Inputs:
  spot   S  - current underlying price
  strike K
  t         - years to expiry (30 days = 30/365)
  vol    σ  - annualised implied volatility (0.18 = 18%)
  rate   r  - risk-free rate (0.04 = 4%)
  div    q  - continuous dividend yield (SPY ~ 0.013)
"""

from __future__ import annotations

import math
from dataclasses import dataclass


def _norm_cdf(x: float) -> float:
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def _norm_pdf(x: float) -> float:
    return math.exp(-0.5 * x * x) / math.sqrt(2 * math.pi)


def _d1_d2(spot, strike, t, vol, rate, div):
    d1 = (math.log(spot / strike) + (rate - div + 0.5 * vol * vol) * t) / (vol * math.sqrt(t))
    return d1, d1 - vol * math.sqrt(t)


def price(kind: str, spot: float, strike: float, t: float, vol: float,
          rate: float = 0.04, div: float = 0.0) -> float:
    kind = kind.lower()
    if kind not in ("call", "put"):
        raise ValueError("kind must be 'call' or 'put'")
    if t <= 0 or vol <= 0:
        intrinsic = spot - strike if kind == "call" else strike - spot
        return max(intrinsic, 0.0)
    d1, d2 = _d1_d2(spot, strike, t, vol, rate, div)
    df_r, df_q = math.exp(-rate * t), math.exp(-div * t)
    if kind == "call":
        return spot * df_q * _norm_cdf(d1) - strike * df_r * _norm_cdf(d2)
    return strike * df_r * _norm_cdf(-d2) - spot * df_q * _norm_cdf(-d1)


@dataclass
class Greeks:
    price: float
    delta: float   # $ change in option per $1 move in the underlying
    gamma: float   # change in delta per $1 move
    vega: float    # $ change per 1 vol POINT (e.g. 18% -> 19%)
    theta: float   # $ change per calendar DAY passing (usually negative for buyers)
    rho: float     # $ change per 1 percentage point change in rates


def greeks(kind: str, spot: float, strike: float, t: float, vol: float,
           rate: float = 0.04, div: float = 0.0) -> Greeks:
    kind = kind.lower()
    p = price(kind, spot, strike, t, vol, rate, div)
    if t <= 0 or vol <= 0:
        itm = (spot > strike) if kind == "call" else (spot < strike)
        return Greeks(p, (1.0 if kind == "call" else -1.0) if itm else 0.0, 0.0, 0.0, 0.0, 0.0)
    d1, d2 = _d1_d2(spot, strike, t, vol, rate, div)
    df_r, df_q = math.exp(-rate * t), math.exp(-div * t)
    sqrt_t = math.sqrt(t)
    gamma = df_q * _norm_pdf(d1) / (spot * vol * sqrt_t)
    vega = spot * df_q * _norm_pdf(d1) * sqrt_t / 100
    common = -spot * df_q * _norm_pdf(d1) * vol / (2 * sqrt_t)
    if kind == "call":
        delta = df_q * _norm_cdf(d1)
        theta = common - rate * strike * df_r * _norm_cdf(d2) + div * spot * df_q * _norm_cdf(d1)
        rho = strike * t * df_r * _norm_cdf(d2) / 100
    else:
        delta = -df_q * _norm_cdf(-d1)
        theta = common + rate * strike * df_r * _norm_cdf(-d2) - div * spot * df_q * _norm_cdf(-d1)
        rho = -strike * t * df_r * _norm_cdf(-d2) / 100
    return Greeks(p, delta, gamma, vega, theta / 365, rho)


def implied_vol(kind: str, market_price: float, spot: float, strike: float, t: float,
                rate: float = 0.04, div: float = 0.0, lo: float = 1e-4, hi: float = 5.0,
                tol: float = 1e-6) -> float:
    """Volatility that makes Black-Scholes match an observed option price (bisection)."""
    if market_price <= price(kind, spot, strike, t, lo, rate, div):
        return lo
    if market_price >= price(kind, spot, strike, t, hi, rate, div):
        raise ValueError("price is above the maximum model value - check inputs")
    for _ in range(200):
        mid = (lo + hi) / 2
        if price(kind, spot, strike, t, mid, rate, div) > market_price:
            hi = mid
        else:
            lo = mid
        if hi - lo < tol:
            break
    return (lo + hi) / 2
