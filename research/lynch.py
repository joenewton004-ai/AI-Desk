"""Peter Lynch's stock-picking rules, quantified and backtested on point-in-time SEC data.

    python research/lynch.py           (first run builds the features from the cached SEC filings; ~5 minutes)

Peter Lynch ran Fidelity Magellan 1977-1990 (about 29%/yr). His books ("One Up on Wall Street",
1989; "Beating the Street", 1993) give rules a computer can check, alongside ones it can't
("buy what you know", boring names, few analysts). The measurable ones, as tested here:

  PEG              P/E divided by the earnings growth rate (in %). Under 1 is attractive, under 0.5
                   very attractive, over 2 expensive. Growth = 3-year net-income growth per year
                   (trailing: historical forecasts don't exist point-in-time).
  Lynch ratio      (growth % + dividend yield %) / P/E - his dividend-adjusted version. 2+ "great",
                   1.5 good, under 1 poor.
  categories       slow growers (under 8%/yr), stalwarts (8-18%), fast growers (18-30%); he avoided
                   the hottest growers (over 30%/yr) as unsustainable.
  balance sheet    debt/equity under 0.5 or more cash than debt ("a company with no debt can't go bankrupt")
  inventory        inventories growing faster than sales is a warning (more than 5 points faster here)
  buybacks         share count not rising (he liked companies buying back stock)

Universe: the 750 largest US companies at each quarter-end, fundamentals as FILED by then
(data/backtest/snapshots_m*.pkl + the cached SEC filings in data/sec/). Quarterly re-picks, equal
weight, held to the next quarter-end, 0.10% per trade, cash in T-bills when nothing passes.
Survivors-only monthly prices flatter every row; compare with the equal-weight universe first
(same bias), SPY second. Writes research/output/lynch.md; findings in research/LYNCH.md.
"""

from __future__ import annotations

import gzip
import json
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ai_desk.data import load_cash_rate  # noqa: E402
from ai_desk.fundamentals import edgar  # noqa: E402
from ai_desk.fundamentals.scoring import score  # noqa: E402

CACHE = ROOT / "data" / "backtest"
SEC = ROOT / "data" / "sec"
OUT = Path(__file__).resolve().parent / "output"
MONTH_END = "2026-09-30"
SPLIT = "2020-01-01"
COST = 0.001

EXTRA_FLOW = {"dividends": ["PaymentsOfDividendsCommonStock", "PaymentsOfDividends", "PaymentsOfOrdinaryDividends",
                            "DividendsPaid", "DividendsPaidClassifiedAsFinancingActivities"]}
EXTRA_INSTANT = {"inventory": ["InventoryNet", "Inventories", "InventoryFinishedGoodsNetOfReserves"],
                 "equity": ["StockholdersEquity", "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
                            "Equity", "EquityAttributableToOwnersOfParent"]}


# --- pure pieces (unit-tested) --------------------------------------------------------

def growth_rate(ni: pd.Series, years: int = 3) -> float:
    """Net-income growth per year over `years`, both ends positive; else NaN."""
    ni = ni.dropna()
    if len(ni) < years + 1:
        return np.nan
    a, b = ni.iloc[-years - 1], ni.iloc[-1]
    if a <= 0 or b <= 0:
        return np.nan
    return (b / a) ** (1 / years) - 1


