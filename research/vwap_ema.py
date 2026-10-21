"""Two popular intraday strategies, as fixed rules: the EMA9/VWAP crossover, and Trend + Momentum + Confirmation.

    python research/vwap_ema.py      (uses the cached intraday bars from research/ict.py and research/orb.py)

A. EMA9 / VWAP crossover
   long when the 9-bar EMA crosses above the day's VWAP (volume-weighted average price, reset each
   morning); out when it crosses back below, or at the close. Shorts are the mirror image. Tested
   both sides and long only. No signal in the first two bars (VWAP is meaningless that early).
B. Trend + Momentum + Confirmation (long only)
   buy setup at a bar's close, all four true:
     20-bar EMA above the 50-bar EMA (trend)
     price above VWAP (institutional reference)
     the bar's volume at least 1.5x the average of the previous 20 bars
     the close breaks above the previous day's high or the opening-range high (first 15 minutes),
     for the first time that day
   entry    the next bar's open (or, variant: the "first pullback" - a limit order back at the
            broken level, filled within the next 6 bars)
   stop     the recent swing low (lowest low of the last 5 bars) or the 20 EMA, whichever is lower
   target   2x the risk (variant: 3x); otherwise out at the close
Every decision is at a bar's close and fills at a later bar (no lookahead). If a bar reaches both
the stop and the target, the stop is assumed ("worst case"); a "best case" column only checks the
stop from the bar after the entry. Controls: the same number of trades on random bars of the same
stocks and days, with the same stop and target rules.

Data: Yahoo regular-hours bars for the 100-150 largest US companies (point-in-time union):
  5-minute bars (~60 days), 1-minute bars (~30 days), 3-minute bars (built from the 1-minute ones; Yahoo has no
  3-minute interval), hourly bars (~3 years; coarse for VWAP/EMAs).
Costs 0.03% each way (large-cap spread), stress 0.10%. Writes research/output/vwap_ema.md; findings in
research/VWAP_EMA.md.
"""

from __future__ import annotations

import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research"))

import ict  # noqa: E402

CACHE = ROOT / "data" / "backtest"
OUT = Path(__file__).resolve().parent / "output"
COST = 0.0003


# --- pure pieces (unit-tested) --------------------------------------------------------

def ema(x: np.ndarray, n: int) -> np.ndarray:
    a = 2 / (n + 1)
    out = np.empty_like(x, dtype=float)
    out[0] = x[0]
    for i in range(1, len(x)):
        out[i] = a * x[i] + (1 - a) * out[i - 1] if np.isfinite(x[i]) else out[i - 1]
    return out


def vwap(h: np.ndarray, lo: np.ndarray, c: np.ndarray, v: np.ndarray, day_start: np.ndarray) -> np.ndarray:
    """Session VWAP from typical prices, reset at each True in day_start."""
    tp = (h + lo + c) / 3
    out = np.empty(len(c))
    pv = vol = 0.0
    for i in range(len(c)):
        if day_start[i]:
            pv = vol = 0.0
        if np.isfinite(tp[i]) and np.isfinite(v[i]) and v[i] > 0:
            pv += tp[i] * v[i]
            vol += v[i]
        out[i] = pv / vol if vol > 0 else tp[i]
    return out


def crossover_trades(o, h, lo, c, e9, vw, day_id, long_only=False, min_bar=2) -> list[dict]:
    """A: enter at the open after EMA9 crosses VWAP, exit at the open after it crosses back, or the day's last close."""
    trades = []
    n = len(c)
    pos = 0
    entry = entry_i = None
    bar_in_day = 0
    for i in range(1, n):
        new_day = day_id[i] != day_id[i - 1]
        bar_in_day = 0 if new_day else bar_in_day + 1
        last_of_day = i == n - 1 or day_id[i + 1] != day_id[i]
        if pos and new_day:                                        # never hold overnight (closed below)
            pos = 0
        above, was = e9[i] > vw[i], e9[i - 1] > vw[i - 1]
        if pos and ((pos > 0 and not above) or (pos < 0 and above)) and not last_of_day:
            px = o[i + 1]
            trades.append(_t(pos, entry, px, entry_i, i + 1, "cross back"))
            pos = 0
        elif pos and last_of_day:
            trades.append(_t(pos, entry, c[i], entry_i, i, "close"))
            pos = 0
            continue
        if not pos and not new_day and bar_in_day >= min_bar and not last_of_day:
            if above and not was:
                pos, entry, entry_i = 1, o[i + 1], i + 1
            elif not above and was and not long_only:
                pos, entry, entry_i = -1, o[i + 1], i + 1
    return trades


def _t(side, entry, exit_, i, j, why) -> dict:
    return {"side": side, "entry": float(entry), "exit": float(exit_), "ret": float(side * (exit_ / entry - 1)),
            "bar_in": int(i), "bar_out": int(j), "why": why}


