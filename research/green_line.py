"""The "big green line" (@pb_ema on Instagram): hold the S&P 500 above a moving average, cash below it.

    python research/green_line.py

The reel (transcript via creatorhouse.app; the indicator is "PB EMA" on TradingView, length not confirmed) says: buy
the S&P 500 when it's above the green line, sell when it falls below, and shows 50 years of it against buy and hold.
The usual lengths are tested, since the reel's isn't known:
  - exponential averages (EMA) of 50, 100, 200 and 250 days; the 200-day simple average (SMA)
  - the 10-month simple average checked at month-ends only (Faber's version: far fewer switches)
  - the 200-day EMA with a 2% band (switch only once the close is 2% past the line: fewer false alarms)
Signal at each close; the switch happens at the next day's open (the overnight move still belongs to the old
position); 0.05% per switch; cash earns T-bills; Sharpe above T-bills.
Data: SPY with dividends (1993-), and the S&P 500 index (^GSPC, 1970-) WITHOUT dividends - holding it understates
buy and hold by ~2%/yr while cash earns its full T-bill rate, so the index version flatters the line. Writes
research/output/green_line.md; findings in research/GREEN_LINE.md.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ai_desk.data import load_yahoo  # noqa: E402
from ai_desk.fundamentals.yahoo import with_retry  # noqa: E402

OUT = Path(__file__).resolve().parent / "output"
COST = 0.0005
END = "2026-10-27"                        # Yahoo end is exclusive: the last bar is 2026-10-26, the last full day
CRASHES = (1974, 1987, 2002, 2008, 2020, 2022)


# --- pure pieces (unit-tested) --------------------------------------------------------

def above(close: pd.Series, line: pd.Series, band: float = 0.0) -> pd.Series:
    """In (True) while the close is above the line. With a band, get in only once the close is `band` above the
    line and out only once it is `band` below; in between, keep the last state. Uses data up to each close."""
    if band == 0:
        return (close > line) & line.notna()
    state, out = False, []
    for c, m in zip(close.to_numpy(float), line.to_numpy(float)):
        if np.isnan(m):
            state = False
        elif c > m * (1 + band):
            state = True
        elif c < m * (1 - band):
            state = False
        out.append(state)
    return pd.Series(out, index=close.index)


def month_end_signal(close: pd.Series, months: int = 10) -> pd.Series:
    """Above the `months`-month simple average, checked at each month's last close and held all next month."""
    m = close.resample("ME").last()
    sig = (m > m.rolling(months).mean()).astype(float)
    last = close.groupby(close.index.to_period("M")).apply(lambda s: s.index[-1])
    return pd.Series(sig.to_numpy(), index=pd.DatetimeIndex(last.to_numpy())).reindex(close.index).ffill().fillna(0) > 0


def book(o: pd.Series, c: pd.Series, rf_daily: pd.Series, sig: pd.Series, cost: float = COST) -> pd.Series:
    """Daily returns: the signal at close t sets the position from t+1's open. Day t+1 = the overnight gap on the
    old position + the open-to-close move on the new one; money out of the market earns T-bills."""
    pos = sig.astype(float).shift(1).fillna(0.0)
    held = pos.shift(1).fillna(0.0)
    gap, day = o / c.shift(1) - 1, c / o - 1
    r = held * gap.fillna(0) + pos * day + (1 - pos) * rf_daily.reindex(c.index).fillna(0)
    return r - pos.diff().abs().fillna(0) * cost


def stats(r: pd.Series, rf_daily: pd.Series) -> dict:
    eq = (1 + r).cumprod()
    ex = r - rf_daily.reindex(r.index).fillna(0)
    return {"CAGR": eq.iloc[-1] ** (252 / len(r)) - 1, "vol": r.std() * np.sqrt(252),
            "Sharpe": ex.mean() / ex.std() * np.sqrt(252), "maxdd": (eq / eq.cummax() - 1).min()}


def rules(c: pd.Series) -> dict[str, pd.Series | None]:
    ema = {n: c.ewm(span=n, adjust=False, min_periods=n).mean() for n in (50, 100, 200, 250)}
    return {"Buy and hold": None,
            **{f"Above the {n}-day EMA": above(c, e) for n, e in ema.items()},
            "Above the 200-day SMA": above(c, c.rolling(200).mean()),
            "200-day EMA with a 2% band": above(c, ema[200], band=0.02),
            "Above the 10-month SMA (month-ends)": month_end_signal(c)}


def main() -> None:
    lines: list[str] = []

    def emit(t=""):
        print(t, flush=True)
        lines.append(t)

    irx = with_retry(lambda: load_yahoo("^IRX", "1969-01-01", END))["close"] / 100
    emit("# The big green line - generated tables\n")
    emit("Signal at each close, switch at the next open, 0.05% per switch, T-bills on cash, Sharpe above T-bills. "
         "Data to the 2026-10-26 close.\n")
    for sym, start, note in (("SPY", "1993-01-01", "SPY, dividends included"),
                             ("^GSPC", "1969-01-01", "S&P 500 index, price only (no dividends: flatters the line)")):
        d = with_retry(lambda sym=sym, start=start: load_yahoo(sym, start, END))
        o, c = d["open"].astype(float), d["close"].astype(float)
        if sym == "^GSPC":                      # Yahoo's early index bars have open = 0 or = close: use the close
            o = o.where((o > 0) & (d.index >= "1982-04-21"), c.shift(1))
        rf = (irx.reindex(c.index).ffill().bfill() / 252)
        first = c.index[260]                    # a year of history so every line exists
        emit(f"## {note}: {first.date()} to {c.index[-1].date()}\n")
        emit("| rule | return/yr | volatility | Sharpe | worst drop | first half Sharpe | second half Sharpe | "
             "time in | switches/yr | " + " | ".join(str(y) for y in CRASHES if y >= first.year) + " |")
        emit("|---|---|---|---|---|---|---|---|---|" + "---|" * sum(y >= first.year for y in CRASHES))
        mid = c.index[first <= c.index][len(c.index[first <= c.index]) // 2]
        for name, sig in rules(c).items():
            r = (c.pct_change() if sig is None else book(o, c, rf, sig)).loc[first:].dropna()
            s, a, b = stats(r, rf), stats(r.loc[:mid], rf), stats(r.loc[mid:], rf)
            yr = (1 + r).groupby(r.index.year).prod() - 1
            sig_in = pd.Series(True, index=c.index) if sig is None else sig
            t_in = sig_in.loc[first:].mean()
            sw = sig_in.loc[first:].astype(int).diff().abs().sum() / (len(r) / 252)
            emit(f"| {name} | {s['CAGR']:.1%} | {s['vol']:.0%} | {s['Sharpe']:.2f} | {s['maxdd']:.0%} | "
                 f"{a['Sharpe']:.2f} | {b['Sharpe']:.2f} | {t_in:.0%} | {sw:.1f} | "
                 + " | ".join(f"{yr.get(y, np.nan):+.0%}" for y in CRASHES if y >= first.year) + " |")
        emit(f"\n(halves split at {mid.date()})\n")

    OUT.mkdir(exist_ok=True)
    (OUT / "green_line.md").write_text("\n".join(lines) + "\n")
    print(f"\nwrote {OUT / 'green_line.md'}")


if __name__ == "__main__":
    main()
