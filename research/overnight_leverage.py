"""The overnight sleeve with borrowed money: 1x, 1.5x and 2x (the owner's question, 2026-10-27). A what-if.

    python research/overnight_leverage.py

The sleeve as it runs live (research/desk_rsi.overnight_live: 12-month ranking, daily re-pick, SPY 200-day and
picks-day checks). On an invested night, L x the night's return after costs, minus margin interest on the borrowed
(L - 1) at the T-bill rate + 2.5% a year (a typical broker margin rate; Alpaca's is in that range - check it). Costs
scale with the money traded: L x the per-trade cost. Cash nights earn T-bills, no borrowing. Costs 0.02% and 0.05% each
way. Daily, 2014-04 to 2026-10; survivors-only prices. Writes research/output/overnight_leverage.md.
"""

from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import desk_rsi as dr  # noqa: E402
import overnight as ov  # noqa: E402
import overnight_regime as orr  # noqa: E402

OUT = orr.OUT
MARGIN_SPREAD = 0.025


def levered(r: pd.Series, invested: pd.Series, rf_daily: pd.Series, lev: float, extra_cost: float) -> pd.Series:
    """Pure: L x (the night after costs) - interest on the borrowed part; cash nights unchanged.
    r already holds 0.02% costs each way; extra_cost adds more per trade on invested nights."""
    inv = invested.reindex(r.index).fillna(False).astype(bool)
    rfd = rf_daily.reindex(r.index).fillna(0)
    night = r - 2 * extra_cost * inv
    margin = (lev - 1) * (rfd + MARGIN_SPREAD / 252)
    return night.where(~inv, lev * night - margin)


def main() -> None:
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    lines: list[str] = []

    def emit(t=""):
        print(t, flush=True)
        lines.append(t)

    r, rf, inv = dr.overnight_live()
    rfd = rf.reindex(r.index).fillna(0)
    emit("# The overnight sleeve with borrowed money - generated tables\n")
    emit("Daily, the live rules, **survivors-only prices**. Margin interest at T-bills + 2.5% on the borrowed part; "
         "cash nights unlevered. Sharpe above T-bills.\n")
    emit("| leverage | costs each way | return/yr | volatility | Sharpe | worst drop | worst night | worst month | "
         "2014-19 | 2020-26 | Feb-Mar 2020 | 2022 |")
    emit("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for cost in (0.0002, 0.0005):
        for lev in (1.0, 1.5, 2.0):
            x = levered(r, inv, rfd, lev, cost - 0.0002)
            s, a, b = orr.stats(x, rfd), orr.stats(x.loc[:ov.MID], rfd), orr.stats(x.loc[ov.MID:], rfd)
            m = (1 + x).resample("ME").prod() - 1
            covid = (1 + x.loc["2020-02-01":"2020-03-31"]).prod() - 1
            y22 = (1 + x.loc["2022"]).prod() - 1
            emit(f"| {lev:.1f}x | {cost:.2%} | {s['CAGR']:.1%} | {s['vol']:.0%} | {s['Sharpe']:.2f} | {s['maxdd']:.0%} | "
                 f"{x.min():+.1%} | {m.min():+.1%} | {a['Sharpe']:.2f} | {b['Sharpe']:.2f} | {covid:+.1%} | {y22:+.1%} |")
    x2 = levered(r, inv, rfd, 2.0, 0.0)
    yrs = (1 + x2).groupby(x2.index.year).prod() - 1
    emit("\n2x at 0.02%, by year: " + ", ".join(f"{y} {v:+.0%}" for y, v in yrs.items()) + ".")
    emit(f"Nights invested: {inv.reindex(r.index).fillna(False).mean():.0%}. At 2x a 1-in-100 night is "
         f"{np.percentile(x2[inv.reindex(r.index).fillna(False).astype(bool)], 1):+.1%}.")

    OUT.mkdir(exist_ok=True)
    (OUT / "overnight_leverage.md").write_text("\n".join(lines) + "\n")
    print(f"\nwrote {OUT / 'overnight_leverage.md'}")


if __name__ == "__main__":
    main()
