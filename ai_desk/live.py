"""Daily paper-trading run: the same strategy + risk code as the backtest,
pointed at a broker instead of historical data.

Run it once per day after the US market close (e.g. 4:30pm New York time).
By default it only PRINTS the order it would place (dry run). Add
--execute to actually send it to your Alpaca paper account.

Every run is appended to logs/journal.csv so you can later compare what
you did live against what the backtest says should have happened.
"""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from ai_desk.risk import RiskConfig
from ai_desk.strategies.base import Strategy


@dataclass
class OrderPlan:
    symbol: str
    signal_date: str
    target_weight: float
    price: float
    equity: float
    current_qty: float
    target_qty: int
    order_qty: int
    side: str | None
    reason: str = ""

    @property
    def notional(self) -> float:
        return abs(self.order_qty) * self.price


def plan_order(prices: pd.DataFrame, strategy: Strategy, risk: RiskConfig, symbol: str,
               equity: float, current_qty: float, max_order_notional: float) -> OrderPlan:
    """Pure function (no network) so it can be unit-tested."""
    weight = float(risk.size(strategy.target_exposure(prices), prices).iloc[-1])
    if weight != weight:
        weight = 0.0
    price = float(prices["close"].iloc[-1])
    target_qty = math.floor(weight * equity / price) if weight >= 0 else math.ceil(weight * equity / price)
    diff = target_qty - int(current_qty)
    plan = OrderPlan(symbol, prices.index[-1].date().isoformat(), weight, price, equity,
                     current_qty, target_qty, abs(diff), "buy" if diff > 0 else "sell" if diff < 0 else None)

    if diff == 0:
        plan.reason = "already at target"
    elif abs(diff) * price / equity < risk.rebalance_threshold and target_qty != 0 and current_qty != 0:
        # same rule as the backtest: skip small resizes, they cost more than they help
        plan.order_qty, plan.side, plan.reason = 0, None, "change below minimum trade size"
    elif plan.notional > max_order_notional:
        plan.order_qty, plan.side = 0, None
        plan.reason = f"BLOCKED: order ${abs(diff) * price:,.0f} exceeds max_order_notional ${max_order_notional:,.0f}"
    return plan


def journal(plan: OrderPlan, status: str, path: str | Path = "logs/journal.csv") -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    new = not p.exists()
    with p.open("a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["run_utc", "symbol", "signal_date", "target_weight", "price", "equity",
                        "current_qty", "target_qty", "side", "order_qty", "status", "reason"])
        w.writerow([datetime.now(timezone.utc).isoformat(timespec="seconds"), plan.symbol,
                    plan.signal_date, f"{plan.target_weight:.4f}", f"{plan.price:.2f}",
                    f"{plan.equity:.2f}", plan.current_qty, plan.target_qty, plan.side or "",
                    plan.order_qty, status, plan.reason])


def run_paper(prices: pd.DataFrame, strategy: Strategy, risk: RiskConfig, symbol: str,
              execute: bool = False, max_order_pct: float = 1.05,
              max_drawdown_halt: float = 0.20, max_data_age_days: int | None = 5) -> OrderPlan:
    from ai_desk.broker.alpaca import AlpacaPaper

    # never trade on missing or stale data (e.g. the download silently failed)
    if len(prices) < 260:
        raise RuntimeError(f"only {len(prices)} bars of data - need ~1 year for the indicators")
    age = (pd.Timestamp.today().normalize() - prices.index[-1]).days
    if max_data_age_days is not None and age > max_data_age_days:
        raise RuntimeError(f"latest bar is {prices.index[-1].date()} ({age} days old) - refusing to trade on stale data")

    broker = AlpacaPaper()
    acct = broker.account()
    equity = float(acct["equity"])
    current = broker.position_qty(symbol)

    # cap any single order at a % of equity: protects against bad data or sizing bugs
    plan = plan_order(prices, strategy, risk, symbol, equity, current, max_order_pct * equity)

    # account-level kill switch: compare to the highest equity in our own journal
    peak = max([equity] + _journal_equities())
    if equity / peak - 1 <= -max_drawdown_halt:
        plan.order_qty, plan.side = 0, None
        plan.reason = (f"HALTED: account is {equity / peak - 1:.1%} below its peak. "
                       "Review before trading again.")
    if broker.open_orders(symbol):
        plan.order_qty, plan.side, plan.reason = 0, None, "open order already pending - not stacking another"

    status = "dry_run"
    if execute and plan.side and plan.order_qty > 0:
        order = broker.submit_market_order(symbol, plan.order_qty, plan.side)
        status = f"submitted:{order.get('id', '?')}"
    journal(plan, status)
    return plan


def _journal_equities(path: str | Path = "logs/journal.csv") -> list[float]:
    p = Path(path)
    if not p.exists():
        return []
    with p.open() as f:
        return [float(r["equity"]) for r in csv.DictReader(f) if r.get("equity")]
