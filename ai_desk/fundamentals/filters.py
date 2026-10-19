"""Which companies the screen is allowed to rank.

1. Business types the metrics don't fit (banks, lenders, insurers, asset
   managers, REITs): their "free cash flow" and "invested capital" mean
   something else, so they'd rank on noise.
2. Too little data to judge.
3. "Great business" gates: the screen is for durable, high-return
   businesses, so cyclical peaks and turnarounds are filtered out BEFORE
   ranking, rather than letting a hot year carry them to the top.
4. The 10-year check: Yahoo only has ~4 years, which can sit entirely inside
   a commodity boom. SEC filings show whether the record holds up over a
   full cycle.
"""

from __future__ import annotations

import pandas as pd

from ai_desk.fundamentals.scoring import METRICS

# financial-sector industries kept IF they report normal operating statements
# (Visa, Mastercard, exchanges, data providers, insurance brokers)
ASSET_LIGHT_FINANCIALS = ("Financial Data & Stock Exchanges", "Credit Services", "Insurance Brokers")

DEFAULT_GATES = {
    "min_roic_avg": 0.12,      # average return on capital of 12%+
    "min_roic_worst": 0.0,     # no year where the business lost money on its capital
    "min_rev_up_years": 0.6,   # revenue rose in most years
    "min_fcf_margin": 0.0,     # generating cash, not burning it
    "min_coverage": 0.75,      # at least 3/4 of the metrics available
}


# the 10-year check (last 10 fiscal years from SEC filings)
LONG_RUN_RULES = {
    "years": 10,
    "min_years": 7,                 # fewer = "short history": flagged, not failed
    "min_profitable_share": 0.8,    # operating profit > 0 in 8 of 10 years
    "max_revenue_declines": 2,      # revenue fell in at most 2 years
    "roic_floor": 0.10,             # pre-tax ROIC of 10%+ ...
    "min_roic_share": 0.7,          # ... in 7 of 10 years
    "min_roic_years": 5,            # (only judged when 5+ years can be measured)
}


def long_run_check(history: pd.DataFrame | None, rules: dict | None = None) -> tuple[str, str]:
    """Judge a company's last 10 years of SEC-reported results.

    Returns (status, detail), where status is "pass", "fail", "short history"
    or "no SEC data". Only "fail" removes a company from the screen.
    """
    r = {**LONG_RUN_RULES, **(rules or {})}
    if history is None or history.empty:
        return "no SEC data", "no filings found (often a foreign IFRS filer)"
    h = history.dropna(subset=["revenue_$bn"]).tail(r["years"])
    n = len(h)
    if n < r["min_years"]:
        return "short history", f"only {n} years of SEC filings"

    problems = []
    margin = h["operating_margin"].dropna()
    profitable = (margin > 0).mean() if len(margin) else float("nan")
    if profitable < r["min_profitable_share"]:
        problems.append(f"operating loss in {int((margin <= 0).sum())} of {len(margin)} years")
    declines = int((h["revenue_growth"].dropna() < 0).sum())
    if declines > r["max_revenue_declines"]:
        problems.append(f"revenue fell in {declines} years")
    roic = h["roic_pretax"].dropna()
    if len(roic) >= r["min_roic_years"]:
        good = (roic >= r["roic_floor"]).mean()
        if good < r["min_roic_share"]:
            problems.append(f"pre-tax ROIC under {r['roic_floor']:.0%} in {int((roic < r['roic_floor']).sum())} "
                            f"of {len(roic)} years")
    detail = f"{n} years: " + ("; ".join(problems) if problems else
                               f"profitable {profitable:.0%} of years, revenue fell {declines}x")
    return ("fail" if problems else "pass"), detail


def apply_long_run(df: pd.DataFrame, histories: dict[str, pd.DataFrame | None],
                   rules: dict | None = None) -> tuple[pd.DataFrame, list[str]]:
    """Add `long_run` / `long_run_detail` columns and drop the failures."""
    results = {sym: long_run_check(histories.get(sym), rules) for sym in df.index}
    df = df.assign(long_run=[results[s][0] for s in df.index],
                   long_run_detail=[results[s][1] for s in df.index])
    counts = df["long_run"].value_counts()
    notes = [f"10-year check (SEC filings): {counts.get('pass', 0)} passed, {counts.get('fail', 0)} failed and "
             f"were excluded, {counts.get('short history', 0)} have under 7 years of filings and "
             f"{counts.get('no SEC data', 0)} have no SEC data (both kept, but unverified)"]
    return df[df["long_run"] != "fail"], notes


def business_type_mask(df: pd.DataFrame) -> pd.Series:
    """True = keep."""
    industry = df["industry"].fillna("")
    reit = industry.str.startswith("REIT")
    financial = df["sector"].eq("Financial Services")
    asset_light = industry.isin(ASSET_LIGHT_FINANCIALS) & df["roic_avg"].notna()
    return ~reit & (~financial | asset_light)


def coverage(df: pd.DataFrame) -> pd.Series:
    cols = [m for m in METRICS if m in df and m != "momentum_12_1"]
    return df[cols].notna().mean(axis=1)


def apply(df: pd.DataFrame, gates: dict | None = None) -> tuple[pd.DataFrame, list[str]]:
    """Returns the companies to rank and a note for each filter applied."""
    notes = []

    def drop(mask: pd.Series, why: str) -> None:
        nonlocal df
        n = int((~mask).sum())
        if n:
            notes.append(f"excluded {n} {why}")
        df = df[mask]

    drop(business_type_mask(df), "banks, lenders, insurers, asset managers and REITs (metrics don't apply)")
    drop(df["years_of_data"] >= 3, "with under 3 years of statements")
    if gates is None:
        return df, notes
    g = {**DEFAULT_GATES, **gates}
    drop(coverage(df) >= g["min_coverage"], f"with under {g['min_coverage']:.0%} of metrics available")
    drop(df["roic_avg"] >= g["min_roic_avg"], f"with average ROIC under {g['min_roic_avg']:.0%}")
    drop(df["roic_min"] > g["min_roic_worst"], f"with a year of ROIC at or below {g['min_roic_worst']:.0%}")
    drop(df["rev_up_years"] >= g["min_rev_up_years"], "where revenue fell in most years")
    drop(df["fcf_margin"] > g["min_fcf_margin"], "with negative free cash flow")
    return df, notes
