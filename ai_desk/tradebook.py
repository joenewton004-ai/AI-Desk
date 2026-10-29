"""Trade journal: every paper trade, why it was made, how it turned out, and
what we learned - so methods can be improved from evidence, not memory.

Files (committed to git - cloud sessions are temporary, the record isn't):
  journal/trades.jsonl   one line per order: sleeve, reason, the signals at
                         decision time, then fills synced from Alpaca
  journal/notes.jsonl    notes on trades or methods, from you or Claude
  journal/review.json    latest review: lots, P&L by sleeve (feeds the dashboard)
  journal/plan.json      the latest plan (dry run or executed): targets by sleeve, orders

Flow:  portfolio run --execute  -> orders recorded automatically
       journal sync             -> fill prices from Alpaca
       journal review           -> open/closed lots, P&L by sleeve, lessons
       journal note             -> add a note to a trade, symbol or method
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

DIR = Path("journal")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _read(name: str) -> list[dict]:
    p = DIR / name
    if not p.exists():
        return []
    return [json.loads(line) for line in p.read_text().splitlines() if line.strip()]


def _write(name: str, rows: list[dict]) -> None:
    DIR.mkdir(parents=True, exist_ok=True)
    (DIR / name).write_text("".join(json.dumps(r, default=str) + "\n" for r in rows))


def _append(name: str, row: dict) -> None:
    DIR.mkdir(parents=True, exist_ok=True)
    with (DIR / name).open("a") as f:
        f.write(json.dumps(row, default=str) + "\n")


def trades() -> list[dict]:
    return _read("trades.jsonl")


def _read_plan() -> dict:
    p = DIR / "plan.json"
    return json.loads(p.read_text()) if p.exists() else {}


def notes() -> list[dict]:
    return _read("notes.jsonl")


# --- recording -------------------------------------------------------------------

OVERNIGHT = "overnight_drift"


def _overnight_rows(sym: str, qty: float, price: float, side: str, signal_date, order_id: str | None,
                    transfer_to: str | None = None) -> dict:
    """One journal line for the overnight sleeve's part of a netted order (or, with no order of its own, a transfer
    of its shares to a desk sleeve at the last close)."""
    transfer = order_id is None
    return {
        "id": uuid.uuid4().hex[:8], "created_utc": _now(), "signal_date": str(signal_date), "symbol": sym,
        "side": side, "qty": qty, "est_price": round(price, 4), "est_notional": round(qty * price, 2),
        "sleeve": OVERNIGHT if side == "sell" else transfer_to, "target_by_sleeve": {}, "action": "close" if side == "sell" else "open",
        "reason": ("overnight: sold at the open inside the desk's order for this stock" if not transfer else
                   f"overnight: {qty:g} shares handed to {transfer_to} at the last close (the desk kept them - no order)"),
        "exit_reason": "overnight: held from the close to the next open" if side == "sell" else None,
        "rationale": {}, "method": "overnight_drift (amendment 330e76e0)", "order_id": order_id,
        "order_type": "market" if not transfer else "transfer", "limit_price": None,
        "status": "submitted" if not transfer else "transfer",
        "filled_qty": qty if transfer else None, "fill_price": round(price, 4) if transfer else None,
        "filled_utc": _now() if transfer else None,
    }


def record_orders(plan, method, sleeves: dict[str, pd.Series], signal_date, responses: dict[str, dict],
                  overnight_book: dict[str, float] | None = None, prices: dict | None = None) -> list[dict]:
    """Write one journal line per submitted order. Shares the overnight sleeve holds (`overnight_book`) are sold
    inside the desk's own order for the stock: that order is written as two lines - the overnight sleeve's part
    and the desk's - sharing the order id, so each sleeve's P&L stays its own."""
    rows = []
    book = dict(overnight_book or {})
    prices = {**{k: float(v) for k, v in dict(prices or {}).items()}, **{o.symbol: o.price for o in plan.orders}}
    for o in plan.sendable:
        by_sleeve = {name: round(float(w.get(o.symbol, 0.0)), 5) for name, w in sleeves.items()
                     if abs(float(w.get(o.symbol, 0.0))) > 1e-9}
        sleeve = max(by_sleeve, key=lambda k: abs(by_sleeve[k])) if by_sleeve else _sleeve_of_open_lot(o.symbol)
        closing = o.side == "sell" and not by_sleeve
        row = {
            "id": uuid.uuid4().hex[:8], "created_utc": _now(), "signal_date": str(signal_date),
            "symbol": o.symbol, "side": o.side, "qty": o.qty, "est_price": round(o.price, 4),
            "est_notional": round(o.notional, 2), "sleeve": sleeve, "target_by_sleeve": by_sleeve,
            "action": o.reason.split(":")[0], "reason": o.reason.split(" [order")[0],
            "exit_reason": method.exit_reason(o.symbol) if o.side == "sell" else None,
            "rationale": method.rationale(o.symbol) if not closing else {},
            "method": method.describe(), "order_id": responses.get(o.symbol, {}).get("id"),
            "order_type": responses.get(o.symbol, {}).get("type", "market"),
            "limit_price": responses.get(o.symbol, {}).get("limit_price"),
            "status": "submitted", "filled_qty": None, "fill_price": None, "filled_utc": None,
        }
        on = book.pop(o.symbol, 0.0)
        if on > 1e-9:
            oid = row["order_id"]
            desk_sleeve = max(by_sleeve, key=lambda k: abs(by_sleeve[k])) if by_sleeve else None
            if o.side == "sell":
                take = min(on, o.qty)
                rows.append(_overnight_rows(o.symbol, take, o.price, "sell", signal_date, oid))
                if on - take > 1e-9:          # the desk wants some of them: they change hands, no order
                    rows.append(_overnight_rows(o.symbol, on - take, o.price, "sell", signal_date, None, desk_sleeve))
                    rows.append(_overnight_rows(o.symbol, on - take, o.price, "buy", signal_date, None, desk_sleeve))
                rest = o.qty - take
                if rest <= 1e-9:
                    row = None
                else:
                    row.update(qty=round(rest, 6), est_notional=round(rest * o.price, 2))
            else:                             # the desk buys more than the overnight shares: they change hands
                rows.append(_overnight_rows(o.symbol, on, o.price, "sell", signal_date, None, desk_sleeve))
                rows.append(_overnight_rows(o.symbol, on, o.price, "buy", signal_date, None, desk_sleeve))
        if row is not None:
            rows.append(row)
    for sym, on in book.items():              # no order at all: the desk kept exactly the overnight shares
        price = prices.get(sym)
        if price and on > 1e-9:
            to = _sleeve_of_open_lot(sym, exclude=OVERNIGHT)
            rows.append(_overnight_rows(sym, on, price, "sell", signal_date, None, to))
            rows.append(_overnight_rows(sym, on, price, "buy", signal_date, None, to))
    for r in rows:
        _append("trades.jsonl", r)
    return rows


def record_overnight_buys(fills: list[dict]) -> int:
    """The overnight sleeve's filled buys near the close, as journal lines (once per order)."""
    seen = {t.get("order_id") for t in trades()}
    n = 0
    for f in fills:
        if not f.get("order_id") or f["order_id"] in seen or not f.get("filled_qty"):
            continue
        _append("trades.jsonl", {
            "id": uuid.uuid4().hex[:8], "created_utc": _now(), "signal_date": f.get("date"), "symbol": f["symbol"],
            "side": "buy", "qty": f["filled_qty"], "est_price": f.get("ref_price"),
            "est_notional": round(f["filled_qty"] * (f.get("ref_price") or 0), 2), "sleeve": OVERNIGHT,
            "target_by_sleeve": {}, "action": "open",
            "reason": f"overnight: bought near the close ({f['filled_qty']:g} of {f.get('qty', f['filled_qty']):g} "
                      "shares filled), to sell at the next open",
            "exit_reason": None, "rationale": {"overnight_drift": f.get("rationale") or {}},
            "method": "overnight_drift (amendment 330e76e0)", "order_id": f["order_id"],
            "order_type": f.get("order_type", "market"), "limit_price": None, "status": "filled",
            "filled_qty": f["filled_qty"], "fill_price": f["fill_price"], "filled_utc": f.get("filled_utc"),
        })
        n += 1
    return n


