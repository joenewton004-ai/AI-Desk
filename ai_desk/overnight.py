"""Overnight sleeve: hold the strongest overnight earners from the close to the next open.

Research: research/OVERNIGHT.md (Lou, Polk & Skouras 2019). Each month, the 20 large US stocks with
the highest average overnight return (previous close -> open) over the past 12 months are locked
in data/portfolio/overnight.json. Every trading day:
  ~3:40pm New York  `overnight buy --execute`   market-on-close buys (the closing auction), equal weight
  ~9:15am New York  `overnight sell --execute`  market-on-open sells of everything (the opening auction)
`overnight review` compares every fill with the official close/open - the cost this whole idea
depends on (break-even about 0.045% per trade). Alpaca's paper fills are simulated, so the review
checks the plumbing; it can't prove what real auction fills would cost.

It runs in its OWN Alpaca paper account (keys APCA_OVERNIGHT_KEY_ID / APCA_OVERNIGHT_SECRET_KEY),
never the desk's: the desk's evening run would otherwise see these positions and sell them. Every
run checks the account number differs from the desk's and refuses otherwise. Journal files go to
journal/overnight/, apart from the desk's scorecard.
"""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

LOCK = Path("data/portfolio/overnight.json")
DIR = Path("journal/overnight")
KEY_ENV = ("APCA_OVERNIGHT_KEY_ID", "APCA_OVERNIGHT_SECRET_KEY")
N, LOOK_BACK, MIN_DAYS = 20, 252, 200
MIN_PRICE, MIN_DOLLAR_VOLUME = 10.0, 20e6
CASH_BUFFER = 0.02            # keep 2% in cash so a closing price above the 3:40pm price can't overdraw
NY = ZoneInfo("America/New_York")
BUY_WINDOW = ((15, 30), (15, 49))    # market-on-close orders must be in before 3:50pm (NYSE)
SELL_WINDOW = ((7, 0), (9, 27))      # market-on-open orders must be in before 9:28am


# --- pure pieces (unit-tested) --------------------------------------------------------

def overnight_score(opens: pd.DataFrame, closes: pd.DataFrame, look_back: int = LOOK_BACK,
                    min_days: int = MIN_DAYS) -> pd.DataFrame:
    """Average overnight return (previous close -> open) over the past `look_back` days, per day.
    Row t uses data up to t's close only (its overnight return ended at t's open)."""
    on = opens / closes.shift(1) - 1
    on = on.where(on.abs() < 0.5)                         # a >50% gap is bad data in a large company
    return on.rolling(look_back, min_periods=min_days).mean()


def eligible(closes: pd.DataFrame, volume: pd.DataFrame) -> pd.DataFrame:
    dollar = (closes * volume).rolling(50, min_periods=40).mean()
    return (closes > MIN_PRICE) & (dollar > MIN_DOLLAR_VOLUME)


def pick(score_row: pd.Series, eligible_row: pd.Series, n: int = N) -> list[str]:
    s = score_row.where(eligible_row.reindex(score_row.index).fillna(False).astype(bool)).dropna()
    return list(s.nlargest(n).index)


def repick_due(lock: dict | None, last_full_day: pd.Timestamp) -> bool:
    """Re-pick at the first run after a month-end: the research picks at each month's last close."""
    if not lock:
        return True
    return pd.Timestamp(last_full_day).to_period("M") > pd.Timestamp(lock["ref_date"]).to_period("M")


