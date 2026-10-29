"""Our own edge: search ~30 indicators and their pairs for patterns, on development years only, then test the few best
ONCE on years the search never saw.

    python research/own_edge.py      (data/backtest/daily_ohlcv.pkl + SEC snapshots for stocks; market_data/*.csv for ETFs)

Two panels:
  stocks  the 500 largest US companies at each date (SEC snapshots, 45-day filing lag), 2013-2026 daily bars
          (survivors-only prices - flatters dip-buying patterns; say so). Target: the next open to the open 5 trading
          days later, minus the average member over the same days (cross-sectional excess).
  ETFs    25 ETFs - indexes, 9 sectors, bonds, gold, silver, oil, gas, broad commodities, REITs, the dollar, high
          yield, emerging/developed markets. Target: the same 5-day return minus that ETF's own average 5-day return
          in the same period (beating holding it).
Indicators at each close (data up to that close only): returns over 1, 2, 5, 10, 20, 60, 120, 250 days and 12-1 month
momentum; RSI(2), RSI(14); distance from the 5/20/50/200-day averages; 20-day volatility and its 5/60-day ratio;
ATR(14) %; volume 5/60-day ratio; IBS (close within the day's range); today's range vs its 20-day average; distance
from the 52-week high and low; the open's gap; 20-day overnight and intraday returns; strength vs SPY over 20 days;
market context: SPY vs its 200-day, SPY's 5-day return, the VIX and its 5-day change; weekday; last 3 days of a month.
Stocks are ranked against each other each day (0-1); ETF indicators are used as they are.
Discovery (development years only: stocks 2013-2019, ETFs to 2012):
  A  each indicator in 10 buckets: the best bucket's average excess and its t (weekly, non-overlapping)
  B  every pair of indicators in 3 x 3 buckets: the best cell (at least 2,000 stock-weeks / 300 ETF-weeks)
  C  a gradient-boosted model (LightGBM) on all indicators, trained on development years, tuned on the last one
Holdout (stocks 2020-2026-10, ETFs 2013-2026), run once on: the 5 best single buckets, the 10 best pair cells, and the
model. Each as a weekly portfolio: every 5 trading days hold the names the rule picks (stocks: up to 20, highest model
score / any in the cell; ETFs: every ETF in the bucket/cell, or the model's top 3), equal weight, costs 0.05% (stocks)
or 0.02% (ETFs) each way on turnover; vs the equal-weight universe (stocks) or holding all ETFs equally.
With ~4,000 cells searched, the development numbers of the winners are inflated by luck - the holdout is the test.
Writes research/output/own_edge.md.
"""

from __future__ import annotations

import itertools
import pickle
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "research"))

from ai_desk.indicators import rsi  # noqa: E402

OUT = Path(__file__).resolve().parent / "output"
CACHE = ROOT / "data" / "backtest"
H = 5
TOP = 500
ETFS = ["SPY", "QQQ", "IWM", "DIA", "EFA", "EEM", "XLK", "XLF", "XLE", "XLV", "XLY", "XLP", "XLI", "XLU", "XLB",
        "TLT", "IEF", "HYG", "GLD", "SLV", "USO", "UNG", "DBC", "VNQ", "UUP"]
STOCK_SPLIT, STOCK_START, STOCK_END = "2020-01-01", "2013-01-01", "2026-10-20"
ETF_SPLIT, ETF_END = "2013-01-01", "2026-10-28"
COST = {"stocks": 0.0005, "ETFs": 0.0002}
MIN_CELL = {"stocks": 2000, "ETFs": 300}


# ---------------------------------------------------------------- data
def market() -> dict[str, pd.Series]:
    def csv(s):
        return pd.read_csv(ROOT / "market_data" / f"{s}.csv", index_col=0, parse_dates=True)
    spy = csv("SPY")["close"]
    vix = csv("VIX")["close"]
    return {"spy": spy, "vix": vix}


def etf_frames() -> dict[str, pd.DataFrame]:
    out = {}
    for f in ("open", "high", "low", "close", "volume"):
        cols = {}
        for s in ETFS:
            d = pd.read_csv(ROOT / "market_data" / f"{s}.csv", index_col=0, parse_dates=True).loc[:ETF_END]
            cols[s] = d[f].astype(float)
        out[f] = pd.DataFrame(cols)
    return out


