"""Day-trading candle patterns on SPY, then NVDA: ten years of Alpaca minute bars, fixed rules, after costs.

    python research/candles.py            # needs research/alpaca_bars.py's cache (it downloads if missing)

All rules were fixed before the first run (textbook definitions) - none was tuned on these results.
Bars: 1-minute SIP bars from Alpaca (split-adjusted) built into 5-minute candles, 9:30-16:00 New York.

Patterns (a 5-minute candle completes at its close; the trade starts at the NEXT candle's open):
  - engulfing: a candle whose body swallows the previous opposite-coloured body (bullish -> long, bearish -> short)
  - hammer (long) / shooting star (short): a wick of at least 60% of the candle's range on one side, at most 15% on the
    other
  Both only count when the candle's range is at least the median of the previous 20 candles (no tiny dojis).
  Context, tested separately:
    plain    - every one
    reversal - long only below the day's VWAP (volume-weighted average price so far), short only above it
    trend    - long only above the day's VWAP, short only below it
  Exits, tested separately:
    30 min   - hold 6 candles (out by 15:55)
    stop/2R  - stop beyond the pattern candle's far end, target twice that risk, out by 15:55
  - inside-bar breakout: a candle inside the previous one; buy a break of the previous ("mother") candle's high within
    3 candles (stop order at that price), or sell a break of its low; stop the other side, target 2R, out by 15:55
  - opening-range breakout (ORB): the high and low of the first 15 or 30 minutes; the first break after that (stop
    order at the level) goes long or short; stop the other side of the range; out at 15:55. One trade a day
  - intraday momentum (Gao, Han, Li & Zhou 2018, J. Financial Economics): the return from yesterday's close to 10:00
    sets the direction of a trade from 15:30 to the close
Signals from 9:35 to 15:00. A stop and a target in the same candle count as the stop.
Costs: 0.01% each way for SPY (a penny on ~$700 is 0.15 basis points; the rest is slippage), 0.02% for NVDA.
Controls: the same direction and the same exit at the same time of day on randomly chosen other days (20 runs) -
what the drift and the time of day alone give, so a pattern is only interesting if it beats that.
Halves: 2016-2020 and 2021-2026. NVDA is the second test: a rule that works on SPY should work there too.
Writes research/output/candles.md; findings in research/CANDLES.md.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research"))

import alpaca_bars  # noqa: E402

OUT = Path(__file__).resolve().parent / "output"
COSTS = {"SPY": 0.0001, "NVDA": 0.0002}
SPLIT = "2021-01-01"
FIRST_SIGNAL, LAST_SIGNAL, LAST_BAR = 9 * 60 + 35, 15 * 60, 15 * 60 + 55
PLACEBO_RUNS = 20
CHECK = ["QQQ", "AAPL", "GOOGL", "MSFT", "BRK.B", "XOM", "AMZN", "META", "GE", "JNJ", "WFC"]


# --- pure pieces (unit-tested) --------------------------------------------------------

def to_bars(m: pd.DataFrame, minutes: int = 5) -> pd.DataFrame:
    """Minute bars -> `minutes` candles inside each day (a candle never spans two days), plus the day's VWAP so far."""
    g = m.groupby([m.index.normalize(), m.index.floor(f"{minutes}min")])
    b = pd.DataFrame({"open": g["open"].first(), "high": g["high"].max(), "low": g["low"].min(),
                      "close": g["close"].last(), "volume": g["volume"].sum(),
                      "pv": (m["vwap"].fillna(m["close"]) * m["volume"]).groupby(
                          [m.index.normalize(), m.index.floor(f"{minutes}min")]).sum()})
    b.index = b.index.droplevel(0)
    day = b.index.normalize()
    b["vwap"] = b["pv"].groupby(day).cumsum() / b["volume"].groupby(day).cumsum().replace(0, np.nan)
    b["tod"] = b.index.hour * 60 + b.index.minute
    b["day"] = pd.factorize(day)[0]
    return b.drop(columns="pv")


