"""Backtest the stock screen with point-in-time SEC data.

    python research/screen_backtest.py

The first run downloads ~1,500 companies' SEC filings and 14 years of
monthly prices (about 15-30 minutes); both are cached. Writes
research/output/screen_backtest.md plus a chart.
"""

from __future__ import annotations

import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ai_desk.data import load_cash_rate, load_csv  # noqa: E402
from ai_desk.fundamentals import screen_backtest as sb  # noqa: E402
from ai_desk.metrics import max_drawdown  # noqa: E402

CACHE = ROOT / "data" / "backtest"
OUT = Path(__file__).resolve().parent / "output"
START = "2014-03-31"
lines: list[str] = []


def emit(text: str = "") -> None:
    print(text)
    lines.append(text)


def cached(name: str, build):
    path = CACHE / f"{name}.pkl"
    if path.exists():
        return pickle.loads(path.read_bytes())
    obj = build()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(pickle.dumps(obj))
    return obj


def stats(r: pd.Series, rf: pd.Series, bench: pd.Series | None = None) -> dict:
    r = r.dropna()
    eq = (1 + r).cumprod()
    years = len(r) / 12
    ex = r - rf.reindex(r.index).fillna(0)
    out = {"CAGR": eq.iloc[-1] ** (1 / years) - 1, "volatility": r.std() * np.sqrt(12),
           "Sharpe": ex.mean() / ex.std() * np.sqrt(12), "max drawdown": max_drawdown(pd.concat(
               [pd.Series([1.0]), eq.reset_index(drop=True)]))}
    if bench is not None:
        b = bench.reindex(r.index)
        out["beta vs SPY"] = r.cov(b) / b.var()
        out["beats SPY (years)"] = None
    return out


def table(rows: dict[str, dict]) -> str:
    cols = list(next(iter(rows.values())))
    head = "| | " + " | ".join(cols) + " |\n|---|" + "---|" * len(cols)
    body = []
    for name, row in rows.items():
        cells = []
        for c in cols:
            v = row.get(c)
            cells.append("" if v is None else (f"{v:.2f}" if c in ("Sharpe", "beta vs SPY") else
                                               f"{v:.1%}" if isinstance(v, float) else str(v)))
        body.append(f"| {name} | " + " | ".join(cells) + " |")
    return head + "\n" + "\n".join(body)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    print("Building the universe from SEC data ...")
    u = cached("universe", lambda: sb.build_universe())
    print(f"  {len(u.tickers)} companies; downloading monthly prices ...")
    tickers = sorted(set(u.tickers.values()))
    prices = cached("prices", lambda: sb.load_prices(tickers + ["SPY"]))

    rf_annual = load_cash_rate(str(ROOT / "market_data" / "SPY.csv"))
    rf = (rf_annual.resample("ME").last() / 12).shift(1)       # earned over the following month
    spy = prices["adj"]["SPY"].pct_change(fill_method=None)

    base = cached(f"run_top25_m3", lambda: sb.run(u, prices, START, 25, 3))
    r = base.returns.copy()
    r["SPY"] = spy.reindex(r.index)
    # market-momentum overlay from research/edges.py: hold the screen while SPY's
    # 12-month return is positive, otherwise T-bills (decided at month-end, applied next month)
    spy_px = prices["adj"]["SPY"]
    risk_on = (spy_px / spy_px.shift(12) - 1 > 0).shift(1).reindex(r.index).fillna(True)
    r["screen_top + momentum"] = r["screen_top"].where(risk_on, rf.reindex(r.index).fillna(0))

    names = {"screen_top": "Screen: top 25", "screen_top + momentum": "Top 25 + market momentum",
             "gates_only": "All that pass the gates", "universe_ew": "Universe, equal-weight",
             "SPY": "S&P 500 (SPY)"}
    emit(f"## 1. Results, {r.index[0]:%b %Y} - {r.index[-1]:%b %Y} (rebalanced each March)\n")
    rows = {names[k]: stats(r[k], rf, r["SPY"]) for k in names}
    for k in names:
        yearly = (1 + r[[k, "SPY"]]).groupby(r.index.year).prod() - 1
        rows[names[k]]["beats SPY (years)"] = f"{int((yearly[k] > yearly['SPY']).sum())}/{len(yearly)}"
    emit(table(rows))

    emit("\n## 2. Calendar years\n")
    yearly = (1 + r[list(names)]).groupby(r.index.year).prod() - 1
    yearly.columns = [names[c] for c in yearly.columns]
    emit("| year | " + " | ".join(yearly.columns) + " |\n|---|" + "---|" * len(yearly.columns))
    for y, row in yearly.iterrows():
        partial = " (part)" if y in (r.index[0].year, r.index[-1].year) else ""
        emit(f"| {y}{partial} | " + " | ".join(f"{v:+.1%}" for v in row) + " |")

    emit("\n## 3. Robustness\n")
    rows = {}
    for n in (10, 25, 50):
        run = base if n == 25 else cached(f"run_top{n}_m3", lambda n=n: sb.run(u, prices, START, n, 3, progress=False))
        rows[f"top {n}, March"] = stats(run.returns["screen_top"], rf)
    for m, label in ((6, "June"), (9, "September"), (12, "December")):
        run = cached(f"run_top25_m{m}", lambda m=m: sb.run(u, prices, START, 25, m, progress=False))
        rows[f"top 25, {label}"] = stats(run.returns["screen_top"], rf)
    rows["costs x5 (0.5%/trade)"] = stats(cached("run_top25_m3_cost5", lambda: sb.run(
        u, prices, START, 25, 3, cost=0.005, progress=False)).returns["screen_top"], rf)
    emit(table(rows))
    for a, b in (("2014", "2019"), ("2020", "2026")):
        sl = r.loc[a:b]
        emit(f"\n{a}-{b}: screen {stats(sl['screen_top'], rf)['CAGR']:.1%}/yr vs universe "
             f"{stats(sl['universe_ew'], rf)['CAGR']:.1%} vs SPY {stats(sl['SPY'], rf)['CAGR']:.1%}")

    emit("\n## 4. Universe and holdings\n")
    emit(table({str(row["date"]): {"universe": str(row["universe"]), "pass gates": str(row["pass_gates"]),
                                   "top 25": ", ".join(base.holdings[pd.Timestamp(row["date"])][:25])}
                for _, row in base.counts.iterrows()}))

    (OUT / "screen_backtest.md").write_text("# Screen backtest - generated tables\n\n" + "\n".join(lines) + "\n")
    r.to_csv(OUT / "screen_backtest_returns.csv")
    chart(r, names)
    print(f"\nwrote {OUT / 'screen_backtest.md'}")


def chart(r: pd.DataFrame, names: dict) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(11, 7), sharex=True, height_ratios=[3, 1.3])
    for k, label in names.items():
        eq = (1 + r[k].fillna(0)).cumprod()
        style = {"color": "black", "linewidth": 1.6} if k == "SPY" else {"linewidth": 1.2}
        a1.plot(eq.index, eq, label=label, **style)
        a2.plot(eq.index, eq / eq.cummax() - 1, linewidth=0.9, **({"color": "black"} if k == "SPY" else {}))
    a1.set_yscale("log")
    a1.set_ylabel("growth of $1 (log)")
    a1.set_title("Stock screen backtest (point-in-time SEC data; survivors only - see notes)")
    a1.legend(fontsize=8)
    a2.set_ylabel("drawdown")
    fig.tight_layout()
    fig.savefig(OUT / "screen_backtest.png", dpi=110)
    plt.close(fig)


if __name__ == "__main__":
    main()
