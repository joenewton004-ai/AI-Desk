"""Drawdown circuit breaker on the whole desk: does stopping after losses help?

    python research/circuit_breaker.py

The rule comes from the `drawdown-circuit-breaker` skill in tradermonty/claude-trading-skills:
after the account loses too much, take no new risk until a set release date. Its defaults:
  daily loss    2% of the account -> halted until the next weekday
  weekly loss   5%                -> halted until next Monday
  monthly loss  8%                -> halted until the first day of next month
Tested here on the desk (50% quality screen + 20% plain momentum + 30% SPY with its 12-month
switch), weekly, 2014-2026. Two ways to "halt":
  freeze   no new buys or increases while halted; sells and exits still happen (the skill's version)
  cash     sell everything to T-bills while halted, buy back at release

Part 1 is weekly (the weekly and monthly limits, on the research's weekly history). Part 2 repeats
it on daily prices (data/backtest/daily_ohlcv.pkl, from research/swing.py), which adds the 2% daily
limit. The halt is decided at a period's close and applies from the next period (no lookahead). Each sleeve is held at constant target weights between its re-picks (as if rebalanced
for free) - the same simplification as the daily portfolio engine. 0.10% per unit of turnover,
cash at T-bills, Sharpe above T-bills. Survivors-only prices flatter every row equally.
Writes research/output/circuit_breaker.md; findings in research/CIRCUIT_BREAKER.md.
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

import weekly  # noqa: E402
from ai_desk.data import load_cash_rate  # noqa: E402
from ai_desk.fundamentals import screen_backtest as sb  # noqa: E402

CACHE = ROOT / "data" / "backtest"
OUT = Path(__file__).resolve().parent / "output"
COST = 0.001


# --- pure pieces (unit-tested) --------------------------------------------------------

def run_breaker(targets: list[dict[str, float]], ret: pd.DataFrame, rf: pd.Series, week_limit: float | None = 0.05,
                month_limit: float | None = 0.08, day_limit: float | None = None, mode: str = "freeze",
                cost: float = COST) -> tuple[pd.Series, pd.Series]:
    """targets[i]: the desk's weights decided at the close of ret.index[i], earned over period i+1
    (a week, or a day for the daily test). `rf` is the cash return per period.
    Returns (returns per period, halted flag per period). The halt is decided from returns up to
    period i's close and changes the weights held over period i+1.
    day_limit: one period's loss (daily data only) -> halted for the next period.
    week_limit / month_limit: loss since the start of the calendar week / month -> halted until
    the next Monday / the first day of next month."""
    dates = ret.index
    held: dict[str, float] = {}
    out, halted_log = {}, {}
    halted_until = None                # halted while date < halted_until
    eq, week_eq, month_eq, cur_week, cur_month = 1.0, 1.0, 1.0, None, None
    for i in range(len(dates) - 1):
        d, nxt = dates[i], dates[i + 1]
        halted = halted_until is not None and d < halted_until
        tgt = targets[i]
        if not halted:
            w = dict(tgt)
        elif mode == "cash":
            w = {}
        else:                          # freeze: may only shrink or keep what's held, never add
            w = {s: min(x, held.get(s, 0.0)) for s, x in tgt.items() if held.get(s, 0.0) > 0}
        turnover = sum(abs(w.get(s, 0.0) - held.get(s, 0.0)) for s in set(w) | set(held))
        r = ret.loc[nxt]
        port = sum(x * (0.0 if pd.isna(r.get(s)) else float(r.get(s))) for s, x in w.items())
        cash = 1 - sum(w.values())
        p_r = port + cash * float(rf.get(nxt, 0.0)) - turnover * cost
        out[nxt], halted_log[nxt] = p_r, halted
        held = w
        # update the breaker with the period just finished (known at nxt's close)
        wk = nxt - pd.Timedelta(days=nxt.weekday())
        if cur_week != wk:
            cur_week, week_eq = wk, eq
        if cur_month != (nxt.year, nxt.month):
            cur_month, month_eq = (nxt.year, nxt.month), eq
        eq *= 1 + p_r
        if halted_until is not None and nxt >= halted_until:
            halted_until = None
        until = []
        if day_limit is not None and p_r <= -day_limit:
            until.append(nxt + pd.Timedelta(days=1))
        if week_limit is not None and eq / week_eq - 1 <= -week_limit:
            until.append(wk + pd.Timedelta(days=7))
        if month_limit is not None and eq / month_eq - 1 <= -month_limit:
            until.append((nxt + pd.offsets.MonthBegin(1)).normalize())
        if until:
            halted_until = max([halted_until or nxt, *until])
    return pd.Series(out), pd.Series(halted_log)


def stats(r: pd.Series, rf_w: pd.Series) -> dict:
    r = r.dropna()
    eq = (1 + r).cumprod()
    ex = r - rf_w.reindex(r.index).fillna(0)
    return {"CAGR": eq.iloc[-1] ** (52 / len(r)) - 1, "volatility": r.std() * np.sqrt(52),
            "Sharpe": ex.mean() / ex.std() * np.sqrt(52), "max drawdown": (eq / eq.cummax() - 1).min()}


# --- the desk's weekly targets -------------------------------------------------------

def desk_targets(px: pd.DataFrame, snaps: dict, f: dict, spy: pd.Series) -> list[dict[str, float]]:
    s_snaps = {}
    for m in (3, 6, 9, 12):
        s_snaps.update(pickle.loads((CACHE / f"snapshots_m{m}.pkl").read_bytes()))
    screen_book = sb.books(dict(sorted(s_snaps.items())), 25)["screen_top"]
    mom_book = weekly.momentum_book(px, snaps, f, lookback=26, n=20, every=4, exit_ma=20)
    spy_m = spy.resample("ME").last()
    spy_on = (spy_m / spy_m.shift(12) - 1 > 0)
    sdates = sorted(screen_book)
    out = []
    for d in f["ret"].index:
        w: dict[str, float] = {}
        known = [k for k in sdates if k <= d]
        if known:
            names = [n for n in screen_book[known[-1]] if n in px.columns and pd.notna(px.at[d, n])]
            for n in names:
                w[n] = w.get(n, 0) + 0.5 / len(names)
        for n, x in mom_book.get(d, {}).items():
            w[n] = w.get(n, 0) + 0.2 * x
        last_me = spy_on.loc[:d]
        if len(last_me) and bool(last_me.iloc[-1]):
            w["SPY"] = w.get("SPY", 0) + 0.3
        out.append(w)
    return out


def main() -> None:
    lines: list[str] = []

    def emit(t=""):
        print(t)
        lines.append(t)

    px, snaps = weekly.load()
    f = weekly.build(px, snaps)
    spy = pd.read_csv(ROOT / "market_data" / "SPY.csv", index_col=0, parse_dates=True)["close"].resample("W-FRI").last()
    dates = f["dates"]
    ret = f["ret"].reindex(dates).copy()
    ret["SPY"] = spy.pct_change().reindex(dates)
    rf = load_cash_rate(str(ROOT / "market_data" / "SPY.csv"))
    rf_w = (rf.resample("W-FRI").last().reindex(dates, method="ffill") / 52).shift(1).fillna(0)
    f["ret"] = ret
    targets = desk_targets(px, snaps, f, spy)

    variants = {
        "Desk as it is (no breaker)": dict(week_limit=None, month_limit=None),
        "Skill defaults, freeze buys (5% week / 8% month)": dict(week_limit=0.05, month_limit=0.08),
        "Skill defaults, go to cash": dict(week_limit=0.05, month_limit=0.08, mode="cash"),
        "Tighter, freeze (3% week / 6% month)": dict(week_limit=0.03, month_limit=0.06),
        "Tighter, go to cash": dict(week_limit=0.03, month_limit=0.06, mode="cash"),
        "Looser, freeze (7% week / 10% month)": dict(week_limit=0.07, month_limit=0.10),
        "Looser, go to cash": dict(week_limit=0.07, month_limit=0.10, mode="cash"),
    }
    res, halts = {}, {}
    for k, kw in variants.items():
        res[k], halts[k] = run_breaker(targets, ret, rf_w, **kw)
    res3 = {k: run_breaker(targets, ret, rf_w, cost=3 * COST, **kw)[0] for k, kw in variants.items()}
    base = res["Desk as it is (no breaker)"]

    emit("# Drawdown circuit breaker on the desk - generated tables\n")
    emit(f"Weekly, {base.index[0].date()} to {base.index[-1].date()}. Desk = 50% quality screen + 20% plain momentum "
         "(100-day exit) + 30% SPY with its 12-month switch. Survivors-only prices. 0.10% per trade (stress 0.30%). "
         "Sharpe above T-bills.\n")
    emit("| | return/yr | volatility | Sharpe | worst drop | at 3x costs | 2014-19 Sharpe | 2020-26 Sharpe | weeks halted | times tripped |")
    emit("|---|---|---|---|---|---|---|---|---|---|")
    for k, r in res.items():
        s, a, b = stats(r, rf_w), stats(r.loc[:weekly.MID], rf_w), stats(r.loc[weekly.MID:], rf_w)
        h = halts[k]
        trips = int((h & ~h.shift(1, fill_value=False)).sum())
        emit(f"| {k} | {s['CAGR']:.1%} | {s['volatility']:.1%} | {s['Sharpe']:.2f} | {s['max drawdown']:.1%} | "
             f"{stats(res3[k], rf_w)['CAGR']:.1%} | {a['Sharpe']:.2f} | {b['Sharpe']:.2f} | {int(h.sum())} | {trips} |")

    emit("\n## When the skill's defaults tripped, and what the desk did over the next 3 months\n")
    h = halts["Skill defaults, freeze buys (5% week / 8% month)"]
    starts = h.index[h & ~h.shift(1, fill_value=False)]
    emit("| halted from | weeks | desk next 13 weeks (no breaker) | with freeze | with cash |\n|---|---|---|---|---|")
    hc = halts["Skill defaults, go to cash"]
    for s0 in starts:
        n = 0
        for v in h.loc[s0:]:
            if not v:
                break
            n += 1
        window = base.loc[s0:].iloc[:13]
        fr = res["Skill defaults, freeze buys (5% week / 8% month)"].reindex(window.index)
        ca = res["Skill defaults, go to cash"].reindex(window.index)
        emit(f"| {s0.date()} | {n} | {(1 + window).prod() - 1:+.1%} | {(1 + fr).prod() - 1:+.1%} | {(1 + ca).prod() - 1:+.1%} |")
    emit(f"\n(The cash version tripped {int((hc & ~hc.shift(1, fill_value=False)).sum())} times; its dates can differ "
         "once its own returns diverge.)")

    emit("\n## Year by year: skill defaults minus the desk as it is\n")
    yb = (1 + base).groupby(base.index.year).prod() - 1
    emit("| year | desk | freeze | cash |\n|---|---|---|---|")
    for y in yb.index:
        fz = res["Skill defaults, freeze buys (5% week / 8% month)"]
        ca = res["Skill defaults, go to cash"]
        yf_ = (1 + fz[fz.index.year == y]).prod() - 1
        yc = (1 + ca[ca.index.year == y]).prod() - 1
        emit(f"| {y} | {yb[y]:+.1%} | {yf_ - yb[y]:+.1%} | {yc - yb[y]:+.1%} |")

    # --- part 2: daily, with the 2% daily limit ---
    daily_path = CACHE / "daily_ohlcv.pkl"
    if daily_path.exists():
        dpx = pickle.loads(daily_path.read_bytes())["close"].astype(float)
        spy_d = pd.read_csv(ROOT / "market_data" / "SPY.csv", index_col=0, parse_dates=True)["close"]
        ddates = dpx.loc[base.index[0]:base.index[-1]].index
        dret = dpx.reindex(ddates).pct_change(fill_method=None).where(lambda r: r.abs() < 1)
        dret["SPY"] = spy_d.reindex(ddates).pct_change()
        rf_d = (rf.reindex(ddates, method="ffill") / 252).shift(1).fillna(0)
        wk_dates = list(f["ret"].index)
        wk_pos = np.searchsorted(np.array(wk_dates, dtype="datetime64[ns]"), np.array(ddates, dtype="datetime64[ns]"),
                                 side="right") - 1
        dtargets = [targets[j] if j >= 0 else {} for j in wk_pos]     # the latest Friday decision on or before each day
        dvariants = {
            "Desk as it is (no breaker)": dict(week_limit=None, month_limit=None),
            "Skill defaults, freeze buys (2% day / 5% week / 8% month)": dict(day_limit=0.02),
            "Skill defaults, go to cash": dict(day_limit=0.02, mode="cash"),
            "Daily limit only (2%), freeze": dict(day_limit=0.02, week_limit=None, month_limit=None),
            "Daily limit only (2%), go to cash": dict(day_limit=0.02, week_limit=None, month_limit=None, mode="cash"),
            "Looser (3% day / 7% week / 10% month), go to cash": dict(day_limit=0.03, week_limit=0.07,
                                                                    month_limit=0.10, mode="cash"),
        }
        emit("\n## Part 2: daily prices, adding the 2% daily limit\n")
        emit("Same desk, same decisions (taken from the latest Friday), but held and checked day by day. "
             "Statistics are annualised from daily returns.\n")
        emit("| | return/yr | volatility | Sharpe | worst drop | days halted | times tripped |\n|---|---|---|---|---|---|---|")
        for k, kw in dvariants.items():
            r, h = run_breaker(dtargets, dret, rf_d, **{"week_limit": 0.05, "month_limit": 0.08, **kw})
            r = r.dropna()
            eqd = (1 + r).cumprod()
            ex = r - rf_d.reindex(r.index).fillna(0)
            cagr = eqd.iloc[-1] ** (252 / len(r)) - 1
            trips = int((h & ~h.shift(1, fill_value=False)).sum())
            emit(f"| {k} | {cagr:.1%} | {r.std() * np.sqrt(252):.1%} | {ex.mean() / ex.std() * np.sqrt(252):.2f} | "
                 f"{(eqd / eqd.cummax() - 1).min():.1%} | {int(h.sum())} | {trips} |")

    OUT.mkdir(exist_ok=True)
    (OUT / "circuit_breaker.md").write_text("\n".join(lines) + "\n")
    print(f"\nwrote {OUT / 'circuit_breaker.md'}")


if __name__ == "__main__":
    main()
