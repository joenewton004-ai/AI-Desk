"""The trader-skill desk - Jakeschincariol/day-trader-skill's day-trading rules run alongside the main desk.

A SEPARATE LEDGER (owner's choice, 2026-10-28): a virtual $5,000 account, its trades replayed after each close on
real Alpaca 5-minute bars (SIP). It sends NO orders and never touches the Alpaca paper account the desk trades in.
The rules are the skill's own, made automatic (owner's choice: its rules, no person or AI picking trades):

  scan     trader-scanner `orb`: the 15-minute opening range (9:30-9:45 New York); a hit = the first completed
           5-minute bar to CLOSE above the range high
  entry    trader-entry: the hit, if its bar closes between 9:45 (no_entries_before) and 15:30 (no_entries_after);
           filled at the NEXT bar's open (an automatic market order can't fill at the close it just saw)
  exit     trader-exit defaults for an orb entry: stop at the range's midpoint, target 2R (entry + 2 x risk, risk =
           the plan's entry - stop), flat by 15:55 win or lose
  size     trader-budget: shares = $50 max loss / risk per share, at most $4,000 an order and 75% of the $5,000
           budget, 10% cash kept back; whole shares
  risk     trader-risk: at most 3 trades a day, none after -$150 that day, one trade per stock a day
Where several stocks break out at once the skill leaves the choice to a person; here it's fixed in advance: earliest
first, then the most traded so far (price x volume), which is how the scanner ranks its candidates.
Universe: the desk's top 100 US companies (the skill scans ~5,900 stocks; the 10-year backtest only has bars for the
top 100). A bar touching both the stop and the target counts as stopped. Costs 0.02% each way (large caps).
Backtest: research/skill_desk.py -> research/SKILL_DESK.md.

    python -m ai_desk skilldesk record [--date YYYY-MM-DD]   (the evening run's `portfolio prepare` records each day)
    python -m ai_desk skilldesk status

Log: journal/skill_desk/trades.jsonl (one line per trade) and journal/skill_desk/days.jsonl (one line per day).
"""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

SOURCE = "Jakeschincariol/day-trader-skill (MIT), commit 3d0f4ef, 2026-10-20"
START_DAY = "2026-10-28"
CONFIG = {
    "budget": 5000.0, "cash_buffer_pct": 10, "max_position_pct": 75, "max_order_usd": 4000.0,
    "max_loss_per_trade_usd": 50.0, "max_daily_loss_usd": 150.0, "max_trades_per_day": 3,
    "no_entries_before": 9 * 60 + 45, "no_entries_after": 15 * 60 + 30, "flat_by": 15 * 60 + 55,
    "or_minutes": 15, "target_r": 2.0, "cost": 0.0002,
}
DIR = Path("journal/skill_desk")
TRADES = DIR / "trades.jsonl"
DAYS = DIR / "days.jsonl"


def _mins(ix: pd.DatetimeIndex) -> np.ndarray:
    return np.asarray(ix.hour * 60 + ix.minute)