def stock_frames() -> tuple[dict[str, pd.DataFrame], pd.DataFrame]:
    import ict
    snaps = ict.snapshots()
    daily = pickle.loads((CACHE / "daily_ohlcv.pkl").read_bytes())
    idx = daily["close"].index
    keys = sorted(snaps)
    member = pd.DataFrame(False, index=idx, columns=daily["close"].columns)
    for a, k in enumerate(keys):
        start = k + pd.Timedelta(days=45)
        end = keys[a + 1] + pd.Timedelta(days=45) if a + 1 < len(keys) else idx[-1] + pd.Timedelta(days=1)
        names = [s for s in snaps[k]["market_cap"].nlargest(TOP).index if s in member.columns]
        member.loc[(idx >= start) & (idx < end), names] = True
    syms = member.columns[member.any()]
    frames = {f: daily[f][syms].astype(float) for f in ("open", "high", "low", "close", "volume")}
    return frames, member[syms]


# ---------------------------------------------------------------- indicators
def features(fr: dict[str, pd.DataFrame], mk: dict[str, pd.Series]) -> dict[str, pd.DataFrame]:
    """Pure: indicators per (day, symbol), from data up to that day's close."""
    o, h, l, c, v = (fr[k] for k in ("open", "high", "low", "close", "volume"))
    lc = np.log(c)
    f = {}
    for n in (1, 2, 5, 10, 20, 60, 120, 250):
        f[f"ret_{n}d"] = lc - lc.shift(n)
    f["mom_12_1"] = lc.shift(21) - lc.shift(252)
    f["rsi_2"] = c.apply(lambda s: rsi(s.dropna(), 2).reindex(s.index))
    f["rsi_14"] = c.apply(lambda s: rsi(s.dropna(), 14).reindex(s.index))
    for n in (5, 20, 50, 200):
        f[f"vs_sma{n}"] = c / c.rolling(n, min_periods=n).mean() - 1
    r = lc.diff()
    f["vol_20d"] = r.rolling(20).std()
    f["vol_ratio_5_60"] = r.rolling(5).std() / r.rolling(60).std()
    tr = pd.concat([(h - l), (h - c.shift(1)).abs(), (l - c.shift(1)).abs()]).groupby(level=0).max().reindex(c.index)
    f["atr_pct"] = tr.rolling(14).mean() / c
    f["volume_5_60"] = v.rolling(5).mean() / v.rolling(60).mean()
    f["ibs"] = (c - l) / (h - l).where(h > l)
    f["range_vs_20d"] = (h - l) / (h - l).rolling(20).mean()
    f["vs_52w_high"] = c / c.rolling(252, min_periods=200).max() - 1
    f["vs_52w_low"] = c / c.rolling(252, min_periods=200).min() - 1
    f["gap"] = o / c.shift(1) - 1
    f["overnight_20d"] = (np.log(o) - lc.shift(1)).rolling(20).sum()
    f["intraday_20d"] = (lc - np.log(o)).rolling(20).sum()
    spy = mk["spy"].reindex(c.index).ffill()
    vix = mk["vix"].reindex(c.index).ffill()
    f["vs_spy_20d"] = f["ret_20d"].sub(np.log(spy) - np.log(spy.shift(20)), axis=0)
    ctx = {"spy_vs_sma200": spy / spy.rolling(200).mean() - 1, "spy_ret_5d": np.log(spy / spy.shift(5)),
           "vix": vix, "vix_chg_5d": np.log(vix / vix.shift(5)),
           "weekday": pd.Series(c.index.dayofweek, index=c.index).astype(float)}
    m = pd.Series(c.index.to_period("M"), index=c.index)
    ctx["month_end_3d"] = (m.groupby(m).cumcount(ascending=False) <= 2).astype(float)
    for k, s in ctx.items():
        f[k] = pd.DataFrame(np.repeat(s.to_numpy()[:, None], c.shape[1], axis=1), index=c.index, columns=c.columns)
    return f


CONTEXT = {"spy_vs_sma200", "spy_ret_5d", "vix", "vix_chg_5d", "weekday", "month_end_3d"}


def target(fr: dict[str, pd.DataFrame]) -> pd.DataFrame:
    o = fr["open"]
    return o.shift(-(H + 1)) / o.shift(-1) - 1           # bought at the next open, sold H days later at the open


