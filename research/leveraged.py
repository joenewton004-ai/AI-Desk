"""Trading a leveraged S&P 500 fund (2x SSO / 3x UPRO) on SPY's signals, with strict risk rules.

    python research/leveraged.py      (first run downloads SSO/UPRO prices from Yahoo for the real-fund check)

Every decision is made at SPY's close and fills at the next open (overnight the old position applies,
from the open the new one). The leveraged fund is simulated from SPY's daily returns back to 1993:
L x SPY's return each day (daily reset, like the real funds), minus the fund's fees (0.89% a year for 2x,
0.91% for 3x) and the cost of the borrowed part ((L - 1) x (T-bill rate + 0.3%)). Section 4 checks
the simulation against the real SSO and UPRO prices. Cash earns T-bills; Sharpe is above T-bills;
0.03% per trade (on the amount traded).

Rules (fixed before running):
  trend      hold the fund only while SPY's close is above its 200-day average (enter above +1%,
             leave below -1%, to cut whipsaws); else T-bills
  vol cap    leverage = min(L, 25% / SPY's 20-day volatility): less leverage when markets are jumpy
             (resized only when it moves by 0.25x or more)
  VIX        go to T-bills while the VIX closes above 30
  stop       if the position is down 10% from its entry value, sell, and stay out until SPY makes a new
             20-day closing high while above its 200-day average
  strict     all four together
Walk-forward: each January pick the average length (100/150/200/250 days) and band (0/1/2%) with the
best Sharpe over the previous 10 years, and use it for that year only.
Writes research/output/leveraged.md; findings in research/LEVERAGED.md.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ai_desk.data import load_cash_rate  # noqa: E402
from ai_desk.fundamentals.yahoo import with_retry  # noqa: E402

CACHE = ROOT / "data" / "backtest"
OUT = Path(__file__).resolve().parent / "output"
START, END, MID = "1994-01-03", "2026-10-20", "2010-01-01"
FEES = {1: 0.0009, 2: 0.0089, 3: 0.0091}      # SPY 0.09%; SSO 0.89%; UPRO 0.91%
SPREAD = 0.003                                # financing over T-bills on the borrowed part
COST = 0.0003


# --- pure pieces (unit-tested) --------------------------------------------------------

def trend_signal(close: pd.Series, n: int = 200, band: float = 0.01) -> pd.Series:
    """1 while in an uptrend, with hysteresis: enter above (1+band) x average, leave below (1-band) x average."""
    ma = close.rolling(n, min_periods=n).mean()
    out, state = [], 0
    for c, m in zip(close.to_numpy(), ma.to_numpy()):
        if np.isfinite(m):
            if state == 0 and c > m * (1 + band):
                state = 1
            elif state == 1 and c < m * (1 - band):
                state = 0
        out.append(state)
    return pd.Series(out, index=close.index, dtype=float)


def vol_cap(close: pd.Series, lev: float, target: float = 0.25, n: int = 20) -> pd.Series:
    vol = close.pct_change().rolling(n, min_periods=n).std() * np.sqrt(252)
    return (target / vol).clip(upper=lev).fillna(lev)


def simulate(o: pd.Series, c: pd.Series, target_lev: pd.Series, rf_d: pd.Series, lev_cap: float,
             cost: float = COST, stop: float | None = None, reentry: pd.Series | None = None,
             min_step: float = 0.25) -> tuple[pd.Series, pd.Series]:
    """Daily equity for a position in an L-times fund, L = target_lev decided at each close, filled at the next open.
    The fund's daily return = L x SPY's return - fees - financing; split into overnight and daytime legs.
    stop: exit when the position's value is down `stop` from its entry, then wait for `reentry` (a bool series).
    min_step: leverage changes smaller than this (e.g. 0.25x) are skipped, so the vol cap doesn't trade every day."""
    fee = FEES[int(round(lev_cap))] if lev_cap in FEES else FEES[3]
    ov, dy = (o / c.shift(1) - 1).to_numpy(), (c / o - 1).to_numpy()
    tl = target_lev.to_numpy()
    rf = rf_d.to_numpy()
    re = reentry.to_numpy() if reentry is not None else None
    eq, w, pending = 1.0, 0.0, 0.0
    entry_val, stopped = None, False
    eq_out, w_out = [], []
    for i in range(len(c)):
        if i > 0:
            drag = (fee + max(w - 1, 0) * (rf[i - 1] * 252 + SPREAD)) / 252 if w > 0 else 0.0
            eq *= 1 + (1 - min(w, 1)) * rf[i - 1] * (w < 1)      # interest on any cash not in the fund
            eq *= 1 + w * ov[i] - drag / 2
            small = pending > 0 and w > 0 and abs(pending - w) < min_step     # skip tiny resizes; entries/exits always trade
            if pending != w and not small:
                eq -= abs(pending - w) * eq * cost
                if w == 0 and pending > 0:
                    entry_val = eq
                w = pending
                if w == 0:
                    entry_val = None
            eq *= 1 + w * dy[i] - (drag / 2 if w > 0 else 0)
        eq_out.append(eq)
        w_out.append(w)
        # decide tomorrow at today's close
        want = float(np.nan_to_num(tl[i]))
        if stop is not None:
            if w > 0 and entry_val is not None and eq / entry_val - 1 <= -stop:
                stopped = True
            if stopped:
                if re is not None and re[i]:
                    stopped = False
                else:
                    want = 0.0
        pending = want
    return pd.Series(eq_out, index=c.index), pd.Series(w_out, index=c.index)