def lynch_metrics(mcap: float, ni: pd.Series, revenue: pd.Series, dividends: float, debt: float, cash: float,
                  equity: float, inventory: pd.Series, shares_now: float, shares_1y: float) -> dict:
    g = growth_rate(ni)
    last_ni = ni.dropna().iloc[-1] if ni.notna().any() else np.nan
    pe = mcap / last_ni if last_ni and last_ni > 0 else np.nan
    gp = g * 100 if pd.notna(g) else np.nan
    dy = (dividends / mcap) if pd.notna(dividends) and mcap > 0 else 0.0
    peg = pe / gp if pd.notna(pe) and pd.notna(gp) and gp > 0 else np.nan
    ratio = (gp + dy * 100) / pe if pd.notna(pe) and pd.notna(gp) else np.nan
    de = debt / equity if equity and equity > 0 else np.nan
    rev, inv = revenue.dropna(), inventory.dropna()
    inv_gap = np.nan
    if len(inv) >= 2 and len(rev) >= 2 and inv.iloc[-2] > 0 and rev.iloc[-2] > 0:
        inv_gap = (inv.iloc[-1] / inv.iloc[-2] - 1) - (rev.iloc[-1] / rev.iloc[-2] - 1)
    sh = shares_now / shares_1y - 1 if shares_now and shares_1y and shares_1y > 0 else np.nan
    return {"growth": g, "pe": pe, "peg": peg, "div_yield": dy, "lynch_ratio": ratio, "debt_equity": de,
            "net_cash": cash > debt, "inv_gap": inv_gap, "share_change": sh}


def category(g: float) -> str:
    if pd.isna(g):
        return "no steady earnings"
    if g < 0.08:
        return "slow grower"
    if g < 0.18:
        return "stalwart"
    if g <= 0.30:
        return "fast grower"
    return "hot grower (over 30%)"


def rules(f: pd.DataFrame) -> dict[str, pd.Series]:
    """Each Lynch rule as a pass/fail column (missing data fails the rule)."""
    safe = (f["debt_equity"] < 0.5) | f["net_cash"].fillna(False).astype(bool)
    inv_ok = f["inv_gap"].isna() | (f["inv_gap"] <= 0.05)        # no inventory (e.g. software) = no warning
    buyback = f["share_change"] <= 0.0
    return {"PEG under 1": f["peg"] < 1, "PEG under 0.5": f["peg"] < 0.5,
            "Lynch ratio 2+": f["lynch_ratio"] >= 2, "Lynch ratio 1.5+": f["lynch_ratio"] >= 1.5,
            "fast grower (18-30%)": f["growth"].between(0.18, 0.30), "stalwart (8-18%)": f["growth"].between(0.08, 0.18),
            "strong balance sheet": safe, "inventory not piling up": inv_ok, "shares not rising": buyback}


# --- features ------------------------------------------------------------------------

def extra_table(cik: int) -> pd.DataFrame:
    path = SEC / f"CIK{cik:010d}.json.gz"
    if not path.exists():
        return pd.DataFrame(columns=["item", "prio", "end", "filed", "accn", "val"])
    facts = json.loads(gzip.decompress(path.read_bytes()))
    rows = []
    for item, tags in (EXTRA_FLOW | EXTRA_INSTANT).items():
        flow = item in EXTRA_FLOW
        for prio, tag in enumerate(tags):
            for e in edgar._entries(facts, tag):
                if e.get("form") not in edgar.ANNUAL_FORMS:
                    continue
                if flow:
                    if "start" not in e or not 350 <= (pd.Timestamp(e["end"]) - pd.Timestamp(e["start"])).days <= 380:
                        continue
                rows.append((item, prio, e["end"], e["filed"], e.get("accn", ""), e["val"]))
    t = pd.DataFrame(rows, columns=["item", "prio", "end", "filed", "accn", "val"])
    t["end"], t["filed"] = pd.to_datetime(t["end"]), pd.to_datetime(t["filed"])
    return t


