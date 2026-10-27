"""Candle patterns mixed with a moving-average trend filter and RSI, on DAILY bars: is there a method that works?

    python research/candle_rsi.py

Why daily: every intraday test (research/CANDLES.md, ICT.md, TJR.md) found patterns carry ~0 information and costs
decide the result. A daily bar moves ~10x more than a 5-minute one, so costs matter far less. RSI(2) dip-buying alone
is known to have faded on SPY (research/FINDINGS.md). The question here: does a reversal candle on top of a trend
filter and an oversold RSI help?

PROTOCOL - written before any result was seen; the rules below are not changed after looking.
Long only. Signal at day t's close; buy at t+1's open; sell at the open after the exit condition (no lookahead).
One position per symbol at a time.
  trend (SMA)     T0 none | T1 close above its 200-day SMA | T2 close > SMA200 and SMA50 > SMA200
  oversold (RSI)  R0 none | R1 RSI(2) < 10 | R2 RSI(14) < 30
  candle (day t)  C0 none
                  C1 hammer: lower wick >= 60% of the day's range, upper wick <= 15%
                  C2 bullish engulfing: yesterday red, today green, today's body covers yesterday's
                  C3 reversal close: a lower low than yesterday, then a close in the top 25% of the day's range
  exit            E1 the first close above the 5-day SMA (sell next open), at most 10 days
                  E2 hold 5 days (sell at the 5th open after entry)
= 72 rules. Costs: 0.02% each way for ETFs, 0.05% for stocks.
Markets and periods:
  ETFs     SPY, QQQ, IWM, DIA, EFA, EEM (market_data/, from 1993-2003). DEVELOPMENT: to 2012-12-31. HOLDOUT: 2013-2026.
  stocks   the 100 largest US companies at the latest quarter known at the time (SEC snapshots, filings public 45 days
           after the quarter), daily bars from Yahoo (data/backtest/daily_ohlcv.pkl; SURVIVORS ONLY - companies that
           later delisted are missing, which flatters dip-buying). DEVELOPMENT: 2014-05 to 2019-12. HOLDOUT: 2020-2026.
Selection: in DEVELOPMENT only, per market, the 3 rules with the highest t-stat (net per trade, at least 100 trades)
that use a candle (C1-C3). Each is then judged in HOLDOUT on:
  1. net per trade > 0 with t > 2,
  2. better per trade than the same trend + RSI + exit WITHOUT the candle (does the candle add anything?),
  3. as a strategy (T-bills on cash): Sharpe at least buy and hold's (ETFs) / the equal-weight universe's (stocks).
A rule chosen on ETFs is also run on the stocks' holdout, and vice versa (a second market).
Writes research/output/candle_rsi.md; findings in research/CANDLE_RSI.md.
"""

from __future__ import annotations

import itertools
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "research"))

from ai_desk.data import load_cash_rate, load_csv  # noqa: E402
from ai_desk.indicators import rsi, sma  # noqa: E402

OUT = Path(__file__).resolve().parent / "output"
CACHE = ROOT / "data" / "backtest"
ETFS = ["SPY", "QQQ", "IWM", "DIA", "EFA", "EEM"]
COST = {"etf": 0.0002, "stock": 0.0005}
PERIODS = {"etf": (("1993-01-01", "2012-12-31"), ("2013-01-01", "2026-10-19")),
           "stock": (("2014-05-15", "2019-12-31"), ("2020-01-01", "2026-10-20"))}
TRENDS, RSIS, CANDLES, EXITS = ("T0", "T1", "T2"), ("R0", "R1", "R2"), ("C0", "C1", "C2", "C3"), ("E1", "E2")
NAMES = {"T0": "no trend filter", "T1": "above SMA200", "T2": "above SMA200 & SMA50>SMA200",
         "R0": "no RSI", "R1": "RSI(2)<10", "R2": "RSI(14)<30",
         "C0": "no candle", "C1": "hammer", "C2": "bullish engulfing", "C3": "reversal close",
         "E1": "exit: close > SMA5", "E2": "exit: 5 days"}


# --- pure pieces (unit-tested) --------------------------------------------------------

