"""Classic daily candlestick patterns on SPY, 1993-2026: do they predict the next day or the next week?

    python research/candles_daily_spy.py      (market_data/SPY, QQQ, IWM, DIA .csv - python -m ai_desk fetch ...)

Earlier tests: 5-minute candles on SPY/NVDA (research/CANDLES.md - nothing) and hammer / bullish engulfing / reversal
close as filters on RSI dips (research/CANDLE_RSI.md - they add nothing). This is the full textbook set on DAILY bars,
standing alone, bullish and bearish. Definitions (Nison / Bulkowski style), fixed before running; body = |close-open|,
range = high-low, "small body" = body <= 30% of range, "long body" = body >= 70% of range:
  bullish (only after a down week: close below the close 5 days earlier)
    hammer, inverted_hammer, bullish_engulfing, piercing_line, morning_star, three_white_soldiers, bullish_harami,
    dragonfly_doji, bullish_marubozu, tweezer_bottom
  bearish (only after an up week)
    shooting_star, hanging_man, bearish_engulfing, dark_cloud_cover, evening_star, three_black_crows, bearish_harami,
    gravestone_doji, bearish_marubozu, tweezer_top
  neutral (no context; judged on the direction they're usually read: doji/inside day = pause, outside day = reversal
    of the prior week)  doji, inside_day, outside_day
Each pattern is known at day t's close; the trade buys at t+1's open and is measured to the open 1 and 5 trading days
later, minus SPY's average return over as many days in the same half ("excess"). Bearish patterns "work" if the
excess is negative (stay out / short). 5-day results take one event at a time (no overlapping holds).
PASS: excess in the predicted direction in BOTH 1993-2009 and 2010-2026 with |t| >= 2, AND the same direction on QQQ,
IWM and DIA pooled in both halves. 46 tests: ~2 would pass by chance at the 5% level. Costs (0.01% each way) are
included in the long trades' returns. Writes research/output/candles_daily_spy.md.
"""

from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research"))

import swing_etf as se  # noqa: E402

OUT = Path(__file__).resolve().parent / "output"
SPLIT = "2010-01-01"
COST = 0.0001
BULL = ["hammer", "inverted_hammer", "bullish_engulfing", "piercing_line", "morning_star", "three_white_soldiers",
        "bullish_harami", "dragonfly_doji", "bullish_marubozu", "tweezer_bottom"]
BEAR = ["shooting_star", "hanging_man", "bearish_engulfing", "dark_cloud_cover", "evening_star", "three_black_crows",
        "bearish_harami", "gravestone_doji", "bearish_marubozu", "tweezer_top"]
NEUTRAL = ["doji", "inside_day", "outside_day"]
EXPECT = {**{p: 1 for p in BULL}, **{p: -1 for p in BEAR}, "doji": 0, "inside_day": 0, "outside_day": 0}


def patterns(d: pd.DataFrame) -> pd.DataFrame:
    """Pure: True where each pattern completes at that day's close (uses that day and earlier only)."""
    o, h, l, c = d["open"], d["high"], d["low"], d["close"]
    rng = (h - l).replace(0, np.nan)
    body = (c - o).abs()
    up, dn = c > o, c < o
    upper = h - np.maximum(o, c)
    lower = np.minimum(o, c) - l
    small = body <= 0.3 * rng
    long_ = body >= 0.7 * rng
    doji = body <= 0.1 * rng
    down_wk = c < c.shift(5)
    up_wk = c > c.shift(5)
    o1, c1, h1, l1 = o.shift(1), c.shift(1), h.shift(1), l.shift(1)
    o2, c2 = o.shift(2), c.shift(2)
    body1 = (c1 - o1).abs()
    rng1 = (h1 - l1).replace(0, np.nan)
    mid1 = (o1 + c1) / 2
    p = {}
    p["hammer"] = down_wk & small & (lower >= 2 * body) & (upper <= 0.1 * rng)
    p["inverted_hammer"] = down_wk & small & (upper >= 2 * body) & (lower <= 0.1 * rng)
    p["bullish_engulfing"] = down_wk & (c1 < o1) & up & (o <= c1) & (c >= o1)
    p["piercing_line"] = down_wk & (c1 < o1) & (body1 >= 0.6 * rng1) & up & (o < l1) & (c > mid1) & (c < o1)
    p["morning_star"] = (down_wk & (c2 < o2) & ((c2 - o2).abs() >= 0.6 * (h.shift(2) - l.shift(2)))
                         & (body1 <= 0.3 * rng1) & (np.maximum(o1, c1) < c2) & up & (c > (o2 + c2) / 2))
    p["three_white_soldiers"] = (down_wk.shift(3, fill_value=False) & up & (c1 > o1) & (c2 > o2) & (c > c1) & (c1 > c2)
                                 & (o > o1) & (o < c1) & (o1 > o2) & (o1 < c2))
    p["bullish_harami"] = down_wk & (c1 < o1) & (body1 >= 0.6 * rng1) & up & (o > c1) & (c < o1)
    p["dragonfly_doji"] = down_wk & doji & (upper <= 0.1 * rng) & (lower >= 0.7 * rng)
    p["bullish_marubozu"] = down_wk & up & (body >= 0.9 * rng)
    p["tweezer_bottom"] = down_wk & (c1 < o1) & up & ((l - l1).abs() <= 0.001 * c)
    p["shooting_star"] = up_wk & small & (upper >= 2 * body) & (lower <= 0.1 * rng)
    p["hanging_man"] = up_wk & small & (lower >= 2 * body) & (upper <= 0.1 * rng)
    p["bearish_engulfing"] = up_wk & (c1 > o1) & dn & (o >= c1) & (c <= o1)
    p["dark_cloud_cover"] = up_wk & (c1 > o1) & (body1 >= 0.6 * rng1) & dn & (o > h1) & (c < mid1) & (c > o1)
    p["evening_star"] = (up_wk & (c2 > o2) & ((c2 - o2).abs() >= 0.6 * (h.shift(2) - l.shift(2)))
                         & (body1 <= 0.3 * rng1) & (np.minimum(o1, c1) > c2) & dn & (c < (o2 + c2) / 2))
    p["three_black_crows"] = (up_wk.shift(3, fill_value=False) & dn & (c1 < o1) & (c2 < o2) & (c < c1) & (c1 < c2)
                              & (o < o1) & (o > c1) & (o1 < o2) & (o1 > c2))
    p["bearish_harami"] = up_wk & (c1 > o1) & (body1 >= 0.6 * rng1) & dn & (o < c1) & (c > o1)
    p["gravestone_doji"] = up_wk & doji & (lower <= 0.1 * rng) & (upper >= 0.7 * rng)
    p["bearish_marubozu"] = up_wk & dn & (body >= 0.9 * rng)
    p["tweezer_top"] = up_wk & (c1 > o1) & dn & ((h - h1).abs() <= 0.001 * c)
    p["doji"] = doji
    p["inside_day"] = (h < h1) & (l > l1)
    p["outside_day"] = (h > h1) & (l < l1)
    return pd.DataFrame(p).fillna(False).astype(bool)


