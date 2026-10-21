"""The desk with momentum top 10 instead of top 20 in its 20% sleeve.

    python research/desk_top10.py

Desk now: 50% quality screen + 20% momentum + 30% overnight (research/DESK_OVERNIGHT.md). The momentum sleeve
holds the top 20 by 6-month return (skipping the latest week) above their 200 AND 100-day averages, re-picked
every 4 weeks, sold below the 100-day average in between (research/MOMENTUM_ENTRY.md). Tested here: the same
desk with the sleeve cut to the top 10 - with the live rules, and plain (no entry filter, no 100-day exit), as in
research/MOMENTUM_SLEEVE.md. Monthly, 2014-2026, survivors-only prices; momentum at 0.10% per trade (and 3x),
the overnight sleeve at 0.02% and 0.03% each way. Writes research/output/desk_top10.md; findings in
research/DESK_TOP10.md.
"""

from __future__ import annotations

import pickle
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "research"))

import desk_overnight as do  # noqa: E402
import momentum_sleeve as ms  # noqa: E402
import weekly  # noqa: E402
from ai_desk.data import load_cash_rate  # noqa: E402
from ai_desk.fundamentals import screen_backtest as sb  # noqa: E402

CACHE, OUT, MONTH_END = do.CACHE, do.OUT, do.MONTH_END