def breakout(b: pd.DataFrame, cfg: dict = CONFIG) -> dict | None:
    """Pure: one stock's 5-minute bars for one day (New York times, regular session) -> its opening-range hit and
    the trade it leads to, or None. Uses each bar only once it's complete (the scanner's rule)."""
    b = b.sort_index()
    t = _mins(b.index)
    n_rng = cfg["or_minutes"] // 5
    want = [9 * 60 + 30 + 5 * k for k in range(n_rng)]
    if len(b) < n_rng + 2 or list(t[:n_rng]) != want:
        return None                                    # a missing opening bar: the scanner calls it unusable
    o, h, l, c, v = (b[k].to_numpy(float) for k in ("open", "high", "low", "close", "volume"))
    hi, lo = h[:n_rng].max(), l[:n_rng].min()
    mid = (hi + lo) / 2
    for k in range(n_rng, len(b) - 1):
        closes_at = t[k] + 5
        if closes_at > cfg["no_entries_after"]:
            return None
        if c[k] <= hi:
            continue
        if closes_at < cfg["no_entries_before"]:
            continue
        risk = c[k] - mid                              # the plan: entry at the hit's close, stop at the midpoint
        target = c[k] + cfg["target_r"] * risk
        entry = o[k + 1]
        if entry <= mid or t[k + 1] >= cfg["flat_by"]:
            return None
        exit_px, why, j_out = None, None, None
        for j in range(k + 1, len(b)):
            if t[j] >= cfg["flat_by"]:
                exit_px, why, j_out = o[j], "flat_by", j
                break
            first = j == k + 1
            if l[j] <= mid:
                exit_px, why, j_out = (mid if first else min(o[j], mid)), "stop", j
                break
            if h[j] >= target:
                exit_px, why, j_out = (max(entry, target) if first else max(o[j], target)), "target", j
                break
        if exit_px is None:
            exit_px, why, j_out = c[-1], "close", len(b) - 1
        return {"signal_min": int(closes_at), "signal_time": f"{closes_at // 60:02d}:{closes_at % 60:02d}",
                "entry_time": str(b.index[k + 1].time())[:5], "exit_time": str(b.index[j_out].time())[:5],
                "exit_min": int(t[j_out]) + (0 if why == "flat_by" else 5),     # known once its bar ends
                "or_high": round(hi, 4), "or_low": round(lo, 4), "plan_entry": round(c[k], 4),
                "entry": round(float(entry), 4), "stop": round(mid, 4), "target": round(target, 4),
                "risk": round(risk, 4), "exit": round(float(exit_px), 4), "exit_why": why,
                "traded_usd": float((c[:k + 1] * v[:k + 1]).sum())}
    return None


def day_trades(bars: dict[str, pd.DataFrame], equity: float, cfg: dict = CONFIG) -> list[dict]:
    """Pure: every stock's bars for one day -> the trades the skill's limits allow, in time order."""
    return allocate([dict(symbol=s, **x) for s, d in bars.items() if len(d) for x in [breakout(d, cfg)] if x],
                    equity, cfg)


def allocate(hits: list[dict], equity: float, cfg: dict = CONFIG) -> list[dict]:
    """Pure: one day's breakouts (from `breakout`, with "symbol") -> the trades the skill's limits allow."""
    hits = sorted(hits, key=lambda x: (x["signal_min"], -x["traded_usd"], x["symbol"]))
    taken: list[dict] = []
    for x in hits:
        if len(taken) >= cfg["max_trades_per_day"]:
            break
        realised = sum(tr["pnl"] for tr in taken if tr["exit_min"] <= x["signal_min"])
        if realised <= -cfg["max_daily_loss_usd"]:
            break
        in_use = sum(tr["shares"] * tr["entry"] for tr in taken if tr["exit_min"] > x["signal_min"])
        cash = equity * (1 - cfg["cash_buffer_pct"] / 100) - in_use
        cap = min(cfg["max_order_usd"], cfg["budget"] * cfg["max_position_pct"] / 100, cash)
        shares = min(math.floor(cfg["max_loss_per_trade_usd"] / x["risk"]), math.floor(cap / x["plan_entry"]))
        if shares < 1:
            continue
        cost = cfg["cost"] * shares * (x["entry"] + x["exit"])
        pnl = shares * (x["exit"] - x["entry"]) - cost
        taken.append({**{k: v for k, v in x.items() if k != "traded_usd"}, "shares": int(shares),
                      "pnl": round(pnl, 2), "ret": round(x["exit"] / x["entry"] - 1 - 2 * cfg["cost"], 6),
                      "R": round((x["exit"] - x["entry"]) / x["risk"], 3)})
    return taken


# --- live recording (network) ---------------------------------------------------------------------------------

