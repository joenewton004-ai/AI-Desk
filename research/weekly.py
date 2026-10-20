"""Weekly strategies: decide at Friday's close, hold for a week.

    python research/weekly.py

Three well-documented weekly ideas, tested on the desk's stock universe:

  reversal   buy last week's biggest losers (short-term reversal: Jegadeesh 1990,
             Lehmann 1990). The bet: one-week drops are partly overreaction and bounce back.
  pullback   the same, but only stocks in an uptrend (above their 40-week average, top half of
             26-week strength) - "buy the dip in a strong stock".
  momentum   buy the strongest stocks of the last 6 months (skipping the latest week),
             re-picked every week.

Universe each week = the 750 largest US companies at the latest quarter-end (point-in-time,
data/backtest/snapshots_m*.pkl). Weekly closes, adjusted (data/backtest/weekly_adj.pkl).
Cash earns T-bills; Sharpe is above T-bills.

Two things flatter every result here, the reversal ones most:
  * prices are survivors-only: a loser that went on to collapse and delist is missing, which is
    exactly the stock a reversal strategy would have bought;
  * trades are modelled at the decision close. Live, we'd fill at Monday's open, after any weekend
    gap. The base cost (0.10% per trade) and the 0.30% stress case stand in for that.
Writes research/output/weekly.md; findings in research/WEEKLY.md.
"""

from __future__ import annotations

import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ai_desk.data import load_cash_rate  # noqa: E402

CACHE = ROOT / "data" / "backtest"
OUT = Path(__file__).resolve().parent / "output"
START, END = "2014-04-04", "2026-10-16"      # first Friday after the first point-in-time universe; last full week
MID = "2020-01-01"
COST = 0.001                                  # per unit of turnover (buy + sell of the whole book = 0.2%)


# --- pure pieces (unit-tested) ----------------------------------------------------

def clean_returns(px: pd.DataFrame) -> pd.DataFrame:
    r = px.pct_change(fill_method=None)
    return r.where(r.abs() < 3)              # a >300% week is bad data in a large company


def members_at(snaps: dict[pd.Timestamp, list[str]], d: pd.Timestamp) -> list[str]:
    """The universe as known at `d`: the latest quarter-end list on or before it."""
    known = [k for k in snaps if k <= d]
    return snaps[max(known)] if known else []


def pick_reversal(ret_w: pd.Series, n: int) -> list[str]:
    return list(ret_w.dropna().nsmallest(n).index)


def pick_pullback(ret_w: pd.Series, above: pd.Series, strength: pd.Series, n: int) -> list[str]:
    ok = above.fillna(False).astype(bool) & (strength.rank(pct=True) >= 0.5)
    return list(ret_w[ok[ok].index].dropna().nsmallest(n).index)


def pick_momentum(mom: pd.Series, above: pd.Series, n: int) -> list[str]:
    ok = above.fillna(False).astype(bool)
    return list(mom[ok[ok].index].dropna().nlargest(n).index)


def simulate(picks: dict[pd.Timestamp, list[str]], ret: pd.DataFrame, cost: float = COST,
             turnover_log: list | None = None) -> pd.Series:
    """Equal weight in each week's picks, held to the next decision date, cost on turnover.
    `picks[d]` may only use data up to d's close; the return earned is the following week's."""
    dates = sorted(picks)
    w = pd.Series(dtype=float)
    out = {}
    for d, nxt in zip(dates, dates[1:]):
        p = picks[d]
        if isinstance(p, dict):              # explicit weights (the rest sits in cash)
            target = pd.Series(p, dtype=float)
        else:
            target = pd.Series(1 / len(p), index=p) if p else pd.Series(dtype=float)
        turnover = target.sub(w, fill_value=0).abs().sum()
        if turnover_log is not None:
            turnover_log.append(turnover)
        r = ret.loc[nxt].reindex(target.index).fillna(0.0)
        out[nxt] = float((target * r).sum()) - turnover * cost
        grown = target * (1 + r)
        w = grown / grown.sum() if grown.sum() > 0 else grown
    return pd.Series(out)


def momentum_book(px, snaps, f, lookback=26, n=20, ma_filter=True, every=1, exit_ma: int | None = None,
                  universe: list[str] | None = None) -> dict:
    """Momentum picks (lookback weeks, skipping the latest), re-picked every `every` weeks.
    exit_ma: between re-picks, sell any holding that closes below its `exit_ma`-week average; its
    slice stays in cash until the next re-pick (the live bottleneck rule).
    universe: a fixed list of symbols instead of the point-in-time top 750."""
    mom = px.shift(1) / px.shift(lookback + 1) - 1
    ma_x = px.rolling(exit_ma, min_periods=exit_ma).mean() if exit_ma else None
    book, last, held = {}, [], {}
    for i, d in enumerate(f["dates"]):
        if i % every == 0 or not last:
            pool = universe if universe is not None else members_at(snaps, d)
            mem = [s for s in pool if s in px.columns and pd.notna(px.at[d, s])]
            above = f["above"].loc[d, mem] if ma_filter else pd.Series(True, index=mem)
            last = pick_momentum(mom.loc[d, mem], above, n)
            held = {s: 1 / len(last) for s in last} if last else {}
        elif ma_x is not None:
            held = {s: w for s, w in held.items() if pd.notna(px.at[d, s]) and px.at[d, s] >= ma_x.at[d, s]}
        book[d] = dict(held) if exit_ma else last
    return book