def save_plan(plan, method, sleeves: dict[str, pd.Series], signal_date, equity, positions, status) -> dict:
    """Snapshot of the latest plan, so the dashboard shows what the desk wants to own."""
    orders = {o.symbol: o for o in plan.orders}
    symbols = sorted(set(plan.targets.index if plan.targets is not None else []) | set(orders)
                     | {s for s, q in positions.items() if q})
    rows = []
    for sym in symbols:
        by_sleeve = {n: round(float(w.get(sym, 0.0)), 5) for n, w in sleeves.items()
                     if abs(float(w.get(sym, 0.0))) > 1e-9}
        o = orders.get(sym)
        rows.append({
            "symbol": sym, "sleeve": max(by_sleeve, key=lambda k: abs(by_sleeve[k])) if by_sleeve else None,
            "target": round(float(plan.targets.get(sym, 0.0)), 5) if plan.targets is not None else None,
            "target_by_sleeve": by_sleeve, "held_qty": float(positions.get(sym, 0.0)),
            "side": o.side if o else None, "qty": o.qty if o else 0.0,
            "notional": round(o.notional, 2) if o else 0.0, "price": round(o.price, 4) if o else None,
            "reason": o.reason.split(" [order")[0] if o else "", "blocked": o.blocked if o else "",
            "exit_reason": method.exit_reason(sym) if o and o.side == "sell" else None,
            "rationale": method.rationale(sym) if by_sleeve else {},
        })
    out = {"created_utc": _now(), "signal_date": str(signal_date), "equity": equity, "status": status,
           "method": method.describe(), "notes": plan.notes, "rows": rows}
    DIR.mkdir(parents=True, exist_ok=True)
    (DIR / "plan.json").write_text(json.dumps(out, indent=1, default=str))
    return out


