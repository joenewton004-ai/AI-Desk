"""Overnight sleeve: the desk's 30% (amendment 330e76e0) - hold the strongest overnight earners from the close to the next open.

Research: research/OVERNIGHT.md (Lou, Polk & Skouras 2019), research/DESK_OVERNIGHT.md. Each month, the 20 large US
stocks with the highest average overnight return (previous close -> open) over the past 12 months are locked in
data/portfolio/overnight.json. It trades in the DESK'S paper account, alongside the quality screen (50%) and momentum
(20%) sleeves:
  ~3:32pm New York  `overnight buy --execute`  market-on-close buys (the closing auction) with the sleeve's share of
                    equity, capped by the cash on hand; whole shares, equal weight
  4:30pm            the desk's evening run (`portfolio run --method desk --execute`) reads today's fills into the
                    overnight book (data/portfolio/overnight_book.json) and sells those shares at the next open in
                    the SAME order as any desk trade in that stock - one net order per symbol, because Alpaca rejects
                    opposite-side orders in one stock as possible wash trades
`overnight review` compares buy fills with the official close and sales with the official open (break-even about
0.045% per trade). Paper fills are simulated: the review checks the plumbing, not real auction costs.
The swap starts on the date in data/portfolio/overnight_live.json (`overnight activate`); before it the desk keeps
SPY momentum. Journal: journal/overnight/.
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
BOOK = Path("data/portfolio/overnight_book.json")
DIR = Path("journal/overnight")
N, LOOK_BACK, MIN_DAYS = 20, 252, 200
SHARE = 0.30
MIN_PRICE, MIN_DOLLAR_VOLUME = 10.0, 20e6
CASH_BUFFER = 0.01            # of equity: a closing price above the 3:32pm price must not overdraw the account
NY = ZoneInfo("America/New_York")
BUY_WINDOW = ((15, 30), (15, 49))    # market-on-close orders must be in before 3:50pm (NYSE)


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


def plan_buys(picks: list[str], equity: float, cash: float, prices: dict[str, float], book_open: bool,
              share: float = SHARE, buffer: float = CASH_BUFFER) -> list[dict]:
    """Whole-share market-on-close buys: an equal slice of the sleeve's budget per pick. The budget is `share` of
    equity, capped by the cash on hand less a buffer (the desk's other sleeves are invested). Nothing is bought while
    the book still holds last night's shares - their sale at the open didn't go through."""
    if book_open:
        return []
    budget = max(0.0, min(share * equity, cash - buffer * equity))
    slice_ = budget / max(len(picks), 1)
    out = []
    for s in picks:
        px = prices.get(s)
        if not px or not math.isfinite(px) or px <= 0:
            continue
        qty = int(slice_ // px)
        if qty >= 1:
            out.append({"symbol": s, "qty": qty, "side": "buy", "ref_price": float(px), "notional": qty * float(px)})
    return out


def net_with_desk(desk_targets: pd.Series, positions: dict[str, float], book: dict[str, float], prices: pd.Series,
                  equity: float, frozen: set[str]) -> tuple[pd.Series, set[str]]:
    """Fold tonight's overnight exits into the desk's own plan, so each stock gets ONE order at the open.
    The desk's targets stay as they are (its sleeves don't know about the overnight shares): plan_orders then sells
    the overnight shares as the excess over the target. For a locked (frozen) desk holding that the overnight sleeve
    also holds, the target becomes the desk's own shares, and the symbol is unfrozen so the overnight part can go."""
    t = desk_targets.copy()
    fz = set(frozen)
    for s, q in book.items():
        if not q:
            continue
        if s in fz:
            own = positions.get(s, 0.0) - q
            px = float(prices.get(s, np.nan))
            if np.isfinite(px) and equity > 0:
                t[s] = own * px / equity
            fz.discard(s)
        elif s not in t.index:
            t[s] = 0.0
    return t, fz


def in_window(now: datetime, window: tuple[tuple[int, int], tuple[int, int]]) -> bool:
    ny = now.astimezone(NY)
    return window[0] <= (ny.hour, ny.minute) <= window[1] and ny.weekday() < 5


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


