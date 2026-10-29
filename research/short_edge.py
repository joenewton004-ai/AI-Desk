"""Our own edge with shorting: the same search as research/own_edge.py, for what to SHORT, and long/short books.

    python research/short_edge.py      (needs own_edge.py's data + scikit-learn/lightgbm; ~15 minutes)

Same panels, ~35 indicators, 5-day horizon and split as own_edge.py (stocks: top 500, search 2014-2019, holdout
2020-2026; ETFs: 25, search 1999-2012, holdout 2013-2026). Fixed before running:
1. Short discovery on the search years: the single buckets and indicator pairs whose names LAGGED the universe most.
2. Holdout, once: the 5 worst singles and 10 worst pairs as short books (every 5 days, equal weight, capped at the 20
   names they rank lowest on the model when more qualify), and long/short books:
     model L/S             LightGBM (as own_edge.py) - long its top 20, short its bottom 20
     pullback L/S          long "fell over 10 days + strong over 120 days" (own_edge's best pair) / short the best
                           short cell
     model L/S walk-forward  retrained each January on every earlier year
   ETFs: the model long top 3 / short bottom 3 across the 25 ETFs (cross-asset), judged against the ETFs' average.
3. Costs 0.05% each way per leg for stocks (0.02% ETFs) on turnover, plus a borrow fee on the short leg: 0.5%/yr
   (stress 2%/yr). Cash and the collateral behind shorts earn T-bills. A short book "works" if the names lag the
   universe; a long/short book is judged on its own return over T-bills and on its alpha after removing what it
   earns from the market moving (regression on the universe's weekly return).
Survivors-only prices: failed or delisted companies (the best shorts of all) are missing, so the SHORT side is shown
WORSE than it was; the long side is flattered as before. Writes research/output/short_edge.md.
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

import own_edge as oe  # noqa: E402
import own_edge_checks as ck  # noqa: E402

OUT = Path(__file__).resolve().parent / "output"
BORROW, BORROW_STRESS = 0.005, 0.02


def book(df: pd.DataFrame, pick: pd.Series, score: pd.Series | None, cap: int, lowest: bool) -> pd.DataFrame:
    """Every 5 trading days: the picked names (capped at `cap` by score, highest or lowest), their average excess and
    turnover."""
    w = oe.weekly(df)
    p = pick.reindex(w.index).fillna(False).to_numpy()
    rows, prev = [], set()
    for d, g in w[p].groupby(level="date"):
        if score is not None and len(g) > cap:
            s = score.reindex(g.index)
            g = g.loc[(s.nsmallest(cap) if lowest else s.nlargest(cap)).index]
        names = set(g.index.get_level_values("sym"))
        rows.append({"date": d, "excess": g["y"].mean(), "n": len(names),
                     "turn": len(names ^ prev) / max(len(names), 1)})
        prev = names
    return pd.DataFrame(rows).set_index("date") if rows else pd.DataFrame(columns=["excess", "n", "turn"])


def t(x: pd.Series) -> float:
    x = x.dropna()
    return x.mean() / x.std() * np.sqrt(len(x)) if len(x) > 2 and x.std() > 0 else np.nan


def long_short(long_b: pd.DataFrame, short_b: pd.DataFrame, cost: float, borrow: float, weeks: pd.Index) -> pd.Series:
    """Weekly return of long - short (each leg 100% of equity), after turnover costs and borrow; 0 when a leg is
    empty that week (the T-bill on equity is added by the caller)."""
    lg = long_b.reindex(weeks)
    sh = short_b.reindex(weeks)
    r = (lg["excess"] - lg["turn"] * cost) - (sh["excess"] + sh["turn"] * cost + borrow * oe.H / 252)
    return r.where(lg["excess"].notna() & sh["excess"].notna(), 0.0).fillna(0.0)


def stats(r: pd.Series, uni: pd.Series, rf_w: pd.Series) -> dict:
    """Weekly long/short returns (excess-based, so T-bills come on top): yearly return incl. T-bills, Sharpe above
    T-bills, worst drop, and alpha after removing what it earns from the market moving."""
    total = r + rf_w.reindex(r.index).fillna(0.0)
    eq = (1 + total).cumprod()
    yrs = len(r) * oe.H / 252
    x = pd.DataFrame({"r": r, "m": uni.reindex(r.index)}).dropna()
    slope, alpha = np.polyfit(x["m"], x["r"], 1) if len(x) > 10 else (np.nan, np.nan)
    res = x["r"] - (slope * x["m"] + alpha)
    return {"cagr": eq.iloc[-1] ** (1 / yrs) - 1, "sharpe": r.mean() / r.std() * np.sqrt(252 / oe.H),
            "worst": (eq / eq.cummax() - 1).min(), "beta": slope, "alpha": alpha,
            "alpha_t": alpha / (res.std() / np.sqrt(len(x))) if len(x) > 10 else np.nan, "weeks": len(r)}


def main() -> None:
    warnings.filterwarnings("ignore")
    lines: list[str] = []

    def emit(s=""):
        print(s, flush=True)
        lines.append(s)

    mk = oe.market()
    irx = pd.read_csv(ROOT / "market_data" / "IRX.csv", index_col=0, parse_dates=True)["close"] / 100 / 252
    emit("# Our own edge with shorting - generated tables\n")
    emit("Short book excess = how much its names did vs the universe (negative = good for a short). Long/short = each "
         "leg 100% of equity, after costs and borrow (0.5%/yr; stress 2%/yr); T-bills on the cash on top. Alpha = what's "
         "left after removing what the book earns from the market moving. **Stock prices are survivors-only: the short "
         "side is shown worse than it was, the long side better.**\n")

    # ---------------- stocks
    fr, member = oe.stock_frames()
    feat = oe.features(fr, mk)
    tgt = oe.target(fr)
    panel = oe.long_panel(feat, tgt, member, oe.STOCK_START, oe.STOCK_END, rank=True)
    feats = [c for c in panel.columns if c != "y"]
    dates = panel.index.get_level_values("date")
    dev, hold = panel[dates < pd.Timestamp(oe.STOCK_SPLIT)], panel[dates >= pd.Timestamp(oe.STOCK_SPLIT)]
    uni = tgt.where(member).mean(axis=1)                                   # the universe's own 5-day return
    rf_w = irx.reindex(uni.index).ffill().rolling(oe.H).sum().shift(-oe.H)  # T-bills over the same 5 days
    neg = dev.copy()
    neg["y"] = -neg["y"]                                                   # search for the worst names
    singles, pairs, edges = oe.discover(neg, "stocks")
    model = ck.fit(dev, feats)
    sc = pd.Series(model.predict(hold[feats]), index=hold.index)
    weeks = oe.weekly(hold).index.get_level_values("date").unique()
    cost = oe.COST["stocks"]
    emit("## Stocks: 2014-2019 search, 2020-2026 holdout\n")
    emit(f"Searched {len(singles)} single buckets and {len(pairs)} pair cells for names that lag.\n")
    emit("### Short books (names lagging the universe; negative = a good short)\n")
    emit("| short candidate | search years: excess a week | t | holdout: excess a week | t | weeks it worked | names |")
    emit("|---|---|---|---|---|---|---|")
    cands = [(f"single: {r['rule'][0]} bucket {r['rule'][1] + 1}/10", r["rule"], r) for r in singles[:5]]
    cands += [(f"pair: {r['rule'][0]} {['low', 'mid', 'high'][r['rule'][1]]} + {r['rule'][2]} "
               f"{['low', 'mid', 'high'][r['rule'][3]]}", r["rule"], r) for r in pairs[:10]]
    short_books = {}
    for name, rule, dv in cands:
        b = book(hold, oe.rule_mask(hold, rule, "stocks", edges), sc, 20, lowest=True)
        short_books[name] = b
        emit(f"| {name} | {-dv['mean']:+.2%} | {-dv['t']:.1f} | {b['excess'].mean():+.2%} | {t(b['excess']):.1f} | "
             f"{(b['excess'] < 0).mean():.0%} | {b['n'].mean():.0f} |")
    rank = sc.groupby(level="date").rank(ascending=False)
    rank_lo = sc.groupby(level="date").rank(ascending=True)
    m_long = book(hold, rank <= 20, None, 20, lowest=False)
    m_short = book(hold, rank_lo <= 20, None, 20, lowest=True)
    emit(f"| model's bottom 20 | - | - | {m_short['excess'].mean():+.2%} | {t(m_short['excess']):.1f} | "
         f"{(m_short['excess'] < 0).mean():.0%} | 20 |")

    emit("\n### Long/short books (holdout 2020-2026)\n")
    emit("| book | return/yr (incl. T-bills) | Sharpe above T-bills | worst drop | market exposure (beta) | "
         "alpha a week | alpha t | at 2% borrow: return/yr |")
    emit("|---|---|---|---|---|---|---|---|")
    pull_rule = ("ret_10d", 0, "ret_120d", 2)
    pull_long = book(hold, oe.rule_mask(hold, pull_rule, "stocks", edges), sc, 20, lowest=False)
    best_short = min(short_books, key=lambda k: t(short_books[k]["excess"]) if len(short_books[k]) else 99)
    books = {"model: long top 20 / short bottom 20": (m_long, m_short),
             f"pullback long / short '{best_short}'": (pull_long, short_books[best_short]),
             "model long top 20 only (for comparison, vs the universe)": (m_long, None)}
    for name, (lb, sb) in books.items():
        if sb is None:
            r = (m_long["excess"] - m_long["turn"] * cost).reindex(weeks).fillna(0.0)
            r2 = r
        else:
            r = long_short(lb, sb, cost, BORROW, weeks)
            r2 = long_short(lb, sb, cost, BORROW_STRESS, weeks)
        s = stats(r, uni, rf_w)
        s2 = stats(r2, uni, rf_w)
        emit(f"| {name} | {s['cagr']:+.1%} | {s['sharpe']:.2f} | {s['worst']:.0%} | {s['beta']:+.2f} | "
             f"{s['alpha']:+.2%} | {s['alpha_t']:.1f} | {s2['cagr']:+.1%} |")

    emit("\n### The model long/short, walk-forward (retrained each January on every earlier year)\n")
    emit("| year | long/short a week | t |")
    emit("|---|---|---|")
    wf = []
    for y in range(2020, 2027):
        tr = panel[dates < pd.Timestamp(f"{y}-01-01")]
        te = panel[(dates >= pd.Timestamp(f"{y}-01-01")) & (dates < pd.Timestamp(f"{y + 1}-01-01"))]
        if te.empty:
            continue
        my = ck.fit(tr, feats)
        s_y = pd.Series(my.predict(te[feats]), index=te.index)
        lb = book(te, s_y.groupby(level="date").rank(ascending=False) <= 20, None, 20, False)
        sb = book(te, s_y.groupby(level="date").rank(ascending=True) <= 20, None, 20, True)
        wk_y = oe.weekly(te).index.get_level_values("date").unique()
        ry = long_short(lb, sb, cost, BORROW, wk_y)
        wf.append(ry)
        emit(f"| {y} | {ry.mean():+.2%} | {t(ry):.1f} |")
    wfr = pd.concat(wf)
    s = stats(wfr, uni, rf_w)
    emit(f"\nWalk-forward 2020-2026: {wfr.mean():+.2%} a week (t {t(wfr):.1f}); {s['cagr']:+.1%} a year incl. T-bills, "
         f"Sharpe {s['sharpe']:.2f}, worst {s['worst']:.0%}, beta {s['beta']:+.2f}, alpha {s['alpha']:+.2%} a week "
         f"(t {s['alpha_t']:.1f}).")

    # ---------------- ETFs: cross-asset long/short
    efr = oe.etf_frames()
    efeat = oe.features(efr, mk)
    etgt = oe.target(efr)
    ep = oe.long_panel(efeat, etgt, None, "1999-06-01", oe.ETF_END, rank=False)
    ep["y"] = ep["y"] - ep["y"].groupby(level="date").transform("mean")   # vs the ETFs' average that day
    ed = ep.index.get_level_values("date")
    edev, ehold = ep[ed < pd.Timestamp(oe.ETF_SPLIT)], ep[ed >= pd.Timestamp(oe.ETF_SPLIT)]
    efeats = [c for c in ep.columns if c != "y"]
    import lightgbm as lgb
    d_ = edev.index.get_level_values("date")
    last = d_.max() - pd.Timedelta(days=365)
    yclip = edev["y"].quantile([0.01, 0.99]).to_numpy()
    params = dict(objective="regression", learning_rate=0.03, num_leaves=15, min_data_in_leaf=oe.MIN_CELL["ETFs"],
                  feature_fraction=0.7, bagging_fraction=0.7, bagging_freq=1, lambda_l2=10.0, verbose=-1, seed=7)
    em = lgb.train(params, lgb.Dataset(edev[d_ < last][efeats], edev[d_ < last]["y"].clip(*yclip)), 600,
                   valid_sets=[lgb.Dataset(edev[d_ >= last][efeats], edev[d_ >= last]["y"].clip(*yclip))],
                   callbacks=[lgb.early_stopping(50, verbose=False)])
    esc = pd.Series(em.predict(ehold[efeats]), index=ehold.index)
    elong = book(ehold, esc.groupby(level="date").rank(ascending=False) <= 3, None, 3, False)
    eshort = book(ehold, esc.groupby(level="date").rank(ascending=True) <= 3, None, 3, True)
    eweeks = oe.weekly(ehold).index.get_level_values("date").unique()
    euni = etgt.mean(axis=1)
    erf = irx.reindex(euni.index).ffill().rolling(oe.H).sum().shift(-oe.H)
    er = long_short(elong, eshort, oe.COST["ETFs"], BORROW, eweeks)
    s = stats(er, euni, erf)
    emit("\n## ETFs: cross-asset long top 3 / short bottom 3 (model trained 1999-2012, holdout 2013-2026)\n")
    emit(f"- Long leg vs the ETFs' average: {elong['excess'].mean():+.2%} a week (t {t(elong['excess']):.1f}); short leg "
         f"{eshort['excess'].mean():+.2%} (t {t(eshort['excess']):.1f}; negative = good).")
    emit(f"- Long/short: {er.mean():+.2%} a week (t {t(er):.1f}); {s['cagr']:+.1%} a year incl. T-bills, Sharpe "
         f"{s['sharpe']:.2f}, worst {s['worst']:.0%}, beta {s['beta']:+.2f}, alpha {s['alpha']:+.2%} (t {s['alpha_t']:.1f}).")

    OUT.mkdir(exist_ok=True)
    (OUT / "short_edge.md").write_text("\n".join(lines) + "\n")
    print(f"\nwrote {OUT / 'short_edge.md'}")


if __name__ == "__main__":
    main()
