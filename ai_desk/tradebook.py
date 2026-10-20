"""Trade journal: every paper trade, why it was made, how it turned out, and
what we learned - so methods can be improved from evidence, not memory.

Files (committed to git - cloud sessions are temporary, the record isn't):
  journal/trades.jsonl   one line per order: sleeve, reason, the signals at
                         decision time, then fills synced from Alpaca
  journal/notes.jsonl    notes on trades or methods, from you or Claude
  journal/review.json    latest review: lots, P&L by sleeve (feeds the dashboard)

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


def notes() -> list[dict]:
    return _read("notes.jsonl")


# --- recording -------------------------------------------------------------------

def record_orders(plan, method, sleeves: dict[str, pd.Series], signal_date, responses: dict[str, dict]) -> list[dict]:
    """Write one journal line per submitted order."""
    rows = []
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
            "status": "submitted", "filled_qty": None, "fill_price": None, "filled_utc": None,
        }
        _append("trades.jsonl", row)
        rows.append(row)
    return rows


def _sleeve_of_open_lot(symbol: str) -> str | None:
    for t in reversed(trades()):
        if t["symbol"] == symbol and t["side"] == "buy":
            return t.get("sleeve")
    return None


def sync_fills(broker) -> int:
    """Fill prices and statuses from Alpaca for orders not yet final."""
    rows, changed = trades(), 0
    for r in rows:
        if r.get("order_id") and r.get("status") not in ("filled", "canceled", "rejected", "expired"):
            o = broker.get_order(r["order_id"]) or {}
            r["status"] = o.get("status", r["status"])
            if o.get("filled_avg_price"):
                r["fill_price"] = float(o["filled_avg_price"])
                r["filled_qty"] = float(o.get("filled_qty") or 0)
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

def lots(rows: list[dict] | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Match sells to earlier buys of the same symbol (first in, first out).
    Returns (open lots, closed lots). Only filled quantities count."""
    rows = [r for r in (rows or trades()) if r.get("fill_price") and r.get("filled_qty")]
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
        for lot in open_lots.get(r["symbol"], []):
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


def review(prices: dict[str, float], equity: float | None = None, write: bool = True) -> dict:
    """Open positions marked to `prices`, closed trades, and P&L by sleeve."""
    op, cl = lots()
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
