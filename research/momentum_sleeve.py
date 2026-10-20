"""Should plain stock momentum replace the bottleneck sleeve's price-flow engine?

    python research/momentum_sleeve.py

Inside the 50/20/30 desk (50% quality screen re-picked quarterly, 20% bottleneck sleeve, 30% SPY
with the 12-month switch), swap the 20% sleeve's engine:

  current   industry money-flow rotation: 8 stocks from the hottest industries, 100-day average
            filter and exit, re-picked every 2 weeks (the live setting; research/BOTTLENECK.md)
  plain     top 20 stocks by 6-month return (skipping the latest week), above their 40-week
            average, re-picked every 4 weeks (research/WEEKLY.md); variants with the live exit
            rule, on the same stock pool as the current engine, and with 10 stocks

Same weekly prices, 0.10% per trade (and 3x), cash at T-bills, Sharpe above T-bills. Survivors-only
prices flatter both engines alike; compare them with each other first. Writes
research/output/momentum_sleeve.md; findings in research/MOMENTUM_SLEEVE.md.
"""

from __future__ import annotations

import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "research"))

import bottleneck_backtest as bb  # noqa: E402
import weekly  # noqa: E402
from ai_desk.data import load_cash_rate  # noqa: E402
from ai_desk.fundamentals import screen_backtest as sb  # noqa: E402

CACHE = ROOT / "data" / "backtest"
OUT = Path(__file__).resolve().parent / "output"
MONTH_END = "2026-09-30"


def monthly(r_weekly: pd.Series) -> pd.Series:
    return (1 + r_weekly).resample("ME").prod() - 1


def mstats(r: pd.Series, rf_m: pd.Series) -> dict:
    r = r.dropna()
    eq = (1 + r).cumprod()
    ex = r - rf_m.reindex(r.index).fillna(0)
    return {"CAGR": eq.iloc[-1] ** (12 / len(r)) - 1, "volatility": r.std() * np.sqrt(12),
            "Sharpe": ex.mean() / ex.std() * np.sqrt(12), "max drawdown": (eq / eq.cummax() - 1).min()}


def fmt_row(name, s):
    return (f"| {name} | {s['CAGR']:.1%} | {s['volatility']:.0%} | {s['Sharpe']:.2f} | {s['max drawdown']:.0%} |")


