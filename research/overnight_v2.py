"""The overnight sleeve, version 2: rank by the plain 12-month return, re-picked every day - as it would run live.

    python research/overnight_v2.py

research/lookbacks.py found two small leads: re-pick daily (free - the sleeve sells everything each morning) and rank
by the plain 12-month return instead of the average overnight return. Live, the ranking of ~750 stocks is too slow for
the 3:55pm buy window, so the evening run ranks on that day's close and the next afternoon buys it: a one-day lag.
Compared, all with the live regime checks (cash when SPY < its 200-day average, or tonight's picks are down past the
cut-off since the open) and without:
  live now       average overnight return, 252 days, re-picked monthly
  v2 (no lag)    plain 252-day return, re-picked daily on the buy day's close
  v2 (as live)   the same, ranked on the PREVIOUS close (evening run)
  v2 skip-month  plain return from 12 months to 1 month ago (the classic momentum measure)
The picks-day cut-off is the 10th percentile of each version's own history. Same data and costs (0.02% per trade
each way) as research/overnight_regime.py; survivors-only prices. Writes research/output/overnight_v2.md.
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

CACHE, OUT = orr.CACHE, orr.OUT


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
    rf = (load_cash_rate(str(ROOT / "market_data" / "SPY.csv")).reindex(dates, method="ffill") / 252).fillna(0)
    mkt = pd.read_csv(ROOT / "market_data" / "SPY.csv", index_col=0, parse_dates=True)["close"].reindex(dates).ffill()
    spy_flag = (mkt < mkt.rolling(200).mean()).shift(1).fillna(False).astype(bool)   # known at the buy (close t-1)

    ret12 = c / c.shift(252) - 1
    skip = c.shift(21) / c.shift(252) - 1
    holds = {   # True = held the night ending at day t (bought at close t-1)
        "Live now: overnight average, monthly": ov.monthly_picks(on.rolling(252, min_periods=200).mean(), eligible, 20
                                                                ).shift(1, fill_value=False),
        "v2: 12-month return, daily (no lag)": lb.daily_top(ret12, eligible).shift(1, fill_value=False),
        "v2: 12-month return, daily, ranked the evening before (as live)": lb.daily_top(ret12, eligible).shift(2, fill_value=False),
        "v2 skip-month, ranked the evening before": lb.daily_top(skip, eligible).shift(2, fill_value=False),
    }
    emit("# Overnight sleeve v2 - generated tables\n")
    emit("**Survivors-only prices**; the 750 largest US companies; 0.02% per trade each way; T-bills in cash.\n")
    emit("| version | checks | bp/night | return/yr | Sharpe | worst drop | 2014-19 | 2020-26 | nights in cash | picks-day cut-off |")
    emit("|---|---|---|---|---|---|---|---|---|---|")
    res = {}
    for name, h in holds.items():
        base = orr.nightly(on, h, orr.COST).loc[ov.START:ov.END]
        idx = base.index
        rfa = rf.reindex(idx).fillna(0)
        pday = day.shift(1).where(h).mean(axis=1).reindex(idx)        # the picks' open-to-close on the buy day
        bad = opc.bad_day(pday, 0.10)
        cut = pday.quantile(0.10)
        for label, flag in (("none", pd.Series(False, index=idx)),
                            ("SPY + picks-day", spy_flag.reindex(idx).fillna(False) | bad)):
            r = orr.switch(base, rfa, flag)
            s, a, b = orr.stats(r, rfa), orr.stats(r.loc[:ov.MID], rfa), orr.stats(r.loc[ov.MID:], rfa)
            res[(name, label)] = r
            emit(f"| {name} | {label} | {r.mean() * 1e4:+.1f} | {s['CAGR']:.1%} | {s['Sharpe']:.2f} | {s['maxdd']:.0%} | "
                 f"{a['Sharpe']:.2f} | {b['Sharpe']:.2f} | {flag.mean():.0%} | {cut:+.2%} |")

    emit("\n## How different are the picks? (v2 as live vs live now)\n")
    a_, b_ = holds["Live now: overnight average, monthly"], holds["v2: 12-month return, daily, ranked the evening before (as live)"]
    both = (a_ & b_).sum(axis=1) / 20
    turnover = (b_ & ~b_.shift(1, fill_value=False)).sum(axis=1)
    emit(f"- Stocks in common on an average night: {both.loc[ov.START:].mean():.0%}")
    emit(f"- v2 changes on average {turnover.loc[ov.START:].mean():.1f} of its 20 names a day (no extra cost: all are sold "
         "each morning anyway)")

    emit("\n## Year by year (with the checks)\n")
    ka, kb = ("Live now: overnight average, monthly", "SPY + picks-day"), \
        ("v2: 12-month return, daily, ranked the evening before (as live)", "SPY + picks-day")
    emit("| year | live now | v2 as live | difference |\n|---|---|---|---|")
    wins = 0
    for y in sorted(set(res[ka].index.year)):
        ra = (1 + res[ka][res[ka].index.year == y]).prod() - 1
        rb = (1 + res[kb][res[kb].index.year == y]).prod() - 1
        wins += rb > ra
        emit(f"| {y} | {ra:+.1%} | {rb:+.1%} | {rb - ra:+.1%} |")
    diff = (res[kb] - res[ka]).dropna()
    emit(f"\nv2 better in {wins} of {len(set(res[ka].index.year))} years; nightly difference {diff.mean() * 1e4:+.1f} bp "
         f"(t {diff.mean() / diff.std() * np.sqrt(len(diff)):.1f}).")

    OUT.mkdir(exist_ok=True)
    (OUT / "overnight_v2.md").write_text("\n".join(lines) + "\n")
    print(f"\nwrote {OUT / 'overnight_v2.md'}")


if __name__ == "__main__":
    main()
