"""Multi-stock executor: target weights -> the orders that get the account there.

    targets (from a method) + current positions + latest prices + equity
        -> safety checks -> order list (sells first, then buys)
        -> dry run (print + journal) or submit to Alpaca PAPER

`plan_orders` is a pure function (no network) so every rule is unit-tested.
`run` adds the broker, data checks, the kill switch and the journal.
"""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


# Broad, diversified funds. A 50% SPY sleeve is by design (research/THESIS.md),
# so these get their own, higher caps instead of the single-stock ones.
INDEX_FUNDS = ("SPY", "VOO", "IVV", "VTI", "QQQ", "IWM", "DIA", "TLT", "IEF", "GLD", "BIL", "SHY", "SGOV")


@dataclass
class Limits:
    max_position: float = 0.10       # no single stock above 10% of equity (long or short)
    max_gross: float = 1.0           # sum of |weights|; 1.0 = no leverage
    max_order: float = 0.25          # refuse any single stock order above 25% of equity
    min_trade: float = 0.005         # skip resizes smaller than 0.5% of equity (closing always trades)
    allow_short: bool = False
    max_fund_position: float = 0.60  # cap for INDEX_FUNDS (position and order size)
    funds: tuple = INDEX_FUNDS
    fractional: bool = True          # fractional shares for longs where the broker allows them
    cash_buffer: float = 0.01        # keep 1% in cash so market orders that fill a bit higher
                                     # than the last close don't push the account onto margin

    def position_cap(self, symbol: str) -> float:
        return self.max_fund_position if symbol in self.funds else self.max_position

    def order_cap(self, symbol: str) -> float:
        return self.max_fund_position if symbol in self.funds else self.max_order


@dataclass
class Order:
    symbol: str
    side: str            # buy | sell
    qty: float           # may be fractional (longs only)
    price: float
    reason: str = ""
    blocked: str = ""    # non-empty = will NOT be sent, and why

    @property
    def notional(self) -> float:
        return self.qty * self.price


@dataclass
class Plan:
    orders: list[Order] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    targets: pd.Series | None = None

    @property
    def sendable(self) -> list[Order]:
        return [o for o in self.orders if not o.blocked]


def apply_limits(targets: pd.Series, limits: Limits) -> tuple[pd.Series, list[str]]:
    """Clean and cap the method's weights before they become orders."""
    notes = []
    t = targets.astype(float).fillna(0.0)
    t = t[t != 0]
    if not limits.allow_short and (t < 0).any():
        notes.append(f"shorting disabled: dropped short targets {sorted(t[t < 0].index)}")
        t = t[t > 0]
    caps = pd.Series({s: limits.position_cap(s) for s in t.index}, dtype=float)
    capped = t.clip(-caps, caps)
    if (capped != t).any():
        notes.append(f"capped at {limits.max_position:.0%} per stock / {limits.max_fund_position:.0%} per index "
                     f"fund: {sorted(t.index[capped != t])}")
    gross = capped.abs().sum()
    if gross > limits.max_gross:
        capped *= limits.max_gross / gross
        notes.append(f"scaled down from {gross:.0%} to {limits.max_gross:.0%} gross exposure")
    longs = capped[capped > 0].sum()
    max_long = 1 - limits.cash_buffer
    if longs > max_long:
        capped[capped > 0] *= max_long / longs
        notes.append(f"kept a {limits.cash_buffer:.0%} cash buffer: long positions scaled to {max_long:.0%} of equity")
    return capped, notes


FRACTION_DP = 4     # fractional orders: 4 decimal places (Alpaca accepts up to 9)


def _round_toward_zero(x: float, dp: int) -> float:
    f = 10 ** dp
    return math.trunc(x * f) / f


def plan_orders(targets: pd.Series, positions: dict[str, float], prices: pd.Series, equity: float,
                limits: Limits | None = None, shortable: dict[str, bool] | None = None,
                fractionable: dict[str, bool] | None = None, frozen: set[str] | None = None) -> Plan:
    """Turn target weights into orders. No network calls.

    With limits.fractional, long positions use fractional shares (so a $2,000
    slot buys 1.61 shares of a $1,240 stock instead of 1). Shorts, and stocks
    the broker marks as not fractionable, use whole shares. Quantities round
    toward zero, so a target is never overshot.

    frozen: symbols already held whose size must not change this run (stocks
    between scheduled re-picks); they can still be closed if no longer targeted.
    """
    limits = limits or Limits()
    t, notes = apply_limits(targets, limits)
    plan = Plan(notes=notes, targets=t)
    symbols = sorted(set(t.index) | {s for s, q in positions.items() if q})
    for sym in symbols:
        price = float(prices.get(sym, float("nan")))
        current = float(positions.get(sym, 0.0))
        weight = float(t.get(sym, 0.0))
        if not price or math.isnan(price) or price <= 0:
            if current or weight:
                plan.notes.append(f"{sym}: no price - left untouched")
            continue
        can_fraction = limits.fractional and (fractionable is None or fractionable.get(sym, False))
        raw = weight * equity / price
        target_qty = _round_toward_zero(raw, FRACTION_DP) if can_fraction and raw > 0 else float(math.trunc(raw))
        diff = round(target_qty - current, FRACTION_DP)
        if diff == 0:
            continue
        if frozen and sym in frozen and current and target_qty and (current > 0) == (target_qty > 0):
            continue    # held until its next scheduled re-pick: let it drift
        closing = target_qty == 0
        if not closing and abs(diff) * price < limits.min_trade * equity:
            continue
        # crossing from long to short (or back) is sent as two orders: close, then open
        flip = current and target_qty and (current > 0) != (target_qty > 0)
        legs = [(-current, "close"), (target_qty, "open")] if flip else \
            [(diff, "close" if closing else "resize" if current else "open")]
        for qty, why in legs:
            order = Order(sym, "buy" if qty > 0 else "sell", round(abs(qty), FRACTION_DP), price,
                          reason=f"{why}: {current:+g} -> {target_qty:+g} shares (target {weight:+.1%})")
            opens_short = target_qty < 0 and why in ("open", "resize") and qty < 0
            if opens_short and shortable is not None and not shortable.get(sym, False):
                order.blocked = "not shortable at the broker"
            elif order.notional > limits.order_cap(sym) * equity:
                order.blocked = f"order ${order.notional:,.0f} is over {limits.order_cap(sym):.0%} of equity"
            plan.orders.append(order)
    # sells first: they free up cash for the buys
    plan.orders.sort(key=lambda o: (o.side != "sell", o.symbol))
    return plan


