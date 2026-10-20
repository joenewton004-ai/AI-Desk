"""Should the 30% momentum sleeve rotate between major indices instead of SPY only?

    python research/index_rotation.py

Index rotation ("dual momentum"): each month, rank the indices by 12-month
return, hold the best `top` in equal slices, but only those with a positive
12-month return (a failing slot sits in cash at the T-bill rate). Compared with
the live sleeve (SPY with the same 12-month switch) and with buy & hold.

Universe: SPY (S&P 500), QQQ (Nasdaq-100), IWM (Russell 2000), DIA (Dow),
EFA (developed markets ex-US), EEM (emerging markets). History starts when
the last of them launched (EEM, April 2003), so tests run from mid-2004.
Daily prices adjusted for dividends, 3bps costs, next-open fills.
Writes research/output/index_rotation.md; findings in research/INDEX_ROTATION.md.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "research"))

from ai_desk.backtest import CostModel  # noqa: E402
from ai_desk.data import load_cash_rate, load_many  # noqa: E402
from ai_desk.metrics import daily_rf, summarize  # noqa: E402
from ai_desk.portfolio.backtest import buy_and_hold, run_portfolio_backtest  # noqa: E402
from ai_desk.portfolio.methods import IndexMomentum, IndexRotation  # noqa: E402

DATA = ROOT / "market_data"
OUT = Path(__file__).resolve().parent / "output"
END = "2026-10-19"                    # last full trading day
START = "2004-06-01"                  # first month with 12 months of history for every index
ALL6 = ["SPY", "QQQ", "IWM", "DIA", "EFA", "EEM"]
US4 = ["SPY", "QQQ", "IWM", "DIA"]
PERIODS = [("2004-06-01", "2012-12-31"), ("2013-01-01", "2019-12-31"), ("2020-01-01", END)]
lines: list[str] = []


def emit(t: str = "") -> None:
    print(t)
    lines.append(t)


def table(rows: dict[str, dict], cols=("cagr", "volatility", "sharpe", "max_drawdown", "trades")) -> str:
    def cell(c, v):
        if v is None or v != v:
            return "n/a"
        if c == "sharpe":
            return f"{v:.2f}"
        if c == "trades":
            return str(int(v))
        return f"{v:.1%}"
    head = "| | " + " | ".join(cols) + " |\n|---|" + "---|" * len(cols)
    return head + "\n" + "\n".join(f"| {k} | " + " | ".join(cell(c, r.get(c)) for c in cols) + " |"
                                   for k, r in rows.items())


def period_stats(eq: pd.Series, cash, a, b) -> dict:
    e = eq.loc[a:b]
    return summarize(e / e.iloc[0], rf_daily=daily_rf(cash, e.index))


def main() -> None:
    prices = load_many(ALL6, start="1998-01-01", end=END, source=str(DATA))
    cash = load_cash_rate(source=str(DATA / "SPY.csv"))
    run = lambda m, costs=None: run_portfolio_backtest(m, prices, costs=costs, cash_rate=cash, start=START)  # noqa: E731

    variants = {
        "Live sleeve: SPY + 12-month switch": IndexMomentum(symbol="SPY"),
        "Rotation, all 6, top 1": IndexRotation(symbols_=ALL6, top=1),
        "Rotation, all 6, top 2": IndexRotation(symbols_=ALL6, top=2),
        "Rotation, all 6, top 3": IndexRotation(symbols_=ALL6, top=3),
        "Rotation, US only (4), top 1": IndexRotation(symbols_=US4, top=1),
        "Rotation, US only (4), top 2": IndexRotation(symbols_=US4, top=2),
        "Rotation, ex-QQQ (5), top 2": IndexRotation(symbols_=[s for s in ALL6 if s != "QQQ"], top=2),
        "Each index with its own switch, equal 1/6": IndexRotation(symbols_=ALL6, top=6),
    }
    res = {k: run(m) for k, m in variants.items()}
    res["SPY buy & hold"] = buy_and_hold(["SPY"], prices, cash_rate=cash, start=START)
    res["All 6 buy & hold, equal weight"] = buy_and_hold(ALL6, prices, cash_rate=cash, start=START)

    emit(f"# Index rotation vs the SPY momentum sleeve - generated tables\n\n"
         f"{START[:7]} to {END}, 3bps costs, cash at T-bills, Sharpe above T-bills.\n")
    emit("## 1. Full period\n")
    emit(table({k: r.metrics for k, r in res.items()}))

    emit("\n## 2. Three eras: return/yr (Sharpe) and worst drop\n")
    emit("| | " + " | ".join(f"{a[:4]}-{b[:4]}" for a, b in PERIODS) + " |\n|---|" + "---|" * len(PERIODS))
    for k, r in res.items():
        cells = []
        for a, b in PERIODS:
            m = period_stats(r.equity, cash, a, b)
            cells.append(f"{m['cagr']:.1%} ({m['sharpe']:.2f}), {m['max_drawdown']:.0%}")
        emit(f"| {k} | " + " | ".join(cells) + " |")

    emit("\n## 3. Sensitivity: lookback x top N (all 6) - return/yr, Sharpe, worst drop\n")
    emit("| lookback | top 1 | top 2 | top 3 |\n|---|---|---|---|")
    grid = {}
    for lb, label in ((126, "6 months"), (189, "9 months"), (252, "12 months")):
        cells = []
        for top in (1, 2, 3):
            r = run(IndexRotation(symbols_=ALL6, top=top, lookback=lb))
            grid[(lb, top)] = r
            m = r.metrics
            cells.append(f"{m['cagr']:.1%}, {m['sharpe']:.2f}, {m['max_drawdown']:.0%}")
        emit(f"| {label} | " + " | ".join(cells) + " |")

    emit("\n## 4. Costs: 3x trading costs (9bps)\n")
    hi = CostModel(commission_bps=3, slippage_bps=6)
    emit(table({k: run(variants[k], hi).metrics for k in
                ("Live sleeve: SPY + 12-month switch", "Rotation, all 6, top 1", "Rotation, all 6, top 2")}))

    emit("\n## 5. Walk-forward: pick the setting on past data only, then trade it\n")
    emit("Every January from 2010, choose the best Sharpe among the 9 grid settings on all data so far, "
         "and hold that setting for the year. Stitched out-of-sample result:\n")
    daily = pd.DataFrame({k: r.equity.pct_change() for k, r in grid.items()})
    rf_d = daily_rf(cash, daily.index)
    stitched, chosen = [], []
    for year in range(2010, int(END[:4]) + 1):
        past = daily.loc[:f"{year - 1}-12-31"].dropna()
        ex = past.sub(rf_d.reindex(past.index), axis=0)
        best = (ex.mean() / ex.std()).idxmax()
        chosen.append(f"{year}: {best[0] // 21}m top {best[1]}")
        stitched.append(daily.loc[f"{year}-01-01":f"{year}-12-31", best])
    oos = (1 + pd.concat(stitched).fillna(0)).cumprod()
    spy_mom = res["Live sleeve: SPY + 12-month switch"].equity.loc[oos.index[0]:]
    wf = {"Walk-forward rotation (out of sample)": summarize(oos, rf_daily=daily_rf(cash, oos.index)),
          "Live sleeve, same years": summarize(spy_mom / spy_mom.iloc[0], rf_daily=daily_rf(cash, spy_mom.index))}
    emit(table(wf, ("cagr", "volatility", "sharpe", "max_drawdown")))
    emit("\nSettings chosen: " + "; ".join(chosen))

    emit("\n## 6. What the top-1 rotation actually held (share of months)\n")
    held = res["Rotation, all 6, top 1"].weights.resample("ME").last()
    share = (held > 0).mean()
    share["cash"] = (held.sum(axis=1) == 0).mean()
    emit(" | ".join(f"{k} {v:.0%}" for k, v in share.sort_values(ascending=False).items()))
    held2 = res["Rotation, all 6, top 2"].weights.resample("ME").last()
    emit("\nTop 2: " + " | ".join(f"{k} {v:.0%}" for k, v in (held2 > 0).mean().sort_values(ascending=False).items())
         + f" | fully in cash {(held2.sum(axis=1) == 0).mean():.0%}")
    switches = (held.diff().abs().sum(axis=1) > 0).sum()
    emit(f"\nTop 1 changed holding {switches} times in {len(held)} months.")

    emit("\n## 7. In the desk (monthly, 2014-04 to 2026-09): 50% screen + 20% flow rotation + 30% index sleeve\n")
    try:
        emit(desk_table(res, cash))
    except FileNotFoundError as e:
        emit(f"(skipped: {e} - run research/screen_backtest.py and research/bottleneck_backtest.py first)")

    OUT.mkdir(exist_ok=True)
    (OUT / "index_rotation.md").write_text("\n".join(lines) + "\n")
    print(f"\nwrote {OUT / 'index_rotation.md'}")


def desk_table(res, cash) -> str:
    """Swap the 30% sleeve inside the desk, using the sleeve backtests already on disk."""
    import pickle

    from ai_desk.fundamentals import screen_backtest as sb

    cache = ROOT / "data" / "backtest"
    prices = pickle.loads((cache / "prices.pkl").read_bytes())
    for k in prices:
        prices[k] = prices[k].groupby(level=0).last() if k != "splits" else prices[k].groupby(level=0).max()
    snaps = {}
    for m in (3, 6, 9, 12):
        snaps.update(pickle.loads((cache / f"snapshots_m{m}.pkl").read_bytes()))
    screen = sb.simulate({"t": sb.books(dict(sorted(snaps.items())), 25)["screen_top"]}, prices, "2026-09-30")["t"]
    import bottleneck_backtest as bb                     # the live bottleneck setting: 100-day MA, 2-week re-picks
    u = pickle.loads((cache / "universe.pkl").read_bytes())
    px = bb.weekly_prices(sorted(set(u.tickers.values())) + ["SPY"]).resample("W-FRI").last().loc[:bb.END]
    sic3 = pd.Series({t: (u.sic[c] or 0) // 10 for c, t in u.tickers.items()})
    stocks = px.drop(columns="SPY")
    flow, _ = bb.flow_rotation(stocks, sic3.reindex(stocks.columns), px["SPY"], repick_weeks=2, ma_weeks=20)
    flow_m = (1 + flow).resample("ME").prod() - 1
    idx = screen.index.intersection(flow_m.index)
    monthly = {k: r.equity.resample("ME").last().pct_change().reindex(idx)
               for k, r in res.items() if k in ("Live sleeve: SPY + 12-month switch", "Rotation, all 6, top 1",
                                               "Rotation, all 6, top 2", "Rotation, US only (4), top 2")}
    rf_m = (cash.resample("ME").last() / 12).shift(1).reindex(idx).fillna(0)
    rows = {}
    for k, sleeve in monthly.items():
        r = 0.5 * screen.reindex(idx) + 0.2 * flow_m.reindex(idx) + 0.3 * sleeve
        eq = (1 + r.fillna(0)).cumprod()
        ex = r - rf_m
        dd = (eq / eq.cummax() - 1).min()
        rows["Desk with " + k.split(":")[0].lower()] = {
            "cagr": eq.iloc[-1] ** (12 / len(eq)) - 1, "volatility": r.std() * np.sqrt(12),
            "sharpe": ex.mean() / ex.std() * np.sqrt(12), "max_drawdown": dd}
    corr = pd.DataFrame({"screen": screen.reindex(idx), **{k[:22]: v for k, v in monthly.items()}}).corr()["screen"]
    note = "\n\nMonthly correlation with the quality screen: " + ", ".join(
        f"{k} {v:.2f}" for k, v in corr.drop("screen").items())
    return table(rows, ("cagr", "volatility", "sharpe", "max_drawdown")) + note


if __name__ == "__main__":
    main()
