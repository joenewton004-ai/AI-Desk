"""Deep dive into the NVIDIA opening-range buy: what happened on the shadow days, why losers lost, and whether any
pattern raises the win rate without fooling ourselves.

    python research/nvda_orb_dive.py      (uses research/alpaca_bars.py's 1-minute caches, NVDA + QQQ to 2026-10-28)

Part 1 - the shadow trades (journal/nvda_orb.jsonl): each trade's path in R (risk = entry - stop): how far it went our
way (MFE) and against us (MAE) before the exit, and what it did after.
Part 2 - the same rule over 2016-2026 on NVDA: winners vs losers by what was known at entry (gap, previous day,
range width vs its own 20-day median, entry time, QQQ already through its own range, weekday) and where trades peaked.
Part 3 - rule changes taken from parts 1-2, fixed before running, judged like research/ORB_VARIANTS.md: a change
counts only if it beats the live rule's average net per trade on NVDA AND on the 11 others pooled (QQQ + the 10
largest US companies of 2016), in BOTH 2016-20 and 2021-26. Win rate is reported but isn't the test: a rule that wins
more often by taking smaller profits can still lose more money.
The rule matches ai_desk/nvda_orb.py (15-minute range on 5-minute bars, buy-stop at the range high, stop at the range
low, a bar touching both counts as stopped, out at the 15:55 bar's close). Costs 0.02% each way. Survivors-only names.
Added after part 1 showed a quiet stock (fixed before its result was seen): trade only when the stock's last 20
daily high-low ranges (median, through yesterday) are wider than their own past year's median.
Writes research/output/nvda_orb_dive.md.
"""

from __future__ import annotations

import json
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
COST = 0.0002
END = "2026-10-28"
SPLIT = pd.Timestamp("2021-01-01")
OTHERS = ["QQQ", "AAPL", "GOOGL", "MSFT", "BRK.B", "XOM", "AMZN", "META", "GE", "JNJ", "WFC"]
RANGE_END, LAST_BAR = 9 * 60 + 45, 15 * 60 + 55


def five_min(sym: str) -> pd.DataFrame:
    m = alpaca_bars.regular_session(alpaca_bars.bars(sym, end=END))
    g = m.resample("5min", label="left", closed="left")
    b = pd.DataFrame({"open": g["open"].first(), "high": g["high"].max(), "low": g["low"].min(),
                      "close": g["close"].last(), "volume": g["volume"].sum()}).dropna()
    return b


def days(b: pd.DataFrame):
    """(day, arrays) per trading day with a complete opening range."""
    t = b.index.hour * 60 + b.index.minute
    for d, idx in pd.Series(np.arange(len(b)), index=b.index).groupby(b.index.normalize()):
        ii = idx.to_numpy()
        tt = t[ii]
        if len(ii) < 10 or tt[0] != 9 * 60 + 30 or (tt < RANGE_END).sum() != 3:
            continue
        yield d, ii, tt