def features(d: pd.DataFrame) -> pd.DataFrame:
    """Per day, each condition as a boolean, from data up to that day's close."""
    o, h, l, c = d["open"], d["high"], d["low"], d["close"]
    rng = (h - l).where(h > l)
    s50, s200 = sma(c, 50), sma(c, 200)
    up, lo = h - np.maximum(o, c), np.minimum(o, c) - l
    o1, c1 = o.shift(1), c.shift(1)
    f = pd.DataFrame(index=d.index)
    f["T0"] = True
    f["T1"] = c > s200
    f["T2"] = (c > s200) & (s50 > s200)
    f["R0"] = True
    f["R1"] = rsi(c, 2) < 10
    f["R2"] = rsi(c, 14) < 30
    f["C0"] = True
    f["C1"] = (lo >= 0.6 * rng) & (up <= 0.15 * rng)
    f["C2"] = (c1 < o1) & (c > o) & (o <= c1) & (c >= o1)
    f["C3"] = (l < l.shift(1)) & ((c - l) >= 0.75 * rng)
    f["sma5"] = sma(c, 5)
    return f                                   # comparisons with a missing value are False


def trades(d: pd.DataFrame, signal: np.ndarray, sma5: np.ndarray, exit_rule: str, max_days: int = 10) -> list[tuple]:
    """(entry position, exit position) pairs: buy at the open after a signal, sell at the open after the exit."""
    o, c = d["open"].to_numpy(float), d["close"].to_numpy(float)
    n, out = len(c), []
    sig = np.flatnonzero(signal)
    k = 0
    while k < len(sig):
        t = sig[k]
        e = t + 1
        if e >= n:
            break
        if exit_rule == "E2":
            x = e + 5
        else:
            x = None
            for j in range(e, min(e + max_days, n)):
                if c[j] > sma5[j]:
                    x = j + 1
                    break
            if x is None:
                x = e + max_days
        if x >= n or not (np.isfinite(o[e]) and np.isfinite(o[x])):
            break
        out.append((e, x))
        k = np.searchsorted(sig, x - 1, side="left")        # one position at a time: the next entry is at the exit's
                                                             # open at the earliest (a signal on the day before it)
    return out


def stats(r: np.ndarray, held: np.ndarray) -> dict:
    if len(r) == 0:
        return {"n": 0}
    t = r.mean() / r.std(ddof=1) * np.sqrt(len(r)) if len(r) > 1 and r.std() > 0 else np.nan
    return {"n": len(r), "net": r.mean(), "win": (r > 0).mean(), "t": t, "days": held.mean()}


# --- data ----------------------------------------------------------------------------

def etf_data() -> dict[str, pd.DataFrame]:
    return {s: load_csv(ROOT / "market_data" / f"{s}.csv") for s in ETFS}


def stock_data():
    import ict
    snaps = ict.snapshots()
    daily = pickle.loads((CACHE / "daily_ohlcv.pkl").read_bytes())
    keys = sorted(snaps)
    idx = daily["close"].index
    member = pd.DataFrame(False, index=idx, columns=daily["close"].columns)
    for a, k in enumerate(keys):
        start = k + pd.Timedelta(days=45)
        end = keys[a + 1] + pd.Timedelta(days=45) if a + 1 < len(keys) else idx[-1] + pd.Timedelta(days=1)
        names = [s for s in snaps[k]["market_cap"].nlargest(100).index if s in member.columns]
        member.loc[(idx >= start) & (idx < end), names] = True
    syms = member.columns[member.any()]
    frames = {s: pd.DataFrame({k: daily[k][s] for k in ("open", "high", "low", "close")}).astype(float).dropna()
              for s in syms}
    return frames, member[syms]


# --- running the grid -----------------------------------------------------------------

def run_rule(frames, feats, rule, cost, period, member=None):
    """All trades of one rule in one period: net returns, days held, and (symbol, entry, exit) dates."""
    T, R, C, E = rule
    rets, held, rows = [], [], []
    a, b = pd.Timestamp(period[0]), pd.Timestamp(period[1])
    for s, d in frames.items():
        f = feats[s]
        sig = (f[T] & f[R] & f[C]).to_numpy(bool)
        inside = (d.index >= a) & (d.index <= b)
        if member is not None:
            inside &= member[s].reindex(d.index, fill_value=False).to_numpy(bool)
        sig &= inside
        o = d["open"].to_numpy(float)
        for e, x in trades(d, sig, f["sma5"].to_numpy(float), E):
            if d.index[x] > b:
                continue
            rets.append(o[x] / o[e] - 1 - 2 * cost)
            held.append(x - e)
            rows.append((s, d.index[e], d.index[x]))
    return np.array(rets), np.array(held), rows


