"""Day trading SPY (and its family) or commodity ETFs: published intraday patterns, backtested on 10 years of minute bars.

    python research/intraday_etf.py      (needs research/alpaca_bars.py minute caches: SPY QQQ IWM DIA GLD SLV USO UNG)

The rules, all fixed before running (each trades at most once a day per side, flat by the close):
  momentum_10am   Gao, Han, Li & Zhou (2018): the move from yesterday's close to 10:00 decides the last half hour -
                  buy (or short) at 15:30, out at 16:00
  momentum_330pm  Baltussen, Da & Soebhag (2021, dealers' gamma hedging): the move from yesterday's close to 15:30
                  decides 15:30 -> 16:00
  gap_fade        a 0.2-1.0% gap at the open is traded back toward yesterday's close from 9:31; out at that close
                  (a limit) or at 12:00
  first_hour_fade a first hour (9:30-10:30) that moved 0.5% or more is faded from 10:30 to the close
  vwap_snapback   from 10:30 to 15:00, a stretch from VWAP of a quarter of the usual daily range (median of the last 20
                  days, through yesterday) is traded back toward VWAP; out when a minute closes back at VWAP, or 15:56
  orb_long        the NVIDIA rule: 15-minute range, buy above its high, stop at its low, out at the close
  orb_both        the same, plus the mirror short below the range low
  long_day / short_day   buy (short) at the open, out at the close - the time-of-day baseline (gold is said to
                  fall in New York hours)
Costs each way: SPY QQQ IWM DIA GLD 0.01%, SLV 0.02%, USO 0.03%, UNG 0.05% (ETF spreads at our size), and 3x as a
stress. A bar touching both a stop and a target counts as stopped. Fills at the minute's close (open for the open).
A rule PASSES only if, on its lead ETF (SPY for the index family, GLD for commodities): average net > 0 in BOTH
2016-20 and 2021-26 and t >= 2; AND the rest of its family pooled is positive in both halves. Sharpe = the daily P&L
of trading 100% of capital (0 on days without a trade; cash would earn T-bills overnight anyway). For comparison the
NVIDIA opening buy (research/NVDA_ORB_DIVE.md): 49% wins, +0.125% a trade. ETFs move less than NVDA, so compare
win rate and Sharpe, not % per trade. Survivors: all these ETFs still trade. Writes research/output/intraday_etf.md.
"""

from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "research"))

import alpaca_bars  # noqa: E402

OUT = Path(__file__).resolve().parent / "output"
SPLIT = pd.Timestamp("2021-01-01")
FAMILIES = {"index ETFs": ["SPY", "QQQ", "IWM", "DIA"], "commodity ETFs": ["GLD", "SLV", "USO", "UNG"]}
COSTS = {"SPY": 0.0001, "QQQ": 0.0001, "IWM": 0.0001, "DIA": 0.0001, "GLD": 0.0001, "SLV": 0.0002, "USO": 0.0003,
         "UNG": 0.0005}
RULES = ["momentum_10am", "momentum_330pm", "gap_fade", "first_hour_fade", "vwap_snapback", "orb_long", "orb_both",
         "long_day", "short_day"]
N = 390                                         # minutes in a full session; column k = the minute starting 9:30 + k


def grid(sym: str) -> dict:
    """Minute bars as day x minute matrices (full sessions only), missing minutes filled from the last close."""
    m = alpaca_bars.minute_bars(sym)
    k = (m.index.hour * 60 + m.index.minute) - (9 * 60 + 30)
    m = m[(k >= 0) & (k < N)]
    k = k[(k >= 0) & (k < N)]
    days = m.index.normalize()
    out = {}
    for f in ("open", "high", "low", "close", "volume"):
        out[f] = pd.DataFrame({"d": days, "k": k, "v": m[f].to_numpy()}).pivot_table(index="d", columns="k", values="v")
        out[f] = out[f].reindex(columns=range(N))
    c = out["close"].ffill(axis=1)
    full = c[N - 1].notna() & out["close"][N - 1].notna() & out["open"][0].notna()
    g = {f: (c if f == "close" else out[f])[full] for f in out}
    g["close"] = c[full]
    for f in ("open", "high", "low"):
        g[f] = g[f].fillna(g["close"])
    g["volume"] = g["volume"].fillna(0.0)
    return {f: v.to_numpy(float) for f, v in g.items()} | {"days": g["close"].index}


