"""Does copying members of Congress's stock purchases beat the market? (House PTRs, 2014-2026)

    python research/house_ptr.py      (first: downloads and parses the House Clerk's reports -> data/congress/trades.csv)
    python research/congress.py

The idea behind day-trader-skill's trader-pelosi helper (and many "copy Congress" apps): members disclose their trades
within 45 days (STOCK Act); buy what they bought. The test buys at the NEXT OPEN AFTER THE REPORT WAS FILED - the
first moment the public could know - and holds 20, 60 or 120 trading days. Each event is measured against the
equal-weight average of all ~1,450 stocks in the price cache over the same days (same survivors-only bias), so the
market's drift doesn't count. Costs 0.05% each way. Rules fixed before running:
  all        every disclosed stock purchase (one event per member, stock and report)
  15k+       purchases with a lower amount band of $15,001 or more
  50k+       $50,001 or more
  cluster    a stock bought by 2+ different members whose reports were filed within 30 days (event = the 2nd report)
  fresh      reported within 14 days of the trade
  own        the member's own account (not spouse/joint/child)
  pelosi     Nancy Pelosi's purchases, stocks and options (scored on the stock) - what trader-pelosi copies
  sales      disclosed sales (should LAG if the trades carry information)
  trade-date all purchases from the TRADE date - not possible to copy; shows what the reporting delay costs
t-stats from monthly averages (events in the same month overlap). Periods 2014-2019 and 2020-2026. Plus a copy book:
every disclosed purchase held 60 trading days, equal weight, vs the equal-weight universe. House only, electronic
reports only (paper scans skipped), stocks in the price cache only (big and mid US companies that still exist).
Writes research/output/congress.md.
"""

from __future__ import annotations

import pickle
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent / "output"
TRADES = ROOT / "data" / "congress" / "trades.csv"
COST = 0.0005
SPLIT = pd.Timestamp("2020-01-01")
HOLDS = (20, 60, 120)


def load_trades() -> pd.DataFrame:
    t = pd.read_csv(TRADES, parse_dates=["date", "filed"], dtype={"doc_id": str})
    t = t[t["ticker"].notna() & t["date"].notna()].copy()
    t["ticker"] = t["ticker"].str.upper().str.replace(".", "-", regex=False).str.replace("/", "-", regex=False)
    t["delay"] = (t["filed"] - t["date"]).dt.days
    return t[(t["delay"] >= 0) & (t["delay"] <= 400)]          # drops mistyped trade dates


def events(t: pd.DataFrame, typ: str = "purchase", types=("ST",), when: str = "filed") -> pd.DataFrame:
    """Pure: one event per member, stock and report (several lots in one report count once)."""
    x = t[(t["type"] == typ) & (t["asset_type"].isin(types) | t["asset_type"].isna())]
    g = x.groupby(["politician", "ticker", "doc_id"], as_index=False).agg(
        filed=("filed", "first"), date=("date", "min"), amount_low=("amount_low", "max"), owner=("owner", "first"),
        delay=("delay", "min"))
    g["when"] = g[when]
    return g


def cluster(ev: pd.DataFrame, days: int = 30) -> pd.DataFrame:
    """Pure: events where a 2nd different member's report on the same stock was filed within `days` of another's;
    the event is dated at that 2nd report (when the cluster became public)."""
    out = []
    for tk, g in ev.sort_values("filed").groupby("ticker"):
        rows = g.to_dict("records")
        for i, r in enumerate(rows):
            prior = [p for p in rows[:i] if p["politician"] != r["politician"]
                     and 0 <= (r["filed"] - p["filed"]).days <= days]
            if prior:
                out.append(r)
    return pd.DataFrame(out, columns=ev.columns)