def _sleeve_of_open_lot(symbol: str, exclude: str | None = None) -> str | None:
    for t in reversed(trades()):
        if t["symbol"] == symbol and t["side"] == "buy" and t.get("sleeve") != exclude:
            return t.get("sleeve")
    return None


def sync_fills(broker) -> int:
    """Fill prices and statuses from Alpaca for orders not yet final."""
    rows, changed = trades(), 0
    # one order can carry two lines (the overnight sleeve's shares and the desk's): share the fill by quantity
    per_order: dict[str, float] = {}
    for r in rows:
        if r.get("order_id"):
            per_order[r["order_id"]] = per_order.get(r["order_id"], 0.0) + float(r.get("qty") or 0)
    cache: dict[str, dict] = {}
    for r in rows:
        if r.get("order_id") and r.get("status") not in ("filled", "canceled", "rejected", "expired"):
            o = cache.get(r["order_id"]) or broker.get_order(r["order_id"]) or {}
            cache[r["order_id"]] = o
            r["status"] = o.get("status", r["status"])
            if o.get("filled_avg_price"):
                share = float(r.get("qty") or 0) / per_order[r["order_id"]] if per_order.get(r["order_id"]) else 1.0
                r["fill_price"] = float(o["filled_avg_price"])
                r["filled_qty"] = round(float(o.get("filled_qty") or 0) * share, 6)
                r["filled_utc"] = o.get("filled_at")
            changed += 1
    _write("trades.jsonl", rows)
    return changed


def add_note(target: str, text: str, author: str = "you", kind: str = "note") -> dict:
    """target: a trade id, a symbol, or a method name (e.g. bottleneck)."""
    row = {"id": uuid.uuid4().hex[:8], "created_utc": _now(), "target": target, "author": author,
           "kind": kind, "text": text}
    _append("notes.jsonl", row)
    return row


# --- review ---------------------------------------------------------------------

def _utc(t: str) -> pd.Timestamp:
    ts = pd.Timestamp(t)
    return ts.tz_localize("UTC") if ts.tzinfo is None else ts.tz_convert("UTC")