def main() -> None:
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    lines: list[str] = []

    def emit(t=""):
        print(t, flush=True)
        lines.append(t)

    px, snaps = weekly.load()
    f = weekly.build(px, snaps)
    ma20 = px.rolling(20, min_periods=20).mean()
    f_both = {**f, "above": f["above"] & (px > ma20)}             # the live entry filter (200 AND 100-day)

    def sleeve(n, entry=True, exit_ma=20, cost=weekly.COST):
        book = weekly.momentum_book(px, snaps, f_both if entry else f, lookback=26, n=n, every=4, exit_ma=exit_ma)
        return ms.monthly(weekly.simulate(book, f["ret"], cost))

    variants = {
        "Top 20, live rules (now)": dict(n=20),
        "Top 10, live rules": dict(n=10),
        "Top 15, live rules": dict(n=15),
        "Top 10, plain (no entry filter, no 100-day exit)": dict(n=10, entry=False, exit_ma=None),
        "Top 20, plain": dict(n=20, entry=False, exit_ma=None),
    }
    print("momentum sleeves...", flush=True)
    sleeves = {k: sleeve(**kw) for k, kw in variants.items()}
    sleeves3 = {k: sleeve(**kw, cost=3 * weekly.COST) for k, kw in variants.items()}

    print("quality screen and overnight...", flush=True)
    prices = pickle.loads((CACHE / "prices.pkl").read_bytes())
    for k in prices:
        prices[k] = prices[k].groupby(level=0).last() if k != "splits" else prices[k].groupby(level=0).max()
    s_snaps = {}
    for m in (3, 6, 9, 12):
        s_snaps.update(pickle.loads((CACHE / f"snapshots_m{m}.pkl").read_bytes()))
    screen = sb.simulate({"t": sb.books(dict(sorted(s_snaps.items())), 25)["screen_top"]}, prices, MONTH_END)["t"]
    rf = load_cash_rate(str(ROOT / "market_data" / "SPY.csv"))
    rf_m = (rf.resample("ME").last() / 12).shift(1)
    idx = screen.index.intersection(sleeves["Top 20, live rules (now)"].index)
    idx = idx[(idx >= pd.Timestamp("2014-06-30")) & (idx <= pd.Timestamp(MONTH_END))]
    rfm = rf_m.reindex(idx).fillna(0)
    ovn = {c: (1 + do.overnight_daily(c)).resample("ME").prod().reindex(idx) - 1 for c in (0.0002, 0.0003)}
    spy = prices["adj"]["SPY"].loc[:MONTH_END].pct_change().reindex(idx)

    emit("# The desk with momentum top 10 - generated tables\n")
    emit(f"Monthly, {idx[0]:%Y-%m} to {idx[-1]:%Y-%m}. **Survivors-only prices.** Desk = 50% quality screen + 20% "
         "momentum + 30% overnight. Momentum at 0.10% per trade (3x in brackets); Sharpe above T-bills.\n")
    emit("## 1. The momentum sleeve on its own\n")
    emit("| sleeve | return/yr | volatility | Sharpe | worst drop | at 3x costs | 2014-19 Sharpe | 2020-26 Sharpe |")
    emit("|---|---|---|---|---|---|---|---|")
    for k, r in sleeves.items():
        r = r.reindex(idx)
        s, a, b = ms.mstats(r, rfm), ms.mstats(r.loc[:"2019"], rfm), ms.mstats(r.loc["2020":], rfm)
        emit(f"| {k} | {s['CAGR']:.1%} | {s['volatility']:.0%} | {s['Sharpe']:.2f} | {s['max drawdown']:.0%} | "
             f"{ms.mstats(sleeves3[k].reindex(idx), rfm)['CAGR']:.1%} | {a['Sharpe']:.2f} | {b['Sharpe']:.2f} |")

    emit("\n## 2. The whole desk\n")
    emit("| momentum sleeve | overnight costs | return/yr | volatility | Sharpe | worst drop | 2014-19 Sharpe | "
         "2020-26 Sharpe | momentum at 3x costs: Sharpe |")
    emit("|---|---|---|---|---|---|---|---|---|")
    desks = {}
    for cost, on in ovn.items():
        for k, r in sleeves.items():
            d = 0.5 * screen.reindex(idx) + 0.2 * r.reindex(idx) + 0.3 * on
            d3 = 0.5 * screen.reindex(idx) + 0.2 * sleeves3[k].reindex(idx) + 0.3 * on
            desks[(k, cost)] = d
            s, a, b = ms.mstats(d, rfm), ms.mstats(d.loc[:"2019"], rfm), ms.mstats(d.loc["2020":], rfm)
            emit(f"| {k} | {cost:.2%} | {s['CAGR']:.1%} | {s['volatility']:.1%} | {s['Sharpe']:.2f} | "
                 f"{s['max drawdown']:.1%} | {a['Sharpe']:.2f} | {b['Sharpe']:.2f} | {ms.mstats(d3, rfm)['Sharpe']:.2f} |")
    emit(ms.fmt_row("SPY (for reference)", ms.mstats(spy, rfm)).replace("| SPY (for reference) |", "| SPY | |"))

    emit("\n## 3. Is the difference more than noise? (top 10 live vs top 20 live, overnight at 0.02%)\n")
    a, b = desks[("Top 10, live rules", 0.0002)], desks[("Top 20, live rules (now)", 0.0002)]
    diff = (a - b).dropna()
    t = diff.mean() / diff.std(ddof=1) * np.sqrt(len(diff))
    rng = np.random.default_rng(0)
    boot = []
    for _ in range(2000):                                          # block bootstrap of the Sharpe gap (12-month blocks)
        starts = rng.integers(0, len(idx) - 12, size=len(idx) // 12 + 1)
        pick = np.concatenate([np.arange(s, s + 12) for s in starts])[:len(idx)]
        sa, sb_ = ms.mstats(a.iloc[pick].reset_index(drop=True), rfm.iloc[pick].reset_index(drop=True)), \
            ms.mstats(b.iloc[pick].reset_index(drop=True), rfm.iloc[pick].reset_index(drop=True))
        boot.append(sa["Sharpe"] - sb_["Sharpe"])
    lo, hi = np.percentile(boot, [5, 95])
    ya, yb = (1 + a).groupby(a.index.year).prod() - 1, (1 + b).groupby(b.index.year).prod() - 1
    emit(f"- Monthly return difference: {diff.mean() * 12:+.2%} a year (t {t:.1f}).")
    emit(f"- Sharpe difference: {ms.mstats(a, rfm)['Sharpe'] - ms.mstats(b, rfm)['Sharpe']:+.2f}, 90% range "
         f"{lo:+.2f} to {hi:+.2f} (block bootstrap).")
    emit(f"- Top 10 did better in {int((ya > yb).sum())} of {len(ya)} years.")
    emit(f"- Each top-10 stock is 2% of the desk (1% now); the momentum sleeve's monthly correlation with the "
         f"quality screen: top 10 {sleeves['Top 10, live rules'].reindex(idx).corr(screen.reindex(idx)):.2f}, "
         f"top 20 {sleeves['Top 20, live rules (now)'].reindex(idx).corr(screen.reindex(idx)):.2f}.")

    emit("\n## 4. Year by year (overnight at 0.02%)\n")
    keys = list(sleeves)
    emit("| year | " + " | ".join(keys) + " |\n|" + "---|" * (len(keys) + 1))
    ys = {k: (1 + desks[(k, 0.0002)]).groupby(idx.year).prod() - 1 for k in keys}
    for y in ys[keys[0]].index:
        emit(f"| {y} | " + " | ".join(f"{ys[k][y]:+.1%}" for k in keys) + " |")
    emit("\n## 5. The market's 10 worst months (desk, overnight at 0.02%)\n")
    worst = spy.nsmallest(10).index.sort_values()
    emit("| month | SPY | " + " | ".join(keys[:3]) + " |\n|" + "---|" * 5)
    for m in worst:
        emit(f"| {m:%Y-%m} | {spy[m]:+.1%} | " + " | ".join(f"{desks[(k, 0.0002)][m]:+.1%}" for k in keys[:3]) + " |")

    OUT.mkdir(exist_ok=True)
    (OUT / "desk_top10.md").write_text("\n".join(lines) + "\n")
    print(f"\nwrote {OUT / 'desk_top10.md'}")


if __name__ == "__main__":
    main()
