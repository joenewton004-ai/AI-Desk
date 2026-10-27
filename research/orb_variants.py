"""Can the NVIDIA opening-range buy be made more profitable - without fooling ourselves?

    python research/orb_variants.py      (uses research/alpaca_bars.py's 1-minute caches)

Base (live shadow, ai_desk/nvda_orb.py): 15-minute opening range; buy the first break above its high (5-minute bars);
stop at its low; out at 15:55. Costs 0.02% each way. Tweaks, each with a reason, fixed before running:
  trend     only when the stock closed above its 50-day average the day before (breakouts with the trend)
  gap_up    only when it opened above the previous close (buyers already in control)
  narrow    only when the opening range is narrower than its own 20-day median (a tight range breaks harder)
  early     only breakouts before 11:00 (late breakouts are often noise)
  mid_stop  stop at the middle of the range instead of its low (half the risk per trade)
  target2R  take profit at 2x the risk instead of holding to 15:55
  wider30   a 30-minute opening range instead of 15
The test that matters: a tweak counts only if it beats the base on NVDA AND on the pooled 11 other stocks (QQQ + the
10 largest US companies of 2016, picked without hindsight), in BOTH 2016-20 and 2021-26. NVDA alone would just
re-fit its own past. Survivors-only names (all still listed). Writes research/output/orb_variants.md.
"""

from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import alpaca_bars  # noqa: E402
import candles as cd  # noqa: E402

OUT = Path(__file__).resolve().parent / "output"
COST = 0.0002
OTHERS = ["QQQ", "AAPL", "GOOGL", "MSFT", "BRK.B", "XOM", "AMZN", "META", "GE", "JNJ", "WFC"]
SPLIT = pd.Timestamp("2021-01-01")
VARIANTS = ["base", "trend", "gap_up", "narrow", "early", "mid_stop", "target2R", "wider30"]


def orb(b: pd.DataFrame, variant: str = "base") -> pd.DataFrame:
    """One trade a day at most, long only, per the variant's rule. Uses only data known at each point of the day
    (the 50-day average and the 20-day median range from earlier days)."""
    o, h, l, c = (b[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    tod, dayid = b["tod"].to_numpy(), b["day"].to_numpy()
    ends = cd.day_ends(b)
    minutes = 30 if variant == "wider30" else 15
    g = pd.Series(np.arange(len(b))).groupby(dayid)
    first = g.first().to_numpy()
    last = g.last().to_numpy()
    day_close = c[last]
    day_open = o[first]
    sma50 = pd.Series(day_close).rolling(50, min_periods=50).mean().shift(1).to_numpy()   # through yesterday's close
    prev_close = np.r_[np.nan, day_close[:-1]]
    ranges = []
    out = []
    for d, idx in g:
        idx = idx.to_numpy()
        rng = idx[tod[idx] < 9 * 60 + 30 + minutes]
        after = idx[tod[idx] >= 9 * 60 + 30 + minutes]
        if len(rng) == 0 or len(after) == 0 or tod[rng[0]] != 9 * 60 + 30:
            ranges.append(np.nan)
            continue
        hi, lo = h[rng].max(), l[rng].min()
        width = hi / lo - 1
        med = np.nanmedian(ranges[-20:]) if len(ranges) >= 10 else np.nan
        ranges.append(width)
        if variant == "trend" and (d == 0 or not np.isfinite(sma50[d]) or not day_close[d - 1] > sma50[d]):
            continue
        if variant == "gap_up" and not (d > 0 and day_open[d] > prev_close[d]):
            continue
        if variant == "narrow" and not (np.isfinite(med) and width < med):
            continue
        for j in after:
            if j > ends[j]:
                break
            if h[j] > hi:
                if variant == "early" and tod[j] >= 11 * 60:
                    break
                entry = max(o[j], hi)
                stop = (hi + lo) / 2 if variant == "mid_stop" else lo
                if entry <= stop:
                    break
                target = entry + 2 * (entry - stop) if variant == "target2R" else None
                r, _ = cd.run_exit(o, h, l, c, j, ends[j], 1, entry, stop, target)
                out.append({"time": b.index[j], "ret": r - 2 * COST})
                break
    return pd.DataFrame(out, columns=["time", "ret"])


def stat(t: pd.DataFrame) -> dict:
    if t.empty:
        return {"n": 0, "net": np.nan, "t": np.nan, "a": np.nan, "b": np.nan}
    r = t["ret"]
    return {"n": len(r), "net": r.mean(), "t": r.mean() / r.std() * np.sqrt(len(r)) if r.std() > 0 else np.nan,
            "a": r[t["time"] < SPLIT].mean(), "b": r[t["time"] >= SPLIT].mean()}


def main() -> None:
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    lines: list[str] = []

    def emit(s=""):
        print(s, flush=True)
        lines.append(s)

    bars = {s: cd.to_bars(alpaca_bars.minute_bars(s)) for s in ["NVDA", *OTHERS]}
    emit("# Can the NVIDIA opening buy be improved? - generated tables\n")
    emit("Per trade after 0.02% costs each way, 5-minute bars 2016-2026. A tweak counts only if it beats the base on NVDA "
         "AND on the 11 others pooled, in both 2016-20 and 2021-26.\n")
    emit("| tweak | NVDA trades | NVDA net | NVDA 2016-20 | NVDA 2021-26 | others trades | others net | others 2016-20 | "
         "others 2021-26 | passes |")
    emit("|---|---|---|---|---|---|---|---|---|---|")
    base = None
    for v in VARIANTS:
        nv = stat(orb(bars["NVDA"], v))
        ot = stat(pd.concat([orb(bars[s], v) for s in OTHERS], ignore_index=True))
        if v == "base":
            base = (nv, ot)
            ok = "-"
        else:
            bn, bo = base
            ok = "yes" if all([nv["a"] > bn["a"], nv["b"] > bn["b"], ot["a"] > bo["a"], ot["b"] > bo["b"]]) else "no"
        emit(f"| {v} | {nv['n']:,} | {nv['net']:+.3%} | {nv['a']:+.3%} | {nv['b']:+.3%} | {ot['n']:,} | {ot['net']:+.3%} | "
             f"{ot['a']:+.3%} | {ot['b']:+.3%} | {ok} |")

    OUT.mkdir(exist_ok=True)
    (OUT / "orb_variants.md").write_text("\n".join(lines) + "\n")
    print(f"\nwrote {OUT / 'orb_variants.md'}")


if __name__ == "__main__":
    main()
