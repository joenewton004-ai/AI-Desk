"""One more timing indicator for the overnight sleeve: six new candidates on top of the live checks.

    python research/overnight_timing.py      (uses data/backtest/daily_ohlcv_ext.pkl from overnight_safety2.py and
                                              market_data/VIX.csv, VIX3M.csv, HYG.csv, IEF.csv, SPY.csv; ~2 minutes)

Asked 2026-11-05 ("add another indicator to be smarter about when we trade"). Already tested and NOT repeated here:
VIX level/change, SPY 200-day (live), tech-vs-defensive, the picks' fall since the open (live), per-stock skips,
earnings nights, sector caps, a lower fixed share (research/OVERNIGHT_REGIME.md, OVERNIGHT_SAFETY*.md). The new
candidates, each added ON TOP of the live rule and its two checks (fixed before running; nothing tuned):
  T  VIX term structure   cash when the VIX closes above the 3-month VIX (VIX3M) - fear priced for now, not later
  C  Credit stress        cash when HYG/IEF (junk bonds vs Treasuries) is below its 50-day average
  B  Breadth              cash when under 40% of the eligible stocks are above their 50-day average
  O  The sleeve's trend   cash when the sleeve's own last 20 nights summed below zero
  V  Volatility target    money overnight = min(100%, typical volatility / the sleeve's last-20-night volatility);
                          'typical' = the median of that 20-night figure over all earlier nights (a sizing rule)
  W  Weekends             cash over weekend and holiday nights (Friday close -> Monday open)
Signals use closes up to the buy day (the live buy is at 3:55pm - the same small flattery as the live checks); each is
also shown a day later as a robustness line. ADOPT only if (fixed before running, as in OVERNIGHT_SAFETY2.md): Sharpe
beats Live in BOTH 2014-2019 and 2020-2026, AND the worst drop or worst month is smaller, at both 0.02% and 0.05% costs
each way. Six candidates = one may pass by luck; the day-later line must not collapse. Survivors-only prices.
Writes research/output/overnight_timing.md.
"""

from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "research"))

COSTS = (0.0002, 0.0005)


# --- pure signal helpers (each value uses only data up to its own date) ------------------------------------------

def below_ma(x: pd.Series, n: int) -> pd.Series:
    return (x < x.rolling(n).mean()).fillna(False).astype(bool)


def breadth(close: pd.DataFrame, eligible: pd.DataFrame, n: int = 50) -> pd.Series:
    """Share of eligible stocks closing above their n-day average, per day."""
    above = (close > close.rolling(n, min_periods=n).mean()).where(eligible)
    return above.sum(axis=1) / eligible.sum(axis=1).replace(0, np.nan)


def own_trend(nights: pd.Series, n: int = 20) -> pd.Series:
    """For the night ending at date t: the sum of the n nights ending BEFORE t (known at the buy on t-1)."""
    return nights.rolling(n).sum().shift(1)


def vol_scale(nights: pd.Series, n: int = 20, min_nights: int = 250) -> pd.Series:
    """Money overnight for the night ending at t: min(1, median past 20-night vol / latest 20-night vol)."""
    vol = nights.rolling(n).std().shift(1)
    typical = vol.expanding(min_nights).median()
    return (typical / vol).clip(upper=1.0).fillna(1.0)


def weekend(dates: pd.DatetimeIndex) -> pd.Series:
    """True for a night that spans more than one calendar day (weekends, holidays)."""
    gap = pd.Series(dates, index=dates).diff().dt.days
    return (gap > 1).fillna(False)


# --- the experiment ----------------------------------------------------------------------------------------------