def stats(eq: pd.Series, rf_d: pd.Series, w: pd.Series | None = None) -> dict:
    r = eq.pct_change().dropna()
    ex = r - rf_d.reindex(r.index).fillna(0)
    yr = eq.resample("YE").last().pct_change().dropna()
    out = {"CAGR": (eq.iloc[-1] / eq.iloc[0]) ** (252 / len(r)) - 1, "vol": r.std() * np.sqrt(252),
           "Sharpe": ex.mean() / ex.std() * np.sqrt(252) if ex.std() > 0 else np.nan,
           "dd": (eq / eq.cummax() - 1).min(), "worst_year": yr.min() if len(yr) else np.nan}
    if w is not None:
        out["invested"] = (w > 0).mean()
        out["avg_lev"] = w[w > 0].mean() if (w > 0).any() else 0.0
        out["trades_yr"] = (w.diff().abs() > 1e-9).sum() / (len(w) / 252)
    return out


# --- the experiment ------------------------------------------------------------------

def real_funds() -> pd.DataFrame:
    path = CACHE / "letf_prices.pkl"
    if path.exists():
        return pd.read_pickle(path)
    import yfinance as yf
    d = with_retry(lambda: yf.download(["SPY", "SSO", "UPRO"], start="2009-06-01", auto_adjust=True, progress=False))
    px = d["Close"]
    px.index = pd.to_datetime(px.index).tz_localize(None)
    CACHE.mkdir(parents=True, exist_ok=True)
    px.to_pickle(path)
    return px