def stats(r: pd.Series, rf_w: pd.Series) -> dict:
    r = r.dropna()
    eq = (1 + r).cumprod()
    ex = r - rf_w.reindex(r.index).fillna(0)
    return {"CAGR": eq.iloc[-1] ** (52 / len(r)) - 1, "volatility": r.std() * np.sqrt(52),
            "Sharpe": ex.mean() / ex.std() * np.sqrt(52), "max drawdown": (eq / eq.cummax() - 1).min()}


# --- the experiment ------------------------------------------------------------------

def load():
    px = pickle.loads((CACHE / "weekly_adj.pkl").read_bytes())
    px = px.resample("W-FRI").last().loc[:END]
    snaps = {}
    for m in (3, 6, 9, 12):
        snaps.update({d: list(s.index) for d, s in pickle.loads((CACHE / f"snapshots_m{m}.pkl").read_bytes()).items()})
    return px, dict(sorted(snaps.items()))


def build(px: pd.DataFrame, snaps: dict) -> dict:
    ret = clean_returns(px)
    ma40 = px.rolling(40, min_periods=40).mean()
    above = px > ma40
    strength = px / px.shift(26) - 1
    mom = px.shift(1) / px.shift(27) - 1                       # 26 weeks, skipping the latest one
    ret2 = px / px.shift(2) - 1
    dates = px.loc[START:END].index
    return {"ret": ret, "above": above, "strength": strength, "mom": mom, "ret2": ret2, "dates": dates}


def run_all(px, snaps, f, cost=COST) -> dict[str, pd.Series]:
    ret, dates = f["ret"], f["dates"]
    books = {k: {} for k in (
        "Reversal: 20 biggest 1-week losers", "Reversal: 10 losers", "Reversal: 50 losers",
        "Reversal: 20 biggest 2-week losers", "Pullback: 20 losers in an uptrend", "Pullback: 10 in an uptrend",
        "Pullback: 50 in an uptrend", "Momentum: top 20 by 6 months", "Momentum: top 50 by 6 months",
        "Equal-weight universe")}
    for d in dates:
        mem = [s for s in members_at(snaps, d) if s in px.columns and pd.notna(px.at[d, s])]
        if not mem:
            continue
        r1 = ret.loc[d, mem]
        books["Reversal: 20 biggest 1-week losers"][d] = pick_reversal(r1, 20)
        books["Reversal: 10 losers"][d] = pick_reversal(r1, 10)
        books["Reversal: 50 losers"][d] = pick_reversal(r1, 50)
        books["Reversal: 20 biggest 2-week losers"][d] = pick_reversal(f["ret2"].loc[d, mem], 20)
        books["Pullback: 20 losers in an uptrend"][d] = pick_pullback(r1, f["above"].loc[d, mem], f["strength"].loc[d, mem], 20)
        books["Pullback: 10 in an uptrend"][d] = pick_pullback(r1, f["above"].loc[d, mem], f["strength"].loc[d, mem], 10)
        books["Pullback: 50 in an uptrend"][d] = pick_pullback(r1, f["above"].loc[d, mem], f["strength"].loc[d, mem], 50)
        books["Momentum: top 20 by 6 months"][d] = pick_momentum(f["mom"].loc[d, mem], f["above"].loc[d, mem], 20)
        books["Momentum: top 50 by 6 months"][d] = pick_momentum(f["mom"].loc[d, mem], f["above"].loc[d, mem], 50)
        books["Equal-weight universe"][d] = mem
    out = {k: simulate(b, ret, 0.0 if k == "Equal-weight universe" else cost) for k, b in books.items()}
    return out