def build_features() -> dict[pd.Timestamp, pd.DataFrame]:
    path = CACHE / "lynch_features.pkl"
    if path.exists():
        return pickle.loads(path.read_bytes())
    u = pickle.loads((CACHE / "universe.pkl").read_bytes())
    snaps = {}
    for m in (3, 6, 9, 12):
        snaps.update(pickle.loads((CACHE / f"snapshots_m{m}.pkl").read_bytes()))
    snaps = dict(sorted(snaps.items()))
    extras: dict[int, pd.DataFrame] = {}
    out = {}
    for n, (d, snap) in enumerate(snaps.items()):
        rows = []
        for sym, r in snap.iterrows():
            cik = int(r["cik"])
            table = u.tables.get(cik)
            if table is None:
                continue
            if cik not in extras:
                extras[cik] = extra_table(cik)
            hist = edgar.annual_history(cik, table=table, as_of=d)
            if hist.empty:
                continue
            ex = extras[cik]
            ex = ex[ex["filed"] <= d]
            div = edgar._annual(ex, "dividends")
            inv = edgar._annual(ex, "inventory")
            eq = edgar._annual(ex, "equity")
            fy_end = eq.index.max() if len(eq) else None
            _, sh_now = edgar.shares_outstanding(table, as_of=d)
            _, sh_1y = edgar.shares_outstanding(table, as_of=d - pd.Timedelta(days=365))
            # align inventory with the same fiscal years as revenue (both annual, by year)
            inv_y = inv.groupby(inv.index.year).last() if len(inv) else pd.Series(dtype=float)
            rev_y = pd.Series(hist["revenue_$bn"].to_numpy() * 1e9, index=pd.PeriodIndex(hist.index, freq="Y").year)
            both = pd.concat([rev_y, inv_y], axis=1, keys=["rev", "inv"]).dropna()
            divs = div.groupby(div.index.year).last() if len(div) else pd.Series(dtype=float)
            dv = float(divs.iloc[-1]) if len(divs) and divs.index[-1] >= rev_y.index[-1] - 1 else 0.0
            m = lynch_metrics(float(r["market_cap"]), hist["net_income_$bn"] * 1e9, both["rev"] if len(both) else rev_y,
                              abs(dv), float(hist["debt_$bn"].iloc[-1] * 1e9), float(hist["cash_$bn"].iloc[-1] * 1e9),
                              float(eq.iloc[-1]) if len(eq) and fy_end is not None and (d - fy_end).days < 550 else np.nan,
                              both["inv"] if len(both) else pd.Series(dtype=float), sh_now, sh_1y)
            rows.append({"symbol": sym, **m})
        out[d] = pd.DataFrame(rows).set_index("symbol")
        print(f"  {d.date()}: {len(out[d])} companies ({n + 1}/{len(snaps)})", flush=True)
    path.write_bytes(pickle.dumps(out))
    return out


# --- the experiment ------------------------------------------------------------------

def simulate(book: dict[pd.Timestamp, list[str]], monthly: pd.DataFrame, rf_m: pd.Series, cost: float = COST) -> pd.Series:
    """Equal weight in each list from its date to the next one; weights drift monthly; empty = T-bills."""
    dates = sorted(book)
    out, w = {}, pd.Series(dtype=float)
    for i, d in enumerate(dates):
        names = [n for n in book[d] if n in monthly.columns]
        target = pd.Series(1 / len(names), index=names) if names else pd.Series(dtype=float)
        turnover = target.sub(w, fill_value=0).abs().sum()
        w = target
        nxt = dates[i + 1] if i + 1 < len(dates) else monthly.index[-1]
        months = monthly.loc[(monthly.index > d) & (monthly.index <= nxt)]
        for j, (m, row) in enumerate(months.iterrows()):
            if w.empty:
                out[m] = float(rf_m.get(m, 0.0)) - (turnover * cost if j == 0 else 0.0)
                continue
            r = row.reindex(w.index).fillna(0.0)
            out[m] = float((w * r).sum()) - (turnover * cost if j == 0 else 0.0)
            grown = w * (1 + r)
            w = grown / grown.sum() if grown.sum() > 0 else grown
    return pd.Series(out)


def stats(r: pd.Series, rf_m: pd.Series) -> dict:
    r = r.dropna()
    eq = (1 + r).cumprod()
    ex = r - rf_m.reindex(r.index).fillna(0)
    return {"CAGR": eq.iloc[-1] ** (12 / len(r)) - 1, "vol": r.std() * np.sqrt(12),
            "Sharpe": ex.mean() / ex.std() * np.sqrt(12) if ex.std() > 0 else np.nan, "dd": (eq / eq.cummax() - 1).min()}


