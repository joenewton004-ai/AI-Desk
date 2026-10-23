"""Overnight sleeve: sit out the whole night when the picks fall together, or skip only the picks that fell?

    python research/overnight_perstock.py

Live (amendments 82c84226 + 9b951502): the top 20 by 12-month return, ranked the evening before; cash for the night
when SPY is below its 200-day average or the 20 picks' AVERAGE return since the open is -2.0% or worse. Tested here:
  per-stock     skip only the picks that are down more than X since the open (X = 2%, 3%, 5%, 8%); the skipped
                stocks' share stays in cash, or is spread over the rest ("fully invested")
  both          the group rule, plus the per-stock skip on the nights it doesn't fire
All keep the SPY rule. Same data, costs (0.02% per trade each way), T-bill cash and survivors-only prices as
research/overnight_v2.py. Writes research/output/overnight_perstock.md; findings in research/OVERNIGHT_REGIME.md.
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

CACHE, OUT, COST = orr.CACHE, orr.OUT, orr.COST


def book_night(on: pd.DataFrame, held: pd.DataFrame, skip: pd.DataFrame, rf: pd.Series, spread: bool,
               cost: float = COST) -> pd.Series:
    """Pure: the sleeve's night when the `skip` picks are left out. spread=False: their 1/n slices earn T-bills;
    spread=True: the money is split over the picks still bought. A night with nothing bought earns T-bills."""
    keep = held & ~skip
    n_held, n_keep = held.sum(axis=1), keep.sum(axis=1)
    gross = on.where(keep).sum(axis=1)
    if spread:
        r = gross / n_keep.replace(0, np.nan) - 2 * cost
    else:
        r = (gross - 2 * cost * n_keep + rf * (n_held - n_keep)) / n_held.replace(0, np.nan)
    return r.where(n_keep > 0, rf).fillna(0.0)


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
        snaps.update({k: list(s.index) for k, s in pickle.loads((CACHE / f"snapshots_m{m}.pkl").read_bytes()).items()})
    dates, symbols = c.index, list(c.columns)
    member = pd.DataFrame(swing.membership(dict(sorted(snaps.items())), dates, symbols), index=dates, columns=symbols)
    eligible = member & (c > 10) & ((c * v).rolling(50, min_periods=40).mean() > 20e6)
    on, day = ov.split_returns(o, c)
    rf_all = (load_cash_rate(str(ROOT / "market_data" / "SPY.csv")).reindex(dates, method="ffill") / 252).fillna(0)
    mkt = pd.read_csv(ROOT / "market_data" / "SPY.csv", index_col=0, parse_dates=True)["close"].reindex(dates).ffill()
    spy = (mkt < mkt.rolling(200).mean()).shift(1).fillna(False).astype(bool)

    held = lb.daily_top(c / c.shift(252) - 1, eligible).shift(2, fill_value=False)   # v2 as live
    pick_day = day.shift(1).where(held)                       # each pick's open-to-close on the buy day
    sl = slice(ov.START, ov.END)
    held, pick_day, on_, rf = held.loc[sl], pick_day.loc[sl], on.loc[sl], rf_all.loc[sl]
    idx = held.index
    group = opc.bad_day(pick_day.mean(axis=1), 0.10)         # the live group rule (~ -2.0%)
    out_all = (spy.reindex(idx).fillna(False) | group)
    none = pd.DataFrame(False, index=idx, columns=held.columns)
    all_out = pd.DataFrame(np.repeat(out_all.to_numpy()[:, None], held.shape[1], axis=1), index=idx, columns=held.columns)
    spy_out = pd.DataFrame(np.repeat(spy.reindex(idx).fillna(False).to_numpy()[:, None], held.shape[1], axis=1),
                           index=idx, columns=held.columns)

    emit("# Overnight sleeve: whole-night cash vs skipping single picks - generated tables\n")
    emit(f"Nights {idx[0].date()} to {idx[-1].date()}; v2 picks (12-month return, ranked the evening before); "
         "**survivors-only prices**; 0.02% per trade each way; T-bills in cash. Every rule includes the SPY "
         "200-day rule.\n")
    emit("| rule | spare money | return/yr | Sharpe | worst drop | 2014-19 | 2020-26 | share of picks bought |")
    emit("|---|---|---|---|---|---|---|---|")
    res = {}

    def row(name, skip, spread):
        r = book_night(on_, held, skip & held, rf, spread)
        s, a, b = orr.stats(r, rf), orr.stats(r.loc[:ov.MID], rf), orr.stats(r.loc[ov.MID:], rf)
        bought = (held & ~skip).sum().sum() / max(held.sum().sum(), 1)
        res[(name, spread)] = r
        emit(f"| {name} | {'spread over the rest' if spread else 'cash'} | {s['CAGR']:.1%} | {s['Sharpe']:.2f} | "
             f"{s['maxdd']:.0%} | {a['Sharpe']:.2f} | {b['Sharpe']:.2f} | {bought:.0%} |")

    row("SPY rule only", spy_out, False)
    row("**Group rule (live): all 20 out when their average is -2%+**", all_out, False)
    for x in (0.02, 0.03, 0.05, 0.08):
        per = (pick_day <= -x).fillna(False)
        for spread in (False, True):
            row(f"Per-stock: skip picks down {x:.0%}+", spy_out | per, spread)
    for x in (0.03, 0.05):
        per = (pick_day <= -x).fillna(False)
        row(f"Group rule + skip single picks down {x:.0%}+", all_out | per, False)

    emit("\n## The skipped stocks themselves: what they did that night\n")
    emit("| down since the open | picks-nights | their night, average (bp) | the other picks that night (bp) | t |")
    emit("|---|---|---|---|---|")
    ON, H = on_.to_numpy(dtype=float), held.to_numpy()
    for x in (0.02, 0.03, 0.05, 0.08):
        m = ((pick_day <= -x).to_numpy() & H)
        night_has = m.any(axis=1)[:, None]
        a_ = pd.Series(ON[m]).dropna()
        b_ = pd.Series(ON[H & ~m & night_has]).dropna()
        t = (a_.mean() - b_.mean()) / np.sqrt(a_.var() / len(a_) + b_.var() / len(b_))
        emit(f"| {x:.0%}+ | {len(a_):,} | {a_.mean() * 1e4:+.1f} | {b_.mean() * 1e4:+.1f} | {t:.1f} |")
    emit("\n(Before costs. The group rule's nights are in the main table; this table asks whether a single fallen "
         "pick does worse than its neighbours on the same nights.)")

    OUT.mkdir(exist_ok=True)
    (OUT / "overnight_perstock.md").write_text("\n".join(lines) + "\n")
    print(f"\nwrote {OUT / 'overnight_perstock.md'}")


if __name__ == "__main__":
    main()
