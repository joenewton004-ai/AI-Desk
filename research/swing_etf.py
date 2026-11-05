"""Swing trades held up to a week on SPY (and its family) and commodity ETFs, from daily bars.

    python research/swing_etf.py      (needs market_data/*.csv: python -m ai_desk fetch SPY QQQ IWM DIA GLD SLV USO UNG ^IRX)

Each rule is decided at a close (data up to that close only), bought at the next open, held at most 5 trading days
(sold at the next open after its exit close, or at the open 5 trading days after entry), one position at a time,
long only. Rules fixed before running:
  rsi2_dip      RSI(2) < 10 and close above the 200-day average (Connors); out after a close above the 5-day average
  rsi14_dip     RSI(14) < 30 above the 200-day (the desk's live dip rule, capped at a week here); same exit
  three_down    three lower closes in a row, above the 200-day; 5 days
  ibs_low       close in the bottom 20% of the day's range (IBS < 0.2), above the 200-day; out after a close above
                the previous day's high
  ten_day_low   the lowest close of 10 days, above the 200-day; out after a close above the 5-day average
  breakout_20   the highest close of 20 days; 5 days
  down_week     Friday's close below the previous Friday's: buy Monday's open, out the next Monday's open
  up_week       Friday's close above the previous Friday's: same timing
  turn_of_month bought at the open of the 4th-last trading day of the month, out at the open of the 4th trading day
                of the next month (the trading calendar is known in advance)
  gap_down      the open 1% or more below the previous close: bought at that open, 5 days
The test that matters: SPY rises over time, so any long rule makes money. Each trade is compared with simply holding
the ETF for the same days (excess = trade return - the ETF's average open-to-open return x days held, in the same half).
PASS: on the lead ETF (SPY 1993-2009 / 2010-2026; GLD 2004-2015 / 2016-2026) the average excess is > 0 in BOTH halves
with t >= 2, AND the rest of the family pooled has excess > 0 in both halves. As strategies: in the ETF while in a trade,
T-bills otherwise, vs buy and hold; Sharpe above T-bills. Costs each way: SPY QQQ IWM DIA GLD 0.01%, SLV 0.02%,
USO 0.03%, UNG 0.05%. Writes research/output/swing_etf.md.
"""

from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ai_desk.indicators import rsi  # noqa: E402

OUT = Path(__file__).resolve().parent / "output"
END = "2026-10-28"                        # the last full trading day when this was run
FAMILIES = {"index ETFs": (["SPY", "QQQ", "IWM", "DIA"], "2010-01-01"),
            "commodity ETFs": (["GLD", "SLV", "USO", "UNG"], "2016-01-01")}
COSTS = {"SPY": 0.0001, "QQQ": 0.0001, "IWM": 0.0001, "DIA": 0.0001, "GLD": 0.0001, "SLV": 0.0002, "USO": 0.0003,
         "UNG": 0.0005}
RULES = ["rsi2_dip", "rsi14_dip", "three_down", "ibs_low", "ten_day_low", "breakout_20", "down_week", "up_week",
         "turn_of_month", "gap_down"]
HOLD = 5


def load(sym: str) -> pd.DataFrame:
    d = pd.read_csv(ROOT / "market_data" / f"{sym}.csv", index_col=0, parse_dates=True).loc[:END]
    return d[["open", "high", "low", "close"]].astype(float).dropna()


