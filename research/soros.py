"""George Soros-style global macro, made testable: trend-following across stock, bond and gold markets.

    python research/soros.py

Soros's Quantum Fund made large, leveraged, discretionary bets on currencies, bonds and stock markets, riding
self-reinforcing booms and busts ("reflexivity") and cutting them when the trend turned. His individual trades and
judgement can't be backtested. The rule-based core of that style - follow each market's trend, long or short, across
asset classes - can, on the ETFs in market_data/: SPY, QQQ, IWM, DIA (US stocks), EFA, EEM (international stocks),
TLT, IEF (Treasuries), GLD (gold).
  A. trend, long only: each month hold every market whose 12-month return beat T-bills (1/9 each; the rest in T-bills)
  B. trend, long/short: the same, plus short the markets that lagged T-bills (as a macro fund would)
  C. B, each market sized to 10% yearly volatility (the usual trend-following set-up), capped at 2x per market
  D. concentration, like a macro fund's big bets: the 3 strongest markets by 12-month return, long only
  E. A, with a faster 3-month trend
Benchmarks: SPY, 60/40 SPY/IEF, all 9 equally. Monthly, decided at each month-end close, held the next month;
0.05% per unit traded; cash and margin at T-bills (shorts earn them). Writes research/output/soros.md;
findings in research/SOROS.md.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ai_desk.data import load_cash_rate  # noqa: E402

OUT = Path(__file__).resolve().parent / "output"
ETFS = ["SPY", "QQQ", "IWM", "DIA", "EFA", "EEM", "TLT", "IEF", "GLD"]
COST = 0.0005
START, END = "2006-01-31", "2026-09-30"


# --- pure pieces (unit-tested) --------------------------------------------------------

def trend_weights(px_m: pd.DataFrame, rf_m: pd.Series, look: int = 12, short: bool = False,
                  vol: pd.DataFrame | None = None, target: float = 0.10, cap: float = 2.0) -> pd.DataFrame:
    """Weights decided at each month-end from data up to it: +1/n where the past `look`-month return beat T-bills,
    -1/n (if short) where it didn't. With `vol`, each market is scaled to `target` yearly volatility (max `cap`x)."""
    past = px_m / px_m.shift(look) - 1
    cash = (1 + rf_m).rolling(look).apply(np.prod, raw=True) - 1
    sig = np.sign(past.sub(cash, axis=0))
    if not short:
        sig = sig.clip(lower=0)
    w = sig / px_m.shape[1]
    if vol is not None:
        w = w * (target / vol).clip(upper=cap)
    return w.where(past.notna())


def top_n(px_m: pd.DataFrame, n: int = 3, look: int = 12) -> pd.DataFrame:
    past = px_m / px_m.shift(look) - 1
    rank = past.rank(axis=1, ascending=False)
    return (rank <= n).astype(float).div(n).where(past.notna())


def book(w: pd.DataFrame, r_m: pd.DataFrame, rf_m: pd.Series, cost: float = COST) -> pd.Series:
    """Next month's return of weights set at this month-end; unused money (and short proceeds) earn T-bills."""
    w = w.fillna(0.0)
    held = w.shift(1).fillna(0.0)
    turnover = (w - w.shift(1).fillna(0.0)).abs().sum(axis=1).shift(1).fillna(0.0)
    cash_w = 1 - held.clip(lower=0).sum(axis=1)                      # shorts don't use cash; their proceeds earn rf
    return (held * r_m).sum(axis=1) + cash_w * rf_m + held.clip(upper=0).abs().sum(axis=1) * rf_m - turnover * cost


def stats(r: pd.Series, rf: pd.Series) -> dict:
    eq = (1 + r).cumprod()
    ex = r - rf.reindex(r.index).fillna(0)
    return {"CAGR": eq.iloc[-1] ** (12 / len(r)) - 1, "vol": r.std() * np.sqrt(12),
            "Sharpe": ex.mean() / ex.std() * np.sqrt(12), "maxdd": (eq / eq.cummax() - 1).min()}


