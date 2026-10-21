"""Overnight vs daytime returns, stock by stock: who earns overnight, does it persist, can it be traded?

    python research/overnight.py

Overnight = previous close to today's open; daytime = today's open to close. Over 2014-2026 most of
the average large stock's gain came overnight (research/SWING_EDGES.md). Lou, Polk & Skouras (2019,
"A tug of war: overnight versus intraday expected returns", Journal of Financial Economics) found
the split is persistent per stock: stocks with high overnight returns in the past keep earning
them. Tested here:

  1. which stocks earned the most overnight, 2014-2026 (descriptive - picked with hindsight)
  2. persistence: each month, rank stocks by their average overnight return over the past 12
     months; measure the NEXT month's overnight and daytime returns by tenth (out of sample)
  3. trading it: each month take the 20 highest past-overnight stocks and hold them only overnight
     (buy at the close, sell at the open, every day), costs 0.02% / 0.05% each way per trade;
     compared with holding the same 20 all day and night
  4. the current list (trailing 12 months to the last full day) - research, not a recommendation

Universe = the 750 largest US companies at each quarter-end (point-in-time), price over $10 and
$20M a day traded; daily Yahoo prices (data/backtest/daily_ohlcv.pkl), survivors-only. Dividend
adjustment removes ex-dividend gaps. Earnings are mostly announced outside market hours, so part of
any stock's overnight return is earnings news. Writes research/output/overnight.md; findings in
research/OVERNIGHT.md.
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

import swing  # noqa: E402
from ai_desk.data import load_cash_rate  # noqa: E402

CACHE = ROOT / "data" / "backtest"
OUT = Path(__file__).resolve().parent / "output"
START, END, MID = "2014-04-01", "2026-10-20", "2020-01-01"


# --- pure pieces (unit-tested) --------------------------------------------------------

def split_returns(o: pd.DataFrame, c: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(overnight, daytime) per stock, dated by the day they end. A >50% move is treated as bad data."""
    on = o / c.shift(1) - 1
    day = c / o - 1
    return on.where(on.abs() < 0.5), day.where(day.abs() < 0.5)


def ann(mean_daily: float) -> float:
    return (1 + mean_daily) ** 252 - 1 if pd.notna(mean_daily) else np.nan


def monthly_picks(score: pd.DataFrame, eligible: pd.DataFrame, n: int) -> pd.DataFrame:
    """At each month's last trading day, True for the n highest-score eligible stocks; held all next month."""
    dates = score.index
    month_end = np.r_[dates.month[1:] != dates.month[:-1], True]
    pick = pd.DataFrame(False, index=dates, columns=score.columns)
    current = pd.Series(False, index=score.columns)
    for i, d in enumerate(dates):
        pick.iloc[i] = current.to_numpy()        # today's holdings were chosen at an earlier month-end
        if month_end[i]:
            s = score.loc[d].where(eligible.loc[d])
            top = s.dropna().nlargest(n).index
            current = pd.Series(score.columns.isin(top), index=score.columns)
    return pick


# --- the experiment ------------------------------------------------------------------

