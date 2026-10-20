"""What did the best-performing stocks of the last 5 years look like BEFORE their run?

    python research/winners.py

Method (so we don't fool ourselves):
  * every quarter-end 2014-2026 we already hold point-in-time fundamentals (SEC filings filed
    by then) for the 750 largest companies at the time (data/backtest/snapshots_m*.pkl)
  * features = those fundamentals + price behaviour measured at the START of each window
  * outcome = the next 5 years' total return (adjusted prices); "winner" = top 10% of that
    window's universe
  * the question is NOT "what do winners have?" (that ignores the many non-winners with the
    same trait) but "does having the trait raise the chance of being a winner, and of being a
    bust, across many windows?" - measured by lift, rank correlation (IC) and a walk-forward test
    that only learns from windows that had finished before the test window started.

Biases (they flatter every number here): prices are survivors-only (bankrupt and acquired
companies are missing) and the universe is the 750 largest companies at each date, so
micro/small caps, where the biggest runs often start, are absent.
Writes research/output/winners.md; the write-up is research/WINNERS.md.
"""

from __future__ import annotations

import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

CACHE = ROOT / "data" / "backtest"
OUT = Path(__file__).resolve().parent / "output"
LAST_PRICE = pd.Timestamp("2026-09-30")          # last full month in the price file
HEADLINE = pd.Timestamp("2021-09-30")            # "the past 5 years": 2021-09-30 -> 2026-09-30
TOP = 0.10                                       # a winner / a bust = top / bottom decile of the window

FUNDAMENTAL = ["roic_avg", "roic_min", "gross_margin", "op_margin", "fcf_margin", "rev_cagr",
               "rev_growth_recent", "rev_up_years", "gm_trend", "net_debt_ebitda", "rev_vs_peers",
               "ebit_yield", "fcf_yield", "fwd_earnings_yield"]
PRICE = ["mom_6m", "mom_12m", "ret_36m", "off_12m_high", "vol_12m"]
DERIVED = ["rev_accel", "size_rank", "revenue_size"]
FEATURES = FUNDAMENTAL + PRICE + DERIVED
LABEL = {
    "roic_avg": "Return on capital (avg)", "roic_min": "Return on capital (worst year)",
    "gross_margin": "Gross margin", "op_margin": "Operating margin", "fcf_margin": "Free-cash-flow margin",
    "rev_cagr": "Revenue growth (multi-year)", "rev_growth_recent": "Revenue growth (latest year)",
    "rev_up_years": "Share of years revenue rose", "gm_trend": "Gross margin trend",
    "net_debt_ebitda": "Net debt / EBITDA", "rev_vs_peers": "Growth vs industry peers",
    "ebit_yield": "Operating earnings yield (cheapness)", "fcf_yield": "Free-cash-flow yield (cheapness)",
    "fwd_earnings_yield": "Earnings yield (cheapness)", "mom_6m": "6-month price momentum",
    "mom_12m": "12-month price momentum", "ret_36m": "3-year price return (before)",
    "off_12m_high": "Closeness to 12-month high", "vol_12m": "Volatility (12m)",
    "rev_accel": "Growth accelerating (latest - multi-year)", "size_rank": "Company size (market cap)",
    "revenue_size": "Revenue size",
}
SIC2 = {1: "Agriculture", 10: "Metal mining", 13: "Oil & gas", 15: "Construction", 16: "Heavy construction",
        20: "Food", 22: "Textiles", 23: "Apparel", 26: "Paper", 28: "Chemicals & pharma", 29: "Refining",
        30: "Rubber & plastics", 33: "Primary metals", 34: "Metal products", 35: "Machinery & computers",
        36: "Electronics", 37: "Transport equipment", 38: "Instruments & medical devices", 39: "Misc manufacturing",
        40: "Railroads", 42: "Trucking", 44: "Water transport", 45: "Airlines", 47: "Travel services",
        48: "Telecom & media", 49: "Utilities", 50: "Wholesale (durable)", 51: "Wholesale (nondurable)",
        53: "General retail", 54: "Food stores", 56: "Apparel retail", 58: "Restaurants", 59: "Misc retail",
        70: "Hotels", 73: "Software & business services", 78: "Entertainment", 79: "Recreation",
        80: "Health services", 87: "Engineering & research"}


# --- pure helpers (unit-tested in tests/test_winners.py) -------------------------

