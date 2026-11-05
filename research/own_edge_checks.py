"""Checks on the one survivor of research/own_edge.py: the LightGBM stock model (top 20 each week).

    python research/own_edge_checks.py      (same data as own_edge.py; ~10 minutes)

Diagnostics only - nothing here re-selects the model, so the holdout stays a holdout:
  1 holdout year by year              4 the model without the market-wide indicators (SPY trend, VIX, weekday, month end)
  2 what it buys (indicator ranks)    5 walk-forward: retrained each January on every earlier year, predicting that year
  3 when it earns (SPY vs 200-day)    6 costs 0.05% / 0.10% / 0.20% each way
  7 how much comes from stocks 40%+ below their 52-week high - where survivors-only prices flatter most
  8 extra market exposure: the picks' excess regressed on the universe's own 5-day return (high-volatility picks
    beat the average in rising weeks just by moving more)
Writes research/output/own_edge_checks.md.
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

OUT = Path(__file__).resolve().parent / "output"


def fit(train: pd.DataFrame, feats: list[str]):
    import lightgbm as lgb
    d = train.index.get_level_values("date")
    last = d.max() - pd.Timedelta(days=365)
    tr, va = train[d < last], train[d >= last]
    yclip = train["y"].quantile([0.01, 0.99]).to_numpy()
    params = dict(objective="regression", learning_rate=0.03, num_leaves=15, min_data_in_leaf=oe.MIN_CELL["stocks"],
                  feature_fraction=0.7, bagging_fraction=0.7, bagging_freq=1, lambda_l2=10.0, verbose=-1, seed=7)
    return lgb.train(params, lgb.Dataset(tr[feats], tr["y"].clip(*yclip)), num_boost_round=600,
                     valid_sets=[lgb.Dataset(va[feats], va["y"].clip(*yclip))],
                     callbacks=[lgb.early_stopping(50, verbose=False)])


def picks(df: pd.DataFrame, score: pd.Series, cap: int = 20) -> pd.Series:
    return score.groupby(level="date").rank(ascending=False) <= cap


def weekly_excess(df: pd.DataFrame, pick: pd.Series, cost: float) -> pd.DataFrame:
    """Per week: the picks' average excess, less turnover costs (both sides)."""
    w = oe.weekly(df)
    p = pick.reindex(w.index).fillna(False)
    rows, prev = [], set()
    for d, g in w.groupby(level="date"):
        sel = g[p.loc[g.index].to_numpy()]
        names = set(sel.index.get_level_values("sym"))
        turn = len(names ^ prev) / max(len(names), 1) if names else 0.0
        prev = names
        rows.append({"date": d, "excess": sel["y"].mean() if names else np.nan, "net": (sel["y"].mean() if names else 0.0)
                     - turn * cost, "n": len(names), "turn": turn})
    return pd.DataFrame(rows).set_index("date")


def t(x: pd.Series) -> float:
    x = x.dropna()
    return x.mean() / x.std() * np.sqrt(len(x)) if len(x) > 2 and x.std() > 0 else np.nan