def load_book() -> dict:
    return json.loads(BOOK.read_text()) if BOOK.exists() else {}


def book_open(today: str) -> bool:
    """True if shares bought on an earlier day were never sent for sale."""
    b = load_book()
    return bool(b.get("holdings")) and not b.get("sell_sent") and b.get("date") != today


def confirm_book(broker, today: str) -> dict[str, float]:
    """Today's filled market-on-close buys -> the overnight book (what the evening run sells at the next open)."""
    orders = [o for o in _read("orders.jsonl") if o.get("kind") == "buy_moc" and o.get("date") == today]
    held = {}
    for o in orders:
        info = broker.get_order(o["order_id"]) if o.get("order_id") else {}
        q = float(info.get("filled_qty") or 0)
        if q:
            held[o["symbol"]] = held.get(o["symbol"], 0.0) + q
    if orders:
        BOOK.parent.mkdir(parents=True, exist_ok=True)
        BOOK.write_text(json.dumps({"date": today, "holdings": held, "sell_sent": False, "confirmed_utc": _now()},
                                   indent=1))
    b = load_book()
    return dict(b.get("holdings") or {}) if b.get("date") == today and not b.get("sell_sent") else {}


def mark_sold(book: dict[str, float], order_ids: dict[str, str], today: str) -> None:
    """The evening run sent the book's shares for sale at the next open (netted with desk trades)."""
    b = load_book()
    BOOK.write_text(json.dumps({**b, "sell_sent": True, "sell_utc": _now()}, indent=1))
    for s, q in book.items():
        _append("orders.jsonl", {"utc": _now(), "date": today, "kind": "sell_open", "symbol": s, "qty": q, "side": "sell",
                                 "order_id": order_ids.get(s), "note": "netted into the desk's order for this stock"})


def swap_active(today: pd.Timestamp | None = None) -> bool:
    from ai_desk.portfolio.methods import overnight_swap
    sw = overnight_swap()
    t = (today or pd.Timestamp.now(tz="America/New_York").tz_localize(None)).normalize()
    return bool(sw) and t >= pd.Timestamp(sw["from"])


def activate(start: str | None = None) -> dict:
    """Start the swap (amendment 330e76e0): from `start` (default today, New York) the desk drops SPY momentum -
    sold at the next open after that evening's run - and the overnight sleeve buys from the next afternoon."""
    from ai_desk.portfolio.methods import OVERNIGHT_SWAP
    row = {"from": start or datetime.now(timezone.utc).astimezone(NY).date().isoformat(), "share": SHARE,
           "amendment": "330e76e0", "activated_utc": _now()}
    OVERNIGHT_SWAP.parent.mkdir(parents=True, exist_ok=True)
    OVERNIGHT_SWAP.write_text(json.dumps(row, indent=1))
    return row


def latest_prices(symbols: list[str]) -> dict[str, float]:
    bars = daily_bars(symbols, period="5d")
    last = bars["close"].ffill().iloc[-1]
    return {k: float(x) for k, x in last.items() if np.isfinite(x)}


