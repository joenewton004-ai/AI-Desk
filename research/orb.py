"""Opening range breakout on "stocks in play" - a first look on the last ~60 days only.

    python research/orb.py      (uses data/backtest/intraday_5m.pkl from research/ict.py)

The rules follow Zarattini, Barbon & Aziz (2024), "A profitable day trading strategy for the U.S.
equity market" (SSRN 4729284), as described there:
  in play   each day, the 20 stocks whose first 5-minute bar has the highest volume relative to
            their own average first-bar volume over the previous 14 days (relative volume >= 1)
  direction the first 5-minute bar: up (close > open) -> only a long; down -> only a short; flat -> none
  entry     a stop order at the first bar's high (long) or low (short), from 9:35 on
  stop      10% of the stock's 14-day average daily range (ATR) from the entry
  exit      stop, or the 15:55 bar's close (no profit target)
  sizing    each trade risks the same amount (1% of the account), capped at 4x leverage overall
Universe: the 100 largest US companies (the cached 5-minute bars). The paper used ~7,000 stocks
and 2016-2023 minute data; with 60 days of large caps this is a preview, not a verdict.
Costs 0.03% each way (stress 0.10%). Writes research/output/orb.md; findings in research/ORB.md.
"""

from __future__ import annotations

import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research"))

import ict  # noqa: E402

CACHE = ROOT / "data" / "backtest"
OUT = Path(__file__).resolve().parent / "output"


def orb_trade(day: pd.DataFrame, atr: float, first_bars: int = 1, optimistic: bool = False) -> dict | None:
    """One stock-day of bars. The first `first_bars` bars (5 minutes) set the direction and the trigger.
    optimistic=False: if the entry bar also reaches the stop, assume the stop came first (worst case).
    optimistic=True: only check the stop from the bar after the entry (best case). The truth is between."""
    o, h, lo, c = (day[k].to_numpy(dtype=float) for k in ("open", "high", "low", "close"))
    k = first_bars
    if len(c) < k + 5 or not np.isfinite(c).all() or not np.isfinite(atr) or atr <= 0:
        return None
    fo, fc, fh, fl = o[0], c[k - 1], h[:k].max(), lo[:k].min()
    if fc > fo:
        side, trigger = 1, fh
    elif fc < fo:
        side, trigger = -1, fl
    else:
        return None
    for i in range(k, len(c)):                                    # stop-order entry at the trigger
        if (side > 0 and h[i] >= trigger) or (side < 0 and lo[i] <= trigger):
            entry = max(trigger, o[i]) if side > 0 else min(trigger, o[i])   # a gap through fills at the open
            stop = entry - side * 0.10 * atr
            if optimistic:
                if i + 1 >= len(c):
                    return None
                tr = ict.run_trade(o, h, lo, c, i + 1, side, entry, stop, entry + side * 1e9, limit=False)
            else:
                tr = ict.run_trade(o, h, lo, c, i, side, entry, stop, entry + side * 1e9, limit=False)
            if tr:
                tr["time"] = day.index[i]
            return tr
    return None


def fetch_1m(tickers: list[str]) -> dict[str, pd.DataFrame]:
    """Yahoo keeps 1-minute bars for ~30 days, at most 8 days per request."""
    path = CACHE / "intraday_1m.pkl"
    if path.exists():
        return pickle.loads(path.read_bytes())
    import yfinance as yf

    sys.path.insert(0, str(ROOT))
    from ai_desk.fundamentals.yahoo import with_retry

    end = pd.Timestamp("2026-10-21")
    parts = {k: [] for k in ("Open", "High", "Low", "Close", "Volume")}
    for w in range(4):
        e = end - pd.Timedelta(days=7 * w)
        s = e - pd.Timedelta(days=7)
        for i in range(0, len(tickers), 50):
            chunk = tickers[i:i + 50]
            d = with_retry(lambda chunk=chunk, s=s, e=e: yf.download(chunk, start=s.date().isoformat(), end=e.date().isoformat(),
                                                                       interval="1m", auto_adjust=False, progress=False,
                                                                       threads=4, prepost=False))
            if d is None or d.empty:
                continue
            for k in parts:
                parts[k].append(d[k])
        print(f"  1-minute bars: week {w + 1}/4", flush=True)
    out = {}
    for k, v in parts.items():
        df = pd.concat(v, sort=True)
        df = df[~df.index.duplicated()].sort_index()
        idx = pd.to_datetime(df.index)
        df.index = idx.tz_convert("America/New_York").tz_localize(None) if idx.tz is not None else idx
        out[k.lower()] = df.loc[:"2026-10-20 23:59"].astype("float32")
    path.write_bytes(pickle.dumps(out))
    return out