def pct_rank(s: pd.Series) -> pd.Series:
    """0-1 percentile among the non-missing values; missing stays missing."""
    return s.rank(pct=True)


def rank_corr(a: pd.Series, b: pd.Series) -> float:
    """Spearman rank correlation (a plain correlation of the ranks - no scipy needed)."""
    return float(a.rank().corr(b.rank()))


def forward_return(prices: pd.DataFrame, start: pd.Timestamp, years: int) -> pd.Series:
    """Total return from `start` to `start + years` (month-end adjusted prices); NaN if either is missing."""
    end = start + pd.DateOffset(years=years) + pd.offsets.MonthEnd(0)
    if start not in prices.index or end not in prices.index:
        return pd.Series(dtype=float)
    return prices.loc[end] / prices.loc[start] - 1


def price_features(prices: pd.DataFrame, start: pd.Timestamp) -> pd.DataFrame:
    """Price behaviour known at `start` (uses only data up to and including it)."""
    hist = prices.loc[:start]
    i = len(hist) - 1
    px = hist.iloc[-1]
    out = pd.DataFrame(index=prices.columns)
    out["mom_6m"] = px / hist.iloc[i - 6] - 1 if i >= 6 else np.nan
    out["mom_12m"] = px / hist.iloc[i - 12] - 1 if i >= 12 else np.nan
    out["ret_36m"] = px / hist.iloc[i - 36] - 1 if i >= 36 else np.nan
    out["off_12m_high"] = px / hist.iloc[max(0, i - 12):].max() - 1
    out["vol_12m"] = hist.iloc[max(0, i - 12):].pct_change().std() * np.sqrt(12) if i >= 12 else np.nan
    return out


def lift(feature_pct: pd.Series, outcome: pd.Series, lo: float, hi: float) -> float:
    """P(outcome | feature percentile in [lo, hi]) divided by the base rate. 1.0 = the trait changes nothing."""
    ok = feature_pct.notna() & outcome.notna()
    f, o = feature_pct[ok], outcome[ok].astype(bool)
    sel = (f > lo) & (f <= hi) if lo > 0 else (f <= hi)
    if sel.sum() == 0 or o.mean() == 0:
        return np.nan
    return float(o[sel].mean() / o.mean())


# --- building the windows ---------------------------------------------------------

def load():
    prices = pickle.loads((CACHE / "prices.pkl").read_bytes())["adj"]
    snaps = {}
    for m in (3, 6, 9, 12):
        snaps.update(pickle.loads((CACHE / f"snapshots_m{m}.pkl").read_bytes()))
    return prices, dict(sorted(snaps.items()))


def window(prices: pd.DataFrame, snaps: dict, start: pd.Timestamp, years: int) -> pd.DataFrame | None:
    """One row per company: features at `start`, forward return, winner/bust flags, percentile ranks."""
    fwd = forward_return(prices, start, years)
    if fwd.empty or start not in snaps:
        return None
    snap = snaps[start]
    df = snap.reindex(columns=FUNDAMENTAL + ["market_cap", "revenue_$bn", "sic2"]).copy()
    df = df.join(price_features(prices, start), how="left")
    df["rev_accel"] = df["rev_growth_recent"] - df["rev_cagr"]
    df["size_rank"] = -df["market_cap"].rank(ascending=False)          # higher = bigger company
    df["revenue_size"] = df["revenue_$bn"]
    df["fwd"] = fwd.reindex(df.index)
    df = df.dropna(subset=["fwd"])
    df["annual"] = (1 + df["fwd"]) ** (1 / years) - 1
    n = len(df)
    df["winner"] = df["fwd"].rank(ascending=False) <= max(1, round(n * TOP))
    df["bust"] = df["fwd"].rank(ascending=True) <= max(1, round(n * TOP))
    for f in FEATURES:
        df[f"p_{f}"] = pct_rank(pd.to_numeric(df[f], errors="coerce").replace([np.inf, -np.inf], np.nan))
    df["start"] = start
    return df


def all_windows(prices, snaps, years: int, last_start: pd.Timestamp | None = None) -> dict[pd.Timestamp, pd.DataFrame]:
    out = {}
    for d in snaps:
        if d + pd.DateOffset(years=years) + pd.offsets.MonthEnd(0) > LAST_PRICE:
            continue
        w = window(prices, snaps, d, years)
        if w is not None and len(w) > 100:
            out[d] = w
    return out