def score(ev: pd.DataFrame, opens: pd.DataFrame, base: dict[int, np.ndarray], lag: int = 1) -> pd.DataFrame:
    """Pure (given prices): each event's return from the open `lag` trading days after its date to the open `h`
    days later, after costs, and its excess over the equal-weight universe on the same days."""
    idx = opens.index
    o = opens.to_numpy(float)
    col = {s: j for j, s in enumerate(opens.columns)}
    rows = []
    for r in ev.itertuples():
        j = col.get(r.ticker)
        if j is None:
            continue
        e = idx.searchsorted(r.when, side="right") + lag - 1          # lag 1 = the first open after that day
        rec = {"ticker": r.ticker, "when": r.when, "entry": idx[e] if e < len(idx) else pd.NaT}
        for h in HOLDS:
            if e + h < len(idx) and o[e, j] > 0 and np.isfinite(o[e + h, j]):
                ret = o[e + h, j] / o[e, j] - 1 - 2 * COST
                rec[f"r{h}"], rec[f"x{h}"] = ret, ret - base[h][e]
            else:
                rec[f"r{h}"] = rec[f"x{h}"] = np.nan
        rows.append(rec)
    return pd.DataFrame(rows)


def stat(s: pd.DataFrame, h: int) -> dict:
    """Mean excess per event and its t from monthly averages, overall and per period."""
    d = s.dropna(subset=[f"x{h}"])
    if d.empty:
        return {"n": 0, "x": np.nan, "t": np.nan, "a": np.nan, "b": np.nan, "win": np.nan}
    m = d.groupby(d["entry"].dt.to_period("M"))[f"x{h}"].mean()
    t = m.mean() / m.std() * np.sqrt(len(m)) if len(m) > 2 and m.std() > 0 else np.nan
    return {"n": len(d), "x": d[f"x{h}"].mean(), "t": t, "win": (d[f"x{h}"] > 0).mean(),
            "a": d.loc[d["entry"] < SPLIT, f"x{h}"].mean(), "b": d.loc[d["entry"] >= SPLIT, f"x{h}"].mean()}


def copy_book(sc: pd.DataFrame, opens: pd.DataFrame, hold: int = 60) -> pd.Series:
    """Daily open-to-open returns of holding every disclosed purchase for `hold` days, equal weight, less turnover
    costs; NaN-free (days with nothing held earn 0 here; T-bill added by the caller)."""
    idx = opens.index
    w = pd.DataFrame(0.0, index=idx, columns=opens.columns)
    pos = {d: i for i, d in enumerate(idx)}
    for r in sc.dropna(subset=["entry"]).itertuples():
        e = pos[r.entry]
        w.iloc[e:e + hold, w.columns.get_loc(r.ticker)] += 1.0
    n = w.sum(axis=1)
    w = w.div(n.where(n > 0), axis=0).fillna(0.0)
    fwd = (opens.shift(-1) / opens - 1).fillna(0.0)
    gross = (w * fwd).sum(axis=1)
    cost = w.diff().abs().sum(axis=1).fillna(0.0) * COST
    return (gross - cost).where(n > 0, np.nan)


def perf(r: pd.Series, rf: pd.Series) -> dict:
    r = r.dropna()
    x = r - rf.reindex(r.index).fillna(0.0)
    eq = (1 + r).cumprod()
    yrs = len(r) / 252
    return {"cagr": eq.iloc[-1] ** (1 / yrs) - 1, "sharpe": x.mean() / x.std() * np.sqrt(252),
            "worst": (eq / eq.cummax() - 1).min()}


