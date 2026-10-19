"""Which companies the screen is allowed to rank.

1. Business types the metrics don't fit (banks, lenders, insurers, asset
   managers, REITs): their "free cash flow" and "invested capital" mean
   something else, so they'd rank on noise.
2. Too little data to judge.
3. "Great business" gates: the screen is for durable, high-return
   businesses, so cyclical peaks and turnarounds are filtered out BEFORE
   ranking, rather than letting a hot year carry them to the top.
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