def long_panel(feat: dict, tgt: pd.DataFrame, member: pd.DataFrame | None, start, end, rank: bool) -> pd.DataFrame:
    """One row per (day, symbol) that is in the universe: indicators (ranked 0-1 across symbols for stocks, except
    the market context) and the 5-day target as excess over the day's universe average."""
    days = tgt.loc[start:end].index
    mask = (member.reindex(days) if member is not None else tgt.loc[days].notna()) & tgt.loc[days].notna()
    cols = {}
    for k, x in feat.items():
        x = x.reindex(days)
        if rank and k not in CONTEXT:
            x = x.where(mask).rank(axis=1, pct=True)
        cols[k] = x.where(mask).stack(future_stack=True)
    y = tgt.loc[days].where(mask)
    if rank:
        y = y.sub(y.mean(axis=1), axis=0)                 # vs the average member that day
    df = pd.DataFrame(cols)
    df["y"] = y.stack(future_stack=True)
    df = df.dropna(subset=["y"])
    df.index.names = ["date", "sym"]
    return df


# ---------------------------------------------------------------- discovery and evaluation
def weekly(df: pd.DataFrame) -> pd.DataFrame:
    """Every 5th trading day (non-overlapping holds)."""
    d = df.index.get_level_values("date")
    u = pd.Index(sorted(d.unique()))
    keep = set(u[::H])
    return df[d.isin(keep)]


def cell_stats(df: pd.DataFrame, mask: pd.Series) -> dict:
    """Average excess of the names a rule picks, per week (equal weight within the week), and its t."""
    x = df.loc[mask, "y"]
    if len(x) == 0:
        return {"n": 0, "mean": np.nan, "t": np.nan, "weeks": 0}
    wk = x.groupby(level="date").mean()
    t = wk.mean() / wk.std() * np.sqrt(len(wk)) if len(wk) > 2 and wk.std() > 0 else np.nan
    return {"n": len(x), "mean": wk.mean(), "t": t, "weeks": len(wk)}


def buckets(s: pd.Series, cuts: np.ndarray) -> pd.Series:
    """Bucket 0..len(cuts) by cut-points fixed on the development years; -1 where the indicator is missing."""
    b = pd.Series(np.digitize(s.to_numpy(), cuts), index=s.index)
    return b.where(s.notna(), -1)


