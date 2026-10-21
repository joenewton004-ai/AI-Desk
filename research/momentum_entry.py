"""Momentum sleeve: should a stock also be above its 100-day average to be picked?

    python research/momentum_entry.py

The live sleeve picks the top 20 by 6-month return among stocks above their 200-day average, then sells any
holding that closes below its 100-day average - checked every evening, the pick day included. A stock above
its 200-day but below its 100-day is therefore picked and sold at once (5 of 20 on 2026-10-21). Tested here,
weekly 2014-2026 (as research/MOMENTUM_SLEEVE.md; 20 weeks ~ 100 days, 40 weeks ~ 200 days):
  current   pick above the 40-week average; exit below the 20-week average from the week after the pick
  same day  as current, but the exit also applies in the pick week (what the live code does): those slots sit
            in cash until the next re-pick
  entry     pick only stocks above BOTH averages - the next-ranked stocks fill the slots
Survivors-only prices; 0.10% per trade. Writes research/output/momentum_entry.md; findings in
research/MOMENTUM_ENTRY.md.
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

import momentum_sleeve as ms  # noqa: E402
import weekly  # noqa: E402
from ai_desk.data import load_cash_rate  # noqa: E402

CACHE = ROOT / "data" / "backtest"
OUT = Path(__file__).resolve().parent / "output"


def book_same_day_exit(px, snaps, f, n=20, every=4, exit_ma=20):
    """Like weekly.momentum_book(exit_ma=...), but the exit rule also applies in the pick week itself."""
    mom = px.shift(1) / px.shift(27) - 1
    ma_x = px.rolling(exit_ma, min_periods=exit_ma).mean()
    book, held, last = {}, {}, []
    for i, d in enumerate(f["dates"]):
        if i % every == 0 or not last:
            mem = [s for s in weekly.members_at(snaps, d) if s in px.columns and pd.notna(px.at[d, s])]
            last = weekly.pick_momentum(mom.loc[d, mem], f["above"].loc[d, mem], n)
            held = {s: 1 / len(last) for s in last} if last else {}
        held = {s: w for s, w in held.items() if pd.notna(px.at[d, s]) and px.at[d, s] >= ma_x.at[d, s]}
        book[d] = dict(held)
    return book


def main() -> None:
    lines: list[str] = []

    def emit(t=""):
        print(t, flush=True)
        lines.append(t)

    px, snaps = weekly.load()
    f = weekly.build(px, snaps)
    ma20 = px.rolling(20, min_periods=20).mean()
    f_both = {**f, "above": f["above"] & (px > ma20)}
    books = {
        "Current rule (exit from the week after the pick)": weekly.momentum_book(px, snaps, f, lookback=26, n=20, every=4, exit_ma=20),
        "As live today (exit also in the pick week)": book_same_day_exit(px, snaps, f),
        "Entry filter: above the 200-day AND 100-day average": weekly.momentum_book(px, snaps, f_both, lookback=26, n=20,
                                                                                     every=4, exit_ma=20),
    }
    rf = load_cash_rate(str(ROOT / "market_data" / "SPY.csv"))
    rf_m = (rf.resample("ME").last() / 12).shift(1)
    res = {k: ms.monthly(weekly.simulate(b, f["ret"], weekly.COST)) for k, b in books.items()}
    res3 = {k: ms.monthly(weekly.simulate(b, f["ret"], 3 * weekly.COST)) for k, b in books.items()}
    idx = res[next(iter(res))].index
    idx = idx[(idx >= pd.Timestamp("2014-06-30")) & (idx <= pd.Timestamp(ms.MONTH_END))]
    rfm = rf_m.reindex(idx).fillna(0)

    emit("# Momentum sleeve: entry filter vs exit timing - generated tables\n")
    emit(f"Monthly, {idx[0]:%Y-%m} to {idx[-1]:%Y-%m}. Top 20 by 6-month return (skipping the latest week), re-picked "
         "every 4 weeks, sold below the 20-week (~100-day) average in between. Survivors-only prices; 0.10% per trade.\n")
    emit("| rule | return/yr | volatility | Sharpe | worst drop | at 3x costs | 2014-19 Sharpe | 2020-26 Sharpe | avg invested |")
    emit("|---|---|---|---|---|---|---|---|---|")
    for k, r in res.items():
        r = r.reindex(idx)
        s, a, b = ms.mstats(r, rfm), ms.mstats(r.loc[:"2019"], rfm), ms.mstats(r.loc["2020":], rfm)
        inv = np.mean([sum(v.values()) if isinstance(v, dict) else (1.0 if v else 0.0) for d, v in books[k].items()
                       if d >= idx[0]])
        emit(f"| {k} | {s['CAGR']:.1%} | {s['volatility']:.0%} | {s['Sharpe']:.2f} | {s['max drawdown']:.0%} | "
             f"{ms.mstats(res3[k].reindex(idx), rfm)['CAGR']:.1%} | {a['Sharpe']:.2f} | {b['Sharpe']:.2f} | {inv:.0%} |")
    # how often the pick-week exit bites
    cur = books["As live today (exit also in the pick week)"]
    picks_wk = [d for i, d in enumerate(f["dates"]) if i % 4 == 0]
    dropped = [20 - len(cur[d]) for d in picks_wk if d in cur]
    emit(f"\nAs live today, picks sold in their own pick week: {np.mean(dropped):.1f} of 20 on average "
         f"({np.mean([x > 0 for x in dropped]):.0%} of re-picks lose at least one).")
    yrs = pd.DataFrame({k: (1 + r.reindex(idx)).groupby(idx.year).prod() - 1 for k, r in res.items()})
    k_cur, k_live, k_new = list(res)
    emit(f"Entry filter beat the current rule in {int((yrs[k_new] > yrs[k_cur]).sum())} of {len(yrs)} years, "
         f"and the as-live version in {int((yrs[k_new] > yrs[k_live]).sum())}.")

    OUT.mkdir(exist_ok=True)
    (OUT / "momentum_entry.md").write_text("\n".join(lines) + "\n")
    print(f"\nwrote {OUT / 'momentum_entry.md'}")


if __name__ == "__main__":
    main()