def trades(g: dict, rule: str, cost: float) -> pd.DataFrame:
    """Pure (given the grid): one row per trade - day, direction, net return after `cost` each way."""
    o, h, l, c, v = g["open"], g["high"], g["low"], g["close"], g["volume"]
    days = g["days"]
    prev = np.r_[np.nan, c[:-1, N - 1]]                      # yesterday's close (previous full session)
    rows = []

    def add(i, d, entry, exit_):
        if np.isfinite(entry) and np.isfinite(exit_) and entry > 0:
            rows.append((days[i], d, d * (exit_ / entry - 1) - 2 * cost))

    rng = (h.max(axis=1) / l.min(axis=1) - 1)
    med_rng = pd.Series(rng).rolling(20).median().shift(1).to_numpy()
    for i in range(len(days)):
        if rule in ("momentum_10am", "momentum_330pm"):
            ref = c[i, 29] if rule == "momentum_10am" else c[i, 359]
            if np.isfinite(prev[i]) and ref != prev[i]:
                add(i, np.sign(ref / prev[i] - 1), c[i, 359], c[i, N - 1])
        elif rule == "gap_fade":
            if not np.isfinite(prev[i]):
                continue
            gap = o[i, 0] / prev[i] - 1
            if not 0.002 <= abs(gap) <= 0.01:
                continue
            d = -np.sign(gap)
            entry = c[i, 0]
            if (d > 0 and entry >= prev[i]) or (d < 0 and entry <= prev[i]):
                continue                                     # filled within the first minute: no trade
            hit = np.nonzero((h[i, 1:150] >= prev[i]) if d > 0 else (l[i, 1:150] <= prev[i]))[0]
            add(i, d, entry, prev[i] if len(hit) else c[i, 149])
        elif rule == "first_hour_fade":
            r1 = c[i, 59] / o[i, 0] - 1
            if abs(r1) >= 0.005:
                add(i, -np.sign(r1), c[i, 59], c[i, N - 1])
        elif rule == "vwap_snapback":
            if not np.isfinite(med_rng[i]):
                continue
            tp = (h[i] + l[i] + c[i]) / 3
            vw = np.cumsum(tp * v[i]) / np.maximum(np.cumsum(v[i]), 1e-9)
            dev = c[i] / vw - 1
            thr = 0.25 * med_rng[i]
            for d in (1, -1):
                sig = np.nonzero((dev[60:330] < -thr) if d > 0 else (dev[60:330] > thr))[0]
                if not len(sig):
                    continue
                j = 60 + sig[0]
                back = np.nonzero((c[i, j + 1:386] >= vw[j + 1:386]) if d > 0 else (c[i, j + 1:386] <= vw[j + 1:386]))[0]
                add(i, d, c[i, j], c[i, j + 1 + back[0]] if len(back) else c[i, 385])
        elif rule in ("orb_long", "orb_both"):
            hi, lo = h[i, :15].max(), l[i, :15].min()
            for d in ((1,) if rule == "orb_long" else (1, -1)):
                brk = np.nonzero((h[i, 15:385] > hi) if d > 0 else (l[i, 15:385] < lo))[0]
                if not len(brk):
                    continue
                j = 15 + brk[0]
                entry = max(o[i, j], hi) if d > 0 else min(o[i, j], lo)
                stop = lo if d > 0 else hi
                stops = np.nonzero((l[i, j:] <= stop) if d > 0 else (h[i, j:] >= stop))[0]
                if len(stops):
                    k = j + stops[0]
                    px = stop if k == j else (min(o[i, k], stop) if d > 0 else max(o[i, k], stop))
                else:
                    px = c[i, N - 1]
                add(i, d, entry, px)
        elif rule == "long_day":
            add(i, 1, o[i, 0], c[i, N - 1])
        elif rule == "short_day":
            add(i, -1, o[i, 0], c[i, N - 1])
    return pd.DataFrame(rows, columns=["date", "dir", "net"])


