"""Michael Sikand's "asymmetric bets" style, turned into testable rules.

    python research/asymmetric.py

His stated process (research/ASYMMETRIC.md, from his public posts, Oct 2026): pick stocks tied to a
"mega theme" (AI infrastructure, defense, space), growing fast, trading at a discount to peers
(price-to-sales or EV/revenue vs comps), often well off their all-time high, and hold a concentrated
handful (5 positions, 15-20% each). The parts we can measure point-in-time:

  theme      the company's industry (2-digit SIC) is in the top quarter by 6-month price momentum
  growth     latest-year revenue growth in the top third of the universe (and above 15%)
  discount   price-to-sales below the median of its industry peers
  off highs  30-75% below its 12-month high
  hold       the top 5 by growth + discount rank, equal weight, re-picked monthly

Not testable: his judgement on moats, management, conference conversations, short-squeeze and
lock-up timing, and the narrative itself.

Universe: the 750 largest US companies at each quarter-end (point-in-time SEC fundamentals,
data/backtest/snapshots_m*.pkl), monthly adjusted prices, 0.10% per trade, cash at T-bills.
Survivors-only prices flatter this a lot: beaten-down growth stocks that went on to collapse and
delist are exactly what it would buy. His real picks are often smaller than this universe allows.
Writes research/output/asymmetric.md.
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
START, END = "2014-06-30", "2026-09-30"
COST = 0.001


# --- pure pieces (unit-tested) --------------------------------------------------------

def latest_snapshot(snaps: dict, d: pd.Timestamp) -> pd.DataFrame | None:
    known = [k for k in snaps if k <= d]
    return snaps[max(known)] if known else None


def features(snap: pd.DataFrame, px: pd.DataFrame, d: pd.Timestamp) -> pd.DataFrame:
    """Everything known at month-end `d`: fundamentals from the latest filing snapshot, prices to d."""
    hist = px.loc[:d]
    syms = [s for s in snap.index if s in hist.columns and pd.notna(hist[s].iloc[-1])]
    f = snap.loc[syms, ["sic2", "market_cap", "revenue_$bn", "rev_growth_recent"]].copy()
    last = hist[syms].iloc[-1]
    f["off_high"] = last / hist[syms].iloc[-12:].max() - 1
    f["mom_6m"] = last / hist[syms].iloc[-7] - 1 if len(hist) > 7 else np.nan
    f["ps"] = f["market_cap"] / (f["revenue_$bn"] * 1e9)
    f.loc[(f["ps"] <= 0) | ~np.isfinite(f["ps"]), "ps"] = np.nan
    ind_ps = f.groupby("sic2")["ps"].transform("median")
    f["ps_vs_peers"] = f["ps"] / ind_ps
    ind_mom = f.groupby("sic2")["mom_6m"].transform("median")
    f["theme"] = ind_mom.rank(pct=True) >= 0.75
    return f


def pick(f: pd.DataFrame, n: int = 5, theme=True, growth=True, discount=True, off_high=(-0.75, -0.30)) -> list[str]:
    ok = pd.Series(True, index=f.index)
    if theme:
        ok &= f["theme"].fillna(False).astype(bool)
    if growth:
        g = f["rev_growth_recent"]
        ok &= (g.rank(pct=True) >= 2 / 3) & (g > 0.15)
    if discount:
        ok &= f["ps_vs_peers"] < 1
    if off_high is not None:
        ok &= f["off_high"].between(*off_high)
    c = f[ok]
    if c.empty:
        return []
    score = c["rev_growth_recent"].rank(pct=True) + (-c["ps_vs_peers"]).rank(pct=True)
    return list(score.nlargest(n).index)


def simulate(picks: dict[pd.Timestamp, list[str]], ret: pd.DataFrame, rf_m: pd.Series, cost: float = COST) -> pd.Series:
    """Equal weight; the unfilled part of the book (fewer than n picks) earns T-bills."""
    dates = sorted(picks)
    w = pd.Series(dtype=float)
    out = {}
    for d, nxt in zip(dates, dates[1:]):
        p, n = picks[d]
        target = pd.Series(1 / n, index=p) if p else pd.Series(dtype=float)
        turnover = target.sub(w, fill_value=0).abs().sum()
        r = ret.loc[nxt].reindex(target.index).fillna(0.0)
        cash = 1 - target.sum()
        out[nxt] = float((target * r).sum()) + cash * float(rf_m.get(nxt, 0.0)) - turnover * cost
        grown = target * (1 + r)
        w = grown / (grown.sum() + cash) if (grown.sum() + cash) > 0 else grown
    return pd.Series(out)


def stats(r: pd.Series, rf_m: pd.Series) -> dict:
    r = r.dropna()
    eq = (1 + r).cumprod()
    ex = r - rf_m.reindex(r.index).fillna(0)
    return {"CAGR": eq.iloc[-1] ** (12 / len(r)) - 1, "volatility": r.std() * np.sqrt(12),
            "Sharpe": ex.mean() / ex.std() * np.sqrt(12) if ex.std() > 0 else np.nan,
            "max drawdown": (eq / eq.cummax() - 1).min()}


def main() -> None:
    lines: list[str] = []

    def emit(t=""):
        print(t)
        lines.append(t)

    px = pickle.loads((CACHE / "prices.pkl").read_bytes())["adj"].groupby(level=0).last().loc[:END]
    snaps = {}
    for m in (3, 6, 9, 12):
        snaps.update(pickle.loads((CACHE / f"snapshots_m{m}.pkl").read_bytes()))
    snaps = dict(sorted(snaps.items()))
    ret = px.pct_change(fill_method=None).where(lambda r: r.abs() < 3)
    rf = load_cash_rate(str(ROOT / "market_data" / "SPY.csv"))
    rf_m = (rf.resample("ME").last() / 12).shift(1).reindex(px.index).fillna(0)
    dates = px.loc[START:END].index

    variants = {
        "All four rules, 5 stocks (his style)": dict(n=5),
        "All four rules, 10 stocks": dict(n=10),
        "Without the theme rule": dict(n=5, theme=False),
        "Without 'off highs' (any price)": dict(n=5, off_high=None),
        "Without the discount rule": dict(n=5, discount=False),
        "Growth + discount only": dict(n=5, theme=False, off_high=None),
        "Theme + growth only (no valuation, no drawdown)": dict(n=5, discount=False, off_high=None),
    }
    books = {k: {} for k in variants}
    fill = {k: [] for k in variants}
    universe = {}
    feats = {}
    for d in dates:
        snap = latest_snapshot(snaps, d)
        if snap is None:
            continue
        f = features(snap, px, d)
        feats[d] = f
        universe[d] = (list(f.index), len(f))
        for k, kw in variants.items():
            n = kw.get("n", 5)
            p = pick(f, **kw)
            books[k][d] = (p, n)
            fill[k].append(len(p) / n)
    res = {k: simulate(b, ret, rf_m) for k, b in books.items()}
    res3 = {k: simulate(b, ret, rf_m, 3 * COST) for k, b in books.items()}
    res["Equal-weight universe"] = simulate(universe, ret, rf_m, 0.0)
    spy = px["SPY"].pct_change().reindex(res["Equal-weight universe"].index) if "SPY" in px else None
    if spy is not None:
        res["SPY"] = spy

    emit("# Asymmetric bets (Sikand-style rules) - generated tables\n")
    emit(f"Monthly, {dates[0]:%Y-%m} to {dates[-1]:%Y-%m}; universe = 750 largest US companies at each quarter-end "
         "(point-in-time); survivors-only prices; 0.10% per trade (stress 0.30%); empty slots earn T-bills.\n")
    emit("| rules | return/yr | volatility | Sharpe | worst drop | at 3x costs | 2014-19 | 2020-26 | slots filled | beat universe (years) |")
    emit("|---|---|---|---|---|---|---|---|---|---|")
    uni = res["Equal-weight universe"]
    yu = (1 + uni).groupby(uni.index.year).prod() - 1
    for k, r in res.items():
        s, a, b = stats(r, rf_m), stats(r.loc[:"2019"], rf_m), stats(r.loc["2020":], rf_m)
        s3 = f"{stats(res3[k], rf_m)['CAGR']:.1%}" if k in res3 else ""
        yr = (1 + r).groupby(r.index.year).prod() - 1
        beat = f"{int((yr > yu.reindex(yr.index)).sum())} of {len(yr)}" if k in variants else ""
        filled = f"{np.mean(fill[k]):.0%}" if k in fill else ""
        emit(f"| {k} | {s['CAGR']:.1%} | {s['volatility']:.0%} | {s['Sharpe']:.2f} | {s['max drawdown']:.0%} | {s3} | "
             f"{a['CAGR']:.1%} ({a['Sharpe']:.2f}) | {b['CAGR']:.1%} ({b['Sharpe']:.2f}) | {filled} | {beat} |")

    # what each single rule does on its own: next-month return of stocks that pass vs the universe
    emit("\n### Each rule on its own: average next-month return of stocks passing it, minus the universe average\n")
    emit("| rule | excess return / month | months positive | stocks passing (avg) |\n|---|---|---|---|")
    rules = {
        "Theme (industry in top quarter by 6-month momentum)": lambda f: f["theme"].fillna(False).astype(bool),
        "Growth (top third, >15%)": lambda f: (f["rev_growth_recent"].rank(pct=True) >= 2 / 3) & (f["rev_growth_recent"] > 0.15),
        "Discount (P/S below industry median)": lambda f: f["ps_vs_peers"] < 1,
        "Off highs (30-75% below 12-month high)": lambda f: f["off_high"].between(-0.75, -0.30),
    }
    ds = sorted(feats)
    for name, rule in rules.items():
        ex, npass = [], []
        for d, nxt in zip(ds, ds[1:]):
            f = feats[d]
            ok = rule(f)
            r = ret.loc[nxt].reindex(f.index)
            if ok.sum() == 0 or r.notna().sum() == 0:
                continue
            ex.append(r[ok].mean() - r.mean())
            npass.append(int(ok.sum()))
        ex = pd.Series(ex)
        emit(f"| {name} | {ex.mean():+.2%} | {(ex > 0).mean():.0%} | {np.mean(npass):.0f} |")

    OUT.mkdir(exist_ok=True)
    (OUT / "asymmetric.md").write_text("\n".join(lines) + "\n")
    print(f"\nwrote {OUT / 'asymmetric.md'}")


if __name__ == "__main__":
    main()
