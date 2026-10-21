"""Flat tables for the trading-journal dashboard.

The dashboard reads plain row files, so this turns the journal (plan, trades,
notes, review, methodology register, amendments) into one JSON array per
table under journal/dashboard/. Run `python -m ai_desk journal export` after
a plan, an execute or a review, then ask Claude to refresh the dashboard.
"""

from __future__ import annotations

import json
import re

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


def _why(rationale: dict | None) -> str:
    """One short line on why a holding is wanted, e.g. '#4 · value 98, quality 90 · P/E 9'."""
    out = []
    for sleeve, r in (rationale or {}).items():
        if not isinstance(r, dict):
            continue
        if sleeve == "index_momentum":
            t = r.get("trailing_12m_return")
            if t is not None:
                out.append(f"12-month return {t:+.0%}: trend {'on' if r.get('signal') else 'off'}")
            continue
        names = ({"flow_score": "flow", "bottleneck_score": "bottleneck", "asymmetry_score": "asymmetry"}
                 if sleeve == "bottleneck" else
                 {"quality_score": "quality", "growth_score": "growth", "value_score": "value",
                  "strength_score": "strength", "momentum_score": "momentum"})
        scores = sorted(((r.get(k), v) for k, v in names.items() if r.get(k) == r.get(k) and r.get(k) is not None),
                        reverse=True)[:2]
        bits = [f"#{int(r['rank'])}"] if r.get("rank") is not None else []
        if scores:
            bits.append(", ".join(f"{v} {k:.0f}" for k, v in scores))
        extra = r.get("rev_growth") if sleeve == "bottleneck" else r.get("forward_pe")
        if extra is not None and extra == extra:
            bits.append(f"revenue {extra:+.0%}" if sleeve == "bottleneck" else f"P/E {extra:.0f}")
        out.append(" · ".join(bits))
    return " / ".join(x for x in out if x)


def _brief(r: dict) -> str:
    """One short line of the scores that decide the rank, e.g. 'Q 72 · G 59 · V 88 · M 90 · P/E 13'."""
    def n(k, fmt="{:.0f}"):
        v = r.get(k)
        return None if v is None or v != v else fmt.format(v)

    if r.get("sleeve") == "bottleneck":
        parts = [("Flow", n("flow_score")), ("Bneck", n("bottleneck_score")), ("Asym", n("asymmetry_score")),
                 ("Rev", n("rev_growth", "{:+.0%}"))]
    else:
        parts = [("Q", n("quality_score")), ("G", n("growth_score")), ("V", n("value_score")),
                 ("M", n("momentum_score")), ("P/E", n("forward_pe"))]
    return " · ".join(f"{k} {v}" for k, v in parts if v is not None)


FUND_NAMES = {"SPY": "SPDR S&P 500 ETF Trust", "RSP": "Invesco S&P 500 Equal Weight ETF",
              "QQQ": "Invesco QQQ Trust (Nasdaq-100)", "IWM": "iShares Russell 2000 ETF",
              "DIA": "SPDR Dow Jones Industrial Average ETF", "EFA": "iShares MSCI EAFE ETF",
              "EEM": "iShares MSCI Emerging Markets ETF"}