def buy(execute: bool = False, now: datetime | None = None, broker=None) -> dict:
    from ai_desk.broker.alpaca import AlpacaPaper
    now = now or datetime.now(timezone.utc)
    today = now.astimezone(NY).date().isoformat()
    broker = broker or AlpacaPaper()
    acct = broker.account() or {}
    clock = broker.clock() or {}
    notes = []
    if not swap_active(pd.Timestamp(today)):
        return {"orders": [], "sent": 0, "blocked": "the overnight swap isn't active yet (`overnight activate`)",
                "notes": [], "dry_run": not execute, "picks": [], "equity": float(acct.get("equity", 0))}
    lock = load_lock()
    ref = None
    if lock is None or repick_due(lock, pd.Timestamp(today) - pd.offsets.BDay(1)):
        s = scan()
        ref = s["ref_date"]
        if repick_due(lock, pd.Timestamp(ref)):
            new_lock = {"picked_on": today, "ref_date": ref, "picks": s["picks"], "rows": s["rows"], "n": N,
                        "look_back_days": LOOK_BACK}
            notes.append(f"re-picked from the {ref} close: {', '.join(s['picks'])}")
            if execute:
                LOCK.parent.mkdir(parents=True, exist_ok=True)
                LOCK.write_text(json.dumps(new_lock, indent=1))
            lock = new_lock
        prices = {k: v for k, v in s["latest_price"].items() if k in lock["picks"]}
    else:
        prices = latest_prices(lock["picks"])
    equity, cash = float(acct.get("equity", 0)), float(acct.get("cash", 0))
    stale = book_open(today)
    if stale:
        notes.append("last night's overnight shares were never sent for sale - no new buys until the evening run sells them")
    orders = plan_buys(lock["picks"], equity, cash, prices, stale)
    if not orders and not stale:
        notes.append(f"no cash free for the sleeve (${cash:,.0f} on hand) - e.g. SPY's sale on the first day "
                     "after activation hasn't happened yet")
    blocked = None
    if not clock.get("is_open"):
        blocked = "market is closed (holiday or early close) - nothing sent"
    elif not in_window(now, BUY_WINDOW):
        blocked = "outside the 3:30-3:49pm New York window for market-on-close orders - nothing sent"
    sent = []
    if execute and not blocked:
        for o in orders:
            r = broker.submit_market_order(o["symbol"], o["qty"], "buy", time_in_force="cls")
            sent.append(o["symbol"])
            _append("orders.jsonl", {"utc": _now(), "date": today, "kind": "buy_moc", **o, "order_id": r.get("id")})
    out = {"account": acct.get("account_number"), "equity": equity, "cash": cash, "picks": lock["picks"],
           "orders": orders, "sent": len(sent), "blocked": blocked, "notes": notes, "dry_run": not execute}
    _append("runs.jsonl", {"utc": _now(), "kind": "buy", **{k: out[k] for k in ("equity", "cash", "sent", "blocked", "dry_run")},
                           "notes": notes})
    return out


def review(write: bool = True, broker=None) -> dict:
    """Buy fills vs the official close that day; sale fills vs the official open the next trading day."""
    from ai_desk.broker.alpaca import AlpacaPaper
    broker = broker or AlpacaPaper()
    orders = _read("orders.jsonl")
    fills = []
    for o in orders:
        info = broker.get_order(o["order_id"]) if o.get("order_id") else {}
        if info.get("status") != "filled":
            continue
        filled_at = pd.Timestamp(info.get("filled_at")).tz_convert(NY).date().isoformat() if info.get("filled_at") else o["date"]
        fills.append({**o, "fill": float(info["filled_avg_price"]), "filled_qty": float(info["filled_qty"]),
                      "fill_date": filled_at, "netted": o.get("kind") == "sell_open"})
    if fills:
        syms = sorted({f["symbol"] for f in fills})
        bars = daily_bars(syms, period="3mo")
        for f in fills:
            d = pd.Timestamp(f["fill_date"])
            ref = bars["close" if f["side"] == "buy" else "open"]
            off = ref[f["symbol"]].get(d) if f["symbol"] in ref else None
            f["official"] = float(off) if off is not None and np.isfinite(off) else None
            f["cost"] = fill_cost(f["side"], f["fill"], f["official"]) if f["official"] else None
    costs = [f["cost"] for f in fills if f.get("cost") is not None]
    side = lambda sd: [f["cost"] for f in fills if f["side"] == sd and f.get("cost") is not None] or [np.nan]  # noqa: E731
    summary = {"asof_utc": _now(), "orders": len(orders), "filled": len(fills),
               "avg_cost": float(np.mean(costs)) if costs else None,
               "avg_cost_buys": float(np.mean(side("buy"))), "avg_cost_sells": float(np.mean(side("sell"))),
               "break_even": 0.00045,
               "note": "paper fills are simulated: this checks the mechanics, not real auction costs. Sales are netted "
                       "with desk trades in the same stock, so their fill price is the whole order's"}
    out = {"summary": summary, "fills": fills}
    if write:
        DIR.mkdir(parents=True, exist_ok=True)
        (DIR / "review.json").write_text(json.dumps(out, indent=1, default=str))
    return out