def stat(t: pd.DataFrame, n_days: int) -> dict:
    if t.empty:
        return {"n": 0, "per_yr": 0, "win": np.nan, "net": np.nan, "t": np.nan, "a": np.nan, "b": np.nan, "sharpe": np.nan}
    r = t["net"]
    daily = t.groupby("date")["net"].sum()
    full = np.zeros(n_days)
    full[: len(daily)] = daily.to_numpy()                    # zero days: no trade (order doesn't matter for Sharpe)
    sh = full.mean() / full.std() * np.sqrt(252) if full.std() > 0 else np.nan
    return {"n": len(r), "per_yr": len(r) / (n_days / 252), "win": (r > 0).mean(), "net": r.mean(),
            "t": r.mean() / r.std() * np.sqrt(len(r)) if r.std() > 0 else np.nan,
            "a": r[t["date"] < SPLIT].mean(), "b": r[t["date"] >= SPLIT].mean(), "sharpe": sh}


def main() -> None:
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    lines: list[str] = []

    def emit(s=""):
        print(s, flush=True)
        lines.append(s)

    grids = {s: grid(s) for fam in FAMILIES.values() for s in fam}
    emit("# Day trading SPY or commodity ETFs - generated tables\n")
    emit("Alpaca minute bars 2016 to " + str(max(g["days"][-1] for g in grids.values()).date()) + ". Net = after costs "
         "(SPY/QQQ/IWM/DIA/GLD 0.01%, SLV 0.02%, USO 0.03%, UNG 0.05% each way). Sharpe = trading 100% of capital, "
         "0 on days without a trade. NVIDIA opening buy for comparison: 49% wins, +0.125% a trade.\n")
    verdicts = []
    for fam, syms in FAMILIES.items():
        emit(f"## {fam}\n")
        emit("| rule | ETF | trades/yr | win rate | avg before costs | avg net | t | 2016-20 | 2021-26 | Sharpe | avg at 3x costs |")
        emit("|---|---|---|---|---|---|---|---|---|---|---|")
        lead, rest = syms[0], syms[1:]
        for rule in RULES:
            per = {}
            for s in syms:
                g = grids[s]
                tr = trades(g, rule, COSTS[s])
                st = stat(tr, len(g["days"]))
                st3 = trades(g, rule, 3 * COSTS[s])["net"].mean()
                gross = trades(g, rule, 0.0)["net"].mean()
                per[s] = (tr, st)
                emit(f"| {rule} | {s} | {st['per_yr']:.0f} | {st['win']:.0%} | {gross:+.3%} | {st['net']:+.3%} | {st['t']:.1f} | "
                     f"{st['a']:+.3%} | {st['b']:+.3%} | {st['sharpe']:.2f} | {st3:+.3%} |")
            pooled = pd.concat([per[s][0] for s in rest], ignore_index=True)
            pa = pooled.loc[pooled["date"] < SPLIT, "net"].mean()
            pb = pooled.loc[pooled["date"] >= SPLIT, "net"].mean()
            ls = per[lead][1]
            ok = ls["a"] > 0 and ls["b"] > 0 and ls["t"] >= 2 and pa > 0 and pb > 0
            verdicts.append((fam, rule, lead, ls, pa, pb, ok))
        emit("")
    emit("## Verdicts (pass = lead ETF positive in both halves with t >= 2, AND the rest of the family positive in both)\n")
    emit("| family | rule | lead | win rate | avg net | t | Sharpe | rest 2016-20 | rest 2021-26 | passes |")
    emit("|---|---|---|---|---|---|---|---|---|---|")
    for fam, rule, lead, ls, pa, pb, ok in verdicts:
        emit(f"| {fam} | {rule} | {lead} | {ls['win']:.0%} | {ls['net']:+.3%} | {ls['t']:.1f} | {ls['sharpe']:.2f} | "
             f"{pa:+.3%} | {pb:+.3%} | {'**yes**' if ok else 'no'} |")
    OUT.mkdir(exist_ok=True)
    (OUT / "intraday_etf.md").write_text("\n".join(lines) + "\n")
    print(f"\nwrote {OUT / 'intraday_etf.md'}")


if __name__ == "__main__":
    main()
