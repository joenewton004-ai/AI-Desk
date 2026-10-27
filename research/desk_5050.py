"""What-if: the desk as 50% overnight sleeve + 50% RSI dip-buying (owner's question, 2026-10-27). Not an amendment.

    python research/desk_5050.py

Drops the quality screen and momentum. The overnight sleeve as it runs live (12-month ranking, daily re-pick, both
checks); the RSI dips as in research/DESK_RSI.md (top-100 stocks above SMA200 with RSI(14) < 30, buy next open, sell
the open after a close above the 5-day SMA). The dips are invested only ~6% of the time, so how their 50% is used
decides almost everything:
  A  50% overnight + 50% dips in 5 slots of 10% of the desk, T-bills when a slot is idle
  B  the same with 10 slots of 5%
  C  shared: the dips take 10% a trade (at most 5); the overnight sleeve buys with everything else each night
     (between 50% and 100% of the desk)
Costs: overnight 0.02% each way (as researched) and 0.05% (stress); dips 0.05% and 0.20%. Same-day dip signals beyond
the free slots: lowest RSI first. Monthly, 2014-06 to 2026-09; survivors-only prices. Writes research/output/desk_5050.md.
"""

from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import desk_rsi as dr  # noqa: E402
import momentum_sleeve as ms  # noqa: E402

OUT = dr.OUT


def main() -> None:
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    lines: list[str] = []

    def emit(t=""):
        print(t, flush=True)
        lines.append(t)

    L = dr.load()
    q, mo, on_r, rf_d, inv, trades, rsi_at, oo, idx, rfm, prices, to_m = (L[k] for k in (
        "q", "mo", "on_r", "rf_d", "invested", "trades", "rsi_at", "oo", "idx", "rfm", "prices", "to_m"))
    days = on_r.index
    rfd = rf_d.reindex(days).fillna(0)
    spy = prices["adj"]["SPY"].loc[:dr.MONTH_END].pct_change().reindex(idx)

    def overnight(cost: float) -> pd.Series:                      # per unit invested; extra cost over the 0.02% base
        return on_r - 2 * (cost - 0.0002) * inv.reindex(days).fillna(False)

    def build(kind: str, on_cost: float, dip_cost: float) -> dict:
        on = overnight(on_cost)
        slot, mx = {"A": (0.10, 5), "B": (0.05, 10), "C": (0.10, 5)}[kind]
        w = dr.book(trades, rsi_at, days, slot, mx)
        held = w.sum(axis=1)
        dips = dr.overlay_daily(w, oo, dip_cost)
        if kind == "C":
            night = held.shift(1, fill_value=0.0)
            daily = (1.0 - night) * on + dips
            on_w = (1.0 - night).mean()
        else:
            daily = 0.5 * on + dips + (0.5 - held) * rfd
            on_w = 0.5
        return {"m": to_m(daily), "dips": to_m(dips), "held": held.mean(), "on_w": on_w,
                "dip_only": to_m(dips + (0.5 - held) * rfd) if kind != "C" else None}

    desks = {"Current desk (50% quality, 20% momentum, 30% overnight)": 0.5 * q + 0.2 * mo + to_m(0.3 * on_r)}
    emit("# What if the desk were 50% overnight + 50% RSI dips? - generated tables\n")
    emit(f"Monthly, {idx[0]:%Y-%m} to {idx[-1]:%Y-%m}. **Survivors-only prices.** Sharpe above T-bills. {len(trades):,} "
         "dip signals over the period. A what-if, not an amendment.\n")
    emit("| desk | overnight costs | dip costs | return/yr | volatility | Sharpe | worst drop | 2014-19 | 2020-26 | "
         "money in dips (avg) | overnight's share (avg) |")
    emit("|---|---|---|---|---|---|---|---|---|---|---|")

    def row(name, d, oc="", dc="", held="", onw=""):
        s, a, b = ms.mstats(d, rfm), ms.mstats(d.loc[:"2019"], rfm), ms.mstats(d.loc["2020":], rfm)
        emit(f"| {name} | {oc} | {dc} | {s['CAGR']:.1%} | {s['volatility']:.1%} | {s['Sharpe']:.2f} | "
             f"{s['max drawdown']:.1%} | {a['Sharpe']:.2f} | {b['Sharpe']:.2f} | {held} | {onw} |")

    row("Current desk (50% quality, 20% momentum, 30% overnight)", desks["Current desk (50% quality, 20% momentum, 30% overnight)"],
        "0.02%", "", "", "30%")
    labels = {"A": "A: 50% overnight + 50% dips (5 x 10%)", "B": "B: 50% overnight + 50% dips (10 x 5%)",
              "C": "C: shared - dips 10% each, overnight gets the rest"}
    keep = {}
    for kind in ("A", "B", "C"):
        for oc in (0.0002, 0.0005):
            for dc in (0.0005, 0.002):
                r = build(kind, oc, dc)
                keep[(kind, oc, dc)] = r
                row(labels[kind], r["m"], f"{oc:.2%}", f"{dc:.2%}", f"{r['held']:.1%}", f"{r['on_w']:.0%}")
    row("Overnight sleeve alone (100%)", to_m(on_r), "0.02%", "", "", "100%")
    r = keep[("A", 0.0002, 0.0005)]
    row("Dips alone (5 x 10% of the money, T-bills otherwise)", to_m(dr.overlay_daily(
        dr.book(trades, rsi_at, days, 0.20, 5), oo, 0.0005) + (1.0 - dr.book(trades, rsi_at, days, 0.20, 5).sum(axis=1)) * rfd),
        "", "0.05%", "", "")
    emit(ms.fmt_row("SPY", ms.mstats(spy, rfm)).replace("| SPY |", "| SPY | | |"))

    a = keep[("A", 0.0002, 0.0005)]["m"]
    c = keep[("C", 0.0002, 0.0005)]["m"]
    cur = desks["Current desk (50% quality, 20% momentum, 30% overnight)"]
    emit("\n## Year by year (overnight 0.02%, dips 0.05%)\n")
    emit("| year | current desk | A: 50/50 | C: shared | SPY |\n|---|---|---|---|---|")
    yr = lambda x: (1 + x).groupby(idx.year).prod() - 1  # noqa: E731
    for y, v in yr(cur).items():
        emit(f"| {y} | {v:+.1%} | {yr(a)[y]:+.1%} | {yr(c)[y]:+.1%} | {yr(spy)[y]:+.1%} |")
    emit("\n## The market's 10 worst months\n")
    emit("| month | SPY | current desk | A: 50/50 | C: shared |\n|---|---|---|---|---|")
    worst = spy.nsmallest(10).index.sort_values()
    for m in worst:
        emit(f"| {m:%Y-%m} | {spy[m]:+.1%} | {cur[m]:+.1%} | {a[m]:+.1%} | {c[m]:+.1%} |")
    emit(f"| average | {spy[worst].mean():+.1%} | {cur[worst].mean():+.1%} | {a[worst].mean():+.1%} | {c[worst].mean():+.1%} |")
    emit(f"\nMonthly correlation with SPY: current desk {cur.corr(spy):.2f}, A {a.corr(spy):.2f}, C {c.corr(spy):.2f}; "
         f"A's dips vs its overnight half {keep[('A', 0.0002, 0.0005)]['dips'].corr(to_m(on_r)):.2f}.")

    OUT.mkdir(exist_ok=True)
    (OUT / "desk_5050.md").write_text("\n".join(lines) + "\n")
    print(f"\nwrote {OUT / 'desk_5050.md'}")


if __name__ == "__main__":
    main()
