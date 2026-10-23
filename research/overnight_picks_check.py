"""Overnight sleeve: judge the bad day by the sleeve's own picks instead of tech vs defensive industries.

    python research/overnight_picks_check.py

The live check (amendment 7a8b29ec, research/OVERNIGHT_REGIME.md) sits in cash on a day tech stocks lag defensive
stocks by more than on 90% of past days. Tech and defensive are fixed industry lists, and what the sleeve holds
changes every month. The alternative: look at the 20 stocks the sleeve is about to buy.
  A. tech minus defensive (live now)
  B. the picks' return today minus the average large stock's (worst 10% of past days)
  C. the picks' own return today (worst 10% of past days)
  D. the picks' return from today's open (the daytime give-back the overnight research found), worst 10%
  E. B, but only the worst 5% / F. the worst 20%
each alone and with the SPY 200-day rule. Cut-offs from past days only (expanding, 250 days minimum). Same nights,
costs (0.02% each way), T-bill cash and survivors-only prices as research/overnight_regime.py. Writes
research/output/overnight_picks_check.md; findings in research/OVERNIGHT_REGIME.md.
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
import overnight_regime as orr  # noqa: E402
import swing  # noqa: E402
from ai_desk.data import load_cash_rate  # noqa: E402

CACHE, OUT = orr.CACHE, orr.OUT


def bad_day(x: pd.Series, q: float, min_days: int = 250) -> pd.Series:
    """Pure: True where x is at or below its q-quantile over all EARLIER days (no lookahead)."""
    cut = x.expanding(min_days).quantile(q).shift(1)
    return (x <= cut).fillna(False).astype(bool)


def main() -> None:
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    lines: list[str] = []

    def emit(t=""):
        print(t, flush=True)
        lines.append(t)

    d = swing.fetch_daily([])
    o, c, v = (d[k].astype(float).loc[:ov.END] for k in ("open", "close", "volume"))
    snaps, sic = {}, {}
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
    pick = ov.monthly_picks(score, eligible, 20).shift(1, fill_value=False)      # held the night ending at t
    base = orr.nightly(on, pick, orr.COST).loc[ov.START:ov.END]
    idx = base.index
    rf = (load_cash_rate(str(ROOT / "market_data" / "SPY.csv")).reindex(dates, method="ffill") / 252).loc[idx].fillna(0)

    rc = c.pct_change(fill_method=None).where(lambda x: x.abs() < 0.5)
    # the buy day = the day before the night's morning: its returns, for tonight's picks
    picks_c2c = rc.shift(1).where(pick).mean(axis=1).reindex(idx)
    picks_day = day.shift(1).where(pick).mean(axis=1).reindex(idx)
    avg_c2c = rc.shift(1).where(eligible.shift(1, fill_value=False)).mean(axis=1).reindex(idx)
    defensive = np.isin(symbols, [s for s, g in sic.items() if g in orr.DEFENSIVE_SIC])
    tech = np.isin(symbols, [s for s, g in sic.items() if g in orr.TECH_SIC])
    rce = rc.where(eligible)
    tech_gap = (rce.loc[:, tech].mean(axis=1) - rce.loc[:, defensive].mean(axis=1)).shift(1).reindex(idx)
    mkt = pd.read_csv(ROOT / "market_data" / "SPY.csv", index_col=0, parse_dates=True)["close"].reindex(dates).ffill()
    spy = (mkt < mkt.rolling(200).mean()).shift(1).reindex(idx).fillna(False).astype(bool)

    flags = {
        "A. tech minus defensive (live now)": bad_day(tech_gap, 0.10),
        "B. picks minus the average stock": bad_day(picks_c2c - avg_c2c, 0.10),
        "C. picks' own return": bad_day(picks_c2c, 0.10),
        "D. picks' return since the open": bad_day(picks_day, 0.10),
        "E. picks minus the average, worst 5%": bad_day(picks_c2c - avg_c2c, 0.05),
        "F. picks minus the average, worst 20%": bad_day(picks_c2c - avg_c2c, 0.20),
    }

    emit("# Overnight sleeve: a bad-day check on its own picks - generated tables\n")
    emit(f"Nights {idx[0].date()} to {idx[-1].date()} ({len(idx):,}); the 750 largest US companies, **survivors-only "
         "prices**; 0.02% per trade each way; T-bills in cash. Each flag uses the buy day's returns and a cut-off from "
         "earlier days only.\n")
    emit("## 1. Each check alone, and with the SPY 200-day rule (cash on flagged nights)\n")
    emit("| check | nights out | return/yr | Sharpe | worst drop | 2014-19 | 2020-26 | + SPY rule: Sharpe | worst drop | 2014-19 | 2020-26 |")
    emit("|---|---|---|---|---|---|---|---|---|---|---|")

    def row(name, f):
        r, r2 = orr.switch(base, rf, f), orr.switch(base, rf, f | spy)
        s, a, b = orr.stats(r, rf), orr.stats(r.loc[:ov.MID], rf), orr.stats(r.loc[ov.MID:], rf)
        s2, a2, b2 = orr.stats(r2, rf), orr.stats(r2.loc[:ov.MID], rf), orr.stats(r2.loc[ov.MID:], rf)
        emit(f"| {name} | {f.mean():.0%} | {s['CAGR']:.1%} | {s['Sharpe']:.2f} | {s['maxdd']:.0%} | {a['Sharpe']:.2f} | "
             f"{b['Sharpe']:.2f} | {s2['Sharpe']:.2f} | {s2['maxdd']:.0%} | {a2['Sharpe']:.2f} | {b2['Sharpe']:.2f} |")

    row("none (always invested)", pd.Series(False, index=idx))
    for k, f in flags.items():
        row(k, f)

    emit("\n## 2. The flagged nights themselves (sleeve's average night, bp; Welch t vs other nights)\n")
    emit("| check | flagged nights | flagged | other | t | 2014-19 flagged | 2020-26 flagged | overlap with A |")
    emit("|---|---|---|---|---|---|---|---|")
    for k, f in flags.items():
        x, y = base[f], base[~f]
        t = (x.mean() - y.mean()) / np.sqrt(x.var() / len(x) + y.var() / len(y))
        a1, b1 = f.loc[:ov.MID], f.loc[ov.MID:]
        both = (f & flags["A. tech minus defensive (live now)"]).sum() / max(f.sum(), 1)
        emit(f"| {k} | {int(f.sum())} | {x.mean() * 1e4:+.1f} | {y.mean() * 1e4:+.1f} | {t:.1f} | "
             f"{base.loc[:ov.MID][a1].mean() * 1e4:+.1f} | {base.loc[ov.MID:][b1].mean() * 1e4:+.1f} | {both:.0%} |")

    emit("\n## 3. Year by year: return of A + SPY rule vs B + SPY rule\n")
    emit("| year | A + SPY | B + SPY | always invested |\n|---|---|---|---|")
    ra = orr.switch(base, rf, flags["A. tech minus defensive (live now)"] | spy)
    rb = orr.switch(base, rf, flags["B. picks minus the average stock"] | spy)
    for y in sorted(set(idx.year)):
        m = idx.year == y
        emit(f"| {y} | {(1 + ra[m]).prod() - 1:+.1%} | {(1 + rb[m]).prod() - 1:+.1%} | {(1 + base[m]).prod() - 1:+.1%} |")

    OUT.mkdir(exist_ok=True)
    (OUT / "overnight_picks_check.md").write_text("\n".join(lines) + "\n")
    print(f"\nwrote {OUT / 'overnight_picks_check.md'}")


if __name__ == "__main__":
    main()