def candle_signals(b: pd.DataFrame) -> dict[str, pd.Series]:
    """+1/-1 at the candle that completes each pattern (0 elsewhere); uses that candle and earlier ones only."""
    o, h, l, c = b["open"], b["high"], b["low"], b["close"]
    rng = h - l
    body = (c - o).abs()
    up, lo = h - np.maximum(o, c), np.minimum(o, c) - l
    same_day = b["day"] == b["day"].shift(1)
    big = rng >= rng.groupby(b["day"]).transform(lambda s: s.shift(1).rolling(20, min_periods=10).median())
    o1, c1 = o.shift(1), c.shift(1)
    bull_eng = same_day & (c1 < o1) & (c > o) & (o <= c1) & (c >= o1) & (body > (c1 - o1).abs())
    bear_eng = same_day & (c1 > o1) & (c < o) & (o >= c1) & (c <= o1) & (body > (c1 - o1).abs())
    hammer = (rng > 0) & (lo >= 0.6 * rng) & (up <= 0.15 * rng)
    star = (rng > 0) & (up >= 0.6 * rng) & (lo <= 0.15 * rng)
    ok = big & b["tod"].between(FIRST_SIGNAL, LAST_SIGNAL)
    z = pd.Series(0, index=b.index)
    return {"engulfing": z.mask(bull_eng & ok, 1).mask(bear_eng & ok, -1),
            "hammer / shooting star": z.mask(hammer & ok, 1).mask(star & ok, -1)}


def with_context(sig: pd.Series, b: pd.DataFrame, kind: str) -> pd.Series:
    if kind == "plain":
        return sig
    above = b["close"] > b["vwap"]
    keep = ((sig > 0) & ~above) | ((sig < 0) & above) if kind == "reversal" else ((sig > 0) & above) | ((sig < 0) & ~above)
    return sig.where(keep, 0)


def day_ends(b: pd.DataFrame) -> np.ndarray:
    """For each candle, the position of its day's last candle at or before 15:55."""
    pos = pd.Series(np.arange(len(b)), index=b.index)
    last = pos.where(b["tod"] <= LAST_BAR).groupby(b["day"].to_numpy()).transform("max")
    return last.to_numpy().astype(int)


def run_exit(o, h, l, c, j: int, end: int, side: int, entry: float, stop: float | None, target: float | None,
             hold: int | None = None) -> tuple[float, int]:
    """Return (gross return, exit position) of a trade entered at `entry` during candle j. Stop first if a candle
    touches both; a candle that opens through the stop exits at its open (a gap)."""
    last = min(end, j + hold - 1) if hold else end
    for k in range(j, last + 1):
        if stop is not None:
            if side > 0 and l[k] <= stop:
                px = min(o[k], stop) if k > j else stop
                return side * (px / entry - 1), k
            if side < 0 and h[k] >= stop:
                px = max(o[k], stop) if k > j else stop
                return side * (px / entry - 1), k
        if target is not None:
            if side > 0 and h[k] >= target:
                return side * (max(o[k], target) / entry - 1) if k > j else side * (target / entry - 1), k
            if side < 0 and l[k] <= target:
                return side * (min(o[k], target) / entry - 1) if k > j else side * (target / entry - 1), k
    return side * (c[last] / entry - 1), last


