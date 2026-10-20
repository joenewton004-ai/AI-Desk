"""Would limit orders have cut what we pay versus the open?

    python research/limit_orders.py

Daily bars (open/high/low/close, adjusted) for the desk's current holdings over two years.
Every stock-day is treated as if we had to buy (and, separately, sell) that day, the way the
executor trades: decided at the previous close, filled after the next open. For each order
style we measure the price paid relative to that day's official open, in basis points
(positive = worse for us), INCLUDING what it costs when a limit order doesn't fill and has
to be done later.

Styles (buys; sells mirror them):
  market            fill at the open (the baseline: 0 by definition, before spread/impact)
  cap +c            limit at the previous close x (1 + c), sent before the open, good for the
                    day. Fills at the open if that is below the limit, at the limit if the day
                    trades down to it, otherwise expires -> buy at the NEXT open instead
  passive -y        wait for the open, then a limit y below it. Fills at the limit if the day
                    trades down through it, otherwise buy at the close (market-on-close)

Daily bars can't show the order of trades within the day or our place in the queue, so a
limit counts as filled only if the low trades at least 2bps through it (a buffer for queue
position). That still flatters limits a little. Writes research/output/limit_orders.md.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

OUT = Path(__file__).resolve().parent / "output"
END = "2026-10-19"                 # last full trading day before the desk's first fills
THROUGH = 0.0002                   # the low must trade 2bps through a buy limit to count as filled


def bars(symbols: list[str], start: str, end: str) -> dict[str, pd.DataFrame]:
    import yfinance as yf

    from ai_desk.fundamentals.yahoo import with_retry

    raw = with_retry(lambda: yf.download(symbols, start=start, end=end, auto_adjust=True, progress=False,
                                         threads=True))
    out = {k: raw[k].copy() for k in ("Open", "High", "Low", "Close")}
    for k in out:
        out[k].index = pd.to_datetime(out[k].index).tz_localize(None)
    return out


# --- pure simulation (unit-tested) ------------------------------------------------

def cap_limit(o, h, lo, c, prev_c, next_o, cap: float, side: str = "buy") -> tuple[np.ndarray, np.ndarray]:
    """Limit at prev close x (1 +/- cap), sent before the open. Returns (cost vs open in bps, filled?)."""
    if side == "buy":
        lim = prev_c * (1 + cap)
        at_open = o <= lim
        intraday = ~at_open & (lo <= lim * (1 - THROUGH))
        px = np.where(at_open, o, np.where(intraday, lim, next_o))
        cost = (px / o - 1) * 1e4
    else:
        lim = prev_c * (1 - cap)
        at_open = o >= lim
        intraday = ~at_open & (h >= lim * (1 + THROUGH))
        px = np.where(at_open, o, np.where(intraday, lim, next_o))
        cost = (1 - px / o) * 1e4
    return cost, at_open | intraday


def passive_limit(o, h, lo, c, y: float, side: str = "buy") -> tuple[np.ndarray, np.ndarray]:
    """Limit y away from the open, placed just after it; unfilled -> market-on-close."""
    if side == "buy":
        lim = o * (1 - y)
        filled = lo <= lim * (1 - THROUGH)
        px = np.where(filled, lim, c)
        cost = (px / o - 1) * 1e4
    else:
        lim = o * (1 + y)
        filled = h >= lim * (1 + THROUGH)
        px = np.where(filled, lim, c)
        cost = (1 - px / o) * 1e4
    return cost, filled


def summarize(cost: np.ndarray, filled: np.ndarray) -> dict:
    ok = ~np.isnan(cost)
    c, f = cost[ok], filled[ok]
    return {"orders": int(ok.sum()), "fill_rate": float(f.mean()), "avg_cost_bps": float(c.mean()),
            "median_cost_bps": float(np.median(c)), "worst_5pct_bps": float(np.percentile(c, 95)),
            "when_filled_bps": float(c[f].mean()) if f.any() else np.nan,
            "when_missed_bps": float(c[~f].mean()) if (~f).any() else np.nan}


def main() -> None:
    plan = json.loads((ROOT / "journal" / "plan.json").read_text())
    symbols = sorted({r["symbol"] for r in plan["rows"]})
    start = (pd.Timestamp(END) - pd.DateOffset(years=2)).date().isoformat()
    b = bars(symbols, start, (pd.Timestamp(END) + pd.Timedelta(days=1)).date().isoformat())
    o, h, lo, c = (b[k][symbols] for k in ("Open", "High", "Low", "Close"))
    prev_c, next_o = c.shift(1), o.shift(-1)
    keep = prev_c.notna() & next_o.notna() & o.notna()
    arr = lambda df: df.where(keep).to_numpy().ravel()  # noqa: E731
    O, H, L, C, PC, NO = map(arr, (o, h, lo, c, prev_c, next_o))

    lines = ["# Limit orders vs market orders - generated tables", "",
             f"{len(symbols)} current holdings, daily bars {start} to {END}. Cost = price paid vs that day's "
             "official open, in basis points (1bp = 0.01%); positive = worse for us. Includes what missed "
             "limit orders cost when done later.", ""]
    for side in ("buy", "sell"):
        rows = {"market at the open": summarize(np.zeros_like(O) + np.where(np.isnan(O), np.nan, 0), np.isfinite(O))}
        for cap in (0.0, 0.0025, 0.005, 0.01, 0.02):
            rows[f"limit at prev close {'+' if side == 'buy' else '-'}{cap:.2%}"] = summarize(
                *cap_limit(O, H, L, C, PC, NO, cap, side))
        for y in (0.001, 0.0025, 0.005, 0.01):
            rows[f"passive limit {y:.2%} {'below' if side == 'buy' else 'above'} the open"] = summarize(
                *passive_limit(O, H, L, C, y, side))
        df = pd.DataFrame(rows).T
        lines += [f"## {side.title()} orders", "",
                  "| style | orders | fill rate | avg cost | median | worst 5% | when filled | when missed |",
                  "|---|---|---|---|---|---|---|---|"]
        for k, r in df.iterrows():
            lines.append(f"| {k} | {r['orders']:,.0f} | {r['fill_rate']:.0%} | {r['avg_cost_bps']:+.1f} | "
                         f"{r['median_cost_bps']:+.1f} | {r['worst_5pct_bps']:+.1f} | {r['when_filled_bps']:+.1f} | "
                         f"{r['when_missed_bps']:+.1f} |")
        lines.append("")
    fills = pd.DataFrame(json.loads((ROOT / "journal" / "scorecard.json").read_text()).get("fills", []))
    if len(fills):
        lines += ["## Our first fills (2026-10-20, market orders, filled 9:32-9:33am)", "",
                  f"{len(fills)} fills: average {fills['vs_open_bps'].mean():+.1f}bps vs the open, median "
                  f"{fills['vs_open_bps'].median():+.1f}, range {fills['vs_open_bps'].min():+.0f} to "
                  f"{fills['vs_open_bps'].max():+.0f}; {int((fills['vs_open_bps'] < 0).sum())} filled below the open. "
                  f"Standard error of the average about {fills['vs_open_bps'].std() / np.sqrt(len(fills)):.0f}bps.", ""]
    OUT.mkdir(exist_ok=True)
    (OUT / "limit_orders.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