def events(d: pd.DataFrame, sig: np.ndarray, hold: int, split: str = SPLIT) -> pd.DataFrame:
    """Each signal's return from the next open to the open `hold` days later (after costs, long), minus SPY's average
    open-to-open drift over as many days in the same half. For hold > 1 events don't overlap."""
    o = d["open"].to_numpy()
    oo = d["open"].pct_change().shift(-1)
    drift = {True: oo[:split].mean(), False: oo[split:].mean()}
    rows, i, n = [], 0, len(d)
    while i < n - hold - 1:
        if sig[i]:
            e, x = i + 1, i + 1 + hold
            early = d.index[e] < pd.Timestamp(split)
            r = o[x] / o[e] - 1 - 2 * COST
            rows.append((d.index[e], r, r - hold * drift[early], early))
            i = x if hold > 1 else i + 1
        else:
            i += 1
    return pd.DataFrame(rows, columns=["entry", "net", "excess", "early"])


def main() -> None:
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    lines: list[str] = []

    def emit(s=""):
        print(s, flush=True)
        lines.append(s)

    data = {s: se.load(s) for s in ("SPY", "QQQ", "IWM", "DIA")}
    pats = {s: patterns(d) for s, d in data.items()}
    emit("# Daily candlestick patterns on SPY, 1993-2026 - generated tables\n")
    emit("Excess = return from the next open, minus SPY's normal drift over as many days (same half). Bullish patterns "
         "should give a positive excess, bearish a negative one. Others = QQQ, IWM and DIA pooled.\n")
    emit("| pattern | expects | horizon | SPY events | per year | SPY win rate | SPY excess | t | 1993-2009 | 2010-2026 | "
         "others 1st half | others 2nd half | passes |")
    emit("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    passed = []
    spy = data["SPY"]
    yrs = (spy.index[-1] - spy.index[0]).days / 365.25
    for p in BULL + BEAR + NEUTRAL:
        want = EXPECT[p]
        for hold in (1, 5):
            ev = events(spy, pats["SPY"][p].to_numpy(), hold)
            oth = pd.concat([events(data[s], pats[s][p].to_numpy(), hold) for s in ("QQQ", "IWM", "DIA")],
                            ignore_index=True)
            if ev.empty:
                emit(f"| {p} | {want:+d} | {hold}d | 0 | - | - | - | - | - | - | - | - | no |")
                continue
            t = se.tstat(ev["excess"])
            a, b = ev.loc[ev["early"], "excess"].mean(), ev.loc[~ev["early"], "excess"].mean()
            oa, ob = oth.loc[oth["early"], "excess"].mean(), oth.loc[~oth["early"], "excess"].mean()
            if want == 0:
                ok = False
            else:
                ok = (want * a > 0 and want * b > 0 and want * t >= 2 and want * oa > 0 and want * ob > 0)
            if ok:
                passed.append((p, hold))
            exp = {1: "up", -1: "down", 0: "-"}[want]
            emit(f"| {p} | {exp} | {hold}d | {len(ev):,} | {len(ev) / yrs:.1f} | {(ev['net'] > 0).mean():.0%} | "
                 f"{ev['excess'].mean():+.2%} | {t:.1f} | {a:+.2%} | {b:+.2%} | {oa:+.2%} | {ob:+.2%} | "
                 f"{'**yes**' if ok else 'no'} |")
    emit(f"\nPassed: {', '.join(f'{p} ({h}d)' for p, h in passed) or 'none'} - of 40 directional tests "
         "(about 2 would pass by chance).")
    OUT.mkdir(exist_ok=True)
    (OUT / "candles_daily_spy.md").write_text("\n".join(lines) + "\n")
    print(f"\nwrote {OUT / 'candles_daily_spy.md'}")


if __name__ == "__main__":
    main()