def main() -> None:
    lines: list[str] = []

    def emit(t=""):
        print(t, flush=True)
        lines.append(t)

    px = pd.concat({s: pd.read_csv(ROOT / "market_data" / f"{s}.csv", index_col=0, parse_dates=True)["close"]
                    for s in ETFS}, axis=1).loc[:END]
    px_m = px.resample("ME").last()
    r_m = px_m.pct_change()
    rf_m = (load_cash_rate(str(ROOT / "market_data" / "SPY.csv")).resample("ME").last() / 12).reindex(px_m.index).ffill().fillna(0)
    vol = px.pct_change().rolling(63, min_periods=40).std().resample("ME").last() * np.sqrt(252)
    books = {
        "A. Trend, long only (12 months)": book(trend_weights(px_m, rf_m), r_m, rf_m),
        "B. Trend, long and short": book(trend_weights(px_m, rf_m, short=True), r_m, rf_m),
        "C. B, sized to 10% volatility each": book(trend_weights(px_m, rf_m, short=True, vol=vol), r_m, rf_m),
        "D. The 3 strongest markets (concentrated)": book(top_n(px_m), r_m, rf_m),
        "E. Trend, long only (3 months)": book(trend_weights(px_m, rf_m, look=3), r_m, rf_m),
        "SPY": r_m["SPY"],
        "60/40 SPY/IEF (monthly rebalanced)": 0.6 * r_m["SPY"] + 0.4 * r_m["IEF"] - 0,
        "All 9 markets, equal weight": r_m.mean(axis=1),
    }
    idx = r_m.loc[START:END].index
    rf = rf_m.reindex(idx)
    mid = "2015-12-31"
    emit("# Soros-style macro trend - generated tables\n")
    emit(f"Monthly, {idx[0]:%Y-%m} to {idx[-1]:%Y-%m}; SPY, QQQ, IWM, DIA, EFA, EEM, TLT, IEF, GLD; 0.05% per unit "
         "traded; T-bills on cash. Sharpe above T-bills.\n")
    emit("| | return/yr | volatility | Sharpe | worst drop | 2006-15 Sharpe | 2016-26 Sharpe | 2008 | 2022 | corr. with SPY |")
    emit("|---|---|---|---|---|---|---|---|---|---|")
    for k, r in books.items():
        r = r.reindex(idx)
        s, a, b = stats(r, rf), stats(r.loc[:mid], rf), stats(r.loc[mid:], rf)
        y = (1 + r).groupby(idx.year).prod() - 1
        emit(f"| {k} | {s['CAGR']:.1%} | {s['vol']:.0%} | {s['Sharpe']:.2f} | {s['maxdd']:.0%} | {a['Sharpe']:.2f} | "
             f"{b['Sharpe']:.2f} | {y.get(2008, np.nan):+.0%} | {y.get(2022, np.nan):+.0%} | {r.corr(books['SPY'].reindex(idx)):.2f} |")
    emit("\n## As a sleeve next to SPY: 70% SPY + 30% of each\n")
    emit("| mix | return/yr | Sharpe | worst drop |\n|---|---|---|---|")
    for k in ("A. Trend, long only (12 months)", "C. B, sized to 10% volatility each", "60/40 SPY/IEF (monthly rebalanced)"):
        r = (0.7 * books["SPY"] + 0.3 * books[k]).reindex(idx)
        s = stats(r, rf)
        emit(f"| 70% SPY + 30% {k} | {s['CAGR']:.1%} | {s['Sharpe']:.2f} | {s['maxdd']:.0%} |")
    s = stats(books["SPY"].reindex(idx), rf)
    emit(f"| 100% SPY | {s['CAGR']:.1%} | {s['Sharpe']:.2f} | {s['maxdd']:.0%} |")

    OUT.mkdir(exist_ok=True)
    (OUT / "soros.md").write_text("\n".join(lines) + "\n")
    print(f"\nwrote {OUT / 'soros.md'}")


if __name__ == "__main__":
    main()