def feature_table(wins: dict[pd.Timestamp, pd.DataFrame]) -> pd.DataFrame:
    """Per feature across all windows: winner percentile, consistency, lift, IC."""
    rows = []
    for f in FEATURES:
        med, ic, lt, lb, bt, lbot, yrs = [], [], [], [], [], [], {}
        for d, w in wins.items():
            p = w[f"p_{f}"]
            if p.notna().sum() < 100:
                continue
            med.append(p[w["winner"]].median())
            r = rank_corr(p, w["fwd"])
            ic.append(r)
            yrs.setdefault(d.year, []).append(r)
            lt.append(lift(p, w["winner"], 0.8, 1.0))
            bt.append(lift(p, w["bust"], 0.8, 1.0))
            lbot.append(lift(p, w["winner"], 0.0, 0.2))
        if not ic:
            continue
        by_year = np.array([np.mean(v) for v in yrs.values()])
        t = by_year.mean() / (by_year.std(ddof=1) / np.sqrt(len(by_year))) if len(by_year) > 2 and by_year.std() > 0 else np.nan
        rows.append({"feature": f, "label": LABEL[f], "winner_pctile": np.nanmean(med),
                     "windows_above_50": float(np.mean(np.array(med) > 0.5)),
                     "ic": np.nanmean(ic), "ic_positive": float(np.mean(np.array(ic) > 0)), "ic_t": t,
                     "lift_top_quintile": np.nanmean(lt), "bust_lift_top_quintile": np.nanmean(bt),
                     "lift_bottom_quintile": np.nanmean(lbot), "windows": len(ic), "years": len(by_year)})
    return pd.DataFrame(rows).set_index("feature")


# --- walk-forward composite -----------------------------------------------------------

def walk_forward(wins: dict[pd.Timestamp, pd.DataFrame], years: int, first_test: pd.Timestamp,
                 min_ic: float = 0.02) -> pd.DataFrame:
    """For each test window: learn each feature's sign from windows that had FINISHED before the test
    start, rank companies by the signed-percentile sum, and see whether the top decile wins."""
    rows = []
    for d, w in wins.items():
        if d < first_test:
            continue
        done = {s: x for s, x in wins.items() if s + pd.DateOffset(years=years) + pd.offsets.MonthEnd(0) <= d}
        if len(done) < 2:
            continue
        sign = {}
        for f in FEATURES:
            ics = [rank_corr(x[f"p_{f}"], x["fwd"]) for x in done.values()
                   if x[f"p_{f}"].notna().sum() > 100]
            m = np.nanmean(ics) if ics else np.nan
            if m == m and abs(m) >= min_ic:
                sign[f] = np.sign(m)
        if not sign:
            continue
        comp = sum(s * w[f"p_{f}"].fillna(0.5) for f, s in sign.items()) / len(sign)
        top = comp.rank(ascending=False) <= max(1, round(len(w) * TOP))
        rows.append({"start": d, "trained_on": len(done), "features_used": len(sign),
                     "hit_rate": float(w.loc[top, "winner"].mean()), "bust_rate": float(w.loc[top, "bust"].mean()),
                     "picks_annual": float(w.loc[top, "annual"].mean()), "universe_annual": float(w["annual"].mean()),
                     "universe_median_annual": float(w["annual"].median()),
                     "picks_median_annual": float(w.loc[top, "annual"].median())})
    return pd.DataFrame(rows)


# --- report -------------------------------------------------------------------------------

def md(df: pd.DataFrame, fmt: dict[str, str]) -> str:
    cols = list(fmt)
    head = "| " + " | ".join(cols) + " |\n|" + "---|" * len(cols)
    body = ["| " + " | ".join(("" if pd.isna(r[c]) else fmt[c].format(r[c])) if c in r else "" for c in cols) + " |"
            for _, r in df.reset_index().iterrows()]
    return head + "\n" + "\n".join(body)