def main() -> None:
    warnings.filterwarnings("ignore")
    lines: list[str] = []

    def emit(s=""):
        print(s, flush=True)
        lines.append(s)

    mk = oe.market()
    fr, member = oe.stock_frames()
    feat = oe.features(fr, mk)
    panel = oe.long_panel(feat, oe.target(fr), member, oe.STOCK_START, oe.STOCK_END, rank=True)
    feats = [c for c in panel.columns if c != "y"]
    dates = panel.index.get_level_values("date")
    dev, hold = panel[dates < pd.Timestamp(oe.STOCK_SPLIT)], panel[dates >= pd.Timestamp(oe.STOCK_SPLIT)]
    model = fit(dev, feats)
    sc = pd.Series(model.predict(hold[feats]), index=hold.index)
    pk = picks(hold, sc)
    wk = weekly_excess(hold, pk, oe.COST["stocks"])
    emit("# Checks on the stock model from research/own_edge.py - generated tables\n")
    emit(f"Holdout 2020-2026: {len(wk)} weeks, average excess {wk['excess'].mean():+.2%} a week (t {t(wk['excess']):.1f}); "
         f"after 0.05% costs each way {wk['net'].mean():+.2%} (average turnover {wk['turn'].mean():.0%} of the book a week). "
         "**Survivors-only prices.**\n")

    emit("## 1. Year by year\n")
    emit("| year | weeks | excess a week | t | weeks beat |")
    emit("|---|---|---|---|---|")
    for y, g in wk.groupby(wk.index.year):
        emit(f"| {y} | {len(g)} | {g['excess'].mean():+.2%} | {t(g['excess']):.1f} | {(g['excess'] > 0).mean():.0%} |")

    emit("\n## 2. What it buys (average rank of the picks, 0 = lowest in the 500, 1 = highest; 0.5 = typical)\n")
    sel = oe.weekly(hold)[pk.reindex(oe.weekly(hold).index).fillna(False).to_numpy()]
    traits = ["vol_20d", "atr_pct", "ret_5d", "ret_20d", "ret_60d", "ret_250d", "vs_52w_high", "vs_52w_low", "vs_sma200",
              "volume_5_60", "rsi_14", "overnight_20d"]
    emit("| indicator | picks' average rank |")
    emit("|---|---|")
    for k in traits:
        emit(f"| {k} | {sel[k].mean():.2f} |")

    emit("\n## 3. When it earns (SPY vs its 200-day average at the pick)\n")
    spy_up = oe.weekly(hold).groupby(level="date")["spy_vs_sma200"].first() > 0
    for lbl, m in (("SPY above its 200-day", spy_up), ("SPY below its 200-day", ~spy_up)):
        g = wk["excess"][m.reindex(wk.index).fillna(False)]
        emit(f"- {lbl}: {len(g)} weeks, {g.mean():+.2%} a week (t {t(g):.1f})")

    emit("\n## 4. Without the market-wide indicators\n")
    stock_only = [f for f in feats if f not in oe.CONTEXT]
    m2 = fit(dev, stock_only)
    w2 = weekly_excess(hold, picks(hold, pd.Series(m2.predict(hold[stock_only]), index=hold.index)), oe.COST["stocks"])
    emit(f"Stock-only indicators: holdout {w2['excess'].mean():+.2%} a week (t {t(w2['excess']):.1f}), after costs "
         f"{w2['net'].mean():+.2%}.")

    emit("\n## 5. Walk-forward (retrained each January on every earlier year)\n")
    emit("| year | excess a week | t |")
    emit("|---|---|---|")
    allw = []
    for y in range(2020, 2027):
        tr = panel[dates < pd.Timestamp(f"{y}-01-01")]
        te = panel[(dates >= pd.Timestamp(f"{y}-01-01")) & (dates < pd.Timestamp(f"{y + 1}-01-01"))]
        if te.empty:
            continue
        my = fit(tr, feats)
        wy = weekly_excess(te, picks(te, pd.Series(my.predict(te[feats]), index=te.index)), oe.COST["stocks"])
        allw.append(wy)
        emit(f"| {y} | {wy['excess'].mean():+.2%} | {t(wy['excess']):.1f} |")
    wf = pd.concat(allw)
    emit(f"\nWalk-forward 2020-2026: {wf['excess'].mean():+.2%} a week (t {t(wf['excess']):.1f}), after 0.05% costs "
         f"{wf['net'].mean():+.2%}.")

    emit("\n## 6. Costs\n")
    for c in (0.0005, 0.001, 0.002):
        wc = weekly_excess(hold, pk, c)
        emit(f"- {c:.2%} each way: {wc['net'].mean():+.2%} a week ({(1 + wc['net'].mean()) ** 52 - 1:+.1%} a year above "
             "the universe)")

    emit("\n## 7. Stocks far below their 52-week high (where survivors-only prices flatter most)\n")
    raw_drop = feat["vs_52w_high"].reindex(oe.weekly(hold).index.get_level_values("date").unique())
    w = oe.weekly(hold)
    pw = pk.reindex(w.index).fillna(False)
    drops = pd.Series([raw_drop.at[d, s] if s in raw_drop.columns else np.nan for d, s in w.index], index=w.index)
    deep = drops <= -0.4
    a = w.loc[pw & deep, "y"]
    b = w.loc[pw & ~deep, "y"]
    emit(f"- picks 40%+ below their 52-week high: {len(a):,} ({len(a) / max(pw.sum(), 1):.0%} of picks), average "
         f"excess {a.mean():+.2%}")
    emit(f"- the other picks: {len(b):,}, average excess {b.mean():+.2%}")
    emit(f"- share of the model's total excess from the deep fallers: {a.sum() / (a.sum() + b.sum()):.0%}")

    emit("\n## 8. Extra market exposure (beta)\n")
    tgt = oe.target(fr)
    uni = tgt.where(member).mean(axis=1).reindex(wk.index)
    x = pd.DataFrame({"ex": wk["excess"], "mkt": uni}).dropna()
    slope, alpha = np.polyfit(x["mkt"], x["ex"], 1)
    res = x["ex"] - (slope * x["mkt"] + alpha)
    emit(f"- The picks' excess rises {slope:+.2f} for every 1.00 the universe moves in a week (they swing "
         f"~{1 + slope:.2f}x the average stock).")
    emit(f"- Part of the +{x['ex'].mean():.2%} a week that is just that: {slope * x['mkt'].mean():+.2%} "
         f"(the universe averaged {x['mkt'].mean():+.2%} a week in 2020-2026).")
    emit(f"- What's left (alpha): {alpha:+.2%} a week, t {alpha / (res.std() / np.sqrt(len(x))):.1f}, before costs.")
    emit(f"- Up weeks: picks {x.loc[x['mkt'] > 0, 'ex'].mean():+.2%} vs the universe; down weeks "
         f"{x.loc[x['mkt'] <= 0, 'ex'].mean():+.2%}.")

    OUT.mkdir(exist_ok=True)
    (OUT / "own_edge_checks.md").write_text("\n".join(lines) + "\n")
    print(f"\nwrote {OUT / 'own_edge_checks.md'}")


if __name__ == "__main__":
    main()