def signals(d: pd.DataFrame, rule: str) -> tuple[np.ndarray, np.ndarray | None]:
    """Pure: (entry signal at each close, or at each OPEN for gap_down; exit condition at each close or None)."""
    c, h, l = d["close"], d["high"], d["low"]
    trend = c > c.rolling(200).mean()
    sma5 = c.rolling(5).mean()
    exit_sma5 = (c > sma5).to_numpy()
    if rule == "rsi2_dip":
        return ((rsi(c, 2) < 10) & trend).to_numpy(), exit_sma5
    if rule == "rsi14_dip":
        return ((rsi(c, 14) < 30) & trend).to_numpy(), exit_sma5
    if rule == "three_down":
        return ((c < c.shift(1)) & (c.shift(1) < c.shift(2)) & (c.shift(2) < c.shift(3)) & trend).to_numpy(), None
    if rule == "ibs_low":
        ibs = (c - l) / (h - l).replace(0, np.nan)
        return ((ibs < 0.2) & trend).to_numpy(), (c > h.shift(1)).to_numpy()
    if rule == "ten_day_low":
        return ((c <= c.rolling(10).min()) & trend).to_numpy(), exit_sma5
    if rule == "breakout_20":
        return (c >= c.rolling(20).max()).to_numpy(), None
    if rule in ("down_week", "up_week"):
        wk = c.index.to_period("W")
        last = pd.Series(wk, index=c.index) != pd.Series(wk, index=c.index).shift(-1)     # last trading day of a week
        fri = c[last]
        chg = fri.pct_change()
        sig = pd.Series(False, index=c.index)
        sig[fri.index] = (chg < 0) if rule == "down_week" else (chg > 0)
        return sig.to_numpy(), None
    if rule == "turn_of_month":
        m = pd.Series(c.index.to_period("M"), index=c.index)
        pos_from_end = m.groupby(m).cumcount(ascending=False)      # 0 = the month's last trading day
        sig = (pos_from_end == 4)                                  # decided at this close -> buy the next open (4th-last)
        return sig.to_numpy(), None
    if rule == "gap_down":
        return (d["open"] <= c.shift(1) * 0.99).to_numpy(), None
    raise ValueError(rule)


def trades(d: pd.DataFrame, rule: str, cost: float) -> pd.DataFrame:
    """Pure (given the bars): every trade, one at a time."""
    o = d["open"].to_numpy()
    sig, ex = signals(d, rule)
    n = len(d)
    hold = HOLD
    if rule == "turn_of_month":
        m = pd.Series(d.index.to_period("M"), index=d.index)
        first4 = (m.groupby(m).cumcount() == 3).to_numpy()        # the 4th trading day of a month
    rows, i = [], 0
    while i < n - 1:
        if not sig[i]:
            i += 1
            continue
        e = i if rule == "gap_down" else i + 1                    # gap_down is known at that open
        if rule == "turn_of_month":
            later = np.nonzero(first4[e + 1:])[0]
            x = e + 1 + later[0] if len(later) else n
        else:
            x = min(e + hold, n - 1)
            if ex is not None:
                hit = np.nonzero(ex[e:min(e + hold, n - 1)])[0]
                if len(hit):
                    x = e + hit[0] + 1                            # out at the open after the exit close
        if x >= n:
            break
        rows.append((d.index[e], d.index[x], x - e, o[x] / o[e] - 1 - 2 * cost))
        i = x if rule != "gap_down" else x
    return pd.DataFrame(rows, columns=["entry", "exit", "days", "net"])


def with_excess(t: pd.DataFrame, d: pd.DataFrame, split: str) -> pd.DataFrame:
    """Each trade's return minus holding the ETF for as many days (its average open-to-open day, in that half)."""
    oo = d["open"].pct_change().shift(-1)                          # open t -> open t+1
    drift = {True: oo[:split].mean(), False: oo[split:].mean()}
    t = t.copy()
    early = t["entry"] < pd.Timestamp(split)
    t["excess"] = t["net"] - t["days"] * np.where(early, drift[True], drift[False])
    t["early"] = early
    return t


def strategy(t: pd.DataFrame, d: pd.DataFrame, rf: pd.Series) -> dict:
    oo = (d["open"].shift(-1) / d["open"] - 1).fillna(0.0)
    inpos = pd.Series(False, index=d.index)
    for r in t.itertuples():
        inpos.loc[r.entry:r.exit] = True
        inpos.loc[r.exit] = False                                  # sold at that open
    rfd = rf.reindex(d.index).ffill().fillna(0.0)
    r = pd.Series(np.where(inpos, oo, rfd), index=d.index)
    first = d.index[200]
    r, rfd, bh = r.loc[first:], rfd.loc[first:], oo.loc[first:]

    def perf(x):
        eq = (1 + x).cumprod()
        yrs = len(x) / 252
        ex = x - rfd
        return eq.iloc[-1] ** (1 / yrs) - 1, ex.mean() / ex.std() * np.sqrt(252), (eq / eq.cummax() - 1).min()
    return {"in_market": inpos.loc[first:].mean(), "strat": perf(r), "hold": perf(bh)}