def main() -> None:
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    lines: list[str] = []

    def emit(t=""):
        print(t, flush=True)
        lines.append(t)

    d = swing.fetch_daily([])
    o, c, v = (d[k].astype(float).loc[:END] for k in ("open", "close", "volume"))
    snaps = {}
    for m in (3, 6, 9, 12):
        snaps.update({k: list(s.index) for k, s in pickle.loads((CACHE / f"snapshots_m{m}.pkl").read_bytes()).items()})
    dates, symbols = c.index, list(c.columns)
    member = pd.DataFrame(swing.membership(dict(sorted(snaps.items())), dates, symbols), index=dates, columns=symbols)
    liquid = (c > 10) & ((c * v).rolling(50, min_periods=40).mean() > 20e6)
    eligible = member & liquid
    on, day = split_returns(o, c)
    rf = (load_cash_rate(str(ROOT / "market_data" / "SPY.csv")).reindex(dates, method="ffill") / 252).shift(1).fillna(0)
    sl = slice(START, END)

    emit("# Overnight vs daytime, stock by stock - generated tables\n")
    emit(f"Daily, {START} to {END}; the 750 largest US companies at each quarter-end (point-in-time), price over $10, "
         "$20M a day traded. Survivors-only Yahoo prices. Overnight = previous close to open; daytime = open to close.\n")

    # 1. who earned overnight (hindsight)
    elig_on, elig_day = on.where(eligible.shift(1, fill_value=False)).loc[sl], day.where(eligible).loc[sl]
    n_days = elig_on.notna().sum()
    stats_ = pd.DataFrame({"days": n_days, "overnight": elig_on.mean().map(ann), "daytime": elig_day.mean().map(ann)})
    stats_ = stats_[stats_["days"] >= 750]
    stats_["gap"] = stats_["overnight"] - stats_["daytime"]
    emit("## 1. Which stocks earned the most overnight (2014-2026, picked with hindsight)\n")
    emit(f"{len(stats_)} stocks with 3+ years in the universe. Median stock: overnight {stats_['overnight'].median():+.1%}/yr, "
         f"daytime {stats_['daytime'].median():+.1%}/yr; overnight beat daytime for "
         f"{(stats_['gap'] > 0).mean():.0%} of stocks.\n")
    emit("| stock | years in universe | overnight /yr | daytime /yr |\n|---|---|---|---|")
    for s, r in stats_.sort_values("overnight", ascending=False).head(15).iterrows():
        emit(f"| {s} | {r['days'] / 252:.1f} | {r['overnight']:+.1%} | {r['daytime']:+.1%} |")
    emit("\nThe other end - stocks that LOST money overnight:\n")
    emit("| stock | years in universe | overnight /yr | daytime /yr |\n|---|---|---|---|")
    for s, r in stats_.sort_values("overnight").head(10).iterrows():
        emit(f"| {s} | {r['days'] / 252:.1f} | {r['overnight']:+.1%} | {r['daytime']:+.1%} |")

    # 2. persistence, out of sample
    past_on = on.rolling(252, min_periods=200).mean()
    past_day = day.rolling(252, min_periods=200).mean()
    month_end = np.r_[dates.month[1:] != dates.month[:-1], True]
    me = [i for i in np.flatnonzero(month_end) if dates[i] >= pd.Timestamp(START)]
    rows = []
    for a, b in zip(me, me[1:]):
        s = past_on.iloc[a].where(eligible.iloc[a]).dropna()
        if len(s) < 100:
            continue
        dec = pd.qcut(s.rank(method="first"), 10, labels=False)
        nxt_on = on.iloc[a + 1:b + 1][s.index].mean()
        nxt_day = day.iloc[a + 1:b + 1][s.index].mean()
        for k in range(10):
            names = dec.index[dec == k]
            rows.append({"date": dates[a], "tenth": k + 1, "on": nxt_on[names].mean(), "day": nxt_day[names].mean()})
    p = pd.DataFrame(rows)
    emit("\n## 2. Does it persist? Ranked on the past 12 months' overnight return, measured the NEXT month\n")
    emit("Average daily return in the following month, annualised. Tenth 10 = the strongest past overnight earners.\n")
    emit("| tenth | next-month overnight /yr | next-month daytime /yr | 24 hours /yr |\n|---|---|---|---|")
    for k, g in p.groupby("tenth"):
        emit(f"| {k} | {ann(g['on'].mean()):+.1%} | {ann(g['day'].mean()):+.1%} | "
             f"{ann((1 + g['on'].mean()) * (1 + g['day'].mean()) - 1):+.1%} |")
    top, bot = p[p["tenth"] == 10].set_index("date"), p[p["tenth"] == 1].set_index("date")
    spread = top["on"] - bot["on"]
    emit(f"\nTop tenth minus bottom tenth, overnight: {spread.mean() * 1e4:+.1f} basis points a day "
         f"(t = {spread.mean() / (spread.std() / np.sqrt(len(spread))):.1f}, positive in {(spread > 0).mean():.0%} of "
         f"{len(spread)} months; 2014-19 {spread.loc[:MID].mean() * 1e4:+.1f}, 2020-26 {spread.loc[MID:].mean() * 1e4:+.1f}).")
    dspread = top["day"] - bot["day"]
    emit(f"Same, daytime: {dspread.mean() * 1e4:+.1f} basis points a day (t = "
         f"{dspread.mean() / (dspread.std() / np.sqrt(len(dspread))):.1f}) - the tug of war: what goes up overnight "
         "tends to give some back in the day.")

    # 3. trading it
    pick = monthly_picks(past_on, eligible, 20)
    emit("\n## 3. Trading it: the 20 strongest past overnight earners, re-picked monthly\n")
    emit("| | return/yr | volatility | Sharpe | worst drop | 2014-19 | 2020-26 |\n|---|---|---|---|---|---|---|")
    held_on = pick.shift(1, fill_value=False)          # chosen at a close, first held overnight into the next open

    def series(r: pd.DataFrame, mask: pd.DataFrame, cost_per_day: float, cash_rf: bool) -> pd.Series:
        x = r.where(mask).mean(axis=1)
        x = x.fillna(0.0) - cost_per_day
        return x.loc[sl] + (rf.loc[sl] if cash_rf else 0)

    def row(name, r):
        eq = (1 + r).cumprod()
        s, a, b = swing.stats(eq, rf), swing.stats(eq.loc[:MID], rf), swing.stats(eq.loc[MID:], rf)
        emit(f"| {name} | {s['CAGR']:.1%} | {s['volatility']:.0%} | {s['Sharpe']:.2f} | {s['max drawdown']:.0%} | "
             f"{a['CAGR']:.1%} ({a['Sharpe']:.2f}) | {b['CAGR']:.1%} ({b['Sharpe']:.2f}) |")

    on_held = on.where(held_on)
    day_held = day.where(pick)
    for cost in (0.0, 0.0002, 0.0005):
        # overnight only: the money sits in cash during the day (earning ~nothing for 6.5 hours; ignored)
        r = on_held.mean(axis=1).fillna(0) - (2 * cost)
        row(f"Overnight only (buy close, sell open), costs {cost:.2%} each way", r.loc[sl])
    both = ((1 + on_held.mean(axis=1).fillna(0)) * (1 + day_held.mean(axis=1).fillna(0)) - 1)
    row("Same 20 stocks held day and night (monthly re-pick, no daily trading)", both.loc[sl])
    uni = ((1 + on.where(eligible.shift(1, fill_value=False)).mean(axis=1)) *
           (1 + day.where(eligible).mean(axis=1)) - 1).fillna(0)
    row("Average stock, held day and night", uni.loc[sl])
    spy = pd.read_csv(ROOT / "market_data" / "SPY.csv", index_col=0, parse_dates=True)
    row("SPY overnight only, costs 0.02% each way", (spy["open"] / spy["close"].shift(1) - 1 - 0.0004).loc[sl])

    # 3b. robustness: other list sizes and look-backs, and the cost that wipes it out
    emit("\n### Robustness (overnight only)\n")
    emit("| variant | zero cost | at 0.02% each way | at 0.03% | break-even cost each way |\n|---|---|---|---|---|")
    for name, look, n in (("20 stocks, 12-month look-back (base)", 252, 20), ("10 stocks", 252, 10),
                          ("50 stocks", 252, 50), ("20 stocks, 6-month look-back", 126, 20),
                          ("20 stocks, 3-month look-back", 63, 20)):
        sc = on.rolling(look, min_periods=int(look * 0.8)).mean()
        pk = monthly_picks(sc, eligible, n).shift(1, fill_value=False)
        g = on.where(pk).mean(axis=1).fillna(0).loc[sl]
        invested = pk.loc[sl].any(axis=1)
        cagr = lambda r: (1 + r).prod() ** (252 / len(r)) - 1  # noqa: E731
        # break-even: the cost per side at which the return/yr falls to the T-bill rate
        lo_c, hi_c = 0.0, 0.002
        target = cagr(rf.loc[sl])
        for _ in range(40):
            mid = (lo_c + hi_c) / 2
            if cagr(g - 2 * mid * invested) > target:
                lo_c = mid
            else:
                hi_c = mid
        emit(f"| {name} | {cagr(g):.1%} | {cagr(g - 0.0004 * invested):.1%} | {cagr(g - 0.0006 * invested):.1%} | "
             f"{lo_c:.3%} |")

    # 4. today's list
    emit("\n## 4. The current list: highest average overnight return over the past 12 months (to "
         f"{dates[-1].date()})\n")
    emit("Research, not a recommendation - section 2 says how much of this tends to carry into the next month.\n")
    last = dates[-1]
    s = past_on.loc[last].where(eligible.loc[last]).dropna().nlargest(20)
    emit("| stock | overnight, past 12 months /yr | daytime, past 12 months /yr | 24 hours |\n|---|---|---|---|")
    for sym, x in s.items():
        dd = past_day.at[last, sym]
        emit(f"| {sym} | {ann(x):+.0%} | {ann(dd):+.0%} | {ann((1 + x) * (1 + dd) - 1):+.0%} |")

    OUT.mkdir(exist_ok=True)
    (OUT / "overnight.md").write_text("\n".join(lines) + "\n")
    print(f"\nwrote {OUT / 'overnight.md'}")


if __name__ == "__main__":
    main()