def discover(dev: pd.DataFrame, kind: str) -> tuple[list, list, dict]:
    feats = [c for c in dev.columns if c != "y"]
    rank = kind == "stocks"
    edges10, edges3 = {}, {}
    for k in feats:                                  # cut-points from the development years only
        edges10[k] = np.unique(np.nanquantile(dev[k], np.linspace(0.1, 0.9, 9)))
        edges3[k] = np.unique(np.nanquantile(dev[k], [1 / 3, 2 / 3]))
    wdev = weekly(dev)
    singles = []
    for k in feats:
        b = buckets(wdev[k], edges10[k])
        for lvl in sorted(set(b.dropna().unique()) - {-1}):
            st = cell_stats(wdev, b == lvl)
            if st["n"] >= MIN_CELL[kind] / 2:
                singles.append({"rule": (k, int(lvl)), **st})
    singles.sort(key=lambda r: -(r["t"] if r["t"] == r["t"] else -99))
    b3 = {k: buckets(wdev[k], edges3[k]) for k in feats}
    pairs = []
    for a, b in itertools.combinations(feats, 2):
        if a in CONTEXT and b in CONTEXT and rank:
            continue                                   # two market-wide indicators pick everyone or no one
        key = b3[a] * 3 + b3[b]
        for cell in range(9):
            m = key == cell
            if m.sum() < MIN_CELL[kind]:
                continue
            st = cell_stats(wdev, m & (b3[a] >= 0) & (b3[b] >= 0))
            pairs.append({"rule": (a, cell // 3, b, cell % 3), **st})
    pairs.sort(key=lambda r: -(r["t"] if r["t"] == r["t"] else -99))
    return singles, pairs, {"edges10": edges10, "edges3": edges3}


def rule_mask(df: pd.DataFrame, rule: tuple, kind: str, edges: dict) -> pd.Series:
    if len(rule) == 2:
        k, lvl = rule
        return buckets(df[k], edges["edges10"][k]) == lvl
    a, la, b, lb = rule
    return (buckets(df[a], edges["edges3"][a]) == la) & (buckets(df[b], edges["edges3"][b]) == lb)


def portfolio(df: pd.DataFrame, picks: pd.Series, cost: float, cap: int | None, score: pd.Series | None = None) -> dict:
    """Weekly equal-weight portfolio of the picks (capped at `cap` by score when given), with turnover costs, vs
    the equal-weight universe. Returns per-week excess and the strategy's yearly stats."""
    w = weekly(df)
    p = picks.reindex(w.index).fillna(False).astype(bool)
    rows, prev = [], set()
    raw = df.attrs.get("raw")                           # the plain 5-day return (not excess), for the strategy line
    for d, g in w.groupby(level="date"):
        sel = g[p.loc[g.index]]
        if score is not None and cap and len(sel) > cap:
            sel = sel.loc[score.reindex(sel.index).nlargest(cap).index]
        names = set(sel.index.get_level_values("sym"))
        turn = len(names ^ prev) / max(len(names), 1) if names else (1.0 if prev else 0.0)
        prev = names
        uni = raw.loc[d] if raw is not None else None
        if names:
            r_pick = raw.loc[d].reindex(list(names)).mean() if raw is not None else sel["y"].mean()
        else:
            r_pick = 0.0
        rows.append({"date": d, "n": len(names), "excess": (sel["y"].mean() if names else np.nan),
                     "ret": r_pick - turn * cost, "uni": uni.mean() if uni is not None else np.nan})
    r = pd.DataFrame(rows).set_index("date")
    act = r[r["n"] > 0]
    ex = act["excess"]
    yrs = len(r) * H / 252

    def stats(x):
        eq = (1 + x.fillna(0)).cumprod()
        return eq.iloc[-1] ** (1 / yrs) - 1, x.mean() / x.std() * np.sqrt(252 / H), (eq / eq.cummax() - 1).min()
    return {"weeks_held": len(act), "avg_names": act["n"].mean() if len(act) else 0, "excess": ex.mean(),
            "t": ex.mean() / ex.std() * np.sqrt(len(ex)) if len(ex) > 2 else np.nan,
            "hit": (ex > 0).mean() if len(ex) else np.nan, "strat": stats(r["ret"]), "uni": stats(r["uni"])}


def run_panel(kind: str, panel: pd.DataFrame, split: str, raw: pd.DataFrame, emit) -> None:
    import lightgbm as lgb
    dev = panel[panel.index.get_level_values("date") < pd.Timestamp(split)]
    hold = panel[panel.index.get_level_values("date") >= pd.Timestamp(split)]
    hold.attrs["raw"] = raw
    emit(f"\n## {kind}: {dev.index.get_level_values('date').min().date()} to {split} (search), "
         f"{split} to {hold.index.get_level_values('date').max().date()} (holdout)\n")
    singles, pairs, edges = discover(dev, kind)
    emit(f"Searched {len(singles)} single buckets and {len(pairs)} pair cells on the development years.\n")
    feats = [c for c in panel.columns if c != "y"]
    # the model: train on development years before the last, tune trees on the last development year
    d_dates = dev.index.get_level_values("date")
    last = d_dates.max() - pd.Timedelta(days=365)
    tr, va = dev[d_dates < last], dev[d_dates >= last]
    yclip = dev["y"].quantile([0.01, 0.99]).to_numpy()
    params = dict(objective="regression", learning_rate=0.03, num_leaves=15, min_data_in_leaf=MIN_CELL[kind],
                  feature_fraction=0.7, bagging_fraction=0.7, bagging_freq=1, lambda_l2=10.0, verbose=-1, seed=7)
    ds_tr = lgb.Dataset(tr[feats], tr["y"].clip(*yclip))
    ds_va = lgb.Dataset(va[feats], va["y"].clip(*yclip))
    model = lgb.train(params, ds_tr, num_boost_round=600, valid_sets=[ds_va],
                      callbacks=[lgb.early_stopping(50, verbose=False)])
    imp = pd.Series(model.feature_importance("gain"), index=feats).sort_values(ascending=False)
    score_dev = pd.Series(model.predict(dev[feats]), index=dev.index)
    score_hold = pd.Series(model.predict(hold[feats]), index=hold.index)
    cap = 20 if kind == "stocks" else 3

    def top_by_score(df, sc):
        rk = sc.groupby(level="date").rank(ascending=False)
        return rk <= cap

    emit("| candidate | development: avg excess per week | t | holdout: avg excess per week | t | weeks beat | "
         "names held | strategy return/yr, Sharpe, worst | universe |")
    emit("|---|---|---|---|---|---|---|---|---|")
    cands = [(f"single: {r['rule'][0]} bucket {r['rule'][1] + 1}/10", r["rule"], r) for r in singles[:5]]
    cands += [(f"pair: {r['rule'][0]} {['low', 'mid', 'high'][r['rule'][1]]} + {r['rule'][2]} "
               f"{['low', 'mid', 'high'][r['rule'][3]]}", r["rule"], r) for r in pairs[:10]]
    for name, rule, devst in cands:
        m = rule_mask(hold, rule, kind, edges)
        st = portfolio(hold, m, COST[kind], None)
        sc, ss, sw = st["strat"]
        uc, us, uw = st["uni"]
        emit(f"| {name} | {devst['mean']:+.2%} | {devst['t']:.1f} | {st['excess']:+.2%} | {st['t']:.1f} | "
             f"{st['hit']:.0%} | {st['avg_names']:.0f} | {sc:+.1%}, {ss:.2f}, {sw:.0%} | {uc:+.1%}, {us:.2f}, {uw:.0%} |")
    dv = cell_stats(weekly(dev), top_by_score(dev, score_dev).reindex(weekly(dev).index))
    st = portfolio(hold, top_by_score(hold, score_hold), COST[kind], cap, score_hold)
    sc, ss, sw = st["strat"]
    uc, us, uw = st["uni"]
    emit(f"| model (LightGBM, top {cap} each week) | {dv['mean']:+.2%} | {dv['t']:.1f} | {st['excess']:+.2%} | "
         f"{st['t']:.1f} | {st['hit']:.0%} | {st['avg_names']:.0f} | {sc:+.1%}, {ss:.2f}, {sw:.0%} | "
         f"{uc:+.1%}, {us:.2f}, {uw:.0%} |")
    # the model's holdout deciles: does a higher score mean a higher return?
    wh = weekly(hold)
    dec = score_hold.reindex(wh.index).groupby(level="date").rank(pct=True)
    dmean = wh["y"].groupby(np.minimum((dec * 10).astype(int), 9)).mean()
    emit(f"\nModel holdout, average 5-day excess by score decile (1 = lowest): "
         + ", ".join(f"{k + 1}: {v:+.2%}" for k, v in dmean.items()))
    emit("Model's most-used indicators: " + ", ".join(f"{k} ({v / imp.sum():.0%})" for k, v in imp.head(8).items()))


def main() -> None:
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    warnings.filterwarnings("ignore", category=pd.errors.PerformanceWarning)
    lines: list[str] = []

    def emit(s=""):
        print(s, flush=True)
        lines.append(s)

    mk = market()
    emit("# Our own edge: a search across indicators, judged on years the search never saw - generated tables\n")
    emit("Excess per week = the picks' 5-day return (next open to the open 5 days later) minus the universe's "
         "average (stocks) or the ETF's own average (ETFs). Strategy = the weekly portfolio after costs. "
         "**Stock prices are survivors-only.**")

    fr, member = stock_frames()
    feat = features(fr, mk)
    tgt = target(fr)
    panel = long_panel(feat, tgt, member, STOCK_START, STOCK_END, rank=True)
    raw = tgt.loc[STOCK_SPLIT:STOCK_END].where(member.reindex(tgt.loc[STOCK_SPLIT:STOCK_END].index))
    run_panel("stocks", panel, STOCK_SPLIT, raw, emit)

    efr = etf_frames()
    efeat = features(efr, mk)
    etgt = target(efr)
    epanel = long_panel(efeat, etgt, None, "1999-06-01", ETF_END, rank=False)
    d = epanel.index.get_level_values("date")
    # an ETF's own average 5-day return in each period - the excess is vs holding it
    for early in (True, False):
        m = (d < pd.Timestamp(ETF_SPLIT)) == early
        mu = epanel.loc[m, "y"].groupby(level="sym").transform("mean")
        epanel.loc[m, "y"] = epanel.loc[m, "y"] - mu
    run_panel("ETFs", epanel, ETF_SPLIT, etgt.loc[ETF_SPLIT:ETF_END], emit)

    OUT.mkdir(exist_ok=True)
    (OUT / "own_edge.md").write_text("\n".join(lines) + "\n")
    print(f"\nwrote {OUT / 'own_edge.md'}")


if __name__ == "__main__":
    main()
