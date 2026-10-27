"""The day-trader-skill's daily setups (Jakeschincariol/day-trader-skill, "Trader skill v2", MIT, reviewed 2026-10-27).

    python research/daily_setups.py

Its pre-market scan tags, from daily closes only (definitions copied from trader-scanner/scan.py find_setups):
  breakout_20d     the last close is above every close of the 20 before it
  bull_flag        up more than 10% over the 10 sessions before the last 5, then the last 5 closes inside a 5% range
  reclaim_ma20     closed under the 20-day average the day before, then closed above it
  oversold         RSI 14 (Wilder) under 30
  oversold_bounce  RSI 14 was under 30 yesterday and today closed up
Tested on the 100 largest US companies at each date (point-in-time SEC snapshots), daily bars, with two holds fixed
before running: the next day's open to close (the pack trades them as day trades) and 5 days (next open to the open
5 days later). Each setup is measured AGAINST the average of all top-100 stocks the same day with the same hold, so
the market's drift doesn't count as skill. Costs 0.05% each way. 2014-05 to 2019 and 2020-2026. **Survivors-only
prices** (flatters dip/bounce setups). Writes research/output/daily_setups.md.
"""

from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import candle_rsi as cr  # noqa: E402
from ai_desk.indicators import rsi  # noqa: E402

OUT = Path(__file__).resolve().parent / "output"
COST = 0.0005
START, SPLIT, END = "2014-05-15", "2020-01-01", "2026-10-20"
SETUPS = ["breakout_20d", "bull_flag", "reclaim_ma20", "oversold", "oversold_bounce"]


def setups(c: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Pure: each setup as True/False per day and stock, from closes up to that day (the pack's definitions)."""
    hi20 = c.shift(1).rolling(20, min_periods=20).max()
    ma20 = c.rolling(20, min_periods=20).mean()
    run = c.shift(5) / c.shift(15) - 1
    rng5 = (c.rolling(5).max() - c.rolling(5).min()) / c
    r = c.apply(lambda s: rsi(s.dropna(), 14).reindex(s.index))
    return {"breakout_20d": c > hi20,
            "bull_flag": (run > 0.10) & (rng5 < 0.05),
            "reclaim_ma20": (c.shift(1) < ma20.shift(1)) & (c > ma20),
            "oversold": r < 30,
            "oversold_bounce": (r.shift(1) < 30) & (c > c.shift(1))}


def main() -> None:
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    lines: list[str] = []

    def emit(s=""):
        print(s, flush=True)
        lines.append(s)

    frames, member = cr.stock_data(100)
    o = pd.DataFrame({s: d["open"] for s, d in frames.items()})
    c = pd.DataFrame({s: d["close"] for s, d in frames.items()})
    member = member.reindex(c.index).fillna(False).astype(bool)
    day1 = c.shift(-1) / o.shift(-1) - 1 - 2 * COST                    # next day, open to close
    hold5 = o.shift(-6) / o.shift(-1) - 1 - 2 * COST                   # next open to the open 5 days later
    sig = setups(c)
    emit("# The day-trader-skill's daily setups on the top 100 - generated tables\n")
    emit("Excess = the setup's average minus the average of all top-100 stocks the same day (same hold, same costs). "
         "t-stats from the daily series of excess returns (5-day holds overlap: their t is divided by sqrt 5). "
         "**Survivors-only prices.**\n")
    emit("| setup | hold | signals/yr | avg after costs | all stocks | excess | t | 2014-19 excess | 2020-26 excess |")
    emit("|---|---|---|---|---|---|---|---|---|")
    span = (pd.Timestamp(END) - pd.Timestamp(START)).days / 365.25
    for name in SETUPS:
        s = sig[name] & member
        for hold, r, adj in (("next day", day1, 1.0), ("5 days", hold5, np.sqrt(5))):
            r = r.loc[START:END]
            s_ = s.loc[START:END]
            pick = r.where(s_).mean(axis=1)
            base = r.where(member.loc[START:END]).mean(axis=1)
            ex = (pick - base).dropna()
            n = int(s_.to_numpy().sum())
            t = ex.mean() / ex.std() * np.sqrt(len(ex)) / adj if len(ex) > 1 else np.nan
            emit(f"| {name} | {hold} | {n / span:.0f} | {r.where(s_).stack().mean():+.3%} | {base.mean():+.3%} | "
                 f"{ex.mean():+.3%} | {t:.1f} | {ex.loc[:SPLIT].mean():+.3%} | {ex.loc[SPLIT:].mean():+.3%} |")
    emit("\nFor comparison, the live dip rule (above the 200-day average AND RSI 14 under 30, sold above the 5-day "
         "average) made +1.0% / +1.2% a dip in the two periods (research/CANDLE_RSI.md).")

    OUT.mkdir(exist_ok=True)
    (OUT / "daily_setups.md").write_text("\n".join(lines) + "\n")
    print(f"\nwrote {OUT / 'daily_setups.md'}")


if __name__ == "__main__":
    main()
