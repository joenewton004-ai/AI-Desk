"""Can the overnight sleeve trade less? Fewer stocks vs keeping tomorrow's repeat picks through the day.

    python research/overnight_turnover.py

The live sleeve (amendment 82c84226: top 20 by 12-month return, re-picked daily, ranked the evening before, with the
SPY 200-day and picks-day checks) sells everything at each open and buys tonight's picks at each close: the whole
book trades twice a day. Costs are a percentage of the money moved, so the NUMBER of stocks barely changes them;
the only way to trade less is to move less money:
  A  live: sell all at the open, buy tonight's picks near the close
  B  keep repeats: a stock that is also in tonight's picks isn't sold at the open - it's held through the day
     (earning that day's open-to-close move) - only the changes trade. On a cash night (a check fails at the buy) the
     repeats are sold at the close
  C  top 10 instead of 20 (same rules as A) - for completeness: same cost per dollar, more concentrated
  D  B with top 10
Costs 0.02%, 0.05% and 0.10% each way. Daily, 2014-04 to 2026-10, survivors-only prices; the picks-day cut-off is the
10th percentile of each version's own history (as research/overnight_v2.py). Writes research/output/overnight_turnover.md.
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

import lookbacks as lb  # noqa: E402
import overnight as ov  # noqa: E402
import overnight_picks_check as opc  # noqa: E402
import overnight_regime as orr  # noqa: E402
import swing  # noqa: E402
from ai_desk.data import load_cash_rate  # noqa: E402

OUT = orr.OUT
COSTS = (0.0002, 0.0005, 0.001)


def simulate(on: pd.DataFrame, day: pd.DataFrame, held: pd.DataFrame, flag: pd.Series, rf: pd.Series,
             cost: float, keep_repeats: bool) -> tuple[pd.Series, float]:
    """Pure: daily returns (night ending at day t's open + day t), and the average share of the book traded a day.

    held[t] = the picks for the night ending at t's open (bought at t-1's close); flag[t] = that night was in cash.
    A: sell everything at t's open. B: names also held the next night (held[t+1]) stay through day t."""
    n = held.sum(axis=1).replace(0, np.nan)
    idx = held.index
    nxt = held.shift(-1, fill_value=False)
    flag_next = flag.shift(-1, fill_value=False)
    invested = held & ~flag.to_numpy()[:, None]                         # the night actually held (not a cash night)
    night = on.where(invested).sum(axis=1) / n
    if keep_repeats:
        keep = invested & nxt                                           # held tonight and picked again for the next night
        daypart = day.where(keep).sum(axis=1) / n
        sold_open = (invested & ~nxt).sum(axis=1)
        sold_close = (keep & flag_next.to_numpy()[:, None]).sum(axis=1)  # next night in cash: sell the repeats at the close
        bought = (nxt & ~flag_next.to_numpy()[:, None] & ~keep).sum(axis=1)
        traded = (sold_open + sold_close + bought) / n
    else:
        daypart = pd.Series(0.0, index=idx)
        traded = (invested.sum(axis=1) + (nxt & ~flag_next.to_numpy()[:, None]).sum(axis=1)) / n
    cash_night = flag.reindex(idx).fillna(False) | held.sum(axis=1).eq(0)
    r = night.fillna(0) + daypart.fillna(0) - traded.fillna(0) * cost
    r = r.where(~cash_night, rf.reindex(idx).fillna(0) + daypart.fillna(0) - traded.fillna(0) * cost)
    return r, float(traded.mean())


def main() -> None:
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    lines: list[str] = []

    def emit(t=""):
        print(t, flush=True)
        lines.append(t)

    d = swing.fetch_daily([])
    o, c, v = (d[k].astype(float).loc[:ov.END] for k in ("open", "close", "volume"))
    snaps = {}
    for m in (3, 6, 9, 12):
        snaps.update({k: list(s.index) for k, s in pickle.loads((orr.CACHE / f"snapshots_m{m}.pkl").read_bytes()).items()})
    dates, symbols = c.index, list(c.columns)
    member = pd.DataFrame(swing.membership(dict(sorted(snaps.items())), dates, symbols), index=dates, columns=symbols)
    eligible = member & (c > 10) & ((c * v).rolling(50, min_periods=40).mean() > 20e6)
    on, day = ov.split_returns(o, c)
    rf = (load_cash_rate(str(ROOT / "market_data" / "SPY.csv")).reindex(dates, method="ffill") / 252).fillna(0)
    mkt = pd.read_csv(ROOT / "market_data" / "SPY.csv", index_col=0, parse_dates=True)["close"].reindex(dates).ffill()
    spy_flag = (mkt < mkt.rolling(200).mean()).shift(1).fillna(False).astype(bool)
    ret12 = c / c.shift(252) - 1

    emit("# Can the overnight sleeve trade less? - generated tables\n")
    emit("**Survivors-only prices**; the 750 largest US companies; the live rules (12-month ranking, daily re-pick "
         "ranked the evening before, SPY 200-day and picks-day checks). 'Traded' = share of the book bought or sold "
         "per day (A: up to 2.0 - everything out at the open, everything back near the close; less on cash nights).\n")
    emit("| version | costs each way | return/yr | volatility | Sharpe | worst drop | 2014-19 | 2020-26 | traded a day |")
    emit("|---|---|---|---|---|---|---|---|---|")
    keepers = {}
    for n in (20, 10):
        held = lb.daily_top(ret12, eligible, n).shift(2, fill_value=False).loc[ov.START:ov.END]
        idx = held.index
        pday = day.shift(1).where(held).mean(axis=1).reindex(idx)
        flag = (spy_flag.reindex(idx).fillna(False) | opc.bad_day(pday, 0.10)).astype(bool)
        o_, d_ = on.reindex(idx), day.reindex(idx)
        for keep in (False, True):
            name = {(20, False): "A: live (sell all at the open)", (20, True): "B: keep repeats through the day",
                    (10, False): "C: top 10, sell all", (10, True): "D: top 10, keep repeats"}[(n, keep)]
            for cost in COSTS:
                r, traded = simulate(o_, d_, held, flag, rf, cost, keep)
                s, a, b = orr.stats(r, rf), orr.stats(r.loc[:ov.MID], rf), orr.stats(r.loc[ov.MID:], rf)
                emit(f"| {name} | {cost:.2%} | {s['CAGR']:.1%} | {s['vol']:.0%} | {s['Sharpe']:.2f} | {s['maxdd']:.0%} | "
                     f"{a['Sharpe']:.2f} | {b['Sharpe']:.2f} | {traded:.2f} |")
            if n == 20:
                keepers[keep] = (held, flag)
    held, flag = keepers[True]
    nxt = held.shift(-1, fill_value=False)
    rep = (held & nxt).sum(axis=1) / held.sum(axis=1).replace(0, np.nan)
    dd = day.reindex(held.index).where(held & nxt)
    emit(f"\nOn an average day {rep.mean():.0%} of tonight's 20 stocks were also tonight's picks the night before. Their "
         f"open-to-close move on the day between: {dd.stack().mean():+.3%} on average (median "
         f"{dd.stack().median():+.3%}); the same stocks' night: {on.reindex(held.index).where(held & nxt).stack().mean():+.3%}.")

    OUT.mkdir(exist_ok=True)
    (OUT / "overnight_turnover.md").write_text("\n".join(lines) + "\n")
    print(f"\nwrote {OUT / 'overnight_turnover.md'}")


if __name__ == "__main__":
    main()