def main() -> None:
    lines: list[str] = []

    def emit(t=""):
        print(t, flush=True)
        lines.append(t)

    feats = build_features()
    snaps = {}
    for m in (3, 6, 9, 12):
        snaps.update(pickle.loads((CACHE / f"snapshots_m{m}.pkl").read_bytes()))
    snaps = dict(sorted(snaps.items()))
    prices = pickle.loads((CACHE / "prices.pkl").read_bytes())
    adj = prices["adj"].groupby(level=0).last().loc[:MONTH_END]
    monthly = adj.pct_change(fill_method=None).where(lambda x: x.abs() < 3)
    rf = load_cash_rate(str(ROOT / "market_data" / "SPY.csv"))
    rf_m = (rf.resample("ME").last() / 12).shift(1).reindex(monthly.index).fillna(0)
    dates = [d for d in feats if d < pd.Timestamp(MONTH_END)]

    books = {k: {} for k in (
        "PEG under 1 (all that pass)", "PEG under 0.5",
        "Lynch ratio 2+ (growth + yield over P/E)",
        "Lynch fast grower: 18-30% growth, PEG under 1, strong balance sheet, inventory OK, no dilution",
        "Lynch stalwart: 8-18% growth, PEG under 1.2, strong balance sheet",
        "Lynch composite: top 25 by Lynch ratio, 8-30% growth, strong balance sheet, inventory OK",
        "Cheap P/E only: lowest 25 P/E (no growth check)",
        "Equal-weight universe", "Desk quality screen (top 25)")}
    fill = {k: [] for k in books}
    single = {}
    for d in dates:
        f = feats[d]
        snap = snaps[d]
        f = f.loc[f.index.intersection(snap.index)]
        r = rules(f)
        peg1 = f.index[r["PEG under 1"]]
        books["PEG under 1 (all that pass)"][d] = list(peg1)
        books["PEG under 0.5"][d] = list(f.index[r["PEG under 0.5"]])
        books["Lynch ratio 2+ (growth + yield over P/E)"][d] = list(f.index[r["Lynch ratio 2+"]])
        fast = r["fast grower (18-30%)"] & r["PEG under 1"] & r["strong balance sheet"] & r["inventory not piling up"] \
            & (f["share_change"] <= 0.02)
        books["Lynch fast grower: 18-30% growth, PEG under 1, strong balance sheet, inventory OK, no dilution"][d] = list(f.index[fast])
        stal = r["stalwart (8-18%)"] & (f["peg"] < 1.2) & r["strong balance sheet"]
        books["Lynch stalwart: 8-18% growth, PEG under 1.2, strong balance sheet"][d] = list(f.index[stal])
        comp = f[f["growth"].between(0.08, 0.30) & r["strong balance sheet"] & r["inventory not piling up"]]
        books["Lynch composite: top 25 by Lynch ratio, 8-30% growth, strong balance sheet, inventory OK"][d] = \
            list(comp["lynch_ratio"].nlargest(25).index)
        books["Cheap P/E only: lowest 25 P/E (no growth check)"][d] = list(f["pe"].dropna().nsmallest(25).index)
        books["Equal-weight universe"][d] = list(snap.index)
        ok = snap[snap["passes_gates"]]
        books["Desk quality screen (top 25)"][d] = list(score(ok.drop(columns="passes_gates")).index[:25]) if len(ok) else []
        for k in books:
            fill[k].append(len(books[k][d]))
        # single rules: next-quarter return of passing stocks minus the universe
        nxt = dates[dates.index(d) + 1] if dates.index(d) + 1 < len(dates) else pd.Timestamp(MONTH_END)
        fwd = (adj.loc[:nxt].iloc[-1] / adj.loc[:d].iloc[-1] - 1).where(lambda x: x.abs() < 3)
        fr = fwd.reindex(f.index)
        for name, ok_ in r.items():
            sel = fr[ok_.fillna(False).astype(bool)].dropna()
            if len(sel) >= 5:
                single.setdefault(name, []).append((d, sel.mean() - fr.mean(), len(sel)))
        # PEG quintiles
        q = pd.qcut(f["peg"].where(f["peg"] > 0).rank(method="first"), 5, labels=False) if f["peg"].notna().sum() >= 25 else None
        if q is not None:
            for k in range(5):
                single.setdefault(f"PEG quintile {k + 1}", []).append((d, fr[q == k].mean() - fr.mean(), int((q == k).sum())))

    res = {k: simulate(b, monthly, rf_m, 0.0 if k == "Equal-weight universe" else COST) for k, b in books.items()}
    res3 = {k: simulate(b, monthly, rf_m, 3 * COST) for k, b in books.items()}
    idx = res["Equal-weight universe"].index
    res["SPY"] = adj["SPY"].pct_change().reindex(idx) if "SPY" in adj else pd.Series(dtype=float)

    emit("# Peter Lynch's rules, quantified - generated tables\n")
    emit(f"Quarterly, {idx[0]:%Y-%m} to {idx[-1]:%Y-%m}; universe = the 750 largest US companies at each quarter-end, "
         "fundamentals as filed by then. Survivors-only prices. 0.10% per trade (stress 0.30%); T-bills when nothing "
         "passes. Sharpe above T-bills.\n")
    emit("## 1. The strategies\n")
    emit("| rules | return/yr | volatility | Sharpe | worst drop | at 3x costs | 2014-19 | 2020-26 | avg holdings | "
         "beat universe (years) |")
    emit("|---|---|---|---|---|---|---|---|---|---|")
    uni = res["Equal-weight universe"]
    yu = (1 + uni).groupby(uni.index.year).prod() - 1
    for k, r in res.items():
        s, a, b = stats(r, rf_m), stats(r.loc[:SPLIT], rf_m), stats(r.loc[SPLIT:], rf_m)
        s3 = f"{stats(res3[k], rf_m)['CAGR']:.1%}" if k in res3 else ""
        yr = (1 + r).groupby(r.index.year).prod() - 1
        beat = f"{int((yr > yu.reindex(yr.index)).sum())} of {len(yr)}" if k not in ("Equal-weight universe", "SPY") else ""
        h = f"{np.mean(fill[k]):.0f}" if k in fill else ""
        emit(f"| {k} | {s['CAGR']:.1%} | {s['vol']:.0%} | {s['Sharpe']:.2f} | {s['dd']:.0%} | {s3} | "
             f"{a['CAGR']:.1%} ({a['Sharpe']:.2f}) | {b['CAGR']:.1%} ({b['Sharpe']:.2f}) | {h} | {beat} |")

    emit("\n## 2. Each rule on its own: next-quarter return of passing stocks minus the universe average\n")
    emit("| rule | excess per quarter | t-stat | quarters it helped | 2014-19 | 2020-26 | stocks passing (avg) |")
    emit("|---|---|---|---|---|---|---|")
    for name, v in single.items():
        s = pd.DataFrame(v, columns=["d", "ex", "n"]).set_index("d")["ex"]
        n = np.mean([x[2] for x in v])
        t = s.mean() / (s.std() / np.sqrt(len(s))) if s.std() > 0 else np.nan
        emit(f"| {name} | {s.mean():+.2%} | {t:.1f} | {(s > 0).mean():.0%} | {s.loc[:SPLIT].mean():+.2%} | "
             f"{s.loc[SPLIT:].mean():+.2%} | {n:.0f} |")

    emit("\n## 3. Today's universe by Lynch category (latest snapshot)\n")
    last = feats[max(feats)]
    cats = last["growth"].map(category).value_counts()
    emit("| category | companies |\n|---|---|")
    for c, n in cats.items():
        emit(f"| {c} | {n} |")

    OUT.mkdir(exist_ok=True)
    (OUT / "lynch.md").write_text("\n".join(lines) + "\n")
    print(f"\nwrote {OUT / 'lynch.md'}")


if __name__ == "__main__":
    main()
