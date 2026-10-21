"""Momentum scan: rank large US companies by their last 6 months' price gain.

The live version of research/WEEKLY.md and research/MOMENTUM_SLEEVE.md (amendment 00e1f2b8,
accepted 2026-10-20): the 20 strongest stocks by 6-month return, skipping the most recent
week, among those trading above their 40-week (200-day) average AND their 100-day average (the
entry filter, amendment of 2026-10-21: a stock below its 100-day would be sold by the exit rule
the same evening). The momentum sleeve buys the top 20 at each re-pick (every 4 weeks) and sells
any holding that closes below its 100-day average in between.

Universe: US-listed companies above $10B today (the backtest used the 750 largest at each
quarter-end - a close match). Writes output/momentum_<date>.csv, ranked best first, with the
companies that fail the trend filter listed after, so the watchlist can show them too.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

LOOKBACK_DAYS = 130      # ~26 weeks
SKIP_DAYS = 5            # skip the latest week (short-term reversal noise)
TREND_DAYS = 200         # ~40 weeks
EXIT_MA_DAYS = 100       # the sell rule between re-picks


def rank(closes: pd.DataFrame, lookback: int = LOOKBACK_DAYS, skip: int = SKIP_DAYS,
         trend: int = TREND_DAYS) -> pd.DataFrame:
    """Pure: momentum and trend for every column of `closes`, using data up to its last row only."""
    c = closes.ffill()
    if len(c) < lookback + skip + 1:
        raise ValueError(f"need at least {lookback + skip + 1} days of prices, got {len(c)}")
    mom = c.iloc[-1 - skip] / c.iloc[-1 - skip - lookback] - 1
    sma = c.rolling(trend, min_periods=trend).mean().iloc[-1]
    sma_exit = c.rolling(EXIT_MA_DAYS, min_periods=EXIT_MA_DAYS).mean().iloc[-1]
    last = c.iloc[-1]
    df = pd.DataFrame({"mom_6m": mom, "price": last, "sma_200": sma, "sma_100": sma_exit})
    df["above_200"] = df["price"] > df["sma_200"]
    df["above_100"] = df["price"] > df["sma_100"]       # entry filter: the exit rule mustn't fire on the pick day
    df["passes"] = df["above_200"] & df["above_100"] & df["mom_6m"].notna()
    df["score"] = df["mom_6m"].rank(pct=True) * 100
    df = df.sort_values(["passes", "mom_6m"], ascending=[False, False])
    df["rank"] = np.where(df["passes"], np.arange(1, len(df) + 1), np.nan)
    df["ma_days"] = EXIT_MA_DAYS
    df.index.name = "symbol"
    return df


def run_scan(min_cap: float = 10e9, progress: bool = True) -> pd.DataFrame:
    from ai_desk.bottleneck.scan import daily_closes
    from ai_desk.fundamentals.universe import large_caps

    uni = large_caps(min_cap)
    if progress:
        print(f"  {len(uni)} US companies above ${min_cap / 1e9:.0f}B; downloading 18 months of prices ...")
    closes = daily_closes(uni["symbol"].tolist(), period="18mo")
    # today's bar is incomplete while the market is open: rank on the last full day
    from ai_desk.live import drop_incomplete_bar
    closes = drop_incomplete_bar(closes)
    enough = closes.notna().sum() >= LOOKBACK_DAYS + SKIP_DAYS + 1
    df = rank(closes.loc[:, enough])
    meta = uni.set_index("symbol")
    for col in ("name", "sector", "industry", "market_cap"):
        if col in meta:
            df[col] = meta[col].reindex(df.index)
    df.attrs["asof"] = closes.index[-1]
    return df


def report(df: pd.DataFrame, top: int = 20, out_dir: str = "output") -> Path:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    stem = out / f"momentum_{date.today().isoformat()}"
    df.to_csv(f"{stem}.csv")
    asof = df.attrs.get("asof")
    head = df[df["passes"]].head(top)
    lines = [f"# Momentum scan - {date.today().isoformat()}", "",
             f"Prices to {pd.Timestamp(asof).date() if asof is not None else 'n/a'}. {int(df['passes'].sum())} of "
             f"{len(df)} companies are above their 200-day average; ranked by 6-month return (skipping the last week).", "",
             "| # | symbol | name | 6-month return | price vs 200-day avg |", "|---|---|---|---|---|"]
    for i, (s, r) in enumerate(head.iterrows(), 1):
        lines.append(f"| {i} | {s} | {r.get('name', '')} | {r['mom_6m']:+.0%} | {r['price'] / r['sma_200'] - 1:+.0%} |")
    lines += ["", "_Price strength only - a research shortlist, not buy recommendations._"]
    Path(f"{stem}.md").write_text("\n".join(lines) + "\n")
    return Path(f"{stem}.md")
