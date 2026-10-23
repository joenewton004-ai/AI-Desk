"""Overnight sleeve: does the fear index (VIX) or a tech sell-off say when to change what it holds?

    python research/overnight_regime.py

The sleeve holds the 20 stocks with the highest average overnight return over 12 months (re-picked monthly) from
each close to the next open (research/OVERNIGHT.md). Those are mostly fast-moving tech/AI hardware names. The
idea tested: in fearful markets, switch to defensive stocks (or cash) for the night.

1. Conditional averages: the sleeve's overnight return grouped by the VIX level and its change the day before,
   by SPY's trend, and after days when tech lagged defensive stocks - next to the low-beta and defensive-industry
   versions of the same rule and the average stock.
2. Switching rules, each decided from data known before the 3:55pm buy (the VIX of the PREVIOUS close; a
   second version lags one more day):
   - cash when VIX > 25 / > 30, or after the VIX rose 15%+ in a day
   - the same, but into a defensive list instead of cash: the top 20 by overnight score among low-beta stocks
     (beta to SPY under 0.8, past year) - also tried as the top 20 in defensive industries (SIC: food and tobacco,
     utilities, grocery, insurance, health services, drugs)
   - always: at most 4 stocks from one industry (SIC 2-digit) - spreads the tech concentration
Each night is bought and sold anyway, so switching lists costs nothing extra. 0.02% per trade each way;
survivors-only prices; the 750 largest US companies at each quarter-end. Writes
research/output/overnight_regime.md; findings in research/OVERNIGHT_REGIME.md.
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

import overnight as ov  # noqa: E402
import swing  # noqa: E402
from ai_desk.data import load_cash_rate  # noqa: E402

CACHE = ROOT / "data" / "backtest"
OUT = Path(__file__).resolve().parent / "output"
COST = 0.0002
DEFENSIVE_SIC = {20, 21, 49, 54, 63, 80, 28}
TECH_SIC = {35, 36, 38, 73}


# --- pure pieces (unit-tested) --------------------------------------------------------

def capped_picks(score: pd.DataFrame, eligible: pd.DataFrame, group: pd.Series, n: int, cap: int) -> pd.DataFrame:
    """Like overnight.monthly_picks, but at most `cap` stocks from one group (industry)."""
    dates = score.index
    month_end = np.r_[dates.month[1:] != dates.month[:-1], True]
    pick = pd.DataFrame(False, index=dates, columns=score.columns)
    current = pd.Series(False, index=score.columns)
    for i, d in enumerate(dates):
        pick.iloc[i] = current.to_numpy()
        if month_end[i]:
            s = score.loc[d].where(eligible.loc[d]).dropna().sort_values(ascending=False)
            taken, count = [], {}
            for sym in s.index:
                g = group.get(sym, "?")
                if count.get(g, 0) < cap:
                    taken.append(sym)
                    count[g] = count.get(g, 0) + 1
                if len(taken) == n:
                    break
            current = pd.Series(score.columns.isin(taken), index=score.columns)
    return pick


def nightly(on: pd.DataFrame, pick: pd.DataFrame, cost: float) -> pd.Series:
    """The book's return each night (dated by the morning it ends), after costs on both sides."""
    r = on.where(pick).mean(axis=1)
    return r.fillna(0.0) - 2 * cost * pick.any(axis=1)


def switch(base: pd.Series, alt: pd.Series, use_alt: pd.Series) -> pd.Series:
    """Night by night: `alt` where the signal (already lagged to what was known at the buy) says so."""
    return base.where(~use_alt.reindex(base.index).fillna(False).astype(bool), alt)


def stats(r: pd.Series, rf: pd.Series) -> dict:
    eq = (1 + r).cumprod()
    ex = r - rf.reindex(r.index).fillna(0)
    return {"CAGR": eq.iloc[-1] ** (252 / len(r)) - 1, "vol": r.std() * np.sqrt(252),
            "Sharpe": ex.mean() / ex.std() * np.sqrt(252) if ex.std() > 0 else np.nan,
            "maxdd": (eq / eq.cummax() - 1).min()}


# --- the experiment ---------------------------------------------------------------------

