"""TJR's day-trading model as fixed rules: a liquidity sweep at the New York open, a break of structure, entry.

    python research/tjr.py

TJR (TJR Trades) is a YouTube/social-media trader who day-trades US index futures, mainly the Nasdaq-100 (NQ) and
S&P 500 (ES) E-minis, around the New York open, with an ICT-style "smart money" model. His own rulebook isn't public;
the rules below follow the descriptions that agree across third-party write-ups and the community TradingView scripts
named after him (see research/TJR.md for sources), made precise so they can be tested:

  liquidity    the previous regular session's high and low, the Asia session's (8pm-midnight New York) and London
               session's (2-5am) highs and lows, and the overnight high and low (6pm-9:29am)
  sweep        between 9:30 and 11:00am, a bar trades through one of those levels and CLOSES back on the other side
               (above a high -> a short setup; below a low -> a long setup)
  confirm      within the next 30 minutes, a break of structure: a close past the extreme of the 3 bars before the
               sweep (BOS) - or, variant, a close through the far edge of the latest fair value gap that the move into
               the sweep left (an "inverse FVG")
  entry        the next bar's open; stop just beyond the sweep's extreme; target 2R, 3R, or the nearest liquidity level
               on the other side (at least 1R away); anything still open is closed at 3:55pm
  bias         optional: only trades in the direction of the 1-hour 50-period average
  one trade per instrument per day (the first). A bar that touches both stop and target counts as a stop.

Data: Yahoo's 5-minute NQ=F and ES=F bars (it keeps only the last ~60 days) and, for a coarse 2-year check, hourly
bars. Costs: 1 tick of slippage each way plus about $5 commission per round trip (NQ 0.75 points, ES 0.60). Random-
direction trades at the same times, with the same stops and targets, are the control. Writes
research/output/tjr.md; findings in research/TJR.md.
"""

from __future__ import annotations

import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "research"))

import ict  # noqa: E402

CACHE = ROOT / "data" / "backtest"
OUT = Path(__file__).resolve().parent / "output"
COST_PTS = {"NQ=F": 0.75, "ES=F": 0.60}
TICK = {"NQ=F": 0.25, "ES=F": 0.25}
DOLLARS_PER_PT = {"NQ=F": 20, "ES=F": 50}


# --- pure pieces (unit-tested) --------------------------------------------------------

def levels(bars: pd.DataFrame, day: pd.Timestamp) -> dict[str, float]:
    """The liquidity levels for `day`'s New York session, from bars BEFORE 9:30am that day only."""
    d = pd.Timestamp(day).normalize()
    prev = bars.loc[:d - pd.Timedelta(minutes=1)]
    rth = prev.between_time("09:30", "15:59")
    out = {}
    if len(rth):
        last = rth.index[-1].normalize()
        p = rth.loc[str(last.date())]
        out["prior day high"], out["prior day low"] = float(p["High"].max()), float(p["Low"].min())
    win = {"Asia": (d - pd.Timedelta(hours=4), d), "London": (d + pd.Timedelta(hours=2), d + pd.Timedelta(hours=5)),
           "overnight": (d - pd.Timedelta(hours=6), d + pd.Timedelta(hours=9, minutes=29))}
    for name, (a, b) in win.items():
        w = bars.loc[a:b - pd.Timedelta(seconds=1)] if name != "overnight" else bars.loc[a:b]
        if len(w):
            out[f"{name} high"], out[f"{name} low"] = float(w["High"].max()), float(w["Low"].min())
    return out


