"""The 'big green line' on QQQ and the 'Magnificent 7' instead of SPY.

    python research/green_line_tech.py

Asked 2026-11-10 after research/GREEN_LINE.md (SPY: halves the worst drop, 1-3%/yr less return, same Sharpe). Same
rules and costs as research/green_line.py (signal at each close, switch at the next open, 0.05% per switch, T-bills on
cash, Sharpe above T-bills), same line lengths. Instruments:
  QQQ (Nasdaq-100, with dividends, from 1999 - so 2000-2002's -83% is in the test)
  AAPL MSFT NVDA AMZN GOOGL META TSLA one at a time, from each one's first year of history
  'Mag 7 basket': equal weight across the seven (rebalanced daily), from 2013 when all seven have a year of history;
  with the line, each stock has its own signal and its seventh sits in T-bills while it is below its line.
HINDSIGHT: the seven are TODAY's biggest winners, picked in 2023 for having won. Any test on them flatters buy and hold
and can't tell us what a line would do on the next seven - it only shows how the line behaves on stocks that went up
a lot with deep falls on the way. Writes research/output/green_line_tech.md; findings in research/GREEN_LINE_TECH.md.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "research"))

from ai_desk.data import load_yahoo  # noqa: E402
from ai_desk.fundamentals.yahoo import with_retry  # noqa: E402
import green_line as gl  # noqa: E402

END = "2026-11-10"                         # Yahoo end is exclusive: the last bar is 2026-11-09, the last full day
MAG7 = ("AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA")
KEEP = ("Buy and hold", "Above the 50-day EMA", "Above the 200-day EMA", "Above the 200-day SMA",
        "200-day EMA with a 2% band", "Above the 10-month SMA (month-ends)")


def basket(rets: pd.DataFrame) -> pd.Series:
    """Pure: equal weight across the columns' daily returns, rebalanced daily."""
    return rets.mean(axis=1)


def main() -> None:
    lines: list[str] = []

    def emit(t=""):
        print(t, flush=True)
        lines.append(t)

    irx = with_retry(lambda: load_yahoo("^IRX", "1990-01-01", END))["close"] / 100
    data = {s: with_retry(lambda s=s: load_yahoo(s, "1995-01-01", END)) for s in ("QQQ", "SPY") + MAG7}
    emit("# The green line on QQQ and the Mag 7 - generated tables\n")
    emit(f"Signal at each close, switch at the next open, 0.05% per switch, T-bills on cash, Sharpe above T-bills. "
         f"Prices with dividends to the {data['SPY'].index[-1].date()} close. **The Mag 7 are picked with hindsight.**\n")
    head = ("| rule | return/yr | Sharpe | worst drop | first half Sharpe | second half Sharpe | time in | switches/yr |"
            "\n|---|---|---|---|---|---|---|---|")
    summary, rets_by = [], {}
    for sym in ("SPY", "QQQ") + MAG7:
        d = data[sym]
        o, c = d["open"].astype(float), d["close"].astype(float)
        rf = irx.reindex(c.index).ffill().bfill() / 252
        first = c.index[260]
        idx = c.index[c.index >= first]
        mid = idx[len(idx) // 2]
        emit(f"## {sym}: {first.date()} to {c.index[-1].date()} (halves split at {mid.date()})\n")
        emit(head)
        res = {}
        for name, sig in gl.rules(c).items():
            if name not in KEEP:
                continue
            r = (c.pct_change() if sig is None else gl.book(o, c, rf, sig)).loc[first:].dropna()
            rets_by[(sym, name)] = r
            s, a, b = gl.stats(r, rf), gl.stats(r.loc[:mid], rf), gl.stats(r.loc[mid:], rf)
            sig_in = pd.Series(True, index=c.index) if sig is None else sig
            t_in = sig_in.loc[first:].mean()
            sw = sig_in.loc[first:].astype(int).diff().abs().sum() / (len(r) / 252)
            res[name] = (s, a, b)
            emit(f"| {name} | {s['CAGR']:.1%} | {s['Sharpe']:.2f} | {s['maxdd']:.0%} | {a['Sharpe']:.2f} | "
                 f"{b['Sharpe']:.2f} | {t_in:.0%} | {sw:.1f} |")
        emit()
        h, l2 = res["Buy and hold"][0], res["Above the 200-day SMA"]
        summary.append((sym, str(first.year), h["CAGR"], h["Sharpe"], h["maxdd"], l2[0]["CAGR"], l2[0]["Sharpe"],
                        l2[0]["maxdd"], l2[1]["Sharpe"] > res["Buy and hold"][1]["Sharpe"]
                        and l2[2]["Sharpe"] > res["Buy and hold"][2]["Sharpe"]))

    # the equal-weight Mag 7 basket, from when all seven have a full year of history
    rf_all = irx.reindex(data["SPY"].index).ffill().bfill() / 252
    start = max(rets_by[(s, "Buy and hold")].index[0] for s in MAG7)
    emit(f"## Mag 7 basket, equal weight: {start.date()} to {data['SPY'].index[-1].date()}\n")
    emit(head)
    for name in KEEP:
        r = basket(pd.DataFrame({s: rets_by[(s, name)] for s in MAG7}).loc[start:]).dropna()
        idx = r.index
        mid = idx[len(idx) // 2]
        s, a, b = gl.stats(r, rf_all), gl.stats(r.loc[:mid], rf_all), gl.stats(r.loc[mid:], rf_all)
        emit(f"| {name} | {s['CAGR']:.1%} | {s['Sharpe']:.2f} | {s['maxdd']:.0%} | {a['Sharpe']:.2f} | "
             f"{b['Sharpe']:.2f} | - | - |")
        if name in ("Buy and hold", "Above the 200-day SMA"):
            summary.append(("Mag 7 basket", str(start.year), s["CAGR"], s["Sharpe"], s["maxdd"], None, None, None,
                            None) if name == "Buy and hold" else None)
            if name != "Buy and hold":
                sym, yr, hc, hs, hd = summary.pop(-2)[:5]
                summary.append((sym, yr, hc, hs, hd, s["CAGR"], s["Sharpe"], s["maxdd"], None))
            summary = [x for x in summary if x is not None]
    emit()
    emit("## Summary: buy and hold vs the 200-day SMA\n")
    emit("| instrument | from | hold return/yr | hold Sharpe | hold worst | line return/yr | line Sharpe | line worst | "
         "line's Sharpe better in both halves |")
    emit("|---|---|---|---|---|---|---|---|---|")
    for sym, yr, hc, hs, hd, lc, ls, ld, both in summary:
        emit(f"| {sym} | {yr} | {hc:.1%} | {hs:.2f} | {hd:.0%} | {lc:.1%} | {ls:.2f} | {ld:.0%} | "
             f"{'-' if both is None else ('yes' if both else 'no')} |")
    gl.OUT.mkdir(exist_ok=True)
    (gl.OUT / "green_line_tech.md").write_text("\n".join(lines) + "\n")
    print(f"\nwrote {gl.OUT / 'green_line_tech.md'}")


if __name__ == "__main__":
    main()