def main() -> None:
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    lines: list[str] = []

    def emit(s=""):
        print(s, flush=True)
        lines.append(s)

    daily = pickle.loads((ROOT / "data" / "backtest" / "daily_ohlcv.pkl").read_bytes())
    opens = daily["open"].astype(float)
    opens = opens.where(opens > 0)
    o = opens.to_numpy(float)
    base = {}
    for h in HOLDS:
        fwd = np.full_like(o, np.nan)
        fwd[:-h] = o[h:] / o[:-h] - 1
        base[h] = np.nanmean(fwd, axis=1) - 2 * COST
    irx = pd.read_csv(ROOT / "market_data" / "IRX.csv", index_col=0, parse_dates=True)["close"]
    rf = (irx.reindex(opens.index).ffill() / 100 / 252).fillna(0.0)

    t = load_trades()
    t = t[t["filed"] <= opens.index[-1] - pd.Timedelta(days=5)]
    buys = events(t)
    emit("# Copying Congress's stock purchases (House, 2014-2026) - generated tables\n")
    emit(f"{t['doc_id'].nunique():,} electronic reports, {len(t):,} transactions with a ticker. Stock purchases: "
         f"{len(buys):,} events, {buys['ticker'].isin(opens.columns).mean():.0%} in the price cache. Median delay "
         f"from trade to report: {buys['delay'].median():.0f} days (90% within {buys['delay'].quantile(0.9):.0f}).\n")
    emit("Excess = the stock minus the equal-weight universe over the same days, after 0.05% costs each way. Bought at "
         "the first open after the report was filed. **Survivors-only prices; paper reports and the Senate missing.**\n")

    variants = {
        "all": buys,
        "15k+": buys[buys["amount_low"] >= 15001],
        "50k+": buys[buys["amount_low"] >= 50001],
        "cluster": cluster(buys),
        "fresh": buys[buys["delay"] <= 14],
        "own": buys[buys["owner"] == "self"],
        "pelosi": events(t[t["politician"].str.contains("Pelosi")], types=("ST", "OP")),
        "sales": events(t, typ="sale"),
        "trade-date": events(t, when="date"),
    }
    scored = {}
    emit("| rule | hold | events | avg excess | t | beat universe | 2014-19 | 2020-26 |")
    emit("|---|---|---|---|---|---|---|---|")
    for name, ev in variants.items():
        sc = score(ev, opens, base)
        scored[name] = sc
        for h in HOLDS:
            s = stat(sc, h)
            emit(f"| {name} | {h}d | {s['n']:,} | {s['x']:+.2%} | {s['t']:.1f} | {s['win']:.0%} | {s['a']:+.2%} | "
                 f"{s['b']:+.2%} |")

    spy = pd.read_csv(ROOT / "market_data" / "SPY.csv", index_col=0, parse_dates=True)["open"].reindex(opens.index)
    so = spy.to_numpy(float)
    emit("\nThe same events against SPY instead (the cache's universe is today's big companies, so it is flattered "
         "by hindsight; SPY isn't):\n")
    for name in ("all", "50k+", "cluster", "pelosi"):
        sc = scored[name].dropna(subset=["entry"])
        e = opens.index.get_indexer(sc["entry"])
        parts = []
        for h in HOLDS:
            ok = e + h < len(so)
            x = sc[f"r{h}"].to_numpy()[ok] - (so[e[ok] + h] / so[e[ok]] - 1)
            parts.append(f"{h}d {np.nanmean(x):+.2%}")
        emit(f"- {name}: " + ", ".join(parts))

    emit("\nRobustness: 'all' bought one day later (2nd open after the report):\n")
    sc2 = score(buys, opens, base, lag=2)
    for h in HOLDS:
        s = stat(sc2, h)
        emit(f"- {h}d: {s['x']:+.2%} (t {s['t']:.1f}), 2014-19 {s['a']:+.2%}, 2020-26 {s['b']:+.2%}")

    emit("\n## Copy book: every disclosed purchase held 60 trading days, equal weight\n")
    emit("| book | period | return/yr | Sharpe (above T-bills) | worst drop |")
    emit("|---|---|---|---|---|")
    book = copy_book(scored["all"], opens)
    univ = pd.Series(np.nanmean((opens.shift(-1) / opens - 1).to_numpy(float), axis=1), index=opens.index)
    first = book.first_valid_index()
    for label, a, b in (("2014-2026", first, opens.index[-2]), ("2014-19", first, SPLIT), ("2020-26", SPLIT,
                                                                                            opens.index[-2])):
        spy_r = spy.shift(-1) / spy - 1
        for nm, r in (("copy Congress", book), ("equal-weight universe", univ), ("SPY", spy_r)):
            rr = r.loc[a:b]
            rr = rr.fillna(rf.reindex(rr.index))
            p = perf(rr, rf)
            emit(f"| {nm} | {label} | {p['cagr']:+.1%} | {p['sharpe']:.2f} | {p['worst']:.0%} |")
    OUT.mkdir(exist_ok=True)
    (OUT / "congress.md").write_text("\n".join(lines) + "\n")
    print(f"\nwrote {OUT / 'congress.md'}")


if __name__ == "__main__":
    main()
