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


@dataclass
class Limits:
    max_position: float = 0.10       # no single holding above 10% of equity (long or short)
    max_gross: float = 1.0           # sum of |weights|; 1.0 = no leverage
    max_order: float = 0.25          # refuse any single order above 25% of equity
    min_trade: float = 0.005         # skip resizes smaller than 0.5% of equity (closing always trades)
    allow_short: bool = False


@dataclass
class Order:
    symbol: str
    side: str            # buy | sell
    qty: int
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
    capped = t.clip(-limits.max_position, limits.max_position)
    if (capped != t).any():
        notes.append(f"capped at {limits.max_position:.0%} per position: {sorted(t.index[capped != t])}")
    gross = capped.abs().sum()
    if gross > limits.max_gross:
        capped *= limits.max_gross / gross
        notes.append(f"scaled down from {gross:.0%} to {limits.max_gross:.0%} gross exposure")
    return capped, notes


def plan_orders(targets: pd.Series, positions: dict[str, float], prices: pd.Series, equity: float,
                limits: Limits | None = None, shortable: dict[str, bool] | None = None) -> Plan:
    """Turn target weights into whole-share orders. No network calls."""
    limits = limits or Limits()
    t, notes = apply_limits(targets, limits)
    plan = Plan(notes=notes, targets=t)
    symbols = sorted(set(t.index) | {s for s, q in positions.items() if q})
    for sym in symbols:
        price = float(prices.get(sym, float("nan")))
        current = int(positions.get(sym, 0))
        weight = float(t.get(sym, 0.0))
        if not price or math.isnan(price) or price <= 0:
            if current or weight:
                plan.notes.append(f"{sym}: no price - left untouched")
            continue
        target_qty = int(weight * equity / price)       # rounds toward zero: never overshoots
        diff = target_qty - current
        if diff == 0:
            continue
        closing = target_qty == 0
        if not closing and abs(diff) * price < limits.min_trade * equity:
            continue
        # crossing from long to short (or back) is sent as two orders: close, then open
        legs = [(-current, "close"), (target_qty, "open")] if current and target_qty and \
            (current > 0) != (target_qty > 0) else [(diff, "close" if closing else "resize" if current else "open")]
        for qty, why in legs:
            order = Order(sym, "buy" if qty > 0 else "sell", abs(qty), price,
                          reason=f"{why}: {current:+d} -> {target_qty:+d} shares (target {weight:+.1%})")
            opens_short = target_qty < 0 and why in ("open", "resize") and qty < 0
            if opens_short and shortable is not None and not shortable.get(sym, False):
                order.blocked = "not shortable at the broker"
            elif order.notional > limits.max_order * equity:
                order.blocked = f"order ${order.notional:,.0f} is over {limits.max_order:.0%} of equity"
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
    plan = plan_orders(targets, positions, closes.iloc[-1], equity, limits, shortable)
    plan.notes.insert(0, f"signals from the close of {closes.index[-1].date()}; equity ${equity:,.0f}")

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
    journal(plan, method.describe(), status, equity)
    return plan
