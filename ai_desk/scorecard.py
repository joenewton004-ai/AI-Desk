"""Scorecard: is the paper desk succeeding, judged against rules written down
in advance (research/SUCCESS_CRITERIA.md, mirrored in CRITERIA below).

Three tiers, because they need very different amounts of time:
  1. process   - fills, slippage, rejected orders. Judge from week one; these are
                 the things we can actually improve.
  2. behaviour - is the desk inside the range its backtest predicted, and are any
                 red flags tripped? Judge over months.
  3. edge      - Sharpe, return vs SPY, drawdown vs SPY, capture ratios. Judge over
                 years: after 1 year a measured Sharpe of 0.9 could really be
                 anywhere from about -0.3 to 2.1.

Files: journal/snapshots.jsonl (one line per trading day: equity, holdings by
sleeve) and journal/scorecard.json (the latest evaluation, for the dashboard).
Daily flow: `python -m ai_desk journal snapshot` after the close (a scheduled task
runs it), then `journal scorecard` and `journal export`.
"""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from ai_desk import tradebook

TRADING_DAYS = 252

# Dated, written in advance. Change them only through an amendment ("criteria").
CRITERIA = {
    "as_of": "2026-10-20",
    "launch": "2026-10-20",
    # the desk's backtest, 50% quality screen + 20% bottleneck + 30% SPY momentum, monthly 2014-2026
    # (research/BOTTLENECK.md). Survivors-only prices: expect less in practice.
    "backtest": {"cagr": 0.163, "volatility": 0.165, "sharpe": 0.89, "max_drawdown": -0.23},
    "benchmarks": {"desk": "SPY", "quality_screen": "RSP", "bottleneck": "SPY", "momentum": "SPY",
                   "index_momentum": "SPY"},     # momentum: the bottleneck sleeve's replacement (amendment 00e1f2b8)
    "min_days": {"behaviour": 63, "edge": 252},       # a quarter; a year
    "red_flags": {
        "drawdown_warn": -0.15,          # the executor halts all trading at -20% from the peak
        "drawdown_halt": -0.20,
        "trail_benchmark_12m": -0.10,    # desk or a sleeve 10+ points behind its benchmark over 12 months
        "slippage_vs_open_bps": 10.0,    # the backtest assumes 3bps; 10bps average over 20+ fills is a flag
        "min_fills_for_slippage": 20,
        "exit_rebound": 0.03,            # bottleneck exits: stocks up 3%+ on average 20 days after we sold
        "min_exits": 10,
        "exit_horizon_days": 20,
    },
    "edge_targets": {
        "sharpe_vs_spy": 0.0,            # desk Sharpe at least SPY's over the same period
        "excess_return_vs_spy": 0.0,     # after costs
        "drawdown_vs_spy": 0.0,          # worst drop no deeper than SPY's
        "upside_capture_min": 0.80,
        "downside_capture_max": 0.70,
    },
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# --- daily snapshot ---------------------------------------------------------------

def sleeve_map() -> dict[str, str]:
    """symbol -> the sleeve that bought it (most recent buy); the overnight sleeve's shares from its book."""
    out = {}
    for t in tradebook.trades():
        if t["side"] == "buy" and t.get("sleeve"):
            out[t["symbol"]] = t["sleeve"]
    # a stock the bottleneck sleeve bought and momentum kept on the switch belongs to momentum now
    try:
        lock = json.loads(Path("data/portfolio/momentum.json").read_text())
        for s in lock.get("picks") or []:
            if out.get(s) == "bottleneck":
                out[s] = "momentum"
    except (OSError, ValueError):
        pass
    try:
        from ai_desk import overnight
        b = overnight.load_book()
        if not b.get("sell_sent"):
            for s in b.get("holdings") or {}:
                out[s] = "overnight_drift" if s not in out else out[s] + " + overnight_drift"
    except Exception:  # noqa: BLE001 - attribution is cosmetic
        pass
    return out


def holdings_now(broker) -> dict:
    """Every position with the broker's current price, P/L and today's move, by sleeve."""
    sleeves = sleeve_map()
    if hasattr(broker, "position_details"):
        f = lambda p, k: float(p[k]) if p.get(k) not in (None, "") else None  # noqa: E731
        holdings = {p["symbol"]: {
            "qty": f(p, "qty"), "price": f(p, "current_price"), "sleeve": sleeves.get(p["symbol"]),
            "avg_cost": f(p, "avg_entry_price"), "last_close": f(p, "lastday_price"),
            "market_value": f(p, "market_value"), "cost_basis": f(p, "cost_basis"),
            "unrealized_pl": f(p, "unrealized_pl"), "unrealized_pct": f(p, "unrealized_plpc"),
            "day_pl": f(p, "unrealized_intraday_pl"), "day_pct": f(p, "unrealized_intraday_plpc"),
        } for p in broker.position_details() if float(p.get("qty") or 0)}
    else:
        prices = broker.latest_prices()
        holdings = {s: {"qty": q, "price": prices.get(s), "sleeve": sleeves.get(s)}
                    for s, q in broker.positions().items() if q}
    return holdings


def snapshot(broker, date: str | None = None) -> dict:
    """Record today's account value and holdings by sleeve. Re-running on the
    same date replaces that day's line."""
    acct = broker.account()
    holdings = holdings_now(broker)
    row = {"date": date or pd.Timestamp.now(tz="America/New_York").date().isoformat(), "utc": _now(),
           "equity": float(acct["equity"]), "cash": float(acct["cash"]), "holdings": holdings}
    rows = [r for r in tradebook._read("snapshots.jsonl") if r["date"] != row["date"]]
    tradebook._write("snapshots.jsonl", sorted(rows + [row], key=lambda r: r["date"]))
    return row


def snapshots() -> list[dict]:
    return tradebook._read("snapshots.jsonl")


def live_snapshot(broker) -> dict:
    """Intraday prices for the dashboard (journal/live.json, overwritten each time). Never written to
    snapshots.jsonl: the scorecard measures daily closes only."""
    acct = broker.account()
    clock = broker.clock() if hasattr(broker, "clock") else {}
    row = {"utc": _now(), "market_open": bool((clock or {}).get("is_open")), "equity": float(acct["equity"]),
           "cash": float(acct["cash"]), "last_equity": float(acct.get("last_equity") or 0) or None,
           "holdings": holdings_now(broker)}
    tradebook.DIR.mkdir(parents=True, exist_ok=True)
    (tradebook.DIR / "live.json").write_text(json.dumps(row, indent=1, default=str))
    return row


def latest_prices_row() -> tuple[dict, str]:
    """The newer of the live snapshot and the last close snapshot, and which it was ("intraday" or "close")."""
    snaps = snapshots()
    close = snaps[-1] if snaps else {}
    p = tradebook.DIR / "live.json"
    live = json.loads(p.read_text()) if p.exists() else {}
    if live and live.get("utc", "") > close.get("utc", "") and live.get("market_open"):
        return live, "intraday"
    return close, "close"


# --- pure calculations (unit-tested) --------------------------------------------

def sharpe_band(sharpe: float, years: float, z: float = 1.645) -> tuple[float, float]:
    """90% range for the true Sharpe given a measured one (Lo 2002, iid returns)."""
    if not years or sharpe != sharpe:
        return (math.nan, math.nan)
    se = math.sqrt((1 + 0.5 * sharpe ** 2) / years)
    return (sharpe - z * se, sharpe + z * se)


def perf(equity: pd.Series, rf_daily: pd.Series | None = None) -> dict:
    """Return, risk and Sharpe (above T-bills) of an equity curve."""
    e = equity.dropna()
    r = e.pct_change().dropna()
    out = {"days": int(len(r)), "total_return": float(e.iloc[-1] / e.iloc[0] - 1) if len(e) > 1 else 0.0,
           "max_drawdown": float((e / e.cummax() - 1).min()) if len(e) else 0.0,
           "current_drawdown": float(e.iloc[-1] / e.cummax().iloc[-1] - 1) if len(e) else 0.0}
    years = len(r) / TRADING_DAYS
    out["cagr"] = float((1 + out["total_return"]) ** (1 / years) - 1) if len(r) >= 63 else math.nan
    out["volatility"] = float(r.std() * math.sqrt(TRADING_DAYS)) if len(r) > 1 else math.nan
    ex = r - (rf_daily.reindex(r.index).fillna(0.0) if rf_daily is not None else 0.0)
    out["sharpe"] = float(ex.mean() / ex.std() * math.sqrt(TRADING_DAYS)) if len(r) > 1 and ex.std() > 1e-12 else math.nan
    out["sharpe_low"], out["sharpe_high"] = sharpe_band(out["sharpe"], years)
    return out


def capture(desk: pd.Series, bench: pd.Series) -> dict:
    """Up/down capture and beta, from monthly returns once there are 6+ months
    (daily before that - noisier)."""
    d, b = desk.dropna().pct_change(), bench.dropna().pct_change()
    if len(desk.dropna()) > 126:
        d = desk.resample("ME").last().pct_change()
        b = bench.resample("ME").last().pct_change()
    both = pd.concat([d, b], axis=1).dropna()
    if len(both) < 5:
        return {"upside_capture": math.nan, "downside_capture": math.nan, "beta": math.nan}
    x, y = both.iloc[:, 1], both.iloc[:, 0]
    up, dn = x > 0, x < 0
    return {"upside_capture": float(y[up].mean() / x[up].mean()) if up.any() else math.nan,
            "downside_capture": float(y[dn].mean() / x[dn].mean()) if dn.any() else math.nan,
            "beta": float(np.cov(y, x)[0, 1] / x.var()) if x.var() > 0 else math.nan}


def sleeve_returns(snaps: list[dict], closes: pd.DataFrame) -> pd.DataFrame:
    """Daily return of each sleeve: yesterday's holdings marked to today's close.
    (A position's first day - bought at the open - is not counted.)"""
    rows = {}
    for prev, cur in zip(snaps, snaps[1:]):
        d0, d1 = pd.Timestamp(prev["date"]), pd.Timestamp(cur["date"])
        if d0 not in closes.index or d1 not in closes.index:
            continue
        by = {}
        for sym, h in prev["holdings"].items():
            if sym not in closes.columns or not h.get("sleeve"):
                continue
            p0, p1 = closes.at[d0, sym], closes.at[d1, sym]
            if p0 != p0 or p1 != p1:
                continue
            v0, pnl = by.get(h["sleeve"], (0.0, 0.0))
            by[h["sleeve"]] = (v0 + h["qty"] * p0, pnl + h["qty"] * (p1 - p0))
        rows[d1] = {s: pnl / v0 for s, (v0, pnl) in by.items() if v0}
    return pd.DataFrame.from_dict(rows, orient="index").sort_index()


def fill_quality(trades: list[dict], opens: pd.DataFrame) -> list[dict]:
    """How each fill compared with the signal close (est_price) and with the
    day's open (what the backtest assumes). Positive bps = cost to us."""
    out = []
    for t in trades:
        if not t.get("fill_price") or not t.get("est_price"):
            continue
        sign = 1 if t["side"] == "buy" else -1
        day = pd.Timestamp(str(t.get("filled_utc") or t["created_utc"])[:10])
        op = opens.at[day, t["symbol"]] if day in opens.index and t["symbol"] in opens.columns else None
        out.append({
            "id": t["id"], "date": day.date().isoformat(), "symbol": t["symbol"], "side": t["side"],
            "sleeve": t.get("sleeve") or "", "order_type": t.get("order_type") or "market", "signal_close": t["est_price"], "day_open": op,
            "fill": t["fill_price"], "notional": round(float(t["fill_price"]) * float(t.get("filled_qty") or 0), 2),
            "vs_close_bps": round(sign * (t["fill_price"] / t["est_price"] - 1) * 1e4, 1),
            "vs_open_bps": round(sign * (t["fill_price"] / op - 1) * 1e4, 1) if op and op == op else None,
        })
    return out


def exit_followup(trades: list[dict], closes: pd.DataFrame, horizon: int = 20) -> list[dict]:
    """After each sell, what did the stock do over the next `horizon` trading
    days? Rising afterwards means the exit cost us money."""
    out = []
    for t in trades:
        if t["side"] != "sell" or not t.get("fill_price") or t["symbol"] not in closes.columns:
            continue
        day = pd.Timestamp(str(t.get("filled_utc") or t["created_utc"])[:10])
        after = closes[t["symbol"]].loc[day:].dropna().iloc[1:horizon + 1]
        out.append({"id": t["id"], "date": day.date().isoformat(), "symbol": t["symbol"],
                    "sleeve": t.get("sleeve") or "", "exit_price": t["fill_price"],
                    "reason": (t.get("exit_reason") or t.get("reason") or "")[:120],
                    "days_after": int(len(after)),
                    "return_after": round(float(after.iloc[-1] / t["fill_price"] - 1), 4) if len(after) else None,
                    "complete": len(after) >= horizon})
    return out


def cone(dates: pd.DatetimeIndex, cagr: float, vol: float, z: float = 1.645) -> pd.DataFrame:
    """Where the desk's cumulative return would sit 90% of the time if paper
    trading behaved like the backtest (normal approximation on log returns)."""
    t = np.arange(len(dates)) / TRADING_DAYS
    mu = math.log(1 + cagr) - 0.5 * vol ** 2
    mid = np.exp(math.log(1 + cagr) * t) - 1
    lo = np.exp(mu * t - z * vol * np.sqrt(t)) - 1
    hi = np.exp(mu * t + z * vol * np.sqrt(t)) - 1
    return pd.DataFrame({"expected": mid, "low": lo, "high": hi}, index=dates)


def _status(ok: bool | None, early: bool, watch: bool = False) -> str:
    if early or ok is None:
        return "too early"
    return "ok" if ok else ("watch" if watch else "flag")


def evaluate(desk: dict, spy: dict, cap: dict, trail_12m: dict, sleeve_rows: list[dict],
             fills: list[dict], exits: list[dict], trades: list[dict], in_cone: bool | None,
             criteria: dict = CRITERIA) -> list[dict]:
    """The scorecard: one row per criterion, with the value, the target and a status."""
    rf, et, md = criteria["red_flags"], criteria["edge_targets"], criteria["min_days"]
    days = desk.get("days", 0)
    early_b, early_e = days < md["behaviour"], days < md["edge"]
    rows = []

    def add(tier, metric, value, fmt, target, status, note=""):
        rows.append({"tier": tier, "metric": metric, "value": None if value is None or value != value else value,
                     "format": fmt, "target": target, "status": status, "note": note})

    # tier 1: process
    filled = [f for f in fills if f.get("vs_open_bps") is not None]
    slip = float(np.average([f["vs_open_bps"] for f in filled], weights=[max(f["notional"], 1) for f in filled])) \
        if filled else None
    enough = len(filled) >= rf["min_fills_for_slippage"]
    add("1 process", "Slippage vs the open (bps, $-weighted)", slip, "bps", f"≤ {rf['slippage_vs_open_bps']:.0f}",
        _status(slip is not None and slip <= rf["slippage_vs_open_bps"], not enough and slip is None,
                watch=not enough), f"{len(filled)} fills; the backtest assumes 3bps")
    gap = [f["vs_close_bps"] for f in fills]
    add("1 process", "Fill vs signal close (bps)", float(np.mean(gap)) if gap else None, "bps", "info only",
        "info" if gap else "too early", "overnight gap + slippage; the backtest includes the gap")
    bad = [t for t in trades if t.get("status") in ("rejected", "canceled", "expired")]
    add("1 process", "Orders rejected, canceled or expired", float(len(bad)), "count", "0",
        "ok" if not bad else "flag", ", ".join(t["symbol"] for t in bad[:8]))
    pending = [t for t in trades if t.get("order_id") and not t.get("fill_price")
               and t.get("status") not in ("rejected", "canceled", "expired")]
    add("1 process", "Orders waiting for a fill", float(len(pending)), "count", "0 after the open",
        "ok" if not pending else "watch")

    # tier 2: behaviour
    dd = desk.get("current_drawdown", 0.0)
    add("2 behaviour", "Drawdown from peak (now)", dd, "pct", f"above {rf['drawdown_warn']:.0%}",
        "ok" if dd > rf["drawdown_warn"] else ("flag" if dd <= rf["drawdown_halt"] else "watch"),
        f"trading halts automatically at {rf['drawdown_halt']:.0%}")
    add("2 behaviour", "Inside the backtest's 90% range", None if in_cone is None else float(in_cone), "bool",
        "yes", _status(in_cone, days < 5, watch=True), "if no: find out why before changing anything")
    t12 = trail_12m.get("desk")
    add("2 behaviour", "Desk vs SPY, last 12 months", t12, "pct", f"above {rf['trail_benchmark_12m']:.0%}",
        _status(t12 is not None and t12 > rf["trail_benchmark_12m"], early_e or t12 is None),
        "evaluated once there are 12 months of history")
    for s in sleeve_rows:
        early_s = s["days"] < md["edge"]
        add("2 behaviour", f"{s['sleeve']} vs {s['benchmark']}" + (" (12m)" if not early_s else ""),
            s["excess"], "pct", f"above {rf['trail_benchmark_12m']:.0%} over 12m",
            _status(s["excess"] is not None and s["excess"] > rf["trail_benchmark_12m"], early_s),
            f"since launch over {s['days']} days")
    done = [e for e in exits if e["complete"] and e["sleeve"] == "bottleneck" and e["return_after"] is not None]
    avg = float(np.mean([e["return_after"] for e in done])) if done else None
    add("2 behaviour", f"Bottleneck: return {rf['exit_horizon_days']} days after an exit", avg, "pct",
        f"below +{rf['exit_rebound']:.0%}", _status(avg is not None and avg < rf["exit_rebound"],
                                                  len(done) < rf["min_exits"]),
        f"{len(done)} completed exits (need {rf['min_exits']})")

    # tier 3: edge
    def edge(metric, value, target, ok, fmt="num", note=""):
        add("3 edge", metric, value, fmt, target, _status(ok, early_e or value is None or value != value), note)

    d_s, s_s = desk.get("sharpe"), spy.get("sharpe")
    edge("Sharpe (above T-bills)", d_s, "≥ SPY's", d_s is not None and s_s is not None and d_s - s_s >= et["sharpe_vs_spy"],
         note=f"SPY {s_s:.2f}; 90% range for the desk {desk['sharpe_low']:.1f} to {desk['sharpe_high']:.1f}"
         if d_s == d_s and s_s == s_s and desk.get("sharpe_low") == desk.get("sharpe_low") else "")
    ex = desk["total_return"] - spy["total_return"] if spy else None
    edge("Return vs SPY since launch", ex, "≥ 0", ex is not None and ex >= et["excess_return_vs_spy"], "pct")
    ddiff = desk["max_drawdown"] - spy["max_drawdown"] if spy else None
    edge("Worst drop vs SPY's", ddiff, "≥ 0 (shallower)", ddiff is not None and ddiff >= et["drawdown_vs_spy"], "pct",
         f"desk {desk['max_drawdown']:.1%}, SPY {spy.get('max_drawdown', float('nan')):.1%}")
    edge("Upside capture", cap.get("upside_capture"), f"≥ {et['upside_capture_min']:.0%}",
         cap.get("upside_capture", math.nan) >= et["upside_capture_min"], "pct")
    edge("Downside capture", cap.get("downside_capture"), f"≤ {et['downside_capture_max']:.0%}",
         cap.get("downside_capture", math.nan) <= et["downside_capture_max"], "pct")
    return rows


# --- putting it together ---------------------------------------------------------

def desk_equity(broker, launch: str) -> pd.Series:
    """Daily closing equity from Alpaca's portfolio history (falls back to snapshots)."""
    try:
        h = broker.portfolio_history()
        s = pd.Series(h.get("equity") or [], index=pd.to_datetime(h.get("timestamp") or [], unit="s", utc=True)
                      .tz_convert("America/New_York").normalize().tz_localize(None), dtype=float)
        s = s[s > 0].loc[launch:]
    except Exception:  # noqa: BLE001 - the snapshots are the fallback
        s = pd.Series(dtype=float)
    snaps = pd.Series({pd.Timestamp(r["date"]): r["equity"] for r in snapshots()}, dtype=float)
    s = s.combine_first(snaps.loc[launch:]) if len(snaps) else s
    return s.groupby(level=0).last().sort_index()


def build(broker, criteria: dict = CRITERIA, write: bool = True, prices: dict | None = None,
          cash_rate: pd.Series | None = None) -> dict:
    from ai_desk.data import load_cash_rate, load_many

    launch = criteria["launch"]
    trades, snaps = tradebook.trades(), snapshots()
    equity = desk_equity(broker, launch)
    symbols = sorted({"SPY", "RSP"} | {t["symbol"] for t in trades})
    start = (pd.Timestamp(launch) - pd.Timedelta(days=10)).date().isoformat()
    if prices is None:
        prices = load_many(symbols, start=start, source="yahoo")
    closes, opens = prices["close"], prices["open"]
    cash_rate = cash_rate if cash_rate is not None else load_cash_rate(start=start)
    from ai_desk.metrics import daily_rf

    idx = equity.index
    if len(idx) and closes.index[-1] < idx[-1]:     # today's benchmark close not out yet
        idx = idx[idx <= closes.index[-1]]
    equity = equity.loc[idx]
    rf_d = daily_rf(cash_rate, idx) if cash_rate is not None and len(idx) else None
    spy = closes["SPY"].reindex(idx).ffill()
    rsp = closes["RSP"].reindex(idx).ffill()
    desk_m = perf(equity, rf_d) if len(equity) > 1 else {"days": 0, "total_return": 0.0, "max_drawdown": 0.0,
                                                           "current_drawdown": 0.0, "sharpe": math.nan,
                                                           "sharpe_low": math.nan, "sharpe_high": math.nan}
    spy_m = perf(spy, rf_d) if len(spy.dropna()) > 1 else {"total_return": 0.0, "max_drawdown": 0.0, "sharpe": math.nan}
    rsp_m = perf(rsp, rf_d) if len(rsp.dropna()) > 1 else {"total_return": 0.0}
    cap = capture(equity, spy) if len(equity) > 5 else {}
    last12 = lambda s: float(s.iloc[-1] / s.loc[s.index[-1] - pd.DateOffset(years=1):].iloc[0] - 1)  # noqa: E731
    trail = {"desk": last12(equity) - last12(spy)} if desk_m["days"] >= TRADING_DAYS else {}

    sr = sleeve_returns(snaps, closes)
    sleeve_rows = []
    for s, bench in criteria["benchmarks"].items():
        if s == "desk" or s not in sr.columns:
            continue
        r = sr[s].dropna()
        b = closes[bench].pct_change().reindex(r.index)
        sret, bret = float((1 + r).prod() - 1), float((1 + b.fillna(0)).prod() - 1)
        if len(r) >= TRADING_DAYS:
            r12, b12 = r.iloc[-TRADING_DAYS:], b.iloc[-TRADING_DAYS:]
            excess = float((1 + r12).prod() - (1 + b12.fillna(0)).prod())
        else:
            excess = sret - bret
        sleeve_rows.append({"sleeve": s, "benchmark": bench, "days": int(len(r)), "return": round(sret, 5),
                            "benchmark_return": round(bret, 5), "excess": round(excess, 5)})

    fills = fill_quality(trades, opens)
    exits = exit_followup(trades, closes, criteria["red_flags"]["exit_horizon_days"])
    bt = criteria["backtest"]
    curve = pd.DataFrame(index=idx)
    in_cone = None
    if len(idx):
        c = cone(idx, bt["cagr"], bt["volatility"])
        curve = pd.DataFrame({"desk": equity / equity.iloc[0] - 1, "spy": spy / spy.iloc[0] - 1,
                              "rsp": rsp / rsp.iloc[0] - 1, **c,
                              "drawdown": equity / equity.cummax() - 1})
        in_cone = bool(c["low"].iloc[-1] <= curve["desk"].iloc[-1] <= c["high"].iloc[-1]) if len(idx) > 1 else None
    rows = evaluate(desk_m, spy_m, cap, trail, sleeve_rows, fills, exits, trades, in_cone, criteria)
    out = {"asof_utc": _now(), "launch": launch, "criteria_as_of": criteria["as_of"], "desk": desk_m,
           "spy": spy_m, "rsp": rsp_m, "capture": cap, "sleeves": sleeve_rows, "scorecard": rows,
           "fills": fills, "exits": exits,
           "curve": [{"date": d.date().isoformat(), **{k: (None if v != v else round(float(v), 5)) for k, v in r.items()}}
                     for d, r in curve.iterrows()]}
    if write:
        tradebook.DIR.mkdir(parents=True, exist_ok=True)
        (tradebook.DIR / "scorecard.json").write_text(json.dumps(out, indent=1, default=str))
    return out