def main() -> None:
    lines: list[str] = []

    def emit(t=""):
        print(t)
        lines.append(t)

    px, snaps = load()
    f = build(px, snaps)
    rf = load_cash_rate(str(ROOT / "market_data" / "SPY.csv"))
    rf_w = (rf.resample("W-FRI").last().reindex(px.index, method="ffill") / 52).shift(1)
    spy_px = pd.read_csv(ROOT / "market_data" / "SPY.csv", index_col=0, parse_dates=True)["close"].resample("W-FRI").last()
    spy = spy_px.pct_change().reindex(px.index)

    base = run_all(px, snaps, f, COST)
    stress = run_all(px, snaps, f, 3 * COST)
    idx = base["Equal-weight universe"].index
    base["SPY"] = spy.reindex(idx)

    emit("# Weekly strategies - generated tables\n")
    emit(f"Decide at Friday's close, hold one week. {idx[0].date()} to {idx[-1].date()}; universe = the 750 largest "
         "US companies at each quarter-end (point-in-time); survivors-only prices. Cost 0.10% per trade "
         "(stress: 0.30%). Sharpe above T-bills.\n")
    cols = ["CAGR", "volatility", "Sharpe", "max drawdown"]
    emit("| | return/yr | volatility | Sharpe | worst drop | at 3x costs | 2014-19 | 2020-26 | beat universe (years) |")
    emit("|---|---|---|---|---|---|---|---|---|")
    uni = base["Equal-weight universe"]
    yearly_u = (1 + uni).groupby(uni.index.year).prod() - 1
    for k, r in base.items():
        s, a, b = stats(r, rf_w), stats(r.loc[:MID], rf_w), stats(r.loc[MID:], rf_w)
        s3 = stats(stress[k], rf_w)["CAGR"] if k in stress else np.nan
        yr = (1 + r).groupby(r.index.year).prod() - 1
        beat = int((yr > yearly_u.reindex(yr.index)).sum()) if k != "Equal-weight universe" else 0
        emit(f"| {k} | {s['CAGR']:.1%} | {s['volatility']:.0%} | {s['Sharpe']:.2f} | {s['max drawdown']:.0%} | "
             f"{'' if s3 != s3 else f'{s3:.1%}'} | {a['CAGR']:.1%} ({a['Sharpe']:.2f}) | {b['CAGR']:.1%} ({b['Sharpe']:.2f}) | "
             f"{'' if k in ('Equal-weight universe', 'SPY') else f'{beat} of {len(yr)}'} |")

    # how much does each trade? (average weekly turnover of the book)
    emit("\n### Correlation of weekly returns with the equal-weight universe and with SPY\n")
    for k, r in base.items():
        if k in ("Equal-weight universe", "SPY"):
            continue
        emit(f"- {k}: {r.corr(uni):.2f} with the universe, {r.corr(base['SPY']):.2f} with SPY")

    # walk-forward: each January pick the variant with the best Sharpe so far, trade it for the year
    emit("\n### Walk-forward: choose the best variant on past data only, every January from 2017\n")
    cand = {k: v for k, v in base.items() if k not in ("Equal-weight universe", "SPY")}
    df = pd.DataFrame(cand)
    stitched, chosen = [], []
    for year in range(2017, int(END[:4]) + 1):
        past = df.loc[:f"{year - 1}-12-31"]
        ex = past.sub(rf_w.reindex(past.index).fillna(0), axis=0)
        best = (ex.mean() / ex.std()).idxmax()
        chosen.append(f"{year}: {best}")
        stitched.append(df.loc[f"{year}-01-01":f"{year}-12-31", best])
    oos = pd.concat(stitched)
    rows = {"Walk-forward choice (out of sample)": stats(oos, rf_w),
            "Equal-weight universe, same years": stats(uni.loc[oos.index[0]:], rf_w),
            "SPY, same years": stats(base["SPY"].loc[oos.index[0]:], rf_w)}
    emit("| | " + " | ".join(cols) + " |\n|---|" + "---|" * len(cols))
    for k, v in rows.items():
        emit(f"| {k} | " + " | ".join(f"{v[c]:.2f}" if c == "Sharpe" else f"{v[c]:.1%}" for c in cols) + " |")
    emit("\nChosen: " + "; ".join(chosen))

    # robustness of the one idea that worked
    emit("\n### Momentum robustness: lookback x number of stocks x trend filter x re-pick frequency\n")
    emit("Each cell: return/yr, Sharpe, worst drop | return at 3x costs | average share of the book traded each week.\n")
    emit("| lookback | stocks | 40-week filter | re-pick | return/yr | Sharpe | worst drop | at 3x costs | traded/week | 2014-19 Sharpe | 2020-26 Sharpe |")
    emit("|---|---|---|---|---|---|---|---|---|---|---|")
    grid = []
    for lb in (13, 26, 52):
        for n in (10, 20, 50):
            grid.append((lb, n, True, 1))
    grid += [(26, 20, False, 1), (26, 20, True, 2), (26, 20, True, 4), (52, 20, True, 4)]
    for lb, n, flt, every in grid:
        book = momentum_book(px, snaps, f, lb, n, flt, every)
        tl: list = []
        r = simulate(book, f["ret"], COST, tl)
        r3 = simulate(book, f["ret"], 3 * COST)
        s_, a, b = stats(r, rf_w), stats(r.loc[:MID], rf_w), stats(r.loc[MID:], rf_w)
        emit(f"| {lb}w | {n} | {'yes' if flt else 'no'} | every {every}w | {s_['CAGR']:.1%} | {s_['Sharpe']:.2f} | "
             f"{s_['max drawdown']:.0%} | {stats(r3, rf_w)['CAGR']:.1%} | {np.mean(tl) / 2:.0%} | {a['Sharpe']:.2f} | {b['Sharpe']:.2f} |")
    emit(f"\nFor comparison: equal-weight universe Sharpe {stats(uni, rf_w)['Sharpe']:.2f}, SPY {stats(base['SPY'], rf_w)['Sharpe']:.2f}. "
         "'Traded/week' is half the turnover: 25% means a quarter of the book is swapped each week.")

    OUT.mkdir(exist_ok=True)
    (OUT / "weekly.md").write_text("\n".join(lines) + "\n")
    print(f"\nwrote {OUT / 'weekly.md'}")


if __name__ == "__main__":
    main()
