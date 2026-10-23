"""Overnight sleeve: the desk's 30% (amendment 330e76e0) - hold the strongest overnight earners from the close to the next open.

Research: research/OVERNIGHT.md (Lou, Polk & Skouras 2019), research/DESK_OVERNIGHT.md. Each month, the 20 large US
stocks with the highest average overnight return (previous close -> open) over the past 12 months are locked in
data/portfolio/overnight.json. It trades in the DESK'S paper account, alongside the quality screen (50%) and momentum
(20%) sleeves:
  ~3:55pm New York  `overnight buy --execute`  market buys a few minutes before the close with the sleeve's share of
                    equity, capped by the cash on hand; whole shares, equal weight. (Until 2026-10-22 these were
                    market-on-close orders; Alpaca's paper account filled only part of them - amendment dc6335fa.)
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
CASH_BUFFER = 0.01            # of equity: a fill above the planning price must not overdraw the account
NY = ZoneInfo("America/New_York")
BUY_WINDOW = ((15, 55), (15, 59))    # market orders in the last minutes before the 4pm close
EARLY_WAIT = 110                      # seconds: a run that starts just before 3:55pm waits (under a 2-minute tool limit)
BUY_KINDS = ("buy_moc", "buy_mkt")    # market-on-close (until 2026-10-21), then market orders near the close


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


def twelve_month_return(adj: pd.DataFrame, days: int = LOOK_BACK) -> pd.DataFrame:
    """The ranking since 2026-10-23 (amendment 82c84226): each stock's plain return over the past `days` trading days,
    on dividend- and split-adjusted closes. Row t uses closes up to t only."""
    return adj / adj.shift(days) - 1


def repick_due(lock: dict | None, last_full_day: pd.Timestamp) -> bool:
    """Re-pick every trading day (amendment 82c84226): due whenever the lock was ranked on an earlier close.
    (Until 2026-10-23 it re-picked only after a month-end.)"""
    if not lock:
        return True
    return pd.Timestamp(last_full_day).normalize() > pd.Timestamp(lock["ref_date"])


def new_month(lock: dict | None, ref_date: str) -> bool:
    """The watchlist keeps one cohort a month: the first ranking of each month."""
    return not lock or pd.Timestamp(ref_date).to_period("M") > pd.Timestamp(lock["ref_date"]).to_period("M")


def plan_buys(picks: list[str], equity: float, cash: float, prices: dict[str, float], book_open: bool,
              share: float = SHARE, buffer: float = CASH_BUFFER) -> list[dict]:
    """Whole-share buys near the close: an equal slice of the sleeve's budget per pick. The budget is `share` of
    equity, capped by the cash on hand less a buffer (the desk's other sleeves are invested). Nothing is bought while
    the book still holds last night's shares - their sale at the open didn't go through."""
    if book_open:
        return []
    budget = max(0.0, min(share * equity, cash - buffer * equity))
    priced = [s for s in picks if prices.get(s) and math.isfinite(prices[s]) and prices[s] > 0]
    slice_ = budget / max(len(priced), 1)
    qty = {s: int(slice_ // prices[s]) for s in priced}
    # whole shares leave money over (one $900 share of a $1,475 slice): spend it one share at a time on the
    # pick furthest below its slice, never above the budget
    left = budget - sum(qty[s] * prices[s] for s in priced)
    while True:
        fits = [s for s in priced if prices[s] <= left]
        if not fits:
            break
        s = min(fits, key=lambda x: (qty[x] * prices[x] + prices[x]) / slice_)
        qty[s] += 1
        left -= prices[s]
    return [{"symbol": s, "qty": qty[s], "side": "buy", "ref_price": float(prices[s]),
             "notional": qty[s] * float(prices[s])} for s in priced if qty[s] >= 1]


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
    parts = {k: [] for k in ("Open", "Close", "Adj Close", "Volume")}
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
        out[k.lower().replace("adj close", "adj")] = df
    return out


def scan(universe_size: int = 750) -> dict:
    """Today's ranking (12-month return) from the last full trading day (no lock written - `buy` locks it)."""
    from ai_desk.fundamentals.universe import large_caps
    from ai_desk.live import drop_incomplete_bar

    uni = large_caps(2e9, limit=universe_size)
    syms = uni["symbol"].tolist()[:universe_size]
    bars = daily_bars(syms)
    latest = bars["close"].ffill().iloc[-1]                 # during the day: the latest price, for sizing only
    c, v, adj = (drop_incomplete_bar(bars[k]) for k in ("close", "volume", "adj"))
    sc, el = twelve_month_return(adj), eligible(c, v)
    last = c.index[-1]
    picks = pick(sc.loc[last], el.loc[last])
    names = uni.set_index("symbol")["name"].to_dict() if "name" in uni else {}
    rows = [{"symbol": s, "name": names.get(s, ""), "score": float(sc.at[last, s]), "ret_12m": float(sc.at[last, s]),
             "close": float(c.at[last, s])} for s in picks]
    return {"ref_date": last.date().isoformat(), "picks": picks, "rows": rows, "universe": len(syms),
            "near": near_misses(sc.loc[last], el.loc[last], c, v, names),
            "latest_price": {k: float(x) for k, x in latest.items() if np.isfinite(x)}}


def near_misses(score_row: pd.Series, eligible_row: pd.Series, closes: pd.DataFrame, volume: pd.DataFrame,
                names: dict | None = None, n: int = N, more: int = 40, failed: int = 20) -> list[dict]:
    """Pure: the stocks ranked just below the picks (the watchlist), plus the best scorers that failed the price or
    liquidity gate - all as of the decision close (the last row of `closes`)."""
    names = names or {}
    ok = eligible_row.reindex(score_row.index).fillna(False).astype(bool)
    s = score_row.dropna()
    ranked = s[ok.reindex(s.index)].sort_values(ascending=False)
    px = closes.iloc[-1]
    dollar = (closes * volume).rolling(50, min_periods=40).mean().iloc[-1]

    def row(sym, eligible, reason=""):
        return {"symbol": sym, "name": names.get(sym, ""), "score": float(s[sym]),
                "ret_12m": float(s[sym]), "close": float(px.get(sym, np.nan)),
                "passes": bool(eligible), "gate_reason": reason}

    out = [row(sym, True) for sym in ranked.index[n:n + more]]
    cut = ranked.iloc[n - 1] if len(ranked) >= n else -np.inf
    for sym in s[~ok.reindex(s.index)].sort_values(ascending=False).index[:failed]:
        if s[sym] <= cut:
            break
        why = []
        if not px.get(sym, 0) > MIN_PRICE:
            why.append(f"price under ${MIN_PRICE:.0f}")
        if not dollar.get(sym, 0) > MIN_DOLLAR_VOLUME:
            why.append(f"trades under ${MIN_DOLLAR_VOLUME / 1e6:.0f}M a day")
        out.append(row(sym, False, ", ".join(why) or "not enough history"))
    return out


def load_book() -> dict:
    return json.loads(BOOK.read_text()) if BOOK.exists() else {}


def held_overnight(now: datetime | None = None) -> dict[str, float]:
    """Shares the overnight sleeve holds right now: the book until its sale at the next open has had time to fill
    (9:31am New York on the next weekday)."""
    b = load_book()
    if not b.get("holdings"):
        return {}
    if not b.get("sell_sent"):
        return dict(b["holdings"])
    ny = (now or datetime.now(timezone.utc)).astimezone(NY)
    sold_by = (pd.Timestamp(b["date"]) + pd.offsets.BDay(1)).replace(hour=9, minute=31)
    return dict(b["holdings"]) if pd.Timestamp(ny.replace(tzinfo=None)) < sold_by else {}


def book_open(today: str) -> bool:
    """True if shares bought on an earlier day were never sent for sale."""
    b = load_book()
    return bool(b.get("holdings")) and not b.get("sell_sent") and b.get("date") != today


def confirm_book(broker, today: str) -> dict[str, float]:
    """Today's filled buys near the close -> the overnight book (what the evening run sells at the next open)."""
    orders = [o for o in _read("orders.jsonl") if o.get("kind") in BUY_KINDS and o.get("date") == today]
    held, paid, fills = {}, {}, []
    for o in orders:
        info = broker.get_order(o["order_id"]) if o.get("order_id") else {}
        q = float(info.get("filled_qty") or 0)
        if q:
            held[o["symbol"]] = held.get(o["symbol"], 0.0) + q
            paid[o["symbol"]] = paid.get(o["symbol"], 0.0) + q * float(info.get("filled_avg_price") or 0)
            fills.append({**o, "filled_qty": q, "fill_price": float(info.get("filled_avg_price") or 0),
                          "filled_utc": info.get("filled_at"),
                          "order_type": "market-on-close" if o.get("kind") == "buy_moc" else "market"})
    if fills:                                  # into the trade journal too, as the overnight sleeve's buys
        from ai_desk import tradebook
        tradebook.record_overnight_buys(fills)
    if orders:
        BOOK.parent.mkdir(parents=True, exist_ok=True)
        costs = {s: round(paid[s] / q, 4) for s, q in held.items() if paid.get(s)}  # fill price per share (dashboard)
        BOOK.write_text(json.dumps({"date": today, "holdings": held, "costs": costs, "sell_sent": False,
                                    "confirmed_utc": _now()}, indent=1))
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


# --- the regime checks (research/OVERNIGHT_REGIME.md) -----------------------------------------------------------
# Cash for the night when SPY is below its 200-day average (amendment 7a8b29ec), or when tonight's 20 picks have
# fallen hard since today's open: their average open-to-now return at or below PICKS_DAY_CUTOFF, the worst 10% of
# days in the research (amendment 9b951502; it replaced 7a8b29ec's tech-vs-defensive check, as industries change
# and the picks change every month). Defensive stocks are NOT a substitute: they lose on the same nights.

REGIME_AMENDMENT = "9b951502"
MA_DAYS = 200
PICKS_DAY_CUTOFF = -0.020      # the picks' worst 10% of days: -1.98% for the daily 12-month ranking (research/overnight_v2.py)


def picks_day_return(opens: pd.Series, prices: pd.Series) -> float | None:
    """Pure: the picks' average return from today's open to now (a >50% move is bad data and left out)."""
    r = (prices / opens - 1).replace([np.inf, -np.inf], np.nan)
    r = r[r.abs() < 0.5].dropna()
    return float(r.mean()) if len(r) else None


def regime_flags(spy: pd.Series, picks_day: float | None, cutoff: float = PICKS_DAY_CUTOFF) -> list[str]:
    """Pure: the reasons to sit in cash tonight (empty = buy). `spy` ends with today's price (3:55pm)."""
    out = []
    if len(spy) >= MA_DAYS:
        ma = spy.iloc[-MA_DAYS:].mean()
        if spy.iloc[-1] < ma:
            out.append(f"SPY ${spy.iloc[-1]:,.2f} is below its 200-day average ${ma:,.2f}")
    if picks_day is not None and np.isfinite(picks_day) and picks_day <= cutoff:
        out.append(f"tonight's picks are down {-picks_day:.2%} since the open (cut-off {-cutoff:.1%}: the worst 10% "
                   "of days in the research)")
    return out


def check_regime(picks: list[str] | None = None, today: str | None = None) -> dict:
    """Live, just before the buy: SPY's trend and tonight's picks' move since today's open (prices as of now)."""
    picks = picks if picks is not None else (load_lock() or {}).get("picks", [])
    today = today or datetime.now(timezone.utc).astimezone(NY).date().isoformat()
    spy = daily_bars(["SPY"], period="15mo")["close"]["SPY"].dropna()
    picks_day, note = None, ""
    if picks:
        bars = daily_bars(sorted(picks), period="5d")
        last = bars["close"].index[-1].date().isoformat()
        if last == today:
            picks_day = picks_day_return(bars["open"].iloc[-1], bars["close"].iloc[-1])
        else:
            note = f"no prices for today yet (latest {last}) - picks check skipped"
    reasons = regime_flags(spy, picks_day)
    return {"cash": bool(reasons), "reasons": reasons, "spy": float(spy.iloc[-1]),
            "spy_ma200": float(spy.iloc[-MA_DAYS:].mean()), "picks_day": picks_day, "cutoff": PICKS_DAY_CUTOFF,
            "picks": len(picks), "note": note}


def _scan_cache() -> Path:
    return DIR / "scan_cache.json"


def prepare_repick(today: pd.Timestamp | None = None) -> str:
    """At the evening run: rank on today's close for tomorrow's buy (re-picked daily, amendment 82c84226), so the buy
    near tomorrow's close doesn't spend its few minutes downloading 750 stocks' prices."""
    t = (today or pd.Timestamp.now(tz="America/New_York").tz_localize(None)).normalize()
    if not swap_active(t):
        return "not active"
    s = scan()
    if s["ref_date"] != t.date().isoformat():
        return f"latest full day is {s['ref_date']}, not today - not cached"
    DIR.mkdir(parents=True, exist_ok=True)
    _scan_cache().write_text(json.dumps({**s, "latest_price": {}}, indent=1))
    return f"tomorrow's picks ranked from the {s['ref_date']} close: {', '.join(s['picks'])}"


def _newer_ranking(lock: dict | None, today: str) -> dict | None:
    """The evening run's ranking, if it is newer than the held picks and from a close before today."""
    if not _scan_cache().exists():
        return None
    s = json.loads(_scan_cache().read_text())
    ref = s.get("ref_date", "")
    return s if ref < today and (lock is None or ref > lock["ref_date"]) else None


def _cached_scan(last_full_day: pd.Timestamp) -> dict | None:
    if not _scan_cache().exists():
        return None
    s = json.loads(_scan_cache().read_text())
    return s if s.get("ref_date") == pd.Timestamp(last_full_day).date().isoformat() else None


def buy(execute: bool = False, now: datetime | None = None, broker=None, regime_check: bool = True) -> dict:
    from ai_desk.broker.alpaca import AlpacaPaper
    now = now or datetime.now(timezone.utc)
    start = datetime.combine(now.astimezone(NY).date(), datetime.min.time(), NY).replace(
        hour=BUY_WINDOW[0][0], minute=BUY_WINDOW[0][1])
    early = (start - now.astimezone(NY)).total_seconds()
    if execute and 0 < early <= EARLY_WAIT:             # a few seconds early: wait for the window
        import time
        time.sleep(early + 1)
        now = datetime.now(timezone.utc)
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
    last_full = pd.Timestamp(today) - pd.offsets.BDay(1)
    s = _newer_ranking(lock, today)
    if s is None and lock is None:
        s = scan()                                      # first ever pick: no ranking prepared - rank now (slow)
    elif s is None and repick_due(lock, last_full):
        notes.append(f"no ranking prepared since the {lock['ref_date']} close - keeping those picks")
    if s is not None:
        ref = s["ref_date"]
        if repick_due(lock, pd.Timestamp(ref)):
            new_lock = {"picked_on": today, "ref_date": ref, "picks": s["picks"], "rows": s["rows"], "n": N,
                        "look_back_days": LOOK_BACK}
            changed = sorted(set(s["picks"]) - set((lock or {}).get("picks", [])))
            notes.append(f"picks from the {ref} close" + (f" - new: {', '.join(changed)}" if lock else
                                                          f": {', '.join(s['picks'])}"))
            if execute:
                LOCK.parent.mkdir(parents=True, exist_ok=True)
                LOCK.write_text(json.dumps(new_lock, indent=1))
                try:                                     # once a month, the rest of the ranking goes on the watchlist
                    from ai_desk import watchlist
                    if new_month(lock, ref):
                        watchlist.capture_overnight(new_lock, s.get("near", []))
                except Exception as e:  # noqa: BLE001 - the watchlist must never block the buys
                    notes.append(f"watchlist not saved: {e}")
            lock = new_lock
    prices = ({k: v for k, v in s["latest_price"].items() if k in lock["picks"]} if s is not None else {}) \
        or latest_prices(lock["picks"])
    equity, cash = float(acct.get("equity", 0)), float(acct.get("cash", 0))
    regime = None
    if regime_check:                                   # tonight's picks are settled: check them and SPY
        try:
            regime = check_regime(lock["picks"], today)
        except Exception as e:  # noqa: BLE001 - a failed check must not stop the sleeve; it buys as before
            regime = {"cash": False, "reasons": [], "error": str(e)}
        if regime.get("error"):
            notes.append(f"regime check failed ({regime['error']}) - buying as usual")
        elif regime.get("note"):
            notes.append(regime["note"])
    if regime and regime["cash"]:
        out = {"account": acct.get("account_number"), "equity": equity, "cash": cash, "picks": lock["picks"],
               "orders": [], "sent": 0, "notes": notes, "dry_run": not execute, "regime": regime,
               "blocked": f"in cash tonight (amendment {REGIME_AMENDMENT}): " + "; ".join(regime["reasons"])}
        _append("runs.jsonl", {"utc": _now(), "kind": "buy", "equity": equity, "cash": cash, "sent": 0,
                               "blocked": out["blocked"], "dry_run": not execute, "notes": notes, "regime": regime})
        return out
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
        blocked = "outside the 3:55-3:59pm New York buy window - nothing sent (the scheduled 3:54pm run buys)"
    sent = []
    if execute and not blocked:
        for o in orders:
            r = broker.submit_market_order(o["symbol"], o["qty"], "buy", time_in_force="day")
            sent.append(o["symbol"])
            _append("orders.jsonl", {"utc": _now(), "date": today, "kind": "buy_mkt", **o, "order_id": r.get("id")})
    out = {"account": acct.get("account_number"), "equity": equity, "cash": cash, "picks": lock["picks"],
           "orders": orders, "sent": len(sent), "blocked": blocked, "notes": notes, "dry_run": not execute}
    out["regime"] = regime
    _append("runs.jsonl", {"utc": _now(), "kind": "buy", **{k: out[k] for k in ("equity", "cash", "sent", "blocked", "dry_run")},
                           "notes": notes, "regime": regime})
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