def main() -> None:
    lines: list[str] = []

    def emit(t=""):
        print(t, flush=True)
        lines.append(t)

    spy = pd.read_csv(ROOT / "market_data" / "SPY.csv", index_col=0, parse_dates=True).loc[:END]
    vix = pd.read_csv(ROOT / "market_data" / "VIX.csv", index_col=0, parse_dates=True)["close"]
    o, c = spy["open"], spy["close"]
    rate = load_cash_rate(str(ROOT / "market_data" / "SPY.csv")).reindex(c.index).ffill().fillna(0)
    rf_d = rate / 252
    sl = slice(START, END)
    vix_ok = (vix.reindex(c.index).ffill() <= 30).astype(float).fillna(1.0)
    trend = trend_signal(c)
    reentry = (c >= c.rolling(20).max()) & (c > c.rolling(200).mean())

    def run(lev, trend_on=True, vc=False, vx=False, stp=False, sig=None):
        t = pd.Series(float(lev), index=c.index)
        if trend_on:
            t = t * (sig if sig is not None else trend)
        if vc:
            t = np.minimum(t, vol_cap(c, lev) * (t > 0))
        if vx:
            t = t * vix_ok
        eq, w = simulate(o, c, t, rf_d, lev, stop=0.10 if stp else None, reentry=reentry if stp else None)
        return eq.loc[sl] / eq.loc[sl].iloc[0], w.loc[sl]

    rows = {
        "SPY buy and hold": run(1, trend_on=False),
        "2x buy and hold (SSO-like)": run(2, trend_on=False),
        "3x buy and hold (UPRO-like)": run(3, trend_on=False),
        "SPY above its 200-day (1x, the desk's old idea)": run(1),
        "2x, trend only": run(2),
        "3x, trend only": run(3),
        "3x, trend + vol cap": run(3, vc=True),
        "3x, trend + VIX filter": run(3, vx=True),
        "3x, trend + 10% stop": run(3, stp=True),
        "2x strict (trend + vol cap + VIX + stop)": run(2, vc=True, vx=True, stp=True),
        "3x strict (trend + vol cap + VIX + stop)": run(3, vc=True, vx=True, stp=True),
    }
    rfs = rf_d.loc[sl]
    emit("# Leveraged S&P 500 fund on SPY signals - generated tables\n")
    emit(f"Daily, {c.loc[sl].index[0].date()} to {c.loc[sl].index[-1].date()}. Signals at SPY's close, fills at the next "
         "open. Simulated funds: L x SPY daily, minus fees (0.89-0.91%/yr) and financing (T-bills + 0.3% on the borrowed "
         "part). 0.03% per trade. Sharpe above T-bills.\n")
    emit("## 1. Results\n")
    emit("| | return/yr | volatility | Sharpe | worst drop | worst year | 1994-2009 | 2010-2026 | in the market | avg leverage | trades/yr |")
    emit("|---|---|---|---|---|---|---|---|---|---|---|")
    for k, (eq, w) in rows.items():
        s, a, b = stats(eq, rfs, w), stats(eq.loc[:MID], rfs), stats(eq.loc[MID:], rfs)
        emit(f"| {k} | {s['CAGR']:.1%} | {s['vol']:.0%} | {s['Sharpe']:.2f} | {s['dd']:.0%} | {s['worst_year']:+.0%} | "
             f"{a['CAGR']:.1%} ({a['Sharpe']:.2f}) | {b['CAGR']:.1%} ({b['Sharpe']:.2f}) | {s['invested']:.0%} | "
             f"{s['avg_lev']:.1f}x | {s['trades_yr']:.1f} |")

    emit("\n## 2. The crashes\n")
    eps = {"2000-02 dot-com": ("2000-03-24", "2002-10-09"), "2008 crisis": ("2007-10-09", "2009-03-09"),
           "2020 Covid": ("2020-02-19", "2020-03-23"), "2022 bear": ("2022-01-03", "2022-10-12"),
           "2025 tariff drop": ("2025-02-19", "2025-04-08")}
    keys = ["SPY buy and hold", "3x buy and hold (UPRO-like)", "3x, trend only", "3x strict (trend + vol cap + VIX + stop)",
            "2x strict (trend + vol cap + VIX + stop)"]
    emit("| episode | " + " | ".join(keys) + " |\n|" + "---|" * (len(keys) + 1))
    for name, (a, b) in eps.items():
        cells = []
        for k in keys:
            e = rows[k][0]
            seg = e.loc[a:b]
            cells.append(f"{seg.iloc[-1] / seg.iloc[0] - 1:+.0%}" if len(seg) > 1 else "")
        emit(f"| {name} | " + " | ".join(cells) + " |")

    emit("\n## 3. Walk-forward: each January choose the average length and band on the past 10 years\n")
    choices = [(n, bd) for n in (100, 150, 200, 250) for bd in (0.0, 0.01, 0.02)]
    sig_cache = {ch: trend_signal(c, *ch) for ch in choices}
    full = {ch: simulate(o, c, 3.0 * sig_cache[ch], rf_d, 3)[0] for ch in choices}
    rets = {ch: e.pct_change() for ch, e in full.items()}
    stitched, picked = [], []
    for y in range(2004, 2027):
        past = slice(f"{y - 10}-01-01", f"{y - 1}-12-31")
        best = max(choices, key=lambda ch: ((rets[ch].loc[past] - rf_d.loc[past]).mean() /
                                            (rets[ch].loc[past] - rf_d.loc[past]).std()))
        picked.append(f"{y}: {best[0]}d/{best[1]:.0%}")
        stitched.append(rets[best].loc[f"{y}-01-01":f"{y}-12-31"])
    oos = pd.concat(stitched).dropna()
    eq_oos = (1 + oos).cumprod()
    fixed = full[(200, 0.01)].loc[eq_oos.index[0]:]
    emit("| 3x trend | return/yr | Sharpe | worst drop |\n|---|---|---|---|")
    for name, e in (("Walk-forward choice (out of sample)", eq_oos), ("Fixed 200-day, 1% band (same years)", fixed / fixed.iloc[0])):
        s = stats(e, rf_d)
        emit(f"| {name} | {s['CAGR']:.1%} | {s['Sharpe']:.2f} | {s['dd']:.0%} |")
    emit("\nChosen: " + "; ".join(picked))

    emit("\n## 4. Does the simulation match the real funds?\n")
    try:
        real = real_funds()
        span = real.dropna().index
        emit(f"Buy and hold, {span[0].date()} to {span[-1].date()} (real prices include fees and financing):\n")
        emit("| fund | real return/yr | simulated | real worst drop | simulated |\n|---|---|---|---|---|")
        for sym, lev in (("SSO", 2), ("UPRO", 3)):
            r = real[sym].loc[span[0]:span[-1]].dropna()
            sim, _ = simulate(o, c, pd.Series(float(lev), index=c.index), rf_d, lev, cost=0.0)
            sim = sim.loc[r.index[0]:r.index[-1]]
            yrs = len(r) / 252
            emit(f"| {sym} ({lev}x) | {(r.iloc[-1] / r.iloc[0]) ** (1 / yrs) - 1:.1%} | "
                 f"{(sim.iloc[-1] / sim.iloc[0]) ** (1 / yrs) - 1:.1%} | {(r / r.cummax() - 1).min():.0%} | "
                 f"{(sim / sim.cummax() - 1).min():.0%} |")
    except Exception as e:  # noqa: BLE001 - the check is optional
        emit(f"(real-fund check skipped: {e})")

    OUT.mkdir(exist_ok=True)
    (OUT / "leveraged.md").write_text("\n".join(lines) + "\n")
    print(f"\nwrote {OUT / 'leveraged.md'}")


if __name__ == "__main__":
    main()