def find_setup(o, h, lo, c, lv: dict[str, float], start: int, stop_bar: int, confirm_bars: int, mode: str = "bos",
               bias: int = 0, swing: int = 3) -> dict | None:
    """The first sweep + confirmation between bars `start` and `stop_bar` (indices into the day's arrays).
    side -1 = short after a sweep of a high, +1 = long after a sweep of a low. bias 0 = both sides."""
    highs = {k: v for k, v in lv.items() if k.endswith("high")}
    lows = {k: v for k, v in lv.items() if k.endswith("low")}
    for i in range(max(start, swing), min(stop_bar, len(c))):
        for side, pool in ((-1, highs), (1, lows)):
            if bias and side != bias:
                continue
            swept = [k for k, v in pool.items() if (side < 0 and h[i] > v > c[i]) or (side > 0 and lo[i] < v < c[i])]
            if not swept:
                continue
            if mode == "bos":
                line = lo[i - swing:i].min() if side < 0 else h[i - swing:i].max()
            else:   # inverse FVG: the latest gap left by the move INTO the sweep, within 6 bars
                line = None
                for k in range(i, max(i - 6, 1), -1):
                    if side < 0 and lo[k] > h[k - 2]:
                        line = h[k - 2]                 # bullish gap's lower edge
                        break
                    if side > 0 and h[k] < lo[k - 2]:
                        line = lo[k - 2]                # bearish gap's upper edge
                        break
                if line is None:
                    continue
            ext = h[i] if side < 0 else lo[i]
            for j in range(i + 1, min(i + 1 + confirm_bars, len(c) - 1)):
                ext = max(ext, h[j]) if side < 0 else min(ext, lo[j])
                if (side < 0 and c[j] < line) or (side > 0 and c[j] > line):
                    return {"side": side, "sweep_bar": i, "confirm_bar": j, "extreme": float(ext), "level": swept[0]}
                if (side < 0 and h[j] > ext) or (side > 0 and lo[j] < ext):
                    continue
    return None


def opposite_target(lv: dict[str, float], side: int, entry: float, risk: float) -> float | None:
    """The nearest liquidity level on the other side, at least 1R away."""
    cands = [v for k, v in lv.items() if (side < 0 and v <= entry - risk) or (side > 0 and v >= entry + risk)]
    if not cands:
        return None
    return max(cands) if side < 0 else min(cands)


# --- the experiment ---------------------------------------------------------------------

