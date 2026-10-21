"""The desk with the overnight sleeve in place of the SPY momentum sleeve.

    python research/desk_overnight.py

Desk today: 50% quality screen + 20% plain momentum (100-day exit) + 30% SPY with its 12-month
switch (in SPY when its 12-month return is positive, else T-bills). Proposed: the same 50/20, with
the 30% in the overnight sleeve (research/OVERNIGHT.md: the 20 stocks with the highest 12-month
average overnight return, re-picked monthly, held only from the close to the next open).

Monthly returns, 2014-2026, survivors-only prices (flatter every sleeve). The overnight sleeve is
shown at several costs per trade each way, because its result depends on them; its cash sits idle
during the day (no interest counted - conservative). Also: correlation between sleeves, and how each
desk did in the market's worst months. Writes research/output/desk_overnight.md; findings in
research/DESK_OVERNIGHT.md.
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

import momentum_sleeve as ms  # noqa: E402
import overnight as ov  # noqa: E402
import swing  # noqa: E402
import weekly  # noqa: E402
from ai_desk.data import load_cash_rate  # noqa: E402
from ai_desk.fundamentals import screen_backtest as sb  # noqa: E402

CACHE = ROOT / "data" / "backtest"
OUT = Path(__file__).resolve().parent / "output"
MONTH_END = "2026-09-30"
COSTS = (0.0, 0.0002, 0.0003, 0.0005)


def overnight_daily(cost: float) -> pd.Series:
    d = swing.fetch_daily([])
    o, c, v = (d[k].astype(float).loc[:ov.END] for k in ("open", "close", "volume"))
    snaps = {}
    for m in (3, 6, 9, 12):
        snaps.update({k: list(s.index) for k, s in pickle.loads((CACHE / f"snapshots_m{m}.pkl").read_bytes()).items()})
    dates, symbols = c.index, list(c.columns)
    member = pd.DataFrame(swing.membership(dict(sorted(snaps.items())), dates, symbols), index=dates, columns=symbols)
    eligible = member & (c > 10) & ((c * v).rolling(50, min_periods=40).mean() > 20e6)
    on, _ = ov.split_returns(o, c)
    pick = ov.monthly_picks(on.rolling(252, min_periods=200).mean(), eligible, 20).shift(1, fill_value=False)
    r = on.where(pick).mean(axis=1)
    invested = pick.any(axis=1)
    return (r.fillna(0) - 2 * cost * invested).loc[ov.START:ov.END]


def main() -> None:
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    lines: list[str] = []

    def emit(t=""):
        print(t, flush=True)
        lines.append(t)

    # the desk's three current sleeves, monthly (same construction as research/momentum_sleeve.py)
    px, snaps = weekly.load()
    f = weekly.build(px, snaps)
    mom = ms.monthly(weekly.simulate(weekly.momentum_book(px, snaps, f, lookback=26, n=20, every=4, exit_ma=20),
                                     f["ret"], weekly.COST))
    prices = pickle.loads((CACHE / "prices.pkl").read_bytes())
    for k in prices:
        prices[k] = prices[k].groupby(level=0).last() if k != "splits" else prices[k].groupby(level=0).max()
    s_snaps = {}
    for m in (3, 6, 9, 12):
        s_snaps.update(pickle.loads((CACHE / f"snapshots_m{m}.pkl").read_bytes()))
    screen = sb.simulate({"t": sb.books(dict(sorted(s_snaps.items())), 25)["screen_top"]}, prices, MONTH_END)["t"]
    rf = load_cash_rate(str(ROOT / "market_data" / "SPY.csv"))
    rf_m = (rf.resample("ME").last() / 12).shift(1)
    spy_m = prices["adj"]["SPY"].loc[:MONTH_END]
    on_ = (spy_m / spy_m.shift(12) - 1 > 0).shift(1)
    idx = screen.index.intersection(mom.index)
    idx = idx[(idx >= pd.Timestamp("2014-06-30")) & (idx <= pd.Timestamp(MONTH_END))]
    spy_mom = spy_m.pct_change().reindex(idx).where(on_.reindex(idx).fillna(True).astype(bool), rf_m.reindex(idx))
    spy_ret = spy_m.pct_change().reindex(idx)
    rfm = rf_m.reindex(idx).fillna(0)
    ovn = {cost: (1 + overnight_daily(cost)).resample("ME").prod().reindex(idx) - 1 for cost in COSTS}

    emit("# The desk with the overnight sleeve instead of SPY momentum - generated tables\n")
    emit(f"Monthly, {idx[0]:%Y-%m} to {idx[-1]:%Y-%m}. Survivors-only prices. Desk = 50% quality screen + 20% momentum + "
         "30% third sleeve.\n")
    emit("## 1. The third sleeve on its own\n")
    emit("| | return/yr | volatility | Sharpe | worst drop |\n|---|---|---|---|---|")
    emit(ms.fmt_row("SPY with its 12-month switch (current)", ms.mstats(spy_mom, rfm)))
    for cost, r in ovn.items():
        emit(ms.fmt_row(f"Overnight sleeve, costs {cost:.2%} each way", ms.mstats(r, rfm)))
    emit(ms.fmt_row("SPY, always invested", ms.mstats(spy_ret, rfm)))

    emit("\n## 2. The whole desk\n")
    emit("| desk | return/yr | volatility | Sharpe | worst drop | 2014-19 Sharpe | 2020-26 Sharpe |\n|---|---|---|---|---|---|---|")
    desks = {"Current: 30% SPY momentum": 0.5 * screen.reindex(idx) + 0.2 * mom.reindex(idx) + 0.3 * spy_mom}
    for cost, r in ovn.items():
        desks[f"30% overnight, costs {cost:.2%}"] = 0.5 * screen.reindex(idx) + 0.2 * mom.reindex(idx) + 0.3 * r
    desks["(15% SPY momentum + 15% overnight at 0.02%)"] = (0.5 * screen.reindex(idx) + 0.2 * mom.reindex(idx)
                                                           + 0.15 * spy_mom + 0.15 * ovn[0.0002])
    for k, d in desks.items():
        s, a, b = ms.mstats(d, rfm), ms.mstats(d.loc[:"2019"], rfm), ms.mstats(d.loc["2020":], rfm)
        emit(f"| {k} | {s['CAGR']:.1%} | {s['volatility']:.1%} | {s['Sharpe']:.2f} | {s['max drawdown']:.1%} | "
             f"{a['Sharpe']:.2f} | {b['Sharpe']:.2f} |")

    emit("\n## 3. How the sleeves move together (monthly correlation)\n")
    cm = pd.DataFrame({"quality screen": screen.reindex(idx), "momentum": mom.reindex(idx), "SPY momentum": spy_mom,
                       "overnight (0.02%)": ovn[0.0002]}).corr()
    emit("| | " + " | ".join(cm.columns) + " |\n|" + "---|" * (len(cm.columns) + 1))
    for k, r in cm.iterrows():
        emit(f"| {k} | " + " | ".join(f"{x:.2f}" for x in r) + " |")

    emit("\n## 4. The market's 10 worst months: SPY vs each desk\n")
    worst = spy_ret.nsmallest(10).index.sort_values()
    cur, new = desks["Current: 30% SPY momentum"], desks["30% overnight, costs 0.02%"]
    emit("| month | SPY | current desk | desk with overnight (0.02%) | overnight sleeve |\n|---|---|---|---|---|")
    for m in worst:
        emit(f"| {m:%Y-%m} | {spy_ret[m]:+.1%} | {cur[m]:+.1%} | {new[m]:+.1%} | {ovn[0.0002][m]:+.1%} |")
    emit(f"| average | {spy_ret[worst].mean():+.1%} | {cur[worst].mean():+.1%} | {new[worst].mean():+.1%} | "
         f"{ovn[0.0002][worst].mean():+.1%} |")

    emit("\n## 5. Year by year (desk with overnight at 0.02% minus the current desk)\n")
    yc = (1 + cur).groupby(cur.index.year).prod() - 1
    yn = (1 + new).groupby(new.index.year).prod() - 1
    emit("| year | current | with overnight | difference |\n|---|---|---|---|")
    for y in yc.index:
        emit(f"| {y} | {yc[y]:+.1%} | {yn[y]:+.1%} | {yn[y] - yc[y]:+.1%} |")
    emit(f"\nThe overnight desk did better in {int((yn > yc).sum())} of {len(yc)} years.")

    OUT.mkdir(exist_ok=True)
    (OUT / "desk_overnight.md").write_text("\n".join(lines) + "\n")
    print(f"\nwrote {OUT / 'desk_overnight.md'}")


if __name__ == "__main__":
    main()