def main() -> None:
    prices, snaps = load()
    lines: list[str] = []

    def emit(t: str = "") -> None:
        print(t)
        lines.append(t)

    emit("# What the best stocks looked like before their run - generated tables\n")
    emit("Universe: the 750 largest US companies at each date (survivors only). "
         "Prices adjusted for splits and dividends. Winner = top 10% of the window by 5-year return.\n")

    # 1. the headline window --------------------------------------------------------------
    h = window(prices, snaps, HEADLINE, 5)
    n = len(h)
    emit(f"## 1. The past 5 years: {HEADLINE.date()} to {LAST_PRICE.date()} ({n} companies)\n")
    emit(f"Universe median 5-year return {h['fwd'].median():+.0%}; average {h['fwd'].mean():+.0%}; "
         f"top decile cut-off {h['fwd'].sort_values(ascending=False).iloc[round(n * TOP) - 1]:+.0%}.\n")
    top = h.sort_values("fwd", ascending=False).head(25)
    show = top.assign(multiple=1 + top["fwd"], sector=top["sic2"].map(lambda c: SIC2.get(int(c), f"SIC {int(c)}") if c == c else ""))
    emit(md(show[["multiple", "sector", "rev_cagr", "gross_margin", "roic_avg", "mom_12m", "ret_36m", "off_12m_high", "size_rank"]]
            .assign(size_rank=lambda d: -d["size_rank"]),
            {"symbol": "{}", "multiple": "{:.1f}x", "sector": "{}", "rev_cagr": "{:.0%}", "gross_margin": "{:.0%}",
             "roic_avg": "{:.0%}", "mom_12m": "{:+.0%}", "ret_36m": "{:+.0%}", "off_12m_high": "{:+.0%}",
             "size_rank": "{:.0f}"}).replace("rev_cagr", "growth/yr").replace("size_rank", "size rank (1=biggest)"))

    emit("\n### Median trait: top 25 vs the whole universe, and the percentile they sat at\n")
    rows = []
    for f in FEATURES:
        p = h[f"p_{f}"]
        rows.append({"feature": LABEL[f], "top25": pd.to_numeric(top[f], errors="coerce").median(),
                     "universe": pd.to_numeric(h[f], errors="coerce").median(),
                     "top25_pctile": p.loc[top.index].median() * 100})
    t = pd.DataFrame(rows).set_index("feature")
    emit(md(t, {"feature": "{}", "top25": "{:.3g}", "universe": "{:.3g}", "top25_pctile": "{:.0f}"}))

    # 2. patterns across all windows ---------------------------------------------------------
    wins1 = {}
    for number, years in ((2, 5), (3, 3), (4, 1)):
        wins = all_windows(prices, snaps, years)
        ft = feature_table(wins).sort_values("ic", ascending=False)
        starts = sorted(wins)
        emit(f"\n## {number}. Does the trait raise the odds? {years}-year outcomes, {len(wins)} overlapping "
             f"windows starting {starts[0].date()} to {starts[-1].date()}\n")
        emit("winner pctile = where the winners sat on this trait (50 = no different from everyone). "
             "IC = rank correlation between the trait and the later return (0 = nothing; above about 0.05 in a "
             "year-averaged t of 2+ is worth noticing). lift = chance of being a winner (or a bust) if you were in "
             "the top fifth on the trait, relative to the 10% base rate.\n")
        emit(md(ft, {"label": "{}", "winner_pctile": "{:.0%}", "windows_above_50": "{:.0%}", "ic": "{:+.3f}",
                     "ic_positive": "{:.0%}", "ic_t": "{:+.1f}", "lift_top_quintile": "{:.2f}",
                     "bust_lift_top_quintile": "{:.2f}", "lift_bottom_quintile": "{:.2f}"})
             .replace("windows_above_50", "winners above 50 in").replace("ic_positive", "IC>0 in")
             .replace("ic_t", "t (by year)").replace("lift_top_quintile", "winner lift (top fifth)")
             .replace("bust_lift_top_quintile", "bust lift (top fifth)").replace("lift_bottom_quintile", "winner lift (bottom fifth)"))
        if years == 5:
            ft5, wins5 = ft, wins
        if years == 1:
            wins1 = wins

    # 3. sectors -------------------------------------------------------------------------------
    emit("\n## 5. Sectors: were the winners clustered? (5-year windows)\n")
    rows = []
    allw = pd.concat(wins5.values())
    allw["sector"] = allw["sic2"].map(lambda c: SIC2.get(int(c), f"SIC {int(c)}") if c == c else "n/a")
    for sec, g in allw.groupby("sector"):
        if len(g) < 150:
            continue
        per = [x.assign(sector=x["sic2"].map(lambda c: SIC2.get(int(c), f"SIC {int(c)}") if c == c else "n/a"))
               for x in wins5.values()]
        lifts = [(x.loc[x["sector"] == sec, "winner"].mean() / x["winner"].mean()) for x in per if (x["sector"] == sec).sum() >= 5]
        rows.append({"sector": sec, "company_windows": len(g), "winner_lift": g["winner"].mean() / allw["winner"].mean(),
                     "bust_lift": g["bust"].mean() / allw["bust"].mean(), "windows_lift_above_1": float(np.mean(np.array(lifts) > 1)) if lifts else np.nan,
                     "median_annual": g["annual"].median()})
    sec = pd.DataFrame(rows).set_index("sector").sort_values("winner_lift", ascending=False)
    emit(md(sec, {"sector": "{}", "company_windows": "{:.0f}", "winner_lift": "{:.2f}", "bust_lift": "{:.2f}",
                  "windows_lift_above_1": "{:.0%}", "median_annual": "{:+.1%}"}))

    # 4. the walk-forward test ---------------------------------------------------------------------
    emit("\n## 6. Out-of-sample: could a composite of these traits have picked winners in advance?\n")
    emit("For each test window, each trait's direction is learned only from 5-year windows that had already "
         "finished before the test window began. Companies are ranked by the direction-adjusted sum of "
         "percentiles; the top decile is compared with the universe. Base rate for a winner is 10%.\n")
    wf = walk_forward(wins5, 5, pd.Timestamp("2019-03-31"))
    if len(wf):
        emit(md(wf, {"start": "{:%Y-%m}", "trained_on": "{:.0f}", "features_used": "{:.0f}", "hit_rate": "{:.0%}",
                     "bust_rate": "{:.0%}", "picks_annual": "{:+.1%}", "picks_median_annual": "{:+.1%}",
                     "universe_annual": "{:+.1%}", "universe_median_annual": "{:+.1%}"}))
        emit(f"\nAverage over {len(wf)} test windows (heavily overlapping - roughly 3 independent years): "
             f"hit rate {wf['hit_rate'].mean():.0%} (random = 10%), bust rate {wf['bust_rate'].mean():.0%} (random = 10%), "
             f"picks {wf['picks_annual'].mean():+.1%}/yr vs universe average {wf['universe_annual'].mean():+.1%}/yr "
             f"(median pick {wf['picks_median_annual'].mean():+.1%} vs median stock {wf['universe_median_annual'].mean():+.1%}).")
    else:
        emit("(not enough finished windows)")

    emit("\n### The same test over 1-year runs (more windows, so a fairer test)\n")
    emit("Winner = top decile by the next 12 months' return; test windows start every quarter from 2019-03.\n")
    wf1 = walk_forward(wins1, 1, pd.Timestamp("2019-03-31"))
    if len(wf1):
        by_year = wf1.assign(year=wf1["start"].dt.year).groupby("year")[
            ["hit_rate", "bust_rate", "picks_annual", "universe_annual", "picks_median_annual", "universe_median_annual"]].mean()
        emit(md(by_year, {"year": "{}", "hit_rate": "{:.0%}", "bust_rate": "{:.0%}", "picks_annual": "{:+.1%}",
                          "picks_median_annual": "{:+.1%}", "universe_annual": "{:+.1%}", "universe_median_annual": "{:+.1%}"}))
        emit(f"\nAverage over {len(wf1)} test windows ({by_year.shape[0]} calendar years): hit rate {wf1['hit_rate'].mean():.0%} "
             f"(random = 10%), bust rate {wf1['bust_rate'].mean():.0%}, picks {wf1['picks_annual'].mean():+.1%} vs universe "
             f"{wf1['universe_annual'].mean():+.1%} (median pick {wf1['picks_median_annual'].mean():+.1%} vs median stock "
             f"{wf1['universe_median_annual'].mean():+.1%}). Years where the picks beat the universe average: "
             f"{int((by_year['picks_annual'] > by_year['universe_annual']).sum())} of {by_year.shape[0]}.")

    OUT.mkdir(exist_ok=True)
    (OUT / "winners.md").write_text("\n".join(lines) + "\n")
    print(f"\nwrote {OUT / 'winners.md'}")


if __name__ == "__main__":
    main()