def main() -> None:
    lines: list[str] = []

    def emit(x=""):
        print(x, flush=True)
        lines.append(x)

    emit("# Opening range breakout on stocks in play - generated tables (preview)\n")
    emit("The 100 largest US companies; Yahoo bars. Each trade risks the same amount; results in R (multiples of that "
         "risk). 'Worst case' assumes the stop came first whenever the entry bar also reached it; 'best case' only "
         "checks the stop from the next bar. The truth lies between; the finer the bars, the closer the two.\n")
    b5 = pickle.loads((CACHE / "intraday_5m.pkl").read_bytes())
    tickers = list(b5["close"].columns)
    b1 = fetch_1m(tickers)
    for label, b, k in (("5-minute bars, ~60 days", b5, 1), ("1-minute bars, ~30 days", b1, 5)):
        for optimistic in (False, True):
            t = run(b, k, optimistic)
            if t.empty:
                continue
            emit(f"\n## {label}, {'best' if optimistic else 'worst'} case\n")
            emit(f"{t['date'].nunique()} trading days ({t['date'].min().date()} to {t['date'].max().date()}).\n")
            table(t, emit)
    _save(lines)


def run(b: dict[str, pd.DataFrame], first_bars: int, optimistic: bool) -> pd.DataFrame:
    o, h, lo, c, v = (b[k].astype(float) for k in ("open", "high", "low", "close", "volume"))
    day_of = c.index.normalize()
    days = sorted(set(day_of))
    stamps = pd.Series(c.index, index=c.index)
    first_k = stamps.groupby(day_of).apply(lambda x: list(x.iloc[:first_bars]))
    fv = pd.DataFrame({d: v.loc[ts].sum() for d, ts in first_k.items()}).T
    rel = fv / fv.rolling(14, min_periods=min(14, max(5, len(fv) // 3))).mean().shift(1)
    dh, dl = h.groupby(day_of).max(), lo.groupby(day_of).min()
    dc = c.groupby(day_of).last()
    tr_range = pd.concat([dh - dl, (dh - dc.shift(1)).abs(), (dl - dc.shift(1)).abs()]).groupby(level=0).max()
    atr = tr_range.rolling(14, min_periods=5).mean().shift(1)
    rows = []
    for d in days:
        if d not in rel.index or rel.loc[d].isna().all():
            continue
        inplay = rel.loc[d][rel.loc[d] >= 1].nlargest(20).index
        sl = slice(d, d + pd.Timedelta(hours=23))
        for s in inplay:
            day = pd.DataFrame({k: b[k][s].loc[sl] for k in ("open", "high", "low", "close")}).dropna()
            tr = orb_trade(day, float(atr.at[d, s]), first_bars, optimistic)
            if tr:
                tr.update({"date": d, "symbol": s, "rel_vol": float(rel.at[d, s])})
                rows.append(tr)
    return pd.DataFrame(rows)


def table(t: pd.DataFrame, emit) -> None:
    emit("| | trades | win rate | avg R before costs | avg R after 0.03% each way | after 0.10% | t-stat (after 0.03%) |")
    emit("|---|---|---|---|---|---|---|")
    for name, part in (("All", t), ("Longs", t[t["side"] > 0]), ("Shorts", t[t["side"] < 0]),
                       ("Relative volume 2x+", t[t["rel_vol"] >= 2])):
        if part.empty:
            continue
        risk_pct = (part["ret"] / part["R"].replace(0, np.nan)).abs()      # the stop distance as a share of the price
        r3, r10 = part["R"] - 2 * 0.0003 / risk_pct, part["R"] - 2 * 0.001 / risk_pct
        emit(f"| {name} | {len(part)} | {(r3 > 0).mean():.0%} | {part['R'].mean():+.3f} | {r3.mean():+.3f} | "
             f"{r10.mean():+.3f} | {r3.mean() / (r3.std() / np.sqrt(len(r3))):.1f} |")
    emit(f"\nHow trades ended: {', '.join(f'{w} {n}' for w, n in t['why'].value_counts().items())}. "
         f"Median stop distance: {(t['ret'] / t['R']).abs().median():.2%} of the price.")
    daily = t.groupby("date")["R"].sum()
    emit(f"Days with a net gain (before costs): {(daily > 0).mean():.0%} of {len(daily)}.")


def _save(lines: list[str]) -> None:
    OUT.mkdir(exist_ok=True)
    (OUT / "orb.md").write_text("\n".join(lines) + "\n")
    print(f"\nwrote {OUT / 'orb.md'}")


if __name__ == "__main__":
    main()