def _read_json_list(name: str) -> list:
    p = tradebook.DIR / name
    return json.loads(p.read_text()) if p.exists() else []


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
        "exit_reason": r["exit_reason"] or "", "why": _why(r.get("rationale")),
        "rationale": _compact(r.get("rationale") or {}),
        "notes": notes_for(r["symbol"]),
    } for r in plan.get("rows", [])]

    trade_rows = [{
        "id": t["id"], "date": (t.get("filled_utc") or t["created_utc"])[:10], "signal_date": t["signal_date"],
        "symbol": t["symbol"], "side": t["side"], "qty": t.get("filled_qty") or t["qty"],
        "price": t.get("fill_price") or t["est_price"], "filled": bool(t.get("fill_price")),
        "notional": round((t.get("filled_qty") or t["qty"]) * (t.get("fill_price") or t["est_price"]), 2),
        "sleeve": t.get("sleeve") or "", "action": t.get("action") or "", "status": t.get("status") or "",
        "order_type": t.get("order_type") or "market", "limit_price": t.get("limit_price"),
        "reason": t.get("reason") or "", "exit_reason": t.get("exit_reason") or "",
        "why": _why(t.get("rationale")), "rationale": _compact(t.get("rationale") or {}),
        "notes": notes_for(t["id"], t["symbol"]),
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
        "exported_utc": tradebook._now(),
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

    # fact sheets: the latest snapshot of each Alpaca position, plus its sleeve and P/E at decision time
    from ai_desk import scorecard
    last, price_kind = scorecard.latest_prices_row()      # intraday prices if a live snapshot is newer than the close
    pe = {}
    for r in plan.get("rows", []):
        for sl, x in (r.get("rationale") or {}).items():
            if isinstance(x, dict) and x.get("forward_pe") == x.get("forward_pe") and x.get("forward_pe") is not None:
                pe[r["symbol"]] = (x["forward_pe"], f"forward P/E from the {str(x.get('source_file', ''))[-14:-4] or 'screen'} scan")
    names = dict(FUND_NAMES)
    for c in _read_json_list("watchlist.json"):
        names.update({r["symbol"]: r["name"] for r in c.get("rows", []) if r.get("name")})
    names.update({sym: h["name"] for sym, h in (last.get("holdings") or {}).items() if h.get("name")})
    why = {r["symbol"]: r["why"] for r in positions}
    holdings = [{
        "symbol": sym, "name": names.get(sym, ""), "sleeve": h.get("sleeve") or "", "shares": h.get("qty"), "price": h.get("price"),
        "avg_cost": h.get("avg_cost"), "market_value": h.get("market_value"), "cost_basis": h.get("cost_basis"),
        "unrealized_pl": h.get("unrealized_pl"), "unrealized_pct": h.get("unrealized_pct"),
        "day_pl": h.get("day_pl"), "day_pct": h.get("day_pct"), "last_close": h.get("last_close"),
        "pe": pe.get(sym, (None, ""))[0], "pe_note": pe.get(sym, (None, "an index fund - no single P/E"))[1],
        "as_of": last.get("utc"), "why": why.get(sym, ""),
    } for sym, h in sorted((last.get("holdings") or {}).items())]
    # the plan table shows each holding's return since purchase and today's move (watchlist layout)
    held = {h["symbol"]: h for h in holdings}
    for r in positions:
        h = held.get(r["symbol"], {})
        r["return"], r["day"] = h.get("unrealized_pct"), h.get("day_pct")

    wl = _read_json("watchlist_review.json")
    watch_summary = [x for x in wl.get("summary", []) if x.get("current")]
    watch_rows = [{**{k: r.get(k) for k in ("cohort", "sleeve", "symbol", "name", "industry", "sector", "rank", "status",
                                            "reason", "score", "return", "vs_picks")},
                   "details": _brief(r)} for r in wl.get("rows", [])]
    for r in watch_rows:                                    # short, one-line reasons
        if r["status"] == "near miss":
            m = re.search(r"top (\d+)", r["reason"] or "")
            r["reason"] = f"outside the top {m.group(1)}" if m else "ranked lower"
        elif r["status"] == "picked":
            r["reason"] = "held"

    # the daily picks-vs-near-misses check: latest per cohort, plus its history for the trend chart
    from ai_desk import watchlist as _wl
    watch_check = [{
        "cohort": c.get("cohort"), "sleeve": c.get("sleeve"), "asof": c.get("asof"), "days": c.get("days"),
        "horizon": c.get("horizon"), "picks": c.get("picks_avg"), "near_misses": c.get("near_miss_avg"),
        "gap": c.get("gap"), "chance": c.get("chance"), "verdict": c.get("verdict"), "reason": c.get("reason"),
        "explanation": c.get("explanation"), "baseline": c.get("baseline"),
        "top_factor": (max((c.get("factors") or {}).items(), key=lambda kv: abs(kv[1]))[0]
                       if c.get("factors") else None),
    } for c in wl.get("checks", [])]
    watch_daily = [{"cohort": c.get("cohort"), "sleeve": c.get("sleeve"), "asof": c.get("asof"), "days": c.get("days"),
                    "gap": c.get("gap"), "chance": c.get("chance"), "verdict": c.get("verdict")}
                   for c in _wl.daily_history()]

    # what the prices on the page are: an intraday refresh or the last close
    summary[0].update({"prices_utc": last.get("utc"), "prices_kind": price_kind,
                       "live_equity": last.get("equity"),
                       "day_pl": round(sum((h.get("day_pl") or 0.0) for h in (last.get("holdings") or {}).values()), 2),
                       "open_pl": round(sum((h.get("unrealized_pl") or 0.0) for h in (last.get("holdings") or {}).values()), 2)})

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
            "holdings": holdings, "sleeve_guide": register.sleeve_guide(),
            "explainer_text": register.explainer_tables()[0], "explainer_backtest": register.explainer_tables()[1], "watch_summary": watch_summary, "watchlist": watch_rows, "watch_check": watch_check, "watch_daily": watch_daily, "score_headline": headline, "scorecard": sc.get("scorecard", []), "curve": sc.get("curve", []),
            "sleeve_perf": sc.get("sleeves", []), "fills": sc.get("fills", []), "exits": sc.get("exits", [])}


def _json_safe(v):
    """NaN and infinity aren't valid JSON (the dashboard rejects the whole file): write them as null."""
    if isinstance(v, float):
        return None if v != v or v in (float("inf"), float("-inf")) else v
    if isinstance(v, dict):
        return {k: _json_safe(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_json_safe(x) for x in v]
    return v


def export() -> dict[str, int]:
    """Write one JSON file per table. A table with no rows yet is written as [] but should have NO dataset on
    the dashboard (it counts an empty file as a failed source): create its dataset when it first has rows.
    journal/dashboard/_manifest.json lists which tables have rows."""
    out = tradebook.DIR / "dashboard"
    out.mkdir(parents=True, exist_ok=True)
    counts = {}
    for name, rows in tables().items():
        (out / f"{name}.json").write_text(json.dumps(_json_safe(rows), indent=1, default=str, allow_nan=False))
        counts[name] = len(rows)
    (out / "_manifest.json").write_text(json.dumps({"with_rows": sorted(k for k, n in counts.items() if n),
                                                    "empty": sorted(k for k, n in counts.items() if not n)}, indent=1))
    return counts