def candle_trades(b: pd.DataFrame, sig: pd.Series, exit_kind: str) -> pd.DataFrame:
    """Enter at the next candle's open after each signal; one trade at a time per day."""
    o, h, l, c = (b[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    ends, s, day = day_ends(b), sig.to_numpy(), b["day"].to_numpy()
    out, busy = [], -1
    for i in np.flatnonzero(s):
        j = i + 1
        if j >= len(b) or day[j] != day[i] or j <= busy or j > ends[i]:
            continue
        side, entry = int(s[i]), o[j]
        if exit_kind == "30 min":
            r, k = run_exit(o, h, l, c, j, ends[i], side, entry, None, None, hold=6)
            risk = np.nan
        else:
            stop = l[i] if side > 0 else h[i]
            risk = side * (entry - stop)
            if risk <= 0:
                continue
            r, k = run_exit(o, h, l, c, j, ends[i], side, entry, stop, entry + side * 2 * risk)
            risk = risk / entry
        out.append({"time": b.index[j], "pos": j, "side": side, "ret": r, "risk": risk, "bars": k - j + 1})
        busy = k
    return pd.DataFrame(out, columns=["time", "pos", "side", "ret", "risk", "bars"])


def inside_trades(b: pd.DataFrame, window: int = 3) -> pd.DataFrame:
    o, h, l, c = (b[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    ends, day, tod = day_ends(b), b["day"].to_numpy(), b["tod"].to_numpy()
    out, busy = [], -1
    for i in range(1, len(b) - 1):
        if day[i] != day[i - 1] or not (FIRST_SIGNAL <= tod[i] <= LAST_SIGNAL) or i <= busy:
            continue
        if not (h[i] <= h[i - 1] and l[i] >= l[i - 1]) or h[i - 1] <= l[i - 1]:
            continue
        mh, ml = h[i - 1], l[i - 1]
        for j in range(i + 1, min(i + window, ends[i]) + 1):
            if day[j] != day[i]:
                break
            up, dn = h[j] > mh, l[j] < ml
            if up and dn:
                break                                        # both sides in one candle: can't tell which came first
            if up or dn:
                side = 1 if up else -1
                entry = max(o[j], mh) if up else min(o[j], ml)
                stop = ml if up else mh
                risk = side * (entry - stop)
                r, k = run_exit(o, h, l, c, j, ends[i], side, entry, stop, entry + side * 2 * risk)
                out.append({"time": b.index[j], "pos": j, "side": side, "ret": r, "risk": risk / entry, "bars": k - j + 1})
                busy = k
                break
    return pd.DataFrame(out, columns=["time", "pos", "side", "ret", "risk", "bars"])


def opening_rvol(b: pd.DataFrame, minutes: int = 15, days: int = 14) -> pd.Series:
    """Per day: volume in the first `minutes` against its average over the previous `days` days (known when the
    range closes)."""
    first = b[b["tod"] < 9 * 60 + 30 + minutes].groupby("day")["volume"].sum()
    return first / first.shift(1).rolling(days, min_periods=days).mean()


def orb_trades(b: pd.DataFrame, minutes: int = 15, min_rvol: float | None = None) -> pd.DataFrame:
    o, h, l, c = (b[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    ends, tod = day_ends(b), b["tod"].to_numpy()
    rvol = opening_rvol(b, minutes) if min_rvol else None
    out = []
    for d, idx in pd.Series(np.arange(len(b))).groupby(b["day"].to_numpy()):
        idx = idx.to_numpy()
        rng = idx[tod[idx] < 9 * 60 + 30 + minutes]
        after = idx[tod[idx] >= 9 * 60 + 30 + minutes]
        if len(rng) == 0 or len(after) == 0 or tod[rng[0]] != 9 * 60 + 30:
            continue
        if rvol is not None and not (rvol.get(d, np.nan) >= min_rvol):
            continue
        hi, lo = h[rng].max(), l[rng].min()
        for j in after:
            if j > ends[j]:
                break
            up, dn = h[j] > hi, l[j] < lo
            if up and dn:
                break
            if up or dn:
                side = 1 if up else -1
                entry = max(o[j], hi) if up else min(o[j], lo)
                stop = lo if up else hi
                r, k = run_exit(o, h, l, c, j, ends[j], side, entry, stop, None)
                out.append({"time": b.index[j], "pos": j, "side": side, "ret": r, "risk": side * (entry - stop) / entry,
                            "bars": k - j + 1})
                break
    return pd.DataFrame(out, columns=["time", "pos", "side", "ret", "risk", "bars"])


def momentum_trades(b: pd.DataFrame) -> pd.DataFrame:
    """Gao et al.: sign of (yesterday's close -> 10:00) decides a 15:30 -> close trade."""
    g = b.groupby("day")
    close = g["close"].last()
    rows = []
    for d, x in g:
        if d == 0:
            continue
        at10 = x[x["tod"] < 10 * 60]
        late = x[x["tod"] >= 15 * 60 + 30]
        if at10.empty or late.empty or at10["tod"].iloc[0] != 9 * 60 + 30:
            continue
        first = at10["close"].iloc[-1] / close[d - 1] - 1
        if first == 0:
            continue
        side = 1 if first > 0 else -1
        entry, exit_ = late["open"].iloc[0], late["close"].iloc[-1]
        rows.append({"time": late.index[0], "pos": b.index.get_loc(late.index[0]), "side": side,
                     "ret": side * (exit_ / entry - 1), "risk": np.nan, "bars": len(late)})
    return pd.DataFrame(rows, columns=["time", "pos", "side", "ret", "risk", "bars"])


_CACHE: dict = {}


def placebo(b: pd.DataFrame, trades: pd.DataFrame, exit_kind: str, rng: np.random.Generator) -> float:
    """Average gross return of the same trades (side, time of day, exit rule, stop distance in %) moved to random
    other days: what the time of day and the market's drift give without the pattern."""
    if trades.empty:
        return np.nan
    key = (id(b), len(b))
    if key not in _CACHE:
        _CACHE.clear()
        _CACHE[key] = ([b[k].to_numpy(float) for k in ("open", "high", "low", "close")], day_ends(b),
                       {t: idx.to_numpy() for t, idx in pd.Series(np.arange(len(b))).groupby(b["tod"].to_numpy())},
                       b["tod"].to_numpy())
    (o, h, l, c), ends, by_tod, tod = _CACHE[key]
    out = []
    for t in trades.itertuples():
        pool = by_tod.get(tod[t.pos])
        j = int(rng.choice(pool))
        side, entry = t.side, o[j]
        if exit_kind == "30 min":
            r, _ = run_exit(o, h, l, c, j, ends[j], side, entry, None, None, hold=6)
        elif exit_kind == "close":
            r, _ = run_exit(o, h, l, c, j, ends[j], side, entry, None, None)
        else:
            risk = t.risk * entry
            stop = entry - side * risk
            target = entry + side * 2 * risk if exit_kind == "stop/2R" else None
            r, _ = run_exit(o, h, l, c, j, ends[j], side, entry, stop, target)
        out.append(r)
    return float(np.mean(out))


def summarise(t: pd.DataFrame, cost: float) -> dict:
    if t.empty:
        return {"n": 0}
    net = t["ret"] - 2 * cost
    first, second = net[t["time"] < SPLIT], net[t["time"] >= SPLIT]
    tt = net.mean() / net.std() * np.sqrt(len(net)) if len(net) > 1 and net.std() > 0 else np.nan
    return {"n": len(t), "per_year": len(t) / max(1e-9, (t["time"].max() - t["time"].min()).days / 365.25),
            "win": (net > 0).mean(), "gross": t["ret"].mean(), "net": net.mean(), "t": tt,
            "first": first.mean() if len(first) else np.nan, "second": second.mean() if len(second) else np.nan,
            "R": (t["ret"] / t["risk"]).mean() if t["risk"].notna().any() else np.nan}


def main() -> None:
    lines: list[str] = []

    def emit(s=""):
        print(s, flush=True)
        lines.append(s)

    emit("# Candle patterns on 5-minute bars - generated tables\n")
    emit("Alpaca SIP minute bars (split-adjusted) -> 5-minute candles; entry at the next candle's open; "
         "out by 15:55. 'Placebo' = the same side, time of day and exit on random other days (gross, average of "
         f"{PLACEBO_RUNS} runs): the bar to beat. 'Edge' = gross minus placebo. Net = after costs both ways. "
         f"Halves split at {SPLIT}. Returns are per trade, in %.\n")
    rng = np.random.default_rng(7)
    for sym in ("SPY", "NVDA"):
        m = alpaca_bars.minute_bars(sym)
        b = to_bars(m)
        cost = COSTS[sym]
        emit(f"## {sym}: {b.index[0].date()} to {b.index[-1].date()}, {b['day'].nunique():,} days, "
             f"{cost:.2%} cost each way\n")
        emit("| rule | side | trades | per year | win rate (net) | gross | placebo | edge | net | t (net) | "
             "2016-20 net | 2021-26 net | avg R |")
        emit("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
        tests = []
        sigs = candle_signals(b)
        for pname, sig in sigs.items():
            for ctx in ("plain", "reversal", "trend"):
                for ex in ("30 min", "stop/2R"):
                    t = candle_trades(b, with_context(sig, b, ctx), ex)
                    tests.append((f"{pname}, {ctx}, {ex}", t, ex))
        tests.append(("inside-bar breakout, stop/2R", inside_trades(b), "stop/2R"))
        for mins in (15, 30):
            tests.append((f"opening range {mins} min, to the close", orb_trades(b, mins), "stop/close"))
        tests.append(("intraday momentum (Gao et al.), 15:30 to close", momentum_trades(b), "close"))
        for name, t, ex in tests:
            for side, lab in ((1, "long"), (-1, "short")):
                ts = t[t["side"] == side].reset_index(drop=True)
                s = summarise(ts, cost)
                if not s["n"]:
                    emit(f"| {name} | {lab} | 0 | | | | | | | | | | |")
                    continue
                pl = np.mean([placebo(b, ts, ex if ex != "stop/close" else "stop", rng) for _ in range(PLACEBO_RUNS)])
                R = f"{s['R']:+.2f}" if s["R"] == s["R"] else ""
                emit(f"| {name} | {lab} | {s['n']:,} | {s['per_year']:.0f} | {s['win']:.0%} | {s['gross']:+.3%} | "
                     f"{pl:+.3%} | {s['gross'] - pl:+.3%} | {s['net']:+.3%} | {s['t']:.1f} | {s['first']:+.3%} | "
                     f"{s['second']:+.3%} | {R} |")
        emit("")

    # --- the one lead: opening-range breakouts. Check on stocks NOT picked with hindsight -------------------
    emit("## Opening-range breakout check: QQQ and the 10 largest US companies at the start of 2016\n")
    emit("NVDA was picked because it is huge NOW (it rose ~100x since 2016), which can flatter buying strength. These "
         "were the largest companies by market value at the end of 2015 (all still listed - survivors, but not "
         "picked for what happened next). Cost 0.02% each way. 'Busy opens' = only days when the opening range "
         "traded 2x+ its usual volume (Zarattini, Barbon & Aziz 2024's 'stocks in play' idea; known at 9:45/10:00).\n")
    emit("| stock | rule | side | trades | net | t | 2016-20 | 2021-26 | edge vs placebo |")
    emit("|---|---|---|---|---|---|---|---|---|")
    pooled: dict[tuple, list] = {}
    for sym in CHECK:
        b = to_bars(alpaca_bars.minute_bars(sym))
        for mins in (15, 30):
            for rv in (None, 2.0):
                t = orb_trades(b, mins, rv)
                for side, lab in ((1, "long"), (-1, "short")):
                    ts = t[t["side"] == side].reset_index(drop=True)
                    s = summarise(ts, 0.0002)
                    rule = f"ORB {mins} min" + (", busy opens" if rv else "")
                    if not s["n"]:
                        continue
                    pl = np.mean([placebo(b, ts, "stop", rng) for _ in range(5)])
                    pooled.setdefault((rule, lab), []).append(ts.assign(ret=ts["ret"] - 0.0004, sym=sym))
                    emit(f"| {sym} | {rule} | {lab} | {s['n']:,} | {s['net']:+.3%} | {s['t']:.1f} | {s['first']:+.3%} | "
                         f"{s['second']:+.3%} | {s['gross'] - pl:+.3%} |")
    emit("\n**Pooled across these 11 (equal weight per trade):**\n")
    emit("| rule | side | trades | net | t | 2016-20 | 2021-26 | stocks with net > 0 |")
    emit("|---|---|---|---|---|---|---|---|")
    for (rule, lab), parts in pooled.items():
        a = pd.concat(parts)
        net = a["ret"]
        t = net.mean() / net.std() * np.sqrt(len(net))
        pos = sum(p["ret"].mean() > 0 for p in parts)
        emit(f"| {rule} | {lab} | {len(a):,} | {net.mean():+.3%} | {t:.1f} | {net[a['time'] < SPLIT].mean():+.3%} | "
             f"{net[a['time'] >= SPLIT].mean():+.3%} | {pos} of {len(parts)} |")

    OUT.mkdir(exist_ok=True)
    (OUT / "candles.md").write_text("\n".join(lines) + "\n")
    print(f"\nwrote {OUT / 'candles.md'}")


if __name__ == "__main__":
    main()
