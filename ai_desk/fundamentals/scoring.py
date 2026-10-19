"""Rank companies against each other and explain the result.

Every metric is converted to a percentile (0-100) across the universe, where
100 = best. Percentiles make different units comparable (a ROIC of 30% and a
forward P/E of 18 can't be averaged, but "top 10%" and "top 40%" can) and
stop one extreme number from dominating.

Category scores average their metrics' percentiles; the overall score is a
weighted average of the categories.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# metric -> (category, higher_is_better, how to describe it)
METRICS = {
    "roic_avg":           ("quality",  True,  "avg ROIC {:.0%}"),
    "roic_min":           ("quality",  True,  "worst-year ROIC {:.0%}"),
    "gross_margin":       ("quality",  True,  "gross margin {:.0%}"),
    "op_margin":          ("quality",  True,  "operating margin {:.0%}"),
    "fcf_conversion":     ("quality",  True,  "FCF/net income {:.2f}x"),
    "rev_cagr":           ("growth",   True,  "revenue growth {:.0%}/yr"),
    "rev_growth_recent":  ("growth",   True,  "latest-quarter revenue {:+.0%} y/y"),
    "rev_vs_peers":       ("growth",   True,  "growing {:+.0%}/yr vs industry peers"),
    "gm_trend":           ("growth",   True,  "gross margin {:+.1%} over the period"),
    "net_debt_ebitda":    ("strength", False, "net debt/EBITDA {:.1f}x"),
    "share_change":       ("strength", False, "share count {:+.1%}/yr"),
    "sbc_pct_revenue":    ("strength", False, "stock comp {:.1%} of revenue"),
    "fwd_earnings_yield": ("value",    True,  "forward P/E {:.0f}"),
    "ebit_yield":         ("value",    True,  "EV/EBIT {:.0f}"),
    "fcf_yield":          ("value",    True,  "FCF yield {:.1%}"),
    "momentum_12_1":      ("momentum", True,  "12-1 month price change {:+.0%}"),
}
DEFAULT_WEIGHTS = {"quality": 0.35, "growth": 0.25, "value": 0.20, "strength": 0.10, "momentum": 0.10}
CATEGORIES = list(DEFAULT_WEIGHTS)


def percentile_scores(df: pd.DataFrame) -> pd.DataFrame:
    """0-100 per metric, 100 = best. Missing data stays missing (not punished
    or rewarded) - check `data_coverage` before trusting a score."""
    out = pd.DataFrame(index=df.index)
    for m, (_, higher, _) in METRICS.items():
        if m in df:
            s = pd.to_numeric(df[m], errors="coerce")
            out[m] = s.rank(pct=True, ascending=higher) * 100
    return out


def score(df: pd.DataFrame, weights: dict[str, float] | None = None) -> pd.DataFrame:
    weights = {**DEFAULT_WEIGHTS, **(weights or {})}
    pct = percentile_scores(df)
    result = df.copy()
    for cat in CATEGORIES:
        cols = [m for m, (c, _, _) in METRICS.items() if c == cat and m in pct]
        result[f"{cat}_score"] = pct[cols].mean(axis=1) if cols else np.nan
    cat_scores = result[[f"{c}_score" for c in CATEGORIES]]
    w = pd.Series({f"{c}_score": weights[c] for c in CATEGORIES})
    present = cat_scores.notna()
    # weighted average over the categories a company has data for
    result["score"] = (cat_scores.fillna(0) * w).sum(axis=1) / (present * w).sum(axis=1).replace(0, np.nan)
    result["data_coverage"] = pct.notna().mean(axis=1)
    result["strengths"] = [explain(df.loc[i], pct.loc[i], best=True) for i in df.index]
    result["weaknesses"] = [explain(df.loc[i], pct.loc[i], best=False) for i in df.index]
    return result.sort_values("score", ascending=False)


def _describe(metric: str, value: float) -> str:
    template = METRICS[metric][2]
    if metric == "fwd_earnings_yield":
        value = 1 / value
    elif metric == "ebit_yield":
        value = 1 / value if value > 0 else np.nan
    return template.format(value) if pd.notna(value) else metric


def explain(row: pd.Series, pct: pd.Series, best: bool, n: int = 3) -> str:
    """The n metrics where this company ranks best (or worst), in words."""
    p = pct.dropna()
    p = p[p >= 80] if best else p[p <= 20]
    p = p.sort_values(ascending=not best).head(n)
    parts = []
    for m, v in p.items():
        rank = f"top {max(1, round(100 - v))}%" if best else f"bottom {max(1, round(v))}%"
        parts.append(f"{_describe(m, row[m])} ({rank})")
    return "; ".join(parts)