def main() -> None:
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    lines: list[str] = []

    def emit(t=""):
        print(t, flush=True)
        lines.append(t)

    d = swing.fetch_daily([])
    o, c, v = (d[k].astype(float).loc[:ov.END] for k in ("open", "close", "volume"))
    snaps = {}
    sic = {}
    for m in (3, 6, 9, 12):
        for k, s in pickle.loads((CACHE / f"snapshots_m{m}.pkl").read_bytes()).items():
            snaps[k] = list(s.index)
            if "sic2" in s:
                sic.update({sym: int(x) for sym, x in s["sic2"].dropna().items()})
    dates, symbols = c.index, list(c.columns)
    member = pd.DataFrame(swing.membership(dict(sorted(snaps.items())), dates, symbols), index=dates, columns=symbols)
    eligible = member & (c > 10) & ((c * v).rolling(50, min_periods=40).mean() > 20e6)
    on, day = ov.split_returns(o, c)
    score = on.rolling(252, min_periods=200).mean()

    mkt = pd.read_csv(ROOT / "market_data" / "SPY.csv", index_col=0, parse_dates=True)["close"].reindex(dates).ffill()
    vix = pd.read_csv(ROOT / "market_data" / "VIX.csv", index_col=0, parse_dates=True)["close"].reindex(dates).ffill()
    rc = c.pct_change()
    rm = mkt.pct_change()
    roll = lambda x: x.rolling(252, min_periods=200).mean()  # noqa: E731
    cov = roll(rc.mul(rm, axis=0)) - roll(rc).mul(roll(rm), axis=0)
    beta = cov.div(rm.rolling(252, min_periods=200).var(ddof=0), axis=0)
    grp = pd.Series(sic)
    defensive = pd.DataFrame(np.broadcast_to(np.isin(symbols, [s for s, g in sic.items() if g in DEFENSIVE_SIC]),
                                             c.shape), index=dates, columns=symbols)
    tech = np.isin(symbols, [s for s, g in sic.items() if g in TECH_SIC])

    # holdings for the night ending at day t (bought at close t-1) - same timing as research/desk_overnight.py
    picks = {
        "base": ov.monthly_picks(score, eligible, 20).shift(1, fill_value=False),
        "lowbeta": ov.monthly_picks(score, eligible & (beta < 0.8), 20).shift(1, fill_value=False),
        "defind": ov.monthly_picks(score, eligible & defensive, 20).shift(1, fill_value=False),
        "cap4": capped_picks(score, eligible, grp, 20, 4).shift(1, fill_value=False),
    }
    nights = {k: nightly(on, p, COST).loc[ov.START:ov.END] for k, p in picks.items()}
    idx = nights["base"].index
    rf = (load_cash_rate(str(ROOT / "market_data" / "SPY.csv")).reindex(dates, method="ffill") / 252).loc[idx].fillna(0)
    cash = rf                                                     # out for the night: T-bills, no trading cost
    avg_on = on.where(eligible.shift(1, fill_value=False)).mean(axis=1).loc[idx]

    # what was known at the buy (close t-1, really 3:55pm): VIX and SPY at close t-1; "lag2" = close t-2
    vix1, vix2 = vix.shift(1).reindex(idx), vix.shift(2).reindex(idx)
    dv1 = (vix / vix.shift(1) - 1).shift(1).reindex(idx)
    dv2 = (vix / vix.shift(1) - 1).shift(2).reindex(idx)
    trend1 = (mkt < mkt.rolling(200).mean()).shift(1).reindex(idx).fillna(False).astype(bool)
    day_c2c = rc.where(eligible)
    tech_gap = (day_c2c.loc[:, tech].mean(axis=1) -
                day_c2c.where(defensive).mean(axis=1)).shift(1).reindex(idx)      # tech minus defensive, day t-1

    emit("# Overnight sleeve vs the fear index - generated tables\n")
    emit(f"Nights from {idx[0].date()} to {idx[-1].date()} ({len(idx):,}). The 750 largest US companies, **survivors-only "
         "prices**, 0.02% per trade each way, cash at T-bills. Signals from the close BEFORE the buy.\n")
    emit("## 1. Average night (bp) by what the market looked like the day before\n")
    emit("| condition (day before) | nights | sleeve (top 20) | low-beta top 20 | defensive-industry top 20 | average stock |")
    emit("|---|---|---|---|---|---|")
    bp = lambda x: f"{x * 1e4:+.1f}"  # noqa: E731

    def cond(name, mask):
        mask = mask.fillna(False).astype(bool)
        emit(f"| {name} | {int(mask.sum()):,} | {bp(nights['base'][mask].mean())} | {bp(nights['lowbeta'][mask].mean())} | "
             f"{bp(nights['defind'][mask].mean())} | {bp(avg_on[mask].mean())} |")

    cond("all nights", pd.Series(True, index=idx))
    for lo_, hi_ in ((0, 15), (15, 20), (20, 25), (25, 30), (30, 200)):
        cond(f"VIX {lo_}-{hi_ if hi_ < 200 else '+'}", (vix1 >= lo_) & (vix1 < hi_))
    cond("VIX fell 10%+", dv1 <= -0.10)
    cond("VIX rose 10%+", dv1 >= 0.10)
    cond("VIX rose 20%+", dv1 >= 0.20)
    cond("SPY below its 200-day", trend1)
    cond("SPY above its 200-day", ~trend1)
    q = tech_gap.quantile([0.1, 0.9])
    cond("tech lagged defensives most (worst 10% of days)", tech_gap <= q.iloc[0])
    cond("tech beat defensives most (best 10%)", tech_gap >= q.iloc[1])
    emit("\n(Costs are already taken off: 0.04% = 4 bp a night. A row's spread is noise unless it holds across the "
         "neighbouring rows and both halves below.)\n")

    emit("## 2. Switching rules (the whole sleeve, night by night)\n")
    emit("| rule | nights switched | return/yr | Sharpe | worst drop | 2014-19 Sharpe | 2020-26 Sharpe |")
    emit("|---|---|---|---|---|---|---|")
    lag_flag = (tech_gap <= tech_gap.expanding(250).quantile(0.1)).fillna(False).astype(bool)   # threshold from the past
    trend2 = (mkt < mkt.rolling(200).mean()).shift(2).reindex(idx).fillna(False).astype(bool)
    lag_flag2 = lag_flag.shift(1, fill_value=False)
    rules = {
        "Always the top 20 (now)": nights["base"],
        "Cash when VIX > 25": switch(nights["base"], cash, vix1 > 25),
        "Cash when VIX > 30": switch(nights["base"], cash, vix1 > 30),
        "Cash after VIX rose 15%+": switch(nights["base"], cash, dv1 >= 0.15),
        "Cash when SPY below its 200-day": switch(nights["base"], cash, trend1),
        "Low-beta list when VIX > 25": switch(nights["base"], nights["lowbeta"], vix1 > 25),
        "Low-beta list when VIX > 20": switch(nights["base"], nights["lowbeta"], vix1 > 20),
        "Low-beta list after VIX rose 15%+": switch(nights["base"], nights["lowbeta"], dv1 >= 0.15),
        "Low-beta list when SPY below its 200-day": switch(nights["base"], nights["lowbeta"], trend1),
        "Defensive-industry list when VIX > 25": switch(nights["base"], nights["defind"], vix1 > 25),
        "Low-beta list after tech lagged most (worst 10%)": switch(nights["base"], nights["lowbeta"],
                                                                   tech_gap <= tech_gap.expanding(250).quantile(0.1)),
        "Cash after tech lagged most (worst 10%)": switch(nights["base"], cash, lag_flag),
        "Cash when SPY below its 200-day OR after tech lagged most": switch(nights["base"], cash, trend1 | lag_flag),
        "Lagged a day more: cash when SPY below its 200-day": switch(nights["base"], cash, trend2),
        "Lagged a day more: cash after tech lagged most": switch(nights["base"], cash, lag_flag2),
        "Always the low-beta list": nights["lowbeta"],
        "Always the defensive-industry list": nights["defind"],
        "Always: at most 4 per industry": nights["cap4"],
        "Lagged a day more: low-beta when VIX > 25": switch(nights["base"], nights["lowbeta"], vix2 > 25),
        "Lagged a day more: cash after VIX rose 15%+": switch(nights["base"], cash, dv2 >= 0.15),
    }
    signals = {"Cash when VIX > 25": vix1 > 25, "Cash when VIX > 30": vix1 > 30, "Cash after VIX rose 15%+": dv1 >= 0.15,
               "Cash when SPY below its 200-day": trend1, "Low-beta list when VIX > 25": vix1 > 25,
               "Low-beta list when VIX > 20": vix1 > 20, "Low-beta list after VIX rose 15%+": dv1 >= 0.15,
               "Low-beta list when SPY below its 200-day": trend1, "Defensive-industry list when VIX > 25": vix1 > 25,
               "Lagged a day more: low-beta when VIX > 25": vix2 > 25,
               "Lagged a day more: cash after VIX rose 15%+": dv2 >= 0.15,
               "Low-beta list after tech lagged most (worst 10%)": lag_flag,
               "Cash after tech lagged most (worst 10%)": lag_flag,
               "Cash when SPY below its 200-day OR after tech lagged most": trend1 | lag_flag,
               "Lagged a day more: cash when SPY below its 200-day": trend2,
               "Lagged a day more: cash after tech lagged most": lag_flag2}
    res = {}
    for k, r in rules.items():
        s, a, b = stats(r, rf), stats(r.loc[:ov.MID], rf), stats(r.loc[ov.MID:], rf)
        res[k] = s
        sw = signals.get(k)
        swn = (f"{sw.fillna(False).astype(bool).mean():.0%}" if sw is not None
               else "all" if k.startswith("Always") and "now" not in k else "-")
        emit(f"| {k} | {swn} | {s['CAGR']:.1%} | {s['Sharpe']:.2f} | {s['maxdd']:.0%} | {a['Sharpe']:.2f} | {b['Sharpe']:.2f} |")

    emit("\n## 2b. Do the signals hold in both halves? (sleeve's average night, bp)\n")
    emit("| signal (day before) | 2014-19 nights | 2014-19 | 2020-26 nights | 2020-26 | episodes (runs of 5+ days) |")
    emit("|---|---|---|---|---|---|")
    for name, m in (("SPY below its 200-day", trend1), ("tech lagged defensives most (worst 10%, past threshold)", lag_flag),
                    ("VIX above 25", vix1 > 25), ("none of these", ~(trend1 | lag_flag | (vix1 > 25)))):
        m = m.fillna(False).astype(bool)
        a1, b1 = m.loc[:ov.MID], m.loc[ov.MID:]
        runs = int(((m & ~m.shift(1, fill_value=False)).astype(int).groupby((~m).cumsum()).sum() > 0).sum())
        long_runs = int((m.groupby((~m).cumsum()).sum() >= 5).sum())
        emit(f"| {name} | {int(a1.sum())} | {bp(nights['base'].loc[:ov.MID][a1].mean())} | {int(b1.sum())} | "
             f"{bp(nights['base'].loc[ov.MID:][b1].mean())} | {long_runs} |")

    emit("\nSignal nights vs all other nights (Welch t):\n")
    for name, m in (("SPY below its 200-day", trend1), ("tech lagged most", lag_flag)):
        x, y = nights["base"][m], nights["base"][~m]
        t = (x.mean() - y.mean()) / np.sqrt(x.var() / len(x) + y.var() / len(y))
        emit(f"- {name}: {bp(x.mean())} vs {bp(y.mean())} bp a night, t {t:.1f}")

    emit("\n## 3. The worst nights for the sleeve - what the VIX said the day before\n")
    worst = nights["base"].nsmallest(15).index.sort_values()
    emit("| morning | sleeve's night | VIX the day before | VIX change that day | SPY below 200-day? | low-beta list that night |")
    emit("|---|---|---|---|---|---|")
    for dt in worst:
        emit(f"| {dt.date()} | {nights['base'][dt]:+.1%} | {vix1[dt]:.1f} | {dv1[dt]:+.0%} | {'yes' if trend1[dt] else 'no'} | "
             f"{nights['lowbeta'][dt]:+.1%} |")
    big = vix1 > 25
    emit(f"\nOf the sleeve's 50 worst nights, {int(big.reindex(nights['base'].nsmallest(50).index).sum())} came after a VIX "
         f"close above 25 (which happened before {big.mean():.0%} of all nights).")

    emit("\n## 4. How often the low-beta list beat the sleeve, by VIX (nights)\n")
    emit("| VIX the day before | low-beta better | difference (bp/night) | t |\n|---|---|---|---|")
    for lo_, hi_ in ((0, 20), (20, 25), (25, 200)):
        m = (vix1 >= lo_) & (vix1 < hi_)
        dd = (nights["lowbeta"] - nights["base"])[m.fillna(False)]
        emit(f"| {lo_}-{hi_ if hi_ < 200 else '+'} | {(dd > 0).mean():.0%} | {bp(dd.mean())} | "
             f"{dd.mean() / dd.std() * np.sqrt(len(dd)):.1f} |")

    OUT.mkdir(exist_ok=True)
    (OUT / "overnight_regime.md").write_text("\n".join(lines) + "\n")
    print(f"\nwrote {OUT / 'overnight_regime.md'}")


if __name__ == "__main__":
    main()
