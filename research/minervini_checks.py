"""Minervini: what could the fixed-rule test (research/minervini.py) have missed?

    python research/minervini_checks.py

The full-SEPA test bought the morning AFTER a breakout close and sold the morning after a close below the stop.
Minervini buys AT the pivot with a buy-stop order during the day and sells with a stop order during the day. He
also concentrates in a few names and trades smaller, younger companies than the 750 largest. Checked here, on
the full-SEPA book (Trend Template + RS 70 + EPS 25% / sales 20% growth + tight base):
  1. intraday fills: buy at max(open, pivot) the day the high crosses the pivot (the highest close of the last
     20 days); setup and growth known at the previous close; a 7.5% stop order fills at min(open, stop) the day
     the low reaches it. No same-day volume check (it isn't known until the close), or - variant - sold the next
     open if the breakout day's volume was under 1.5x average (his "failed breakout" rule)
  2. concentration: 5 positions of 20%, as he describes
  3. smaller companies: only the less-traded half of the universe each day (50-day dollar volume)
  4. looser growth: EPS 20%+ only, no sales rule - more candidates, more of the time invested
Same universe (750 largest, survivors-only prices), costs (0.10% each way), T-bills on cash. Writes
research/output/minervini_checks.md; findings in research/MINERVINI.md.
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

import minervini as mv  # noqa: E402
import swing  # noqa: E402
from ai_desk.data import load_cash_rate  # noqa: E402

CACHE, OUT = mv.CACHE, mv.OUT


def simulate_intraday(o, h, lo, c, setup_prev, pivot, surge, rank, ma50, rf, dates, symbols, slots: int = 10,
                      stop: float = 0.075, breakeven_at: float = 0.15, vol_check: bool = False,
                      cost: float = mv.COST, start: int = 0) -> tuple[pd.Series, pd.DataFrame]:
    """Buy-stop entries and stop-order exits inside the day.
    setup_prev[i, j]: the stock qualified at close i-1 (base, trend, growth all known then).
    pivot[i, j]: the buy point for day i, from closes up to i-1. Entry when high[i] >= pivot[i]."""
    cash, pos = 1.0, {}
    exits_due = {}
    eq_out, trades = [], []

    def close_pos(j, px, i, why):
        nonlocal cash
        p = pos.pop(j)
        cash += p["shares"] * px * (1 - cost)
        trades.append({"symbol": symbols[j], "entry_date": p["entry_date"], "exit_date": dates[i],
                       "return": px / p["entry"] * (1 - cost) ** 2 - 1, "days": i - p["entry_i"], "why": why})

    for i in range(max(start, 1), len(dates)):
        for j, why in list(exits_due.items()):           # decided at yesterday's close: the open
            if j in pos:
                close_pos(j, o[i, j] if np.isfinite(o[i, j]) else c[i - 1, j], i, why)
        exits_due = {}
        for j in list(pos):                               # stop orders resting in the market
            p = pos[j]
            if np.isfinite(lo[i, j]) and lo[i, j] <= p["floor"]:
                close_pos(j, min(o[i, j], p["floor"]) if np.isfinite(o[i, j]) else p["floor"], i,
                          "break-even stop" if p["even"] else "stop")
        # buy-stops at the pivot for stocks that qualified at yesterday's close, best RS first
        if len(pos) < slots:
            equity = cash + sum(p["shares"] * c[i - 1, j] for j, p in pos.items() if np.isfinite(c[i - 1, j]))
            cand = [j for j in np.flatnonzero(setup_prev[i]) if j not in pos and np.isfinite(pivot[i, j])
                    and np.isfinite(h[i, j]) and h[i, j] >= pivot[i, j] and np.isfinite(o[i, j])]
            cand.sort(key=lambda j: -rank[i - 1, j])
            for j in cand:
                if len(pos) >= slots:
                    break
                spend = min(equity / slots, cash)
                if spend <= equity / slots * 0.2:
                    break
                px = max(o[i, j], pivot[i, j])
                pos[j] = {"shares": spend * (1 - cost) / px, "entry": px, "entry_i": i, "entry_date": dates[i],
                          "floor": px * (1 - stop), "even": False, "new": True}
                cash -= spend
        cash *= 1 + rf[i]
        eq_out.append(cash + sum(p["shares"] * (c[i, j] if np.isfinite(c[i, j]) else p["entry"]) for j, p in pos.items()))
        for j, p in pos.items():                          # decisions at the close, for tomorrow's open
            px = c[i, j]
            if not np.isfinite(px):
                continue
            if p.pop("new", False):
                if px <= p["floor"]:
                    exits_due[j] = "stop"
                elif vol_check and not surge[i, j] >= 1.5:
                    exits_due[j] = "failed breakout (light volume)"
                continue
            if not p["even"] and px >= p["entry"] * (1 + breakeven_at):
                p["even"], p["floor"] = True, max(p["floor"], p["entry"])
            if p["even"] and np.isfinite(ma50[i, j]) and px < ma50[i, j]:
                exits_due[j] = "below 50-day"
    return pd.Series(eq_out, index=dates[max(start, 1):]), pd.DataFrame(trades)


def main() -> None:
    lines: list[str] = []

    def emit(t=""):
        print(t, flush=True)
        lines.append(t)

    u = pickle.loads((CACHE / "universe.pkl").read_bytes())
    d = swing.fetch_daily(swing.universe_tickers())
    o, h, lo, c, v = (d[k].astype(float).loc[:mv.END] for k in ("open", "high", "low", "close", "volume"))
    snaps = {}
    for m in (3, 6, 9, 12):
        snaps.update({k: list(s.index) for k, s in pickle.loads((CACHE / f"snapshots_m{m}.pkl").read_bytes()).items()})
    dates, symbols = c.index, list(c.columns)
    member = swing.membership(dict(sorted(snaps.items())), dates, symbols)
    rf = (load_cash_rate(str(ROOT / "market_data" / "SPY.csv")).reindex(dates, method="ffill") / 252).shift(1).fillna(0)
    R = rf.to_numpy()
    start = int(dates.searchsorted(pd.Timestamp(mv.START)))
    O, H, L, C = (x.to_numpy(dtype=float) for x in (o, h, lo, c))

    print("signals...", flush=True)
    dollar = (c * v).rolling(50, min_periods=40).mean()
    liquid = ((c > 10) & (dollar > 20e6)).to_numpy()
    rs = mv.rs_rating(c, member)
    tmpl_rs = mv.trend_template(c, h, lo).to_numpy() & liquid & member & (rs >= 70)
    fund = mv.fundamentals(u)
    grow = mv.growth_on_days(fund, dates, symbols)
    grow_eps = mv.growth_on_days(fund, dates, symbols, min_sales=-np.inf, min_eps=0.20)
    sig = swing.signals(o, h, lo, c, v)
    base_close = sig["setup"].to_numpy() & member                      # breakout confirmed at the close
    ma50 = sig["ma50"].to_numpy(dtype=float)
    surge = np.nan_to_num(sig["surge"].to_numpy(dtype=float))
    # the base as of each close, without today's breakout (for buy-stops tomorrow)
    rng10 = (h.rolling(10).max() - lo.rolling(10).min()) / c
    rng_prior = (h.shift(10).rolling(50).max() - lo.shift(10).rolling(50).min()) / c.shift(10)
    quiet = v.rolling(10).mean() < v.rolling(50, min_periods=40).mean()
    tight = ((rng10 < 0.5 * rng_prior) & quiet).to_numpy()
    pivot_next = c.rolling(20).max().shift(1).to_numpy(dtype=float)  # day i's buy point: max close of i-20..i-1
    rank_dv = dollar.where(pd.DataFrame(member, index=dates, columns=symbols)).rank(axis=1, pct=True).to_numpy()
    small = np.nan_to_num(rank_dv, nan=1.0) <= 0.5

    def shift1(a):
        out = np.zeros_like(a)
        out[1:] = a[:-1]
        return out

    def close_fill(buy, slots=10):
        return mv.simulate(O, C, buy, None, rs, ma50, R, dates, symbols, start=start, slots=slots)

    def intraday(qual, slots=10, vol_check=False):
        return simulate_intraday(O, H, L, C, shift1(qual), pivot_next, surge, rs, ma50, R, dates, symbols,
                                 slots=slots, vol_check=vol_check, start=start)

    sepa = tmpl_rs & grow
    books = {
        "Full SEPA as tested (next-open fills)": close_fill(sepa & base_close),
        "1. Buy at the pivot, stop orders in the day": intraday(sepa & tight),
        "1b. + sold next open if breakout volume < 1.5x": intraday(sepa & tight, vol_check=True),
        "2. 1 with 5 positions of 20%": intraday(sepa & tight, slots=5),
        "3. 1 on the less-traded half of the universe": intraday(sepa & tight & small),
        "4. 1 with looser growth (EPS 20%+, no sales rule)": intraday(tmpl_rs & grow_eps & tight),
        "4b. 4 with 5 positions": intraday(tmpl_rs & grow_eps & tight, slots=5),
    }
    uni_r = pd.Series(np.nanmean(np.where(member[start + 1:], C[start + 1:] / C[start:-1] - 1, np.nan), axis=1),
                      index=dates[start + 1:]).clip(-0.5, 0.5)
    uni = pd.concat([pd.Series([1.0], index=[dates[start]]), (1 + uni_r).cumprod()])
    spy = pd.read_csv(ROOT / "market_data" / "SPY.csv", index_col=0, parse_dates=True)["close"].reindex(dates).ffill()
    spy_eq = spy.iloc[start:] / spy.iloc[start]

    emit("# Minervini: what the fixed-rule test could have missed - generated tables\n")
    emit(f"Daily, {dates[start].date()} to {dates[-1].date()}; the 750 largest US companies (point-in-time), "
         "**survivors-only prices**; 0.10% per trade each way; T-bills on cash; Sharpe above T-bills.\n")
    emit("| | return/yr | Sharpe | worst drop | 2014-19 | 2020-26 | trades | win rate | avg win | avg loss | "
         "invested | without 2024 |")
    emit("|---|---|---|---|---|---|---|---|---|---|---|---|")

    def no24(eq):
        r = eq.pct_change().dropna()
        r = r[r.index.year != 2024]
        return (1 + r).prod() ** (252 / len(r)) - 1

    def row(name, eq, t=None, slots=10):
        s, a, b = swing.stats(eq, rf), swing.stats(eq.loc[:mv.MID], rf), swing.stats(eq.loc[mv.MID:], rf)
        if t is not None and len(t):
            ts = swing.trade_stats(t)
            inv = t["days"].sum() / (slots * (len(dates) - start))
            extra = f"{len(t)} | {ts['win rate']:.0%} | {ts['avg win']:+.1%} | {ts['avg loss']:+.1%} | {inv:.0%}"
        else:
            extra = " | | | | 100%"
        emit(f"| {name} | {s['CAGR']:.1%} | {s['Sharpe']:.2f} | {s['max drawdown']:.0%} | {a['Sharpe']:.2f} | "
             f"{b['Sharpe']:.2f} | {extra} | {no24(eq):.1%} |")

    for k, (eq, t) in books.items():
        row(k, eq, t, slots=5 if "5 positions" in k else 10)
    row("Equal-weight universe", uni)
    row("SPY", spy_eq)

    emit("\n## How the pivot-entry trades (1) ended\n")
    t1 = books["1. Buy at the pivot, stop orders in the day"][1]
    emit("| exit | trades | avg return |\n|---|---|---|")
    for why, g in t1.groupby("why"):
        emit(f"| {why} | {len(g)} | {g['return'].mean():+.1%} |")
    emit("\n## Year by year\n")
    names = list(books)
    emit("| year | " + " | ".join(n.split(" ")[0].rstrip(".") if n[0].isdigit() else "tested" for n in names)
         + " | equal-weight | SPY |")
    emit("|---" * (len(names) + 3) + "|")
    yr = lambda eq: eq.resample("YE").last().pct_change().fillna(eq.resample("YE").last().iloc[0] / eq.iloc[0] - 1)  # noqa: E731
    ys = [yr(books[n][0]) for n in names] + [yr(uni), yr(spy_eq)]
    for y in ys[0].index:
        emit(f"| {y.year} | " + " | ".join(f"{s.get(y, np.nan):+.0%}" for s in ys) + " |")

    OUT.mkdir(exist_ok=True)
    (OUT / "minervini_checks.md").write_text("\n".join(lines) + "\n")
    print(f"\nwrote {OUT / 'minervini_checks.md'}")


if __name__ == "__main__":
    main()