def tstat(x: pd.Series) -> float:
    return x.mean() / x.std() * np.sqrt(len(x)) if len(x) > 1 and x.std() > 0 else np.nan


def main() -> None:
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    lines: list[str] = []

    def emit(s=""):
        print(s, flush=True)
        lines.append(s)

    irx = pd.read_csv(ROOT / "market_data" / "IRX.csv", index_col=0, parse_dates=True)["close"]
    rf = irx / 100 / 252
    data = {s: load(s) for fam in FAMILIES.values() for s in fam[0]}
    emit("# Swing trades up to a week on SPY or commodity ETFs - generated tables\n")
    emit(f"Daily bars to {END} (Yahoo, split/dividend adjusted). Excess = the trade minus holding the ETF for the same "
         "days. Strategy = in the ETF during trades, T-bills otherwise.\n")
    verdicts = []
    for fam, (syms, split) in FAMILIES.items():
        emit(f"## {fam} (halves split at {split[:4]})\n")
        emit("| rule | ETF | trades/yr | days held | win rate | avg net | avg excess | t (excess) | 1st half excess | "
             "2nd half excess | in market | strategy return/yr, Sharpe, worst | buy and hold |")
        emit("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
        for rule in RULES:
            per = {}
            for s in syms:
                d = data[s]
                t = with_excess(trades(d, rule, COSTS[s]), d, split)
                per[s] = t
                if t.empty:
                    continue
                st = strategy(t, d, rf)
                yrs = (d.index[-1] - d.index[200]).days / 365.25
                (sc, ss, sw), (hc, hs, hw) = st["strat"], st["hold"]
                emit(f"| {rule} | {s} | {len(t) / yrs:.0f} | {t['days'].mean():.1f} | {(t['net'] > 0).mean():.0%} | "
                     f"{t['net'].mean():+.2%} | {t['excess'].mean():+.2%} | {tstat(t['excess']):.1f} | "
                     f"{t.loc[t['early'], 'excess'].mean():+.2%} | {t.loc[~t['early'], 'excess'].mean():+.2%} | "
                     f"{st['in_market']:.0%} | {sc:+.1%}, {ss:.2f}, {sw:.0%} | {hc:+.1%}, {hs:.2f}, {hw:.0%} |")
            lead = per[syms[0]]
            rest = pd.concat([per[s] for s in syms[1:]], ignore_index=True)
            la, lb = lead.loc[lead["early"], "excess"].mean(), lead.loc[~lead["early"], "excess"].mean()
            ra, rb = rest.loc[rest["early"], "excess"].mean(), rest.loc[~rest["early"], "excess"].mean()
            ok = la > 0 and lb > 0 and tstat(lead["excess"]) >= 2 and ra > 0 and rb > 0
            verdicts.append((fam, rule, syms[0], lead, la, lb, ra, rb, ok))
        emit("")
    emit("## Verdicts (pass = lead ETF beats holding in both halves with t >= 2, AND the rest of the family does too)\n")
    emit("| family | rule | lead | win rate | avg net | avg excess | t | lead halves | rest halves | passes |")
    emit("|---|---|---|---|---|---|---|---|---|---|")
    for fam, rule, lead, t, la, lb, ra, rb, ok in verdicts:
        emit(f"| {fam} | {rule} | {lead} | {(t['net'] > 0).mean():.0%} | {t['net'].mean():+.2%} | {t['excess'].mean():+.2%} | "
             f"{tstat(t['excess']):.1f} | {la:+.2%} / {lb:+.2%} | {ra:+.2%} / {rb:+.2%} | {'**yes**' if ok else 'no'} |")
    OUT.mkdir(exist_ok=True)
    (OUT / "swing_etf.md").write_text("\n".join(lines) + "\n")
    print(f"\nwrote {OUT / 'swing_etf.md'}")


if __name__ == "__main__":
    main()