def plan_buys(picks: list[str], equity: float, prices: dict[str, float], held: dict[str, float],
              buffer: float = CASH_BUFFER) -> list[dict]:
    """Whole-share market-on-close buys, an equal slice of (1 - buffer) of equity per pick.
    Nothing is bought if anything is still held: the morning sell didn't go through."""
    if any(q for q in held.values()):
        return []
    slice_ = equity * (1 - buffer) / max(len(picks), 1)
    out = []
    for s in picks:
        px = prices.get(s)
        if not px or not math.isfinite(px) or px <= 0:
            continue
        qty = int(slice_ // px)
        if qty >= 1:
            out.append({"symbol": s, "qty": qty, "side": "buy", "ref_price": float(px), "notional": qty * float(px)})
    return out


def plan_sells(held: dict[str, float]) -> list[dict]:
    return [{"symbol": s, "qty": int(q), "side": "sell"} for s, q in sorted(held.items()) if q >= 1]


def in_window(now: datetime, window: tuple[tuple[int, int], tuple[int, int]]) -> bool:
    ny = now.astimezone(NY)
    return window[0] <= (ny.hour, ny.minute) <= window[1] and ny.weekday() < 5


def same_account_guard(overnight_account: str, desk_account: str | None) -> None:
    if not overnight_account:
        raise RuntimeError("couldn't read the overnight paper account number - not trading")
    if desk_account and overnight_account == desk_account:
        raise RuntimeError(f"the overnight keys point at the desk's account ({desk_account}) - refusing to trade. "
                           "Create a second paper account and use its keys for APCA_OVERNIGHT_KEY_ID/SECRET_KEY.")


def fill_cost(side: str, fill: float, official: float) -> float:
    """Cost of a fill vs the official auction price, as a fraction (positive = worse than official)."""
    return (fill / official - 1) if side == "buy" else (1 - fill / official)


# --- files ---------------------------------------------------------------------------

def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_lock() -> dict | None:
    return json.loads(LOCK.read_text()) if LOCK.exists() else None


def _append(name: str, row: dict) -> None:
    DIR.mkdir(parents=True, exist_ok=True)
    with (DIR / name).open("a") as f:
        f.write(json.dumps(row, default=str) + "\n")


def _read(name: str) -> list[dict]:
    p = DIR / name
    return [json.loads(x) for x in p.read_text().splitlines() if x.strip()] if p.exists() else []


# --- network --------------------------------------------------------------------------

def daily_bars(symbols: list[str], period: str = "15mo") -> dict[str, pd.DataFrame]:
    """Unadjusted daily open/close/volume (the official auction prices, not dividend-adjusted)."""
    import yfinance as yf

    from ai_desk.fundamentals.yahoo import with_retry
    parts = {k: [] for k in ("Open", "Close", "Volume")}
    for i in range(0, len(symbols), 100):
        chunk = symbols[i:i + 100]
        d = with_retry(lambda chunk=chunk: yf.download(chunk, period=period, interval="1d", auto_adjust=False,
                                                       progress=False, threads=4))
        for k in parts:
            x = d[k]
            parts[k].append(x.to_frame(chunk[0]) if isinstance(x, pd.Series) else x)
    out = {}
    for k, v in parts.items():
        df = pd.concat(v, axis=1)
        df = df.loc[:, ~df.columns.duplicated()]
        df.index = pd.to_datetime(df.index).tz_localize(None)
        out[k.lower()] = df
    return out


def scan(universe_size: int = 750) -> dict:
    """Today's ranking from the last full trading day (no lock written - `buy` locks on a re-pick)."""
    from ai_desk.fundamentals.universe import large_caps
    from ai_desk.live import drop_incomplete_bar

    uni = large_caps(2e9, limit=universe_size)
    syms = uni["symbol"].tolist()[:universe_size]
    bars = daily_bars(syms)
    latest = bars["close"].ffill().iloc[-1]                 # during the day: the latest price, for sizing only
    o, c, v = (drop_incomplete_bar(bars[k]) for k in ("open", "close", "volume"))
    sc, el = overnight_score(o, c), eligible(c, v)
    last = c.index[-1]
    picks = pick(sc.loc[last], el.loc[last])
    names = uni.set_index("symbol")["name"].to_dict() if "name" in uni else {}
    rows = [{"symbol": s, "name": names.get(s, ""), "score": float(sc.at[last, s]),
             "overnight_yr": float((1 + sc.at[last, s]) ** 252 - 1), "close": float(c.at[last, s])} for s in picks]
    return {"ref_date": last.date().isoformat(), "picks": picks, "rows": rows, "universe": len(syms),
            "latest_price": {k: float(x) for k, x in latest.items() if np.isfinite(x)}}


def brokers():
    from ai_desk.broker.alpaca import AlpacaPaper
    ovn = AlpacaPaper(key_env=KEY_ENV, require_keys=True)
    try:
        desk_acct = AlpacaPaper().account().get("account_number")
    except Exception:  # noqa: BLE001 - the desk's keys may be unavailable; the guard then relies on the keys differing
        desk_acct = None
    acct = ovn.account() or {}
    same_account_guard(acct.get("account_number", ""), desk_acct)
    return ovn, acct


def buy(execute: bool = False, now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    ovn, acct = brokers()
    clock = ovn.clock() or {}
    lock = load_lock()
    s = scan()
    notes = []
    if repick_due(lock, pd.Timestamp(s["ref_date"])):
        new_lock = {"picked_on": now.astimezone(NY).date().isoformat(), "ref_date": s["ref_date"], "picks": s["picks"],
                    "rows": s["rows"], "n": N, "look_back_days": LOOK_BACK}
        notes.append(f"re-picked from the {s['ref_date']} close: {', '.join(s['picks'])}")
        if execute:
            LOCK.parent.mkdir(parents=True, exist_ok=True)
            LOCK.write_text(json.dumps(new_lock, indent=1))
        lock = new_lock
    held = ovn.positions()
    equity = float(acct.get("equity", 0))
    orders = plan_buys(lock["picks"], equity, s["latest_price"], held)
    if held:
        notes.append(f"still holding {', '.join(sorted(held))} - the morning sell didn't complete; no new buys")
    blocked = None
    if not clock.get("is_open"):
        blocked = "market is closed (holiday or early close) - nothing sent"
    elif not in_window(now, BUY_WINDOW):
        blocked = "outside the 3:30-3:49pm New York window for market-on-close orders - nothing sent"
    elif ovn.open_orders():
        blocked = "orders still open at the broker - nothing sent"
    sent = []
    if execute and not blocked:
        for o in orders:
            r = ovn.submit_market_order(o["symbol"], o["qty"], "buy", time_in_force="cls")
            sent.append({**o, "order_id": r.get("id")})
            _append("orders.jsonl", {"utc": _now(), "date": now.astimezone(NY).date().isoformat(), "kind": "buy_moc",
                                     **o, "order_id": r.get("id")})
    out = {"account": acct.get("account_number"), "equity": equity, "picks": lock["picks"], "orders": orders,
           "sent": len(sent), "blocked": blocked, "notes": notes, "dry_run": not execute}
    _append("runs.jsonl", {"utc": _now(), "kind": "buy", **{k: out[k] for k in ("equity", "sent", "blocked", "dry_run")},
                           "notes": notes})
    return out


def sell(execute: bool = False, now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    ovn, acct = brokers()
    held = ovn.positions()
    orders = plan_sells(held)
    clock = ovn.clock() or {}
    blocked = None
    today = now.astimezone(NY).date().isoformat()
    if str(clock.get("next_open", ""))[:10] != today or clock.get("is_open"):
        blocked = "not before a trading day's open (holiday, weekend or already open) - nothing sent"
    elif not in_window(now, SELL_WINDOW):
        blocked = "outside the 7:00-9:27am New York window for market-on-open orders - nothing sent"
    elif ovn.open_orders():
        blocked = "orders still open at the broker - nothing sent"
    sent = 0
    if execute and not blocked:
        for o in orders:
            r = ovn.submit_market_order(o["symbol"], o["qty"], "sell", time_in_force="opg")
            sent += 1
            _append("orders.jsonl", {"utc": _now(), "date": today, "kind": "sell_moo", **o, "order_id": r.get("id")})
    out = {"account": acct.get("account_number"), "held": held, "orders": orders, "sent": sent, "blocked": blocked,
           "dry_run": not execute}
    _append("runs.jsonl", {"utc": _now(), "kind": "sell", "sent": sent, "blocked": blocked, "dry_run": not execute})
    return out


def review(write: bool = True) -> dict:
    """Every filled order vs the official close (buys) or open (sells) that day, and each night's result."""
    ovn, _ = brokers()
    orders = _read("orders.jsonl")
    fills = []
    for o in orders:
        info = ovn.get_order(o["order_id"]) if o.get("order_id") else {}
        if info.get("status") != "filled":
            continue
        fills.append({**o, "fill": float(info["filled_avg_price"]), "filled_qty": float(info["filled_qty"]),
                      "filled_at": info.get("filled_at")})
    if fills:
        syms = sorted({f["symbol"] for f in fills})
        bars = daily_bars(syms, period="3mo")
        for f in fills:
            d = pd.Timestamp(f["date"])
            ref = bars["close" if f["side"] == "buy" else "open"]
            off = ref[f["symbol"]].get(d) if f["symbol"] in ref else None
            f["official"] = float(off) if off is not None and np.isfinite(off) else None
            f["cost"] = fill_cost(f["side"], f["fill"], f["official"]) if f["official"] else None
    costs = [f["cost"] for f in fills if f.get("cost") is not None]
    summary = {"asof_utc": _now(), "orders": len(orders), "filled": len(fills),
               "avg_cost": float(np.mean(costs)) if costs else None,
               "avg_cost_buys": float(np.mean([f["cost"] for f in fills if f["side"] == "buy" and f.get("cost") is not None]
                                              or [np.nan])),
               "avg_cost_sells": float(np.mean([f["cost"] for f in fills if f["side"] == "sell" and f.get("cost") is not None]
                                               or [np.nan])),
               "break_even": 0.00045, "note": "paper fills are simulated: this checks the mechanics, not real auction costs"}
    out = {"summary": summary, "fills": fills}
    if write:
        DIR.mkdir(parents=True, exist_ok=True)
        (DIR / "review.json").write_text(json.dumps(out, indent=1, default=str))
    return out