def main() -> None:
    import ict
    import lookbacks as lb
    import overnight as ov
    import overnight_picks_check as opc
    import overnight_regime as orr
    import overnight_safety2 as os2
    import swing
    from ai_desk.data import load_cash_rate

    warnings.filterwarnings("ignore", category=RuntimeWarning)
    lines: list[str] = []

    def emit(t=""):
        print(t, flush=True)
        lines.append(t)

    d = os2.extended_prices()
    o, c, v = (d[k].astype(float) for k in ("open", "close", "volume"))
    c_ff = c.ffill(limit=1)
    snaps = {k: list(s.index) for k, s in ict.snapshots().items()}
    dates, symbols = c.index, list(c.columns)
    member = pd.DataFrame(swing.membership(dict(sorted(snaps.items())), dates, symbols), index=dates, columns=symbols)
    eligible = member & (c_ff > 10) & ((c_ff * v).rolling(50, min_periods=40).mean() > 20e6)
    on, day = ov.split_returns(o, c_ff)
    rf = (load_cash_rate(str(ROOT / "market_data" / "SPY.csv")).reindex(dates, method="ffill") / 252).fillna(0)

    def series(sym: str) -> pd.Series:
        return pd.read_csv(ROOT / "market_data" / f"{sym}.csv", index_col=0, parse_dates=True)["close"] \
            .reindex(dates).ffill()

    mkt = series("SPY")
    spy_flag = below_ma(mkt, 200).shift(1, fill_value=False)
    held = lb.daily_top(c_ff / c_ff.shift(252) - 1, eligible, 20).shift(2, fill_value=False).loc[ov.START:os2.END]
    idx = held.index
    pday = day.shift(1).where(held).mean(axis=1).reindex(idx)
    live_flag = (spy_flag.reindex(idx).fillna(False) | opc.bad_day(pday, 0.10)).astype(bool)
    rfi = rf.reindex(idx).fillna(0)

    # signals dated at the close they use; .shift(1) moves them to the night that starts at that close
    at_close = {
        "T": series("VIX") > series("VIX3M"),
        "C": below_ma(series("HYG") / series("IEF"), 50),
        "B": breadth(c_ff, eligible) < 0.40,
    }

    emit("# One more timing indicator for the overnight sleeve - generated tables\n")
    emit(f"Daily, {ov.START} to the {os2.END} open, the live rule and both live checks, **survivors-only prices**; "
         "Sharpe above T-bills; cash nights earn T-bills.\n")
    emit("| version | costs | nights out / avg money | return/yr | Sharpe | worst drop | worst month | 2014-19 | 2020-26 | "
         "Oct 2026 |")
    emit("|---|---|---|---|---|---|---|---|---|---|")
    res, extra = {}, {}
    for cost in COSTS:
        base = orr.nightly(on.reindex(idx), held, cost)
        live = orr.switch(base, rfi, live_flag)
        flags = {k: s.shift(1, fill_value=False).reindex(idx).fillna(False).astype(bool) for k, s in at_close.items()}
        flags.update({k + " (day later)": s.shift(2, fill_value=False).reindex(idx).fillna(False).astype(bool)
                      for k, s in at_close.items()})
        flags["O"] = (own_trend(base) < 0).fillna(False)
        flags["O (day later)"] = (own_trend(base).shift(1) < 0).fillna(False)
        flags["W"] = weekend(idx)
        runs = {"Live": (live, 0.0)}
        for k, f in flags.items():
            runs[k] = (orr.switch(live, rfi, f), float((f & ~live_flag).mean()))
        for lag, name in ((0, "V"), (1, "V (day later)")):
            s = vol_scale(base).shift(lag).fillna(1.0)
            runs[name] = (s * live + (1 - s) * rfi, float(s.mean()))
        for name, (r, out) in sorted(runs.items(), key=lambda x: (x[0] != "Live", x[0])):
            s, a, b = orr.stats(r, rf), orr.stats(r.loc[:ov.MID], rf), orr.stats(r.loc[ov.MID:], rf)
            m = (1 + r).resample("ME").prod() - 1
            res[(name, cost)] = (s, a, b, m.min())
            oct26 = (1 + r.loc["2026-10"]).prod() - 1
            used = f"avg {out:.0%}" if name.startswith("V") else ("-" if name == "Live" else f"{out:.0%} out")
            emit(f"| {name} | {cost:.2%} | {used} | {s['CAGR']:.1%} | {s['Sharpe']:.2f} | {s['maxdd']:.0%} | "
                 f"{m.min():+.1%} | {a['Sharpe']:.2f} | {b['Sharpe']:.2f} | {oct26:+.1%} |")
        if cost == COSTS[0]:
            for k in ("T", "C", "B", "O", "W"):
                f = flags[k] & ~live_flag
                inv = ~live_flag
                extra[k] = (live[f].mean(), live[inv & ~f].mean(), int(f.sum()))

    emit("\n## The live sleeve's average night when each new signal is on vs off (0.02% costs, nights the live checks "
         "already invest)\n")
    emit("| signal | nights flagged | avg night when flagged | avg night otherwise |")
    emit("|---|---|---|---|")
    for k, (on_, off_, n) in extra.items():
        emit(f"| {k} | {n} | {on_ * 1e4:+.1f} bp | {off_ * 1e4:+.1f} bp |")

    emit("\n## Verdicts (Sharpe beats Live in both halves AND smaller worst drop or worst month, at both costs)\n")
    for name in sorted({k for k, _ in res} - {"Live"}):
        ok = True
        for cost in COSTS:
            s, a, b, wm = res[(name, cost)]
            s0, a0, b0, wm0 = res[("Live", cost)]
            ok &= a["Sharpe"] > a0["Sharpe"] and b["Sharpe"] > b0["Sharpe"] and (s["maxdd"] > s0["maxdd"] or wm > wm0)
        emit(f"- {name}: {'**passes**' if ok else 'no'}")
    out = Path(__file__).resolve().parent / "output"
    out.mkdir(exist_ok=True)
    (out / "overnight_timing.md").write_text("\n".join(lines) + "\n")
    print(f"\nwrote {out / 'overnight_timing.md'}")


if __name__ == "__main__":
    main()
