"""Ross Cameron (Warrior Trading)-style gap-and-go day trading, on the data we have.

    python research/cameron.py

Cameron day-trades small-cap momentum: stocks up 10%+ on the day with 5x+ normal volume and a news catalyst (his "5
pillars" also include a low share price and a small float), bought on the first pullbacks in the first hours and sold
the same day. We have NO historical small-cap data (Yahoo has no point-in-time list of past low-float gappers, and its
prices are survivors only), so this tests the core pattern - big gaps up at the open keep running during the day - on
what we have:
  A. daily bars, the 750 largest US companies (point-in-time), 2014-2026: buy every stock that OPENS X% above the
     previous close (X = 4, 10, 20%), sell at that day's close; also the cheapest names ($10-20) and the smaller half
  B. the same, but only stocks whose full-day volume was 5x+ normal - known only at the close, so this is HINDSIGHT,
     an upper bound on what a volume filter could add
  C. 5-minute bars (120 large stocks, the last ~60 days): on gap-ups of 3%+, buy a break of the first red 5-minute
     candle's high before 10:30, stop at its low, target 2R, out by 11:00
0.10% per trade each way (gappers' real spreads are usually wider). Writes research/output/cameron.md; findings in
research/CAMERON.md.
"""

from __future__ import annotations

import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "research"))

import ict  # noqa: E402
import swing  # noqa: E402

CACHE = ROOT / "data" / "backtest"
OUT = Path(__file__).resolve().parent / "output"
COST = 0.001
START, END = swing.START, swing.END


def gap_trades(o: pd.DataFrame, c: pd.DataFrame, mask: pd.DataFrame, gap_min: float) -> pd.Series:
    """Pure: each qualifying stock-day's open-to-close return after costs; the gap is known at the open."""
    gap = o / c.shift(1) - 1
    sel = mask & (gap >= gap_min)
    r = (c / o - 1).where(sel)
    return r.stack().dropna() - 2 * COST


def first_pullback(day: pd.DataFrame, rr: float = 2.0) -> dict | None:
    """Pure: the first red 5-minute bar before 10:30; buy when a later bar trades above its high; stop its low."""
    o, h, lo, c = (day[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    t = day.index
    for i in range(1, len(c)):
        if t[i].hour * 60 + t[i].minute >= 10 * 60 + 30:
            return None
        if c[i] < o[i]:                                    # the first red candle
            for j in range(i + 1, len(c)):
                if t[j].hour * 60 + t[j].minute >= 10 * 60 + 30:
                    return None
                if h[j] > h[i]:
                    entry = max(o[j], h[i])
                    stop = lo[i]
                    if entry <= stop:
                        return None
                    end = int(np.searchsorted([x.hour * 60 + x.minute for x in t], 11 * 60))
                    tr = ict.run_trade(o[:end], h[:end], lo[:end], c[:end], j, 1, entry, stop,
                                       entry + rr * (entry - stop), limit=False)
                    return tr
            return None
    return None


def main() -> None:
    lines: list[str] = []

    def emit(s=""):
        print(s, flush=True)
        lines.append(s)

    d = swing.fetch_daily(swing.universe_tickers())
    o, c, v = (d[k].astype(float).loc[:END] for k in ("open", "close", "volume"))
    snaps = {}
    for m in (3, 6, 9, 12):
        snaps.update({k: list(s.index) for k, s in pickle.loads((CACHE / f"snapshots_m{m}.pkl").read_bytes()).items()})
    dates, symbols = c.index, list(c.columns)
    member = pd.DataFrame(swing.membership(dict(sorted(snaps.items())), dates, symbols), index=dates, columns=symbols)
    member = member.loc[START:]
    o, c, v = o.loc[START:], c.loc[START:], v.loc[START:]
    prev = c.shift(1)
    dollar = (c * v).rolling(50, min_periods=40).mean().shift(1)
    small = dollar.where(member).rank(axis=1, pct=True) <= 0.5
    cheap = (prev >= 10) & (prev <= 20)
    rvol = v / v.rolling(30, min_periods=20).mean().shift(1)            # needs the day's full volume: hindsight
    base = member & (prev > 5)

    emit("# Ross Cameron-style gap and go - generated tables\n")
    emit(f"Daily, {dates[dates >= pd.Timestamp(START)][0].date()} to {dates[-1].date()}; the 750 largest US companies "
         "(point-in-time), **survivors-only prices** - NOT his small-cap universe. Buy at the open, sell at the close; "
         "0.10% per trade each way.\n")
    emit("| rule | trades | win rate | avg per trade | t | best year | worst year |")
    emit("|---|---|---|---|---|---|---|")

    def row(name, r):
        if r.empty:
            emit(f"| {name} | 0 | | | | | |")
            return
        y = r.groupby(r.index.get_level_values(0).year).mean()
        t = r.mean() / r.std() * np.sqrt(len(r))
        emit(f"| {name} | {len(r):,} | {(r > 0).mean():.0%} | {r.mean():+.2%} | {t:.1f} | {y.max():+.2%} | {y.min():+.2%} |")

    for g in (0.04, 0.10, 0.20):
        row(f"A. Gap up {g:.0%}+", gap_trades(o, c, base, g))
    row("A. Gap up 4%+, price $10-20", gap_trades(o, c, base & cheap, 0.04))
    row("A. Gap up 4%+, the less-traded half", gap_trades(o, c, base & small, 0.04))
    row("A. Gap up 10%+, the less-traded half", gap_trades(o, c, base & small, 0.10))
    row("B. Gap up 4%+ AND 5x volume (hindsight)", gap_trades(o, c, base & (rvol >= 5), 0.04))
    row("B. Gap up 10%+ AND 5x volume (hindsight)", gap_trades(o, c, base & (rvol >= 5), 0.10))
    row("(For comparison) every stock, open to close", gap_trades(o, c, base, -1.0))

    emit("\n## C. 5-minute first pullback on gap-ups (120 large stocks, ~60 days)\n")
    b = pickle.loads((CACHE / "intraday_5m.pkl").read_bytes())
    trades = []
    days = sorted({t.normalize() for t in b["close"].index})
    for sym in b["close"].columns:
        df = pd.DataFrame({k: b[k][sym] for k in ("open", "high", "low", "close")}).dropna()
        closes = df["close"].groupby(df.index.normalize()).last()
        opens = df["open"].groupby(df.index.normalize()).first()
        for k, dd in enumerate(days[1:], 1):
            if dd not in opens.index or days[k - 1] not in closes.index:
                continue
            gap = opens[dd] / closes[days[k - 1]] - 1
            if gap < 0.03:
                continue
            tr = first_pullback(df.loc[str(dd.date())])
            if tr:
                trades.append({**tr, "sym": sym, "date": dd.date(), "gap": gap})
    t = pd.DataFrame(trades)
    if t.empty:
        emit("No trades.")
    else:
        net = t["ret"] - 2 * COST
        emit(f"{len(t)} trades on {t['date'].nunique()} days: win rate {(net > 0).mean():.0%}, average {net.mean():+.2%} "
             f"per trade after costs (t {net.mean() / net.std() * np.sqrt(len(net)):.1f}), average R before costs "
             f"{t['R'].mean():+.2f}; stopped out {(t['why'] == 'stop').mean():.0%}.")

    OUT.mkdir(exist_ok=True)
    (OUT / "cameron.md").write_text("\n".join(lines) + "\n")
    print(f"\nwrote {OUT / 'cameron.md'}")


if __name__ == "__main__":
    main()