def tmc_signal(c, v, e20, e50, vw, pdh, orh, k, avg_vol) -> bool:
    """B's setup at bar k's close (all inputs known by then)."""
    level = min(pdh, orh) if np.isfinite(pdh) and np.isfinite(orh) else (pdh if np.isfinite(pdh) else orh)
    return bool(e20[k] > e50[k] and c[k] > vw[k] and np.isfinite(avg_vol) and v[k] >= 1.5 * avg_vol
                and np.isfinite(level) and c[k] > level and c[k - 1] <= level)


def resample_bars(b: dict[str, pd.DataFrame], rule: str) -> dict[str, pd.DataFrame]:
    """Combine bars into longer ones within each day (9:30, 9:33, ... for "3min"); empty bins dropped."""
    agg = {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    out = {k: b[k].resample(rule, label="left", closed="left").agg(f) for k, f in agg.items()}
    keep = out["close"].notna().any(axis=1)
    out = {k: v.loc[keep] for k, v in out.items()}
    out["volume"] = out["volume"].where(out["close"].notna())
    return out


# --- the experiment ------------------------------------------------------------------

def run_tmc(o, h, lo, c, v, e20, e50, vw, day_id, rr=2.0, pullback=False, use_volume=True, optimistic=False,
            or_bars=3, rng=None) -> list[dict]:
    """B on one stock's bars. rng: control mode - random bars instead of the setup (same count per day)."""
    trades = []
    days = np.unique(day_id)
    prev_high = np.nan
    for d in days:
        idx = np.flatnonzero(day_id == d)
        if len(idx) < or_bars + 3:
            prev_high = np.nanmax(h[idx]) if len(idx) else prev_high
            continue
        orh = np.nanmax(h[idx[:or_bars]])
        cand = []
        for k in idx[or_bars:-1]:
            avg_v = np.nanmean(v[max(0, k - 20):k]) if k >= 5 else np.nan
            vol_ok = use_volume
            if tmc_signal(c, v if vol_ok else np.full_like(v, np.inf), e20, e50, vw, prev_high, orh, k,
                          avg_v if vol_ok else 0.0):
                cand.append(k)
                break                                               # first setup of the day only
        if rng is not None:
            n_take = len(cand)
            cand = list(rng.choice(idx[or_bars:-2], size=n_take, replace=False)) if n_take else []
        for k in cand:
            last = idx[-1]
            swing = np.nanmin(lo[max(idx[0], k - 4):k + 1])
            stop = min(swing, e20[k])
            seg = slice(k + 1, last + 1)
            oo, hh, ll, cc = o[seg], h[seg], lo[seg], c[seg]
            if pullback:
                level = c[k] if rng is not None else (min(prev_high, orh) if np.isfinite(prev_high) else orh)
                if level <= stop:
                    continue
                tr = ict.run_trade(oo, hh, ll, cc, 0, 1, level, stop, level + rr * (level - stop), limit=True,
                                   fill_by=min(5, len(cc) - 1))
            else:
                entry = oo[0]
                if not np.isfinite(entry) or entry <= stop:
                    continue
                start = 1 if optimistic else 0
                if optimistic and len(cc) < 2:
                    continue
                tr = ict.run_trade(oo, hh, ll, cc, start, 1, entry, stop, entry + rr * (entry - stop), limit=False)
            if tr:
                tr["day"] = d
                trades.append(tr)
        prev_high = np.nanmax(h[idx])
    return trades


def summarize(t: pd.DataFrame) -> dict:
    if t.empty:
        return {"trades": 0}
    net = t["ret"] - 2 * COST
    net10 = t["ret"] - 2 * 0.001
    return {"trades": len(t), "days": t["day"].nunique() if "day" in t else np.nan, "win": (net > 0).mean(),
            "gross": t["ret"].mean(), "net": net.mean(), "net10": net10.mean(),
            "t": net.mean() / (net.std() / np.sqrt(len(net))) if net.std() > 0 else np.nan,
            "R": t["R"].mean() if "R" in t else np.nan}


def main() -> None:
    lines: list[str] = []

    def emit(x=""):
        print(x, flush=True)
        lines.append(x)

    emit("# EMA9/VWAP crossover and Trend + Momentum + Confirmation - generated tables\n")
    emit("Yahoo regular-hours bars, the 100-150 largest US companies. Costs 0.03% each way (stress 0.10%). "
         "'per trade' = average return per trade; R = multiples of the risk (strategy B).\n")
    only = sys.argv[1:]                      # e.g. `python research/vwap_ema.py 3m` runs one bar size
    sets = [("5-minute bars (~60 days)", "intraday_5m.pkl", 3, None), ("1-minute bars (~30 days)", "intraday_1m.pkl", 15, None),
            ("3-minute bars (~30 days, built from 1-minute)", "intraday_1m.pkl", 5, "3min"),
            ("Hourly bars (~3 years)", "intraday_1h.pkl", 1, None)]
    if only:
        keys = {"5m": 0, "1m": 1, "3m": 2, "1h": 3}
        sets = [sets[keys[k]] for k in only]
    rng = np.random.default_rng(5)
    for label, fname, or_bars, rule in sets:
        path = CACHE / fname
        if not path.exists():
            emit(f"\n(skipped {label}: {fname} not cached)")
            continue
        b = pickle.loads(path.read_bytes())
        if rule:
            b = resample_bars(b, rule)
        O, H, L, C, V = (b[k].astype(float) for k in ("open", "high", "low", "close", "volume"))
        day_id = C.index.normalize().to_numpy()
        day_start = np.r_[True, day_id[1:] != day_id[:-1]]
        res = {k: [] for k in ("A both sides", "A long only", "B base (2R)", "B 3R target", "B without the volume rule",
                               "B first pullback entry", "B best case (stop from the next bar)", "B control: random bars")}
        for s in C.columns:
            o, h, lo, c, v = (x[s].to_numpy() for x in (O, H, L, C, V))
            ok = np.isfinite(c) & np.isfinite(o)
            if ok.sum() < 200:
                continue
            o, h, lo, c, v, dd, ds = o[ok], h[ok], lo[ok], c[ok], np.nan_to_num(v[ok]), day_id[ok], day_start[ok]
            vw = vwap(h, lo, c, v, ds)
            e9, e20, e50 = ema(c, 9), ema(c, 20), ema(c, 50)
            res["A both sides"] += crossover_trades(o, h, lo, c, e9, vw, dd)
            res["A long only"] += crossover_trades(o, h, lo, c, e9, vw, dd, long_only=True)
            res["B base (2R)"] += run_tmc(o, h, lo, c, v, e20, e50, vw, dd, or_bars=or_bars)
            res["B 3R target"] += run_tmc(o, h, lo, c, v, e20, e50, vw, dd, rr=3.0, or_bars=or_bars)
            res["B without the volume rule"] += run_tmc(o, h, lo, c, v, e20, e50, vw, dd, use_volume=False, or_bars=or_bars)
            res["B first pullback entry"] += run_tmc(o, h, lo, c, v, e20, e50, vw, dd, pullback=True, or_bars=or_bars)
            res["B best case (stop from the next bar)"] += run_tmc(o, h, lo, c, v, e20, e50, vw, dd, optimistic=True,
                                                                   or_bars=or_bars)
            res["B control: random bars"] += run_tmc(o, h, lo, c, v, e20, e50, vw, dd, or_bars=or_bars, rng=rng)
        span = f"{pd.Timestamp(day_id[0]).date()} to {pd.Timestamp(day_id[-1]).date()}"
        emit(f"\n## {label}, {span}\n")
        emit("| rules | trades | win rate | per trade before costs | per trade after 0.03% | after 0.10% | t-stat | avg R |")
        emit("|---|---|---|---|---|---|---|---|")
        for k, tr in res.items():
            s = summarize(pd.DataFrame(tr))
            if not s["trades"]:
                emit(f"| {k} | 0 | | | | | | |")
                continue
            r = f"{s['R']:+.2f}" if np.isfinite(s["R"]) else ""
            emit(f"| {k} | {s['trades']} | {s['win']:.0%} | {s['gross']:+.3%} | {s['net']:+.3%} | {s['net10']:+.3%} | "
                 f"{s['t']:.1f} | {r} |")
        a = pd.DataFrame(res["A both sides"])
        if len(a):
            emit(f"\nA: {len(a) / max(1, len(np.unique(day_id))) / C.shape[1]:.1f} trades per stock per day; "
                 f"how they ended: {', '.join(f'{w} {n}' for w, n in a['why'].value_counts().items())}.")
        bt = pd.DataFrame(res["B base (2R)"])
        if len(bt):
            emit(f"B: how trades ended: {', '.join(f'{w} {n}' for w, n in bt['why'].value_counts().items())}.")
            if label.startswith("Hourly"):
                m = bt.assign(q=pd.to_datetime(bt["day"]).dt.to_period("Q"))
                g = m.groupby("q")["ret"].mean() - 2 * COST
                emit("B by quarter, per trade after costs: " + ", ".join(f"{k} {v:+.2%}" for k, v in g.items()) + ".")

    OUT.mkdir(exist_ok=True)
    name = "vwap_ema.md" if not only else f"vwap_ema_{'_'.join(only)}.md"
    (OUT / name).write_text("\n".join(lines) + "\n")
    print(f"\nwrote {OUT / name}")


if __name__ == "__main__":
    main()