def lots(rows: list[dict] | None = None, asof: str | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Match sells to earlier buys of the same symbol (first in, first out).
    Returns (open lots, closed lots). Only filled quantities count; with `asof` (a UTC time), only fills up to then."""
    rows = [r for r in (rows or trades()) if r.get("fill_price") and r.get("filled_qty")]
    if asof:
        rows = [r for r in rows if _utc(r.get("filled_utc") or r["created_utc"]) <= _utc(asof)]
    open_lots: dict[str, list[dict]] = {}
    closed = []
    for r in sorted(rows, key=lambda x: x.get("filled_utc") or x["created_utc"]):
        q = float(r["filled_qty"])
        if r["side"] == "buy":
            open_lots.setdefault(r["symbol"], []).append({
                "trade_id": r["id"], "symbol": r["symbol"], "sleeve": r.get("sleeve"), "qty": q,
                "entry_price": r["fill_price"], "entry_utc": r.get("filled_utc") or r["created_utc"],
                "entry_rationale": r.get("rationale", {})})
            continue
        # a sleeve's sale closes that sleeve's own lots first (the overnight sleeve shares stocks with the desk)
        mine = [lt for lt in open_lots.get(r["symbol"], []) if lt["sleeve"] == r.get("sleeve")]
        for lot in mine + [lt for lt in open_lots.get(r["symbol"], []) if lt["sleeve"] != r.get("sleeve")]:
            if q <= 1e-9:
                break
            take = min(q, lot["qty"])
            if take <= 0:
                continue
            closed.append({**{k: lot[k] for k in ("trade_id", "symbol", "sleeve", "entry_price", "entry_utc")},
                           "qty": take, "exit_trade_id": r["id"], "exit_price": r["fill_price"],
                           "exit_utc": r.get("filled_utc") or r["created_utc"],
                           "exit_reason": r.get("exit_reason") or r.get("reason"),
                           "pnl": take * (r["fill_price"] - lot["entry_price"]),
                           "return": r["fill_price"] / lot["entry_price"] - 1})
            lot["qty"] -= take
            q -= take
    still_open = [lot for lots_ in open_lots.values() for lot in lots_ if lot["qty"] > 1e-9]
    return pd.DataFrame(still_open), pd.DataFrame(closed)


# a sleeve replaced by another: a stock the new sleeve kept on the switch day belongs to it from then on
HANDOVERS = {"bottleneck": ("momentum", Path("data/portfolio/momentum.json"))}


def handed_over(sleeve: str, symbol: str) -> str:
    """The sleeve that owns an open position now: the buyer's sleeve, unless its successor's lock kept the stock."""
    if sleeve not in HANDOVERS:
        return sleeve
    to, lock = HANDOVERS[sleeve]
    try:
        picks = json.loads(lock.read_text()).get("picks") or []
    except (OSError, ValueError):
        return sleeve
    return to if symbol in picks else sleeve


def review(prices: dict[str, float], equity: float | None = None, write: bool = True, asof: str | None = None) -> dict:
    """Open positions marked to `prices`, closed trades, and P&L by sleeve (with `asof`: fills up to that time only,
    so the lots match a price snapshot taken then)."""
    op, cl = lots(asof=asof)
    if len(op):
        now = [handed_over(s, y) for s, y in zip(op["sleeve"], op["symbol"])]
        op["handed_over_from"] = [s if n != s else None for s, n in zip(op["sleeve"], now)]
        op["sleeve"] = now
    if len(op):
        op["price"] = op["symbol"].map(prices)
        op["unrealized_pnl"] = op["qty"] * (op["price"] - op["entry_price"])
        op["return"] = op["price"] / op["entry_price"] - 1
        op["held_days"] = (pd.Timestamp.now(tz="UTC") - pd.to_datetime(op["entry_utc"], utc=True)).dt.days
    if len(cl):
        cl["held_days"] = (pd.to_datetime(cl["exit_utc"], utc=True) - pd.to_datetime(cl["entry_utc"], utc=True)).dt.days
    sleeves = sorted(set(op.get("sleeve", pd.Series(dtype=str)).dropna()) | set(cl.get("sleeve", pd.Series(dtype=str)).dropna()))
    by_sleeve = {}
    for s in sleeves:
        o = op[op["sleeve"] == s] if len(op) else op
        c = cl[cl["sleeve"] == s] if len(cl) else cl
        cost = float((o["qty"] * o["entry_price"]).sum()) if len(o) else 0.0
        by_sleeve[s] = {
            "open_positions": int(len(o)), "invested": round(cost, 2),
            "unrealized_pnl": round(float(o["unrealized_pnl"].sum()), 2) if len(o) else 0.0,
            "realized_pnl": round(float(c["pnl"].sum()), 2) if len(c) else 0.0,
            "closed_trades": int(len(c)),
            "win_rate": round(float((c["pnl"] > 0).mean()), 3) if len(c) else None,
            "avg_closed_return": round(float(c["return"].mean()), 4) if len(c) else None,
        }
    exits = cl.groupby(cl["exit_reason"].str.split(":").str[0])["return"].agg(["count", "mean"]).round(4) \
        if len(cl) else pd.DataFrame()
    out = {"asof_utc": _now(), "equity": equity, "by_sleeve": by_sleeve,
           "open": op.to_dict("records") if len(op) else [], "closed": cl.to_dict("records") if len(cl) else [],
           "exit_reasons": exits.reset_index().to_dict("records") if len(exits) else [],
           "trades_logged": len(trades()), "notes": len(notes())}
    if write:
        DIR.mkdir(parents=True, exist_ok=True)
        (DIR / "review.json").write_text(json.dumps(out, indent=1, default=str))
    return out