def main() -> None:
    lines: list[str] = []

    def emit(t=""):
        print(t)
        lines.append(t)

    # --- the sleeves (weekly) ---
    px, snaps = weekly.load()
    f = weekly.build(px, snaps)
    u = pickle.loads((CACHE / "universe.pkl").read_bytes())
    pool = sorted(set(u.tickers.values()) & set(px.columns))
    bpx = bb.weekly_prices(sorted(set(u.tickers.values())) + ["SPY"]).resample("W-FRI").last().loc[:bb.END]
    sic3 = pd.Series({t: (u.sic[c] or 0) // 10 for c, t in u.tickers.items()})
    stocks = bpx.drop(columns="SPY")
    sleeves_w = {}
    sleeves_w["Current: industry flow rotation (live setting)"], _ = bb.flow_rotation(
        stocks, sic3.reindex(stocks.columns), bpx["SPY"], repick_weeks=2, ma_weeks=20)
    sleeves3 = {}
    sleeves3["Current: industry flow rotation (live setting)"], _ = bb.flow_rotation(
        stocks, sic3.reindex(stocks.columns), bpx["SPY"], repick_weeks=2, ma_weeks=20, cost=0.003)
    variants = {
        "Plain momentum: top 20, every 4 weeks": dict(n=20, every=4),
        "Plain momentum + live exit (below 100-day avg)": dict(n=20, every=4, exit_ma=20),
        "Plain momentum on the current engine's pool": dict(n=20, every=4, universe=pool),
        "Plain momentum: top 10, every 4 weeks": dict(n=10, every=4),
    }
    for k, kw in variants.items():
        book = weekly.momentum_book(px, snaps, f, lookback=26, **kw)
        sleeves_w[k] = weekly.simulate(book, f["ret"], weekly.COST)
        sleeves3[k] = weekly.simulate(book, f["ret"], 3 * weekly.COST)

    # --- the other two sleeves (monthly) ---
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
    on = (spy_m / spy_m.shift(12) - 1 > 0).shift(1)
    sleeves_m = {k: monthly(v) for k, v in sleeves_w.items()}
    idx = screen.index
    for v in sleeves_m.values():
        idx = idx.intersection(v.index)
    idx = idx[idx <= pd.Timestamp(MONTH_END)]
    spy_mom = spy_m.pct_change().reindex(idx).where(on.reindex(idx).fillna(True).astype(bool), rf_m.reindex(idx))
    spy_ret = spy_m.pct_change().reindex(idx)
    rfm = rf_m.reindex(idx).fillna(0)

    emit("# Plain momentum vs the bottleneck sleeve's flow rotation - generated tables\n")
    emit(f"Monthly, {idx[0]:%Y-%m} to {idx[-1]:%Y-%m}. Survivors-only prices (both engines). 0.10% per trade.\n")

    emit("## 1. The 20% sleeve on its own\n")
    emit("| | return/yr | volatility | Sharpe | worst drop | at 3x costs | 2014-19 Sharpe | 2020-26 Sharpe |")
    emit("|---|---|---|---|---|---|---|---|")
    for k, v in sleeves_m.items():
        v = v.reindex(idx)
        s, a, b = mstats(v, rfm), mstats(v.loc[:"2019"], rfm), mstats(v.loc["2020":], rfm)
        s3 = mstats(monthly(sleeves3[k]).reindex(idx), rfm)
        emit(f"| {k} | {s['CAGR']:.1%} | {s['volatility']:.0%} | {s['Sharpe']:.2f} | {s['max drawdown']:.0%} | "
             f"{s3['CAGR']:.1%} | {a['Sharpe']:.2f} | {b['Sharpe']:.2f} |")
    emit(fmt_row("SPY (for reference)", mstats(spy_ret, rfm)).replace(" |", " |", 1) + " | | | |")

    emit("\n## 2. The whole desk: 50% quality screen + 20% sleeve + 30% SPY momentum\n")
    emit("| desk with | return/yr | volatility | Sharpe | worst drop | 2014-19 Sharpe | 2020-26 Sharpe | corr. with screen |")
    emit("|---|---|---|---|---|---|---|---|")
    desks = {}
    for k, v in sleeves_m.items():
        d = 0.5 * screen.reindex(idx) + 0.2 * v.reindex(idx) + 0.3 * spy_mom
        desks[k] = d
        s, a, b = mstats(d, rfm), mstats(d.loc[:"2019"], rfm), mstats(d.loc["2020":], rfm)
        emit(f"| {k} | {s['CAGR']:.1%} | {s['volatility']:.1%} | {s['Sharpe']:.2f} | {s['max drawdown']:.1%} | "
             f"{a['Sharpe']:.2f} | {b['Sharpe']:.2f} | {v.reindex(idx).corr(screen.reindex(idx)):.2f} |")
    d70 = 0.7 * screen.reindex(idx) + 0.3 * spy_mom
    s = mstats(d70, rfm)
    emit(f"| (no 20% sleeve: 70% screen + 30% SPY momentum) | {s['CAGR']:.1%} | {s['volatility']:.1%} | {s['Sharpe']:.2f} | "
         f"{s['max drawdown']:.1%} | | | |")

    cur = desks["Current: industry flow rotation (live setting)"]
    plain = desks["Plain momentum: top 20, every 4 weeks"]
    emit("\n## 3. How consistent is the difference?\n")
    yr = pd.DataFrame({"current": (1 + cur).groupby(cur.index.year).prod() - 1,
                       "plain": (1 + plain).groupby(plain.index.year).prod() - 1})
    emit("| year | desk with current engine | desk with plain momentum | difference |\n|---|---|---|---|")
    for y, r in yr.iterrows():
        emit(f"| {y} | {r['current']:+.1%} | {r['plain']:+.1%} | {r['plain'] - r['current']:+.1%} |")
    emit(f"\nPlain momentum's desk did better in {int((yr['plain'] > yr['current']).sum())} of {len(yr)} calendar years.")
    roll = pd.DataFrame({"c": cur, "p": plain})
    r36 = ((1 + roll).rolling(36).apply(np.prod, raw=True) - 1).dropna()
    emit(f"Over rolling 3-year windows it did better in {(r36['p'] > r36['c']).mean():.0%} of {len(r36)} windows.")

    emit("\n## 4. Walk-forward: each January, keep the engine with the better desk Sharpe so far\n")
    stitched, chosen = [], []
    for year in range(2017, 2027):
        past = pd.DataFrame({"current": cur, "plain": plain}).loc[:f"{year - 1}-12-31"]
        ex = past.sub(rfm.reindex(past.index), axis=0)
        best = (ex.mean() / ex.std()).idxmax()
        chosen.append(f"{year}: {best}")
        stitched.append((plain if best == "plain" else cur).loc[f"{year}-01-01":f"{year}-12-31"])
    oos = pd.concat(stitched)
    emit("| | return/yr | volatility | Sharpe | worst drop |\n|---|---|---|---|---|")
    emit(fmt_row("Walk-forward choice (out of sample)", mstats(oos, rfm)))
    emit(fmt_row("Always the current engine, same years", mstats(cur.loc[oos.index[0]:], rfm)))
    emit(fmt_row("Always plain momentum, same years", mstats(plain.loc[oos.index[0]:], rfm)))
    emit("\nChosen: " + "; ".join(chosen))

    OUT.mkdir(exist_ok=True)
    (OUT / "momentum_sleeve.md").write_text("\n".join(lines) + "\n")
    print(f"\nwrote {OUT / 'momentum_sleeve.md'}")


if __name__ == "__main__":
    main()