JOURNAL = Path("logs/portfolio_journal.csv")


def journal(plan: Plan, method: str, status: str, equity: float, path: str | Path | None = None) -> None:
    """One row per order (or one 'no changes' row), so every run is on record."""
    p = Path(path or JOURNAL)
    p.parent.mkdir(parents=True, exist_ok=True)
    new = not p.exists()
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with p.open("a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["run_utc", "method", "equity", "symbol", "side", "qty", "price", "notional", "reason",
                        "blocked", "status"])
        for o in plan.orders:
            w.writerow([now, method, f"{equity:.2f}", o.symbol, o.side, o.qty, f"{o.price:.2f}",
                        f"{o.notional:.2f}", o.reason, o.blocked, "blocked" if o.blocked else status])
        if not plan.orders:
            w.writerow([now, method, f"{equity:.2f}", "", "", 0, "", "", "no changes needed", "", status])


def journal_peak(path: str | Path | None = None) -> float:
    p = Path(path or JOURNAL)
    if not p.exists():
        return 0.0
    with p.open() as f:
        return max((float(r["equity"]) for r in csv.DictReader(f) if r.get("equity")), default=0.0)


def run(method, limits: Limits | None = None, execute: bool = False, source: str = "yahoo",
        max_data_age_days: int = 5, account_dd_halt: float = 0.20, broker=None) -> Plan:
    """Compute today's targets, compare with the paper account, and (optionally) trade."""
    from ai_desk.broker.alpaca import AlpacaPaper
    from ai_desk.data import load_many
    from ai_desk.live import drop_incomplete_bar

    limits = limits or Limits(allow_short=method.can_short)
    # two years covers the longest signal (200-day average, 12-month momentum);
    # the synthetic demo data is old, so it uses everything
    start = "2000-01-01" if source == "synthetic" else (pd.Timestamp.today() - pd.DateOffset(years=2)).date().isoformat()
    prices = load_many(method.symbols(), start, source=source)
    closes = drop_incomplete_bar(prices["close"])
    if len(closes) < 260:
        raise RuntimeError(f"only {len(closes)} days of prices for {method.symbols()} - need about a year")
    age = (pd.Timestamp.today().normalize() - closes.index[-1]).days
    if max_data_age_days is not None and age > max_data_age_days:
        raise RuntimeError(f"latest prices are from {closes.index[-1].date()} ({age} days old) - not trading")
    targets = method.latest(closes)

    broker = broker or AlpacaPaper()
    equity = float(broker.account()["equity"])
    positions = broker.positions()
    shortable = {s: bool(broker.asset(s).get("shortable")) for s in targets.index[targets < 0]}
    fractionable = ({s: bool(broker.asset(s).get("fractionable")) for s in targets.index[targets > 0]}
                    if limits.fractional else None)
    plan = plan_orders(targets, positions, closes.iloc[-1], equity, limits, shortable, fractionable,
                       frozen=method.frozen())
    plan.notes[:0] = [f"signals from the close of {closes.index[-1].date()}; equity ${equity:,.0f}",
                      *method.status()]

    peak = max(equity, journal_peak())
    if equity / peak - 1 <= -account_dd_halt:
        for o in plan.orders:
            o.blocked = o.blocked or f"HALTED: account {equity / peak - 1:.1%} below its peak - review first"
    if broker.open_orders():
        for o in plan.orders:
            o.blocked = o.blocked or "orders still pending at the broker - not stacking more"

    status = "dry_run"
    if execute:
        for o in plan.sendable:
            resp = broker.submit_market_order(o.symbol, o.qty, o.side)
            o.reason += f" [order {resp.get('id', '?')}]"
        status = "submitted"
        if not any(o.blocked for o in plan.orders):
            method.on_executed()       # e.g. lock in the new stock picks
    journal(plan, method.describe(), status, equity)
    return plan
