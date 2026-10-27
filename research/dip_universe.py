"""The RSI dip rule on wider universes: the top 100 (live), 250, 500 and 750 US companies.

    python research/dip_universe.py

Rule as live (amendment c52ce018): close above the 200-day average and RSI(14) < 30 -> buy at the next open, sell at
the open after a close above the 5-day average (at most 10 days). Universe = the N largest US companies at each
quarter-end known at the time (SEC snapshots, 45-day lag). Per dip after costs (0.05% each way, and 0.20%), in the
older years (2014-19) and the newer ones (2020-26); then the live desk shape - dips 10% each, at most 5, lowest RSI
first, and the overnight sleeve (as live, 0.02% costs) with all the rest. **Survivors-only prices**: companies that
later collapsed and delisted are missing, which flatters dip-buying - and more so the further down the list you go.
Writes research/output/dip_universe.md.
"""

from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import candle_rsi as cr  # noqa: E402
import desk_rsi as dr  # noqa: E402
import overnight as ov  # noqa: E402
import overnight_regime as orr  # noqa: E402
from ai_desk.indicators import rsi  # noqa: E402

OUT = orr.OUT
RULE = ("T1", "R2", "C0", "E1")
SPLIT = pd.Timestamp("2020-01-01")


def main() -> None:
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    lines: list[str] = []

    def emit(t=""):
        print(t, flush=True)
        lines.append(t)

    on_r, rf, inv = dr.overnight_live()
    days = on_r.index
    rfd = rf.reindex(days).fillna(0)
    base = orr.stats(on_r, rfd)
    emit("# The RSI dip rule on wider universes - generated tables\n")
    emit("**Survivors-only prices** (flatters dip-buying, more so for smaller companies). Per dip after costs. Desk = dips "
         "10% each (max 5, lowest RSI first) + the overnight sleeve (0.02%) with the rest, daily 2014-04 to 2026-10. "
         f"Overnight sleeve alone: {base['CAGR']:.1%}/yr, Sharpe {base['Sharpe']:.2f}, worst drop {base['maxdd']:.0%}.\n")
    emit("| universe | dips/yr | win rate | net per dip (0.05%) | t | 2014-19 | 2020-26 | at 0.20% costs | worst dip | "
         "dips taken (5 slots) | money in dips | desk return/yr | desk Sharpe | desk worst drop |")
    emit("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for top in (100, 250, 500, 750):
        frames, member = cr.stock_data(top)
        feats = {s: cr.features(d) for s, d in frames.items()}
        r, h, trades = cr.run_rule(frames, feats, RULE, 0.0005, dr.PERIOD, member)
        when = pd.to_datetime([e for _, e, _ in trades])
        st = cr.stats(r, h)
        yrs = (when.max() - when.min()).days / 365.25
        rsis = {s: rsi(frames[s]["close"], 14) for s in {t[0] for t in trades}}
        rsi_at = {}
        for s, e, _ in trades:
            prev = rsis[s].index[rsis[s].index < e]
            rsi_at[(s, e)] = float(rsis[s].loc[prev[-1]]) if len(prev) else 0.0
        oo = pd.DataFrame({s: d["open"].shift(-1) / d["open"] - 1 for s, d in frames.items()})
        w = dr.book(trades, rsi_at, days, 0.10, 5)
        taken = int(dr.entry_mask(w).to_numpy().sum())
        held = w.sum(axis=1)
        desk = (1.0 - held.shift(1, fill_value=0.0)) * on_r + dr.overlay_daily(w, oo, 0.0005)
        ds = orr.stats(desk, rfd)
        emit(f"| top {top} | {len(r) / yrs:.0f} | {st['win']:.0%} | {st['net']:+.2%} | {st['t']:.1f} | "
             f"{r[when < SPLIT].mean():+.2%} | {r[when >= SPLIT].mean():+.2%} | {(r - 0.003).mean():+.2%} | {r.min():+.0%} | "
             f"{taken:,} of {len(trades):,} | {held.mean():.1%} | {ds['CAGR']:.1%} | {ds['Sharpe']:.2f} | {ds['maxdd']:.0%} |")

    OUT.mkdir(exist_ok=True)
    (OUT / "dip_universe.md").write_text("\n".join(lines) + "\n")
    print(f"\nwrote {OUT / 'dip_universe.md'}")


if __name__ == "__main__":
    main()
