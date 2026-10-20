"""Flat tables for the trading-journal dashboard.

The dashboard reads plain row files, so this turns the journal (plan, trades,
notes, review, methodology register, amendments) into one JSON array per
table under journal/dashboard/. Run `python -m ai_desk journal export` after
a plan, an execute or a review, then ask Claude to refresh the dashboard.
"""

from __future__ import annotations

import json

from ai_desk import register, tradebook


def _fmt(v) -> str:
    if isinstance(v, float):
        return f"{v:.4g}"
    return str(v)


def _compact(d: dict, depth: int = 0) -> str:
    """{'quality_screen': {'roic': 0.31, 'fwd_pe': 22}} -> 'quality_screen: roic=0.31, fwd_pe=22'"""
    parts = []
    for k, v in (d or {}).items():
        if isinstance(v, dict):
            parts.append(f"{k}: {_compact(v, depth + 1)}")
        elif v is not None and v == v:          # skip None and NaN
            parts.append(f"{k}={_fmt(v)}")
    return (" | " if depth == 0 else ", ").join(parts)


def _read_json(name: str) -> dict:
    p = tradebook.DIR / name
    return json.loads(p.read_text()) if p.exists() else {}


def tables() -> dict[str, list[dict]]:
    reg = register.register()
    plan = tradebook._read_plan()
    review = _read_json("review.json")
    trades, notes, amends = tradebook.trades(), tradebook.notes(), register.amendments()

    def notes_for(*targets):
        return " / ".join(n["text"] for n in notes if n["target"] in targets)

    methods = [{
        "method": m["name"], "live": m["in_live_mix"], "allocation": m["allocation"], "status": m["status"],
        "description": m["description"], "evidence": m["evidence_summary"],
        "parameters": "; ".join(f"{k}={v}" for k, v in m["parameters"].items()),
        "docs": ", ".join(m["docs"]),
        "open_amendments": sum(1 for a in m["amendments"] if a["status"] in ("proposed", "testing")),
        "notes": notes_for(m["name"]),
    } for m in reg["methods"]]

    positions = [{
        "symbol": r["symbol"], "sleeve": r["sleeve"] or "", "target": r["target"] or 0.0,
        "target_usd": round((r["target"] or 0.0) * (plan.get("equity") or 0.0), 2),
        "held_qty": r["held_qty"], "order": f"{r['side']} {r['qty']:g}" if r["side"] else "",
        "order_usd": r["notional"], "reason": r["reason"], "blocked": r["blocked"],
        "exit_reason": r["exit_reason"] or "", "rationale": _compact(r.get("rationale") or {}),
        "notes": notes_for(r["symbol"]),
    } for r in plan.get("rows", [])]

    trade_rows = [{
        "id": t["id"], "date": (t.get("filled_utc") or t["created_utc"])[:10], "signal_date": t["signal_date"],
        "symbol": t["symbol"], "side": t["side"], "qty": t.get("filled_qty") or t["qty"],
        "price": t.get("fill_price") or t["est_price"], "filled": bool(t.get("fill_price")),
        "notional": round((t.get("filled_qty") or t["qty"]) * (t.get("fill_price") or t["est_price"]), 2),
        "sleeve": t.get("sleeve") or "", "action": t.get("action") or "", "status": t.get("status") or "",
        "reason": t.get("reason") or "", "exit_reason": t.get("exit_reason") or "",
        "rationale": _compact(t.get("rationale") or {}), "notes": notes_for(t["id"], t["symbol"]),
    } for t in trades]

    closed = [{
        "symbol": c["symbol"], "sleeve": c.get("sleeve") or "", "entry_date": str(c["entry_utc"])[:10],
        "exit_date": str(c["exit_utc"])[:10], "held_days": c.get("held_days"), "qty": c["qty"],
        "entry_price": c["entry_price"], "exit_price": c["exit_price"], "pnl": round(c["pnl"], 2),
        "return": round(c["return"], 4), "exit_reason": c.get("exit_reason") or "",
        "notes": notes_for(c["trade_id"], c["exit_trade_id"]),
    } for c in review.get("closed", [])]

    by_sleeve = review.get("by_sleeve", {})
    alloc = reg["live_allocation"]
    planned = {}
    for r in plan.get("rows", []):
        for s, w in r["target_by_sleeve"].items():
            planned[s] = planned.get(s, 0.0) + w
    sleeves = [{
        "sleeve": s, "allocation": alloc.get(s, 0.0), "planned_weight": round(planned.get(s, 0.0), 4),
        "open_positions": by_sleeve.get(s, {}).get("open_positions", 0),
        "invested": by_sleeve.get(s, {}).get("invested", 0.0),
        "unrealized_pnl": by_sleeve.get(s, {}).get("unrealized_pnl", 0.0),
        "realized_pnl": by_sleeve.get(s, {}).get("realized_pnl", 0.0),
        "closed_trades": by_sleeve.get(s, {}).get("closed_trades", 0),
        "win_rate": by_sleeve.get(s, {}).get("win_rate"),
    } for s in dict.fromkeys([*alloc, *planned, *by_sleeve])]

    orders = [r for r in plan.get("rows", []) if r["side"] and not r["blocked"]]
    summary = [{
        "equity": review.get("equity") or plan.get("equity"), "signal_date": plan.get("signal_date"),
        "plan_status": plan.get("status"), "plan_method": plan.get("method"),
        "orders": len(orders),
        "buy_usd": round(sum(r["notional"] for r in orders if r["side"] == "buy"), 2),
        "sell_usd": round(sum(r["notional"] for r in orders if r["side"] == "sell"), 2),
        "trades_logged": len(trades), "trades_filled": sum(1 for t in trades if t.get("fill_price")),
        "notes": len(notes), "open_amendments": sum(1 for a in amends if a["status"] in ("proposed", "testing")),
        "unrealized_pnl": round(sum(v.get("unrealized_pnl", 0.0) for v in by_sleeve.values()), 2),
        "realized_pnl": round(sum(v.get("realized_pnl", 0.0) for v in by_sleeve.values()), 2),
        "plan_utc": plan.get("created_utc"), "review_utc": review.get("asof_utc"),
    }]

    amendments = [{
        "id": a["id"], "date": a["created_utc"][:10], "method": a["method"], "proposal": a["proposal"],
        "rationale": a["rationale"], "author": a["author"], "status": a["status"], "evidence": a["evidence"],
        "decided": (a.get("decided_utc") or "")[:10],
    } for a in amends]

    note_rows = [{"id": n["id"], "date": n["created_utc"][:10], "target": n["target"], "author": n["author"],
                  "kind": n["kind"], "text": n["text"]} for n in notes]

    wl = _read_json("watchlist_review.json")
    watch_summary = [x for x in wl.get("summary", []) if x.get("current")]
    watch_rows = [{**{k: r.get(k) for k in ("cohort", "sleeve", "symbol", "name", "industry", "sector", "rank", "status",
                                            "reason", "score", "return", "vs_picks")},
                   "details": _compact({k: v for k, v in r.items() if k not in (
                       "cohort", "sleeve", "symbol", "name", "industry", "sector", "rank", "status", "reason", "score",
                       "return", "vs_picks")})} for r in wl.get("rows", [])]

    sc = _read_json("scorecard.json")
    d = sc.get("desk", {})
    headline = [{
        "asof": (sc.get("asof_utc") or "")[:10], "launch": sc.get("launch"), "days": d.get("days", 0),
        "desk_return": d.get("total_return"), "spy_return": sc.get("spy", {}).get("total_return"),
        "rsp_return": sc.get("rsp", {}).get("total_return"), "sharpe": d.get("sharpe"),
        "sharpe_low": d.get("sharpe_low"), "sharpe_high": d.get("sharpe_high"),
        "max_drawdown": d.get("max_drawdown"), "current_drawdown": d.get("current_drawdown"),
        "flags": sum(1 for r in sc.get("scorecard", []) if r["status"] == "flag"),
        "watch": sum(1 for r in sc.get("scorecard", []) if r["status"] == "watch"),
        "criteria_as_of": sc.get("criteria_as_of"),
    }] if sc else []

    return {"summary": summary, "sleeves": sleeves, "positions": positions, "trades": trade_rows,
            "closed": closed, "methods": methods, "amendments": amendments, "notes": note_rows,
            "sleeve_guide": register.sleeve_guide(), "watch_summary": watch_summary, "watchlist": watch_rows, "score_headline": headline, "scorecard": sc.get("scorecard", []), "curve": sc.get("curve", []),
            "sleeve_perf": sc.get("sleeves", []), "fills": sc.get("fills", []), "exits": sc.get("exits", [])}


def export() -> dict[str, int]:
    out = tradebook.DIR / "dashboard"
    out.mkdir(parents=True, exist_ok=True)
    counts = {}
    for name, rows in tables().items():
        (out / f"{name}.json").write_text(json.dumps(rows, indent=1, default=str))
        counts[name] = len(rows)
    return counts