def simulate(b: pd.DataFrame, qqq: pd.DataFrame | None = None, stop: str = "low", target_r: float | None = None,
             back_inside: bool = False, breakeven_r: float | None = None, last_entry: int = LAST_BAR,
             entry_by: int | None = None) -> pd.DataFrame:
    """Every trade of the rule on one stock, with what was known at entry. Pure given the bars."""
    o, h, l, c = (b[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    daily_close = b["close"].groupby(b.index.normalize()).last()
    daily_open = b["open"].groupby(b.index.normalize()).first()
    prev_close = daily_close.shift(1)
    prev_ret = daily_close.pct_change()
    g = b.groupby(b.index.normalize())
    day_range = g["high"].max() / g["low"].min() - 1                    # each day's high-low range
    recent = day_range.rolling(20).median().shift(1)                     # the last 20 days, through yesterday
    lively = (recent > recent.rolling(250, min_periods=120).median())  # vs its own past year
    q_hi = {}
    if qqq is not None:
        for d, ii, tt in days(qqq):
            q_hi[d] = (qqq.index[ii], qqq["high"].to_numpy(float)[ii], tt)
    widths: list[float] = []
    rows = []
    for d, ii, tt in days(b):
        rng = ii[tt < RANGE_END]
        hi, lo = h[rng].max(), l[rng].min()
        width = hi / lo - 1
        med = np.median(widths[-20:]) if len(widths) >= 10 else np.nan
        widths.append(width)
        after = ii[(tt >= RANGE_END) & (tt <= LAST_BAR)]
        for n, j in enumerate(after):
            tj = tt[tt >= RANGE_END][n]
            if h[j] <= hi:
                continue
            if tj > last_entry or (entry_by is not None and tj > entry_by):
                break
            entry = max(o[j], hi)
            st = (hi + lo) / 2 if stop == "mid" else lo
            if entry <= st:
                break
            risk = entry - st
            tgt = entry + target_r * risk if target_r else None
            exit_px, why, peak, trough = None, None, h[j], l[j]
            for k in after[n:]:
                first = k == j
                peak, trough = max(peak, h[k]), min(trough, l[k])
                if l[k] <= st:
                    exit_px, why = (st if first else min(o[k], st)), "stop"
                    break
                if tgt is not None and h[k] >= tgt:
                    exit_px, why = (max(entry, tgt) if first else max(o[k], tgt)), "target"
                    break
                if back_inside and not first and c[k] < hi:
                    exit_px, why = c[k], "back inside"
                    break
                if breakeven_r is not None and h[k] >= entry + breakeven_r * risk:
                    st = max(st, entry)
            if exit_px is None:
                exit_px, why = c[after[-1]], "close"
            qconf = np.nan
            if d in q_hi:
                qi, qh, qt = q_hi[d]
                qr = qh[qt < RANGE_END].max()
                done = qh[(qt >= RANGE_END) & (qi < b.index[j])]           # QQQ bars completed before ours
                qconf = bool(len(done) and done.max() > qr)
            rows.append({"date": d, "entry_min": int(tj), "entry": entry, "risk": risk, "exit": exit_px, "why": why,
                         "net": exit_px / entry - 1 - 2 * COST, "R": (exit_px - entry) / risk,
                         "mfe_R": (peak - entry) / risk, "mae_R": (entry - trough) / risk,
                         "gap": daily_open[d] / prev_close.get(d, np.nan) - 1, "prev_ret": prev_ret.shift(0).get(d - pd.Timedelta(0), np.nan),
                         "width": width, "narrow": width < med if np.isfinite(med) else np.nan,
                         "qqq_through": qconf, "weekday": d.dayofweek,
                         "lively": bool(lively.get(d)) if pd.notna(recent.get(d)) else np.nan})
            break
    t = pd.DataFrame(rows)
    if len(t):                                   # the previous day's return, known at the open
        t["prev_ret"] = t["date"].map(prev_ret.shift(1))
    return t


def stat(t: pd.DataFrame) -> dict:
    if t.empty:
        return {"n": 0, "win": np.nan, "net": np.nan, "t": np.nan, "a": np.nan, "b": np.nan}
    r = t["net"]
    return {"n": len(r), "win": (r > 0).mean(), "net": r.mean(), "t": r.mean() / r.std() * np.sqrt(len(r)),
            "a": r[t["date"] < SPLIT].mean(), "b": r[t["date"] >= SPLIT].mean()}


def main() -> None:
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    lines: list[str] = []

    def emit(s=""):
        print(s, flush=True)
        lines.append(s)

    nv, qq = five_min("NVDA"), five_min("QQQ")
    emit("# The NVIDIA opening buy, taken apart - generated tables\n")

    # ---- part 1: the shadow days
    shadow = [json.loads(x) for x in (ROOT / "journal" / "nvda_orb.jsonl").read_text().splitlines() if x.strip()]
    sd = {pd.Timestamp(r["date"]) for r in shadow}
    base_all = simulate(nv, qq)
    sh = base_all[base_all["date"].isin(sd)]
    emit(f"## 1. The shadow days ({min(sd).date()} to {max(sd).date()}): {len(sd)} days, {len(sh)} trades\n")
    emit("| result | trades | avg net | avg best run (MFE) | avg worst dip (MAE) | reached +1R | reached +2R |")
    emit("|---|---|---|---|---|---|---|")
    for lbl, m in (("stopped", sh["why"] == "stop"), ("held to 3:55, won", (sh["why"] == "close") & (sh["net"] > 0)),
                   ("held to 3:55, lost", (sh["why"] == "close") & (sh["net"] <= 0)), ("all", sh["net"] == sh["net"])):
        x = sh[m]
        emit(f"| {lbl} | {len(x)} | {x['net'].mean():+.2%} | {x['mfe_R'].mean():+.2f}R | {x['mae_R'].mean():.2f}R | "
             f"{(x['mfe_R'] >= 1).sum()} | {(x['mfe_R'] >= 2).sum()} |")

    # ---- part 2: ten years, winners vs losers
    emit("\n## 2. Ten years of NVDA (2016-2026): what separates winners from losers\n")
    t = base_all
    s = stat(t)
    emit(f"All trades: {s['n']:,}, win rate {s['win']:.0%}, average {s['net']:+.3%} after costs (t {s['t']:.1f}); "
         f"2016-20 {s['a']:+.3%}, 2021-26 {s['b']:+.3%}.\n")
    emit("| known at entry | bucket | trades | win rate | avg net | 2016-20 | 2021-26 |")
    emit("|---|---|---|---|---|---|---|")
    buckets = {
        "gap at the open": pd.cut(t["gap"], [-1, -0.01, 0, 0.01, 1], labels=["down >1%", "down 0-1%", "up 0-1%", "up >1%"]),
        "previous day": pd.cut(t["prev_ret"], [-1, -0.02, 0, 0.02, 1], labels=["down >2%", "down 0-2%", "up 0-2%", "up >2%"]),
        "range vs its 20-day median": t["narrow"].map({True: "narrower", False: "wider"}),
        "entry time": pd.cut(t["entry_min"], [0, 9 * 60 + 50, 10 * 60 + 30, 12 * 60, 24 * 60],
                             labels=["9:45-9:50", "9:55-10:30", "10:35-12:00", "after 12:00"]),
        "QQQ already through its range": t["qqq_through"].map({True: "yes", False: "no"}),
        "weekday": t["weekday"].map(dict(enumerate(["Mon", "Tue", "Wed", "Thu", "Fri"]))),
        "last 20 days' ranges vs past year": t["lively"].map({True: "wider", False: "narrower"}),
    }
    for name, bk in buckets.items():
        for lvl in [x for x in pd.unique(bk.dropna())]:
            x = t[bk == lvl]
            st = stat(x)
            emit(f"| {name} | {lvl} | {st['n']:,} | {st['win']:.0%} | {st['net']:+.3%} | {st['a']:+.3%} | {st['b']:+.3%} |")
    emit("\n**Where trades went** (R = the risk taken; NVDA 2016-2026):\n")
    stp, cls = t[t["why"] == "stop"], t[t["why"] == "close"]
    emit(f"- Stopped: {len(stp):,} ({len(stp) / len(t):.0%}); {(stp['mfe_R'] >= 0.5).mean():.0%} of them were +0.5R "
         f"up first, {(stp['mfe_R'] >= 1).mean():.0%} +1R up first.")
    emit(f"- Held to 3:55: {len(cls):,}; {(cls['mfe_R'] >= 1).mean():.0%} reached +1R, {(cls['mfe_R'] >= 2).mean():.0%} "
         f"+2R, {(cls['mfe_R'] >= 3).mean():.0%} +3R; they ended at {cls['R'].mean():+.2f}R on average.")
    emit(f"- The best 10% of trades made {t['net'].quantile(0.9):+.2%} or more and {t.loc[t['net'] >= t['net'].quantile(0.9), 'net'].sum() / t['net'].sum():.0%} "
         "of the total profit.")

    # ---- part 3: rule changes, judged on NVDA and the others
    emit("\n## 3. Rule changes, fixed in advance (pass = better average on NVDA AND the others, both halves)\n")
    others = {s: five_min(s) for s in OTHERS}
    variants = {
        "live rule": {},
        "no entries after 15:30 (fixes the 3:55pm entry)": {"last_entry": 15 * 60 + 30},
        "previous day down only": {"filter": lambda x: x["prev_ret"] < 0},
        "breakout by 10:00 only": {"entry_by": 10 * 60},
        "QQQ already through its range": {"filter": lambda x: x["qqq_through"] == True},  # noqa: E712
        "out if it closes back inside the range": {"back_inside": True},
        "stop to break-even at +1R": {"breakeven_r": 1.0},
        "take profit at +1R": {"target_r": 1.0},
        "take profit at +1R, stop at the range middle": {"target_r": 1.0, "stop": "mid"},
        "gap-up days (already shadowed)": {"filter": lambda x: x["gap"] > 0},
        "lively stock only (last 20 days' ranges wider than its past year)": {"filter": lambda x: x["lively"] == True},  # noqa: E712
    }
    emit("| change | NVDA trades | NVDA win rate | NVDA avg | 2016-20 | 2021-26 | others win rate | others avg | "
         "others 2016-20 | others 2021-26 | passes |")
    emit("|---|---|---|---|---|---|---|---|---|---|---|")
    base = None
    for name, v in variants.items():
        v = dict(v)
        flt = v.pop("filter", None)
        nt = simulate(nv, qq, **v)
        ot = pd.concat([simulate(b, qq, **v) for b in others.values()], ignore_index=True)
        if flt is not None:
            nt, ot = nt[flt(nt)], ot[flt(ot)]
        a, o_ = stat(nt), stat(ot)
        if base is None:
            base, ok = (a, o_), "-"
        else:
            bn, bo = base
            ok = "yes" if all([a["a"] > bn["a"], a["b"] > bn["b"], o_["a"] > bo["a"], o_["b"] > bo["b"]]) else "no"
        emit(f"| {name} | {a['n']:,} | {a['win']:.0%} | {a['net']:+.3%} | {a['a']:+.3%} | {a['b']:+.3%} | {o_['win']:.0%} | "
             f"{o_['net']:+.3%} | {o_['a']:+.3%} | {o_['b']:+.3%} | {ok} |")

    OUT.mkdir(exist_ok=True)
    (OUT / "nvda_orb_dive.md").write_text("\n".join(lines) + "\n")
    print(f"\nwrote {OUT / 'nvda_orb_dive.md'}")


if __name__ == "__main__":
    main()