def strategy_curve(frames, rows, period, rf, cost: float, slots: int | None = None) -> pd.Series:
    """Daily open-to-open returns of holding the trades (one ETF: all in; stocks: `slots` equal slots), T-bills on
    the rest; each trade's round-trip cost is charged on its entry day."""
    a, b = pd.Timestamp(period[0]), pd.Timestamp(period[1])
    days = None
    for d in frames.values():
        ix = d.loc[a:b].index
        days = ix if days is None else days.union(ix)
    w = pd.DataFrame(0.0, index=days, columns=list(frames))
    entry = pd.DataFrame(0.0, index=days, columns=list(frames))
    for s, e, x in rows:
        w.loc[e:x - pd.Timedelta(days=1), s] += 1.0
        if e in entry.index:
            entry.at[e, s] = 1.0
    oo = pd.DataFrame({s: d["open"].shift(-1) / d["open"] - 1 for s, d in frames.items()}).reindex(days).fillna(0.0)
    if slots:
        w = w.clip(upper=1.0)
        w = w.div(np.maximum(w.sum(axis=1), slots), axis=0)
    else:
        w = w.clip(upper=1.0) / max(1, len(frames))
    cash = 1 - w.sum(axis=1)
    r = (w * oo).sum(axis=1) + cash * rf.reindex(days).ffill().fillna(0) / 252
    return r - (w * entry).sum(axis=1) * 2 * cost


def sharpe(r: pd.Series, rf: pd.Series) -> float:
    ex = r - rf.reindex(r.index).ffill().fillna(0) / 252
    return float(ex.mean() / ex.std() * np.sqrt(252)) if ex.std() > 0 else np.nan