def fetch_day(symbols: list[str], day: str) -> dict[str, pd.DataFrame]:
    """5-minute regular-session bars for many stocks on one day (Alpaca SIP, many symbols per request)."""
    from ai_desk.broker.alpaca import AlpacaPaper
    s = AlpacaPaper().session
    end = min(pd.Timestamp(f"{day}T23:59:59Z"), pd.Timestamp.now(tz="UTC") - pd.Timedelta(minutes=16))
    rows: dict[str, list] = {}
    for i in range(0, len(symbols), 50):
        params = {"symbols": ",".join(x.replace("-", ".") for x in symbols[i:i + 50]),     # Alpaca writes BRK.B
                  "timeframe": "5Min", "start": f"{day}T13:00:00Z",
                  "end": end.strftime("%Y-%m-%dT%H:%M:%SZ"), "limit": 10000, "adjustment": "split", "feed": "sip"}
        while True:
            r = s.get("https://data.alpaca.markets/v2/stocks/bars", params=params, timeout=30)
            r.raise_for_status()
            js = r.json()
            for sym, bs in (js.get("bars") or {}).items():
                rows.setdefault(sym, []).extend(bs)
            if not js.get("next_page_token"):
                break
            params["page_token"] = js["next_page_token"]
    out = {}
    for sym, bs in rows.items():
        df = pd.DataFrame(bs).rename(columns={"o": "open", "h": "high", "l": "low", "c": "close", "v": "volume"})
        df.index = pd.to_datetime(df.pop("t"), utc=True).dt.tz_convert("America/New_York").dt.tz_localize(None)
        t = _mins(df.index)
        out[sym.replace(".", "-")] = df[(t >= 9 * 60 + 30) & (t < 16 * 60)][
            ["open", "high", "low", "close", "volume"]].astype(float)
    return out


def _read(path: Path) -> list[dict]:
    return [json.loads(x) for x in path.read_text().splitlines() if x.strip()] if path.exists() else []


def days() -> list[dict]:
    return _read(DAYS)


def trades() -> list[dict]:
    return _read(TRADES)


def equity_now() -> float:
    d = days()
    return d[-1]["equity"] if d else CONFIG["budget"]


def record(day: str | None = None, symbols: list[str] | None = None) -> dict | None:
    """Replay one finished trading day for the ledger (once). None if there's no finished session yet."""
    day = day or pd.Timestamp.now(tz="America/New_York").date().isoformat()
    if day < START_DAY:
        return None
    have = {d["date"]: d for d in days()}
    if day in have:
        return have[day]
    if any(d > day for d in have):
        raise ValueError(f"{day} is before the ledger's last day; the ledger only moves forward")
    if symbols is None:
        from ai_desk.rsi_dip import universe
        symbols = universe()
    bars = fetch_day(symbols, day)
    full = [d for d in bars.values() if len(d) and _mins(d.index).max() >= CONFIG["flat_by"]]
    if not full:
        return None                                    # a holiday, or the session isn't over
    eq0 = equity_now()
    tr = day_trades(bars, eq0)
    pnl = round(sum(x["pnl"] for x in tr), 2)
    row = {"date": day, "recorded_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "stocks": len(bars), "breakouts": sum(1 for d in bars.values() if len(d) and breakout(d)),
           "trades": len(tr), "pnl": pnl, "equity": round(eq0 + pnl, 2)}
    DIR.mkdir(parents=True, exist_ok=True)
    with TRADES.open("a") as f:
        for x in tr:
            f.write(json.dumps({"date": day, **x}) + "\n")
    with DAYS.open("a") as f:
        f.write(json.dumps(row) + "\n")
    return row


def summary() -> dict:
    """Pure-ish (reads the log): days, trades, win rate, P&L and return so far vs the $5,000 start."""
    d, t = days(), trades()
    pnl = np.array([x["pnl"] for x in t], dtype=float)
    eq = d[-1]["equity"] if d else CONFIG["budget"]
    return {"days": len(d), "trades": len(t), "win_rate": float((pnl > 0).mean()) if len(t) else None,
            "avg_pnl": float(pnl.mean()) if len(t) else None, "avg_R": float(np.mean([x["R"] for x in t])) if t else None,
            "equity": eq, "return": eq / CONFIG["budget"] - 1}
