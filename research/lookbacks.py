"""How far back should a sleeve look when it ranks stocks? 1 day, a week, 10 days, two weeks, a month... a year.

    python research/lookbacks.py

Part A - the overnight sleeve (held close to next open, every night). Live it ranks by the AVERAGE OVERNIGHT return
over 12 months, re-picked monthly. Here: the top 20 by
  - average overnight return over the last 1, 5, 10, 21, 63, 126 or 252 trading days
  - plain (close-to-close) return over the same windows
re-picked every day - free here, since the sleeve sells everything each morning anyway - and, for 21 days and
longer, also monthly as live. Rank uses data up to the buy day's close (the overnight return that ended at its open);
the night's return is that close to the next open. 0.02% per trade each way.

Part B - the momentum sleeve (held 4 weeks, sold below the 100-day average; entry above 200 and 100-day averages,
as live). Live it ranks by 6-month return skipping the latest week. Here: 1, 2, 4, 8, 13, 26 and 52-week windows
(the latest week always skipped, so "1 week" = the week before last). 0.10% per trade.

The 750 largest US companies at each quarter-end, **survivors-only prices**, T-bills on cash, Sharpe above T-bills.
Writes research/output/lookbacks.md; findings in research/LOOKBACKS.md.
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
import overnight_regime as orr  # noqa: E402
import swing  # noqa: E402
import weekly  # noqa: E402
from ai_desk.data import load_cash_rate  # noqa: E402

CACHE, OUT = orr.CACHE, orr.OUT
DAYS = (1, 5, 10, 21, 63, 126, 252)
WEEKS = (1, 2, 4, 8, 13, 26, 52)


def daily_top(score: pd.DataFrame, eligible: pd.DataFrame, n: int = 20) -> pd.DataFrame:
    """Pure: True for the n highest-score eligible stocks on each row (ties broken by column order)."""
    s = score.where(eligible).to_numpy(dtype=float)
    out = np.zeros_like(s, dtype=bool)
    for i, row in enumerate(s):
        ok = np.flatnonzero(np.isfinite(row))
        if len(ok) >= n:
            out[i, ok[np.argsort(-row[ok], kind="stable")[:n]]] = True
    return pd.DataFrame(out, index=score.index, columns=score.columns)


def main() -> None:
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    lines: list[str] = []

    def emit(t=""):
        print(t, flush=True)
        lines.append(t)

    # --- Part A ------------------------------------------------------------------------
    print("part A...", flush=True)
    d = swing.fetch_daily([])
    o, c, v = (d[k].astype(float).loc[:ov.END] for k in ("open", "close", "volume"))
    snaps = {}
    for m in (3, 6, 9, 12):
        snaps.update({k: list(s.index) for k, s in pickle.loads((CACHE / f"snapshots_m{m}.pkl").read_bytes()).items()})
    dates, symbols = c.index, list(c.columns)
    member = pd.DataFrame(swing.membership(dict(sorted(snaps.items())), dates, symbols), index=dates, columns=symbols)
    eligible = member & (c > 10) & ((c * v).rolling(50, min_periods=40).mean() > 20e6)
    on, _ = ov.split_returns(o, c)
    rc = c.pct_change(fill_method=None).where(lambda x: x.abs() < 0.5)
    rf = (load_cash_rate(str(ROOT / "market_data" / "SPY.csv")).reindex(dates, method="ffill") / 252).fillna(0)

    def night(pick_at_close: pd.DataFrame) -> pd.Series:
        """Picks decided at close t-1 -> the night ending at t's open."""
        return orr.nightly(on, pick_at_close.shift(1, fill_value=False), orr.COST).loc[ov.START:ov.END]

    books = {}
    for L in DAYS:
        on_score = on.rolling(L, min_periods=max(1, int(L * 0.8))).mean()
        tot_score = c / c.shift(L) - 1
        books[("overnight return", L, "daily")] = night(daily_top(on_score, eligible))
        books[("plain return", L, "daily")] = night(daily_top(tot_score, eligible))
        if L >= 21:   # the live way: chosen at each month-end, held all month (monthly_picks already lags a day)
            books[("overnight return", L, "monthly")] = orr.nightly(
                on, ov.monthly_picks(on_score, eligible, 20).shift(1, fill_value=False), orr.COST).loc[ov.START:ov.END]
    idx = books[("overnight return", 252, "monthly")].index
    rfa = rf.reindex(idx).fillna(0)
    avg = on.where(eligible.shift(1, fill_value=False)).mean(axis=1).reindex(idx) - 2 * orr.COST

    emit("# Ranking windows - generated tables\n")
    emit("**Survivors-only prices.** The 750 largest US companies at each quarter-end. Sharpe above T-bills.\n")
    emit("## A. The overnight sleeve: top 20, held from the close to the next open\n")
    emit(f"Nights {idx[0].date()} to {idx[-1].date()}; 0.02% per trade each way. Live = average overnight return, "
         "252 days, monthly.\n")
    emit("| ranked by | window | re-pick | bp/night | return/yr | Sharpe | worst drop | 2014-19 | 2020-26 |")
    emit("|---|---|---|---|---|---|---|---|---|")
    for (kind, L, rp), r in books.items():
        s, a, b = orr.stats(r, rfa), orr.stats(r.loc[:ov.MID], rfa), orr.stats(r.loc[ov.MID:], rfa)
        live = " **(live)**" if (kind, L, rp) == ("overnight return", 252, "monthly") else ""
        emit(f"| {kind}{live} | {L} days | {rp} | {r.mean() * 1e4:+.1f} | {s['CAGR']:.1%} | {s['Sharpe']:.2f} | "
             f"{s['maxdd']:.0%} | {a['Sharpe']:.2f} | {b['Sharpe']:.2f} |")
    s = orr.stats(avg, rfa)
    emit(f"| average stock, every night | - | - | {avg.mean() * 1e4:+.1f} | {s['CAGR']:.1%} | {s['Sharpe']:.2f} | "
         f"{s['maxdd']:.0%} | | |")

    # --- Part B ------------------------------------------------------------------------
    print("part B...", flush=True)
    px, wsnaps = weekly.load()
    f = weekly.build(px, wsnaps)
    ma20 = px.rolling(20, min_periods=20).mean()
    f_both = {**f, "above": f["above"] & (px > ma20)}
    rf_m = (load_cash_rate(str(ROOT / "market_data" / "SPY.csv")).resample("ME").last() / 12).shift(1)
    sleeves = {}
    for L in WEEKS:
        book = weekly.momentum_book(px, wsnaps, f_both, lookback=L, n=20, every=4, exit_ma=20)
        sleeves[L] = (ms.monthly(weekly.simulate(book, f["ret"], weekly.COST)),
                      ms.monthly(weekly.simulate(book, f["ret"], 3 * weekly.COST)))
    midx = sleeves[26][0].index
    midx = midx[(midx >= pd.Timestamp("2014-06-30")) & (midx <= pd.Timestamp(ms.MONTH_END))]
    rfm = rf_m.reindex(midx).fillna(0)
    emit("\n## B. The momentum sleeve: top 20, re-picked every 4 weeks, sold below the 100-day average\n")
    emit(f"Monthly, {midx[0]:%Y-%m} to {midx[-1]:%Y-%m}; 0.10% per trade (3x in brackets). Live = 26 weeks.\n")
    emit("| window (latest week skipped) | return/yr | Sharpe | worst drop | at 3x costs | 2014-19 | 2020-26 |")
    emit("|---|---|---|---|---|---|---|")
    for L, (r, r3) in sleeves.items():
        r, r3 = r.reindex(midx), r3.reindex(midx)
        s, a, b = ms.mstats(r, rfm), ms.mstats(r.loc[:"2019"], rfm), ms.mstats(r.loc["2020":], rfm)
        live = " **(live)**" if L == 26 else ""
        emit(f"| {L} weeks{live} | {s['CAGR']:.1%} | {s['Sharpe']:.2f} | {s['max drawdown']:.0%} | "
             f"{ms.mstats(r3, rfm)['CAGR']:.1%} | {a['Sharpe']:.2f} | {b['Sharpe']:.2f} |")

    OUT.mkdir(exist_ok=True)
    (OUT / "lookbacks.md").write_text("\n".join(lines) + "\n")
    print(f"\nwrote {OUT / 'lookbacks.md'}")


if __name__ == "__main__":
    main()