def main() -> None:
    lines: list[str] = []

    def emit(s=""):
        print(s, flush=True)
        lines.append(s)

    rf = load_cash_rate(str(ROOT / "market_data" / "SPY.csv"))
    etf = etf_data()
    stk, member = stock_data()
    markets = {"etf": (etf, None), "stock": (stk, member)}
    feats = {m: {s: features(d) for s, d in fr.items()} for m, (fr, _) in markets.items()}
    rules = list(itertools.product(TRENDS, RSIS, CANDLES, EXITS))
    label = lambda r: ", ".join(NAMES[x] for x in r)                            # noqa: E731

    emit("# Candles + SMA trend + RSI on daily bars - generated tables\n")
    emit("Protocol fixed in research/candle_rsi.py before running. Long only; signal at the close, buy next open, "
         "sell at the open after the exit. Per-trade returns are after costs (ETFs 0.02%, stocks 0.05% each way). "
         "Stocks: point-in-time top 100, **survivors-only prices**.\n")
    picked: dict[str, list] = {}
    dev_tables = {}
    for m, (fr, mem) in markets.items():
        dev, hold = PERIODS[m]
        res = []
        for rule in rules:
            r, h, _ = run_rule(fr, feats[m], rule, COST[m], dev, mem)
            res.append((rule, stats(r, h)))
        dev_tables[m] = res
        cands = [x for x in res if x[0][2] != "C0" and x[1]["n"] >= 100]
        picked[m] = [x[0] for x in sorted(cands, key=lambda x: -(x[1]["t"] if x[1]["t"] == x[1]["t"] else -9))[:3]]
        emit(f"## {m.upper()}S - development period {dev[0]} to {dev[1]}: all 72 rules\n")
        emit("| trend | RSI | candle | exit | trades | net/trade | win | t | days held |")
        emit("|---|---|---|---|---|---|---|---|---|")
        for rule, s in sorted(res, key=lambda x: -(x[1].get("t") if x[1].get("t") == x[1].get("t") else -99)):
            if not s["n"]:
                emit(f"| {NAMES[rule[0]]} | {NAMES[rule[1]]} | {NAMES[rule[2]]} | {NAMES[rule[3]]} | 0 | | | | |")
                continue
            emit(f"| {NAMES[rule[0]]} | {NAMES[rule[1]]} | {NAMES[rule[2]]} | {NAMES[rule[3]]} | {s['n']:,} | "
                 f"{s['net']:+.3%} | {s['win']:.0%} | {s['t']:.1f} | {s['days']:.1f} |")
        emit("\nPicked for the holdout (best t-stat with a candle, 100+ trades): "
             + "; ".join(label(r) for r in picked[m]) + "\n")

    emit("## HOLDOUT - the picked rules on data they never saw\n")
    emit("| picked on | tested on | rule | trades | net/trade | win | t | same without the candle | strategy Sharpe | "
         "benchmark Sharpe | passes 1/2/3 |")
    emit("|---|---|---|---|---|---|---|---|---|---|---|")
    for src in ("etf", "stock"):
        for rule in picked[src]:
            for m, (fr, mem) in markets.items():
                hold = PERIODS[m][1]
                r, h, rows = run_rule(fr, feats[m], rule, COST[m], hold, mem)
                s = stats(r, h)
                base_rule = (rule[0], rule[1], "C0", rule[3])
                rb, hb, _ = run_rule(fr, feats[m], base_rule, COST[m], hold, mem)
                sb = stats(rb, hb)
                if not s["n"]:
                    emit(f"| {src} | {m} | {label(rule)} | 0 | | | | | | | |")
                    continue
                if m == "etf":
                    # one ETF strategy per fund, averaged; benchmark = buy and hold of each, averaged
                    shs, bhs = [], []
                    for sym, d in fr.items():
                        rr = strategy_curve({sym: d}, [x for x in rows if x[0] == sym], hold, rf, COST[m])
                        shs.append(sharpe(rr, rf))
                        bh = (d["open"].shift(-1) / d["open"] - 1).loc[hold[0]:hold[1]].dropna()
                        bhs.append(sharpe(bh, rf))
                    sh, bench = np.nanmean(shs), np.nanmean(bhs)
                else:
                    rr = strategy_curve(fr, rows, hold, rf, COST[m], slots=10)
                    sh = sharpe(rr, rf)
                    ew = pd.DataFrame({sy: d["open"].shift(-1) / d["open"] - 1 for sy, d in fr.items()})
                    ew = ew.where(mem.reindex(ew.index).fillna(False)).loc[hold[0]:hold[1]].mean(axis=1).dropna()
                    bench = sharpe(ew, rf)
                ok = [s["net"] > 0 and s["t"] > 2, sb["n"] > 0 and s["net"] > sb["net"], sh >= bench]
                emit(f"| {src} | {m} | {label(rule)} | {s['n']:,} | {s['net']:+.3%} | {s['win']:.0%} | {s['t']:.1f} | "
                     f"{sb.get('net', np.nan):+.3%} ({sb.get('n', 0):,}) | {sh:.2f} | {bench:.2f} | "
                     + "/".join("yes" if x else "no" for x in ok) + " |")

    # context for the write-up: does adding any candle help, rule by rule, in the holdout?
    emit("\n## Does a candle add anything? Holdout, every trend x RSI x exit, candle vs no candle (net per trade)\n")
    emit("| market | trend | RSI | exit | no candle | hammer | bullish engulfing | reversal close |")
    emit("|---|---|---|---|---|---|---|---|")
    for m, (fr, mem) in markets.items():
        hold = PERIODS[m][1]
        for T, R, E in itertools.product(TRENDS, RSIS, EXITS):
            cells = []
            for C in CANDLES:
                r, h, _ = run_rule(fr, feats[m], (T, R, C, E), COST[m], hold, mem)
                s = stats(r, h)
                cells.append(f"{s['net']:+.3%} ({s['n']:,})" if s["n"] else "-")
            emit(f"| {m} | {NAMES[T]} | {NAMES[R]} | {NAMES[E]} | " + " | ".join(cells) + " |")

    OUT.mkdir(exist_ok=True)
    (OUT / "candle_rsi.md").write_text("\n".join(lines) + "\n")
    print(f"\nwrote {OUT / 'candle_rsi.md'}")


if __name__ == "__main__":
    main()