def run(bars: pd.DataFrame, sym: str, interval: str, mode="bos", target="2R", use_bias=False, seed: int | None = None):
    bar_min = 5 if interval == "5m" else 60
    confirm = 30 // bar_min if bar_min < 60 else 1
    hourly = bars["Close"].resample("1h").last().dropna()
    ema = hourly.ewm(span=50, adjust=False).mean()
    rng = np.random.default_rng(seed) if seed is not None else None
    trades = []
    days = sorted({d.normalize() for d in bars.index if d.time() >= pd.Timestamp("09:30").time()
                   and d.weekday() < 5})
    for d in days:
        day = bars.loc[d + pd.Timedelta(hours=9, minutes=30): d + pd.Timedelta(hours=15, minutes=59)]
        if len(day) < (60 // bar_min) * 2:
            continue
        lv = levels(bars, d)
        if len(lv) < 4:
            continue
        o, h, lo, c = (day[k].to_numpy(float) for k in ("Open", "High", "Low", "Close"))
        last_hr = hourly.loc[:d + pd.Timedelta(hours=9, minutes=29)]
        bias = 0
        if use_bias and len(last_hr) > 50:
            bias = 1 if last_hr.iloc[-1] > ema.loc[last_hr.index[-1]] else -1
        window_end = int(((day.index.hour * 60 + day.index.minute) < 11 * 60).sum())
        pre = bars.loc[:d + pd.Timedelta(hours=9, minutes=29)].tail(3)
        O = np.r_[pre["Open"].to_numpy(float), o]
        H = np.r_[pre["High"].to_numpy(float), h]
        L = np.r_[pre["Low"].to_numpy(float), lo]
        C = np.r_[pre["Close"].to_numpy(float), c]
        off = len(pre)
        s = find_setup(O, H, L, C, lv, off, off + window_end, confirm, mode, bias)
        if s is None:
            continue
        side = s["side"] if rng is None else int(rng.choice([-1, 1]))
        k = s["confirm_bar"] + 1
        if k >= len(C):
            continue
        entry = O[k]
        stop = s["extreme"] + TICK[sym] * (1 if s["side"] < 0 else -1)
        if rng is not None and side != s["side"]:
            stop = entry + (entry - stop)                       # same distance, other side
        risk = abs(entry - stop)
        if risk < 4 * TICK[sym] or (side < 0 and stop <= entry) or (side > 0 and stop >= entry):
            continue
        if target == "opposite":
            tgt = opposite_target(lv, side, entry, risk) or entry + side * 2 * risk
        else:
            tgt = entry + side * float(target.rstrip("R")) * risk
        tr = ict.run_trade(O, H, L, C, k, side, entry, stop, tgt, limit=False)
        if tr is None:
            continue
        cost_r = COST_PTS[sym] / risk
        trades.append({**tr, "date": d.date(), "sym": sym, "risk_pts": risk, "R_net": tr["R"] - cost_r,
                       "pts_net": tr["R"] * risk - COST_PTS[sym], "level": s["level"],
                       "usd_net": (tr["R"] * risk - COST_PTS[sym]) * DOLLARS_PER_PT[sym]})
    return pd.DataFrame(trades)


def summarize(t: pd.DataFrame) -> dict:
    if t.empty:
        return {"n": 0}
    x = t["R_net"]
    return {"n": len(t), "win": (x > 0).mean(), "R": x.mean(), "t": x.mean() / x.std() * np.sqrt(len(x)) if len(x) > 1 else np.nan,
            "R_gross": t["R"].mean(), "stops": (t["why"] == "stop").mean(), "usd": t["usd_net"].sum(),
            "pf": x[x > 0].sum() / -x[x <= 0].sum() if (x <= 0).any() else np.inf}


def main() -> None:
    lines: list[str] = []

    def emit(s=""):
        print(s, flush=True)
        lines.append(s)

    data = pickle.loads((CACHE / "futures_intraday.pkl").read_bytes())
    emit("# TJR's model as fixed rules - generated tables\n")
    for interval in ("5m", "1h"):
        b0 = data[("NQ=F", interval)]
        emit(f"## {interval} bars, {b0.index[0].date()} to {b0.index[-1].date()} (NQ=F and ES=F, New York time)\n")
        emit("Net of costs (NQ 0.75 points, ES 0.60 per round trip). R = the trade's risk (entry to stop).\n")
        emit("| rules | trades | win rate | avg R (net) | t | avg R before costs | stopped out | $ per contract, total | profit factor |")
        emit("|---|---|---|---|---|---|---|---|---|")
        variants = [("BOS, 2R", dict(mode="bos", target="2R")), ("BOS, 3R", dict(mode="bos", target="3R")),
                    ("BOS, opposite liquidity", dict(mode="bos", target="opposite")),
                    ("BOS, 2R, 1-hour bias", dict(mode="bos", target="2R", use_bias=True)),
                    ("inverse FVG, 2R", dict(mode="ifvg", target="2R")),
                    ("inverse FVG, 2R, 1-hour bias", dict(mode="ifvg", target="2R", use_bias=True))]
        for name, kw in variants:
            t = pd.concat([run(data[(s, interval)], s, interval, **kw) for s in ("NQ=F", "ES=F")], ignore_index=True)
            r = summarize(t)
            if not r["n"]:
                emit(f"| {name} | 0 | | | | | | | |")
                continue
            emit(f"| {name} | {r['n']} | {r['win']:.0%} | {r['R']:+.2f} | {r['t']:.1f} | {r['R_gross']:+.2f} | "
                 f"{r['stops']:.0%} | ${r['usd']:+,.0f} | {r['pf']:.2f} |")
            if name == "BOS, 2R":
                ctrl = [summarize(pd.concat([run(data[(s, interval)], s, interval, mode="bos", target="2R", seed=k)
                                             for s in ("NQ=F", "ES=F")], ignore_index=True))["R"] for k in range(20)]
                emit(f"| *control: same times, random direction (20 runs)* | | | {np.mean(ctrl):+.2f} "
                     f"(range {min(ctrl):+.2f} to {max(ctrl):+.2f}) | | | | | |")
        t = pd.concat([run(data[(s, interval)], s, interval) for s in ("NQ=F", "ES=F")], ignore_index=True)
        if len(t):
            emit("\nBy level swept (BOS, 2R):\n")
            emit("| level | trades | avg R (net) | win rate |\n|---|---|---|---|")
            for lv, g in t.groupby("level"):
                emit(f"| {lv} | {len(g)} | {g['R_net'].mean():+.2f} | {(g['R_net'] > 0).mean():.0%} |")
            emit("\n| instrument | trades | avg R (net) | $ per contract |\n|---|---|---|---|")
            for s, g in t.groupby("sym"):
                emit(f"| {s} | {len(g)} | {g['R_net'].mean():+.2f} | ${g['usd_net'].sum():+,.0f} |")
        emit("")

    OUT.mkdir(exist_ok=True)
    (OUT / "tjr.md").write_text("\n".join(lines) + "\n")
    print(f"wrote {OUT / 'tjr.md'}")


if __name__ == "__main__":
    main()
