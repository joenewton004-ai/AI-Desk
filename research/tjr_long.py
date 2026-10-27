"""TJR's model re-run on ten years of bars: QQQ and SPY as stand-ins for the NQ and ES futures.

    python research/tjr_long.py      (needs: python research/alpaca_bars.py --5min --extended QQQ SPY)

The first test (research/tjr.py) had ~49 days of 5-minute futures bars from Yahoo. Alpaca has no futures, but it has
ten years of 5-minute bars, pre-market and after-hours included, for QQQ (tracks the Nasdaq-100, like NQ) and SPY (the
S&P 500, like ES). The rules are research/tjr.py's, unchanged (sweep 9:30-11:00, break of structure or inverse FVG
within 30 minutes, entry at the next bar's open, stop beyond the sweep, 2R / 3R / opposite liquidity, out at 15:55,
optional 1-hour 50-period bias, one trade a day per instrument), with two differences forced by the data:
  - liquidity levels: the previous session's high/low and the overnight high/low (after-hours to 8pm plus
    pre-market from 4am). The Asia (8pm-midnight) and London (2-5am) sessions don't trade in US stocks, so those
    levels are dropped
  - costs: 0.01% of the price each way (a penny spread plus slippage on QQQ/SPY) instead of futures ticks
Control: the same times with a random direction (20 runs). Results by half (2016-20, 2021-26).
Writes research/output/tjr_long.md; findings in research/TJR.md.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "research"))

import alpaca_bars  # noqa: E402
import tjr  # noqa: E402

OUT = Path(__file__).resolve().parent / "output"
SYMS = ("QQQ", "SPY")
SPLIT = pd.Timestamp("2021-01-01").date()
_levels = tjr.levels


def stock_levels(bars: pd.DataFrame, day: pd.Timestamp) -> dict[str, float]:
    """tjr.levels without the Asia and London sessions (US stocks don't trade then; 4-5am would be a partial London)."""
    return {k: v for k, v in _levels(bars, day).items() if not k.startswith(("Asia", "London"))}


def load(sym: str) -> pd.DataFrame:
    b = alpaca_bars.bars(sym, timeframe="5Min", extended=True)
    return b.rename(columns={"open": "Open", "high": "High", "low": "Low", "close": "Close", "volume": "Volume"})


def main() -> None:
    lines: list[str] = []

    def emit(s=""):
        print(s, flush=True)
        lines.append(s)

    tjr.levels = stock_levels                      # run() looks levels up on the module
    data = {s: load(s) for s in SYMS}
    b0 = data["QQQ"]
    emit("# TJR's model on ten years of QQQ and SPY 5-minute bars - generated tables\n")
    emit(f"{b0.index[0].date()} to {b0.index[-1].date()}, Alpaca SIP bars incl. pre-market and after-hours (New York "
         "time). QQQ stands in for NQ, SPY for ES. Levels: previous session high/low, overnight high/low (Asia and "
         "London sessions don't exist for stocks). Costs 0.01% of the price each way. R = the trade's risk.\n")
    emit("| rules | trades | win rate | avg R (net) | t | avg R before costs | stopped out | 2016-20 R | 2021-26 R | "
         "profit factor |")
    emit("|---|---|---|---|---|---|---|---|---|---|")
    variants = [("BOS, 2R", dict(mode="bos", target="2R")), ("BOS, 3R", dict(mode="bos", target="3R")),
                ("BOS, opposite liquidity", dict(mode="bos", target="opposite")),
                ("BOS, 2R, 1-hour bias", dict(mode="bos", target="2R", use_bias=True)),
                ("inverse FVG, 2R", dict(mode="ifvg", target="2R")),
                ("inverse FVG, 2R, 1-hour bias", dict(mode="ifvg", target="2R", use_bias=True))]
    base = None
    for name, kw in variants:
        t = pd.concat([tjr.run(data[s], s, "5m", **kw) for s in SYMS], ignore_index=True)
        if name == "BOS, 2R":
            base = t
        r = tjr.summarize(t)
        if not r["n"]:
            emit(f"| {name} | 0 | | | | | | | | |")
            continue
        a, b = t[t["date"] < SPLIT]["R_net"], t[t["date"] >= SPLIT]["R_net"]
        emit(f"| {name} | {r['n']:,} | {r['win']:.0%} | {r['R']:+.3f} | {r['t']:.1f} | {r['R_gross']:+.3f} | "
             f"{r['stops']:.0%} | {a.mean():+.3f} | {b.mean():+.3f} | {r['pf']:.2f} |")
        if name == "BOS, 2R":
            ctrl = [tjr.summarize(pd.concat([tjr.run(data[s], s, "5m", mode="bos", target="2R", seed=k) for s in SYMS],
                                            ignore_index=True))["R"] for k in range(20)]
            emit(f"| *control: same times, random direction (20 runs)* | | | {np.mean(ctrl):+.3f} "
                 f"(range {min(ctrl):+.3f} to {max(ctrl):+.3f}) | | | | | | |")
    if base is not None and len(base):
        emit("\nBy instrument and level swept (BOS, 2R):\n")
        emit("| instrument | level | trades | avg R (net) | win rate |\n|---|---|---|---|---|")
        for (s, lv), g in base.groupby(["sym", "level"]):
            emit(f"| {s} | {lv} | {len(g):,} | {g['R_net'].mean():+.3f} | {(g['R_net'] > 0).mean():.0%} |")
        yr = base.groupby(pd.to_datetime(base["date"]).dt.year)["R_net"].agg(["count", "mean"])
        emit("\nBy year (BOS, 2R, avg R net): " + ", ".join(f"{y} {r['mean']:+.3f} ({int(r['count'])})"
                                                            for y, r in yr.iterrows()) + ".")
        emit(f"\nAverage risk per trade: {(base['risk_pts'] / base['entry']).mean():.2%} of the price; costs are "
             f"{(2 * tjr.ETF_COST * base['entry'] / base['risk_pts']).mean():.3f} R a trade on average.")

    OUT.mkdir(exist_ok=True)
    (OUT / "tjr_long.md").write_text("\n".join(lines) + "\n")
    print(f"\nwrote {OUT / 'tjr_long.md'}")


if __name__ == "__main__":
    main()
