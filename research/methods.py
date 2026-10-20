"""Evaluate the moving-average crossover and duopoly pairs trading.

    python research/methods.py

Uses Yahoo daily prices (adjusted for splits and dividends), 3bps costs,
cash earning the T-bill rate and a 0.5%/yr borrow fee on shorts. Writes
research/output/methods.md. Findings are summarised in research/METHODS.md.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ai_desk.backtest import CostModel, run_backtest  # noqa: E402
from ai_desk.data import load_cash_rate, load_csv, load_many  # noqa: E402
from ai_desk.metrics import daily_rf, summarize  # noqa: E402
from ai_desk.portfolio.backtest import buy_and_hold, run_portfolio_backtest  # noqa: E402
from ai_desk.portfolio.methods import DUOPOLY_PAIRS, PairsMethod  # noqa: E402
from ai_desk.strategies import get_strategy  # noqa: E402
from ai_desk.validation import walk_forward  # noqa: E402

DATA = ROOT / "market_data"
OUT = Path(__file__).resolve().parent / "output"
END = "2026-10-16"
COLS = ["cagr", "volatility", "sharpe", "max_drawdown", "trades"]
lines: list[str] = []


def emit(t: str = "") -> None:
    print(t)
    lines.append(t)


def fmt(rows: dict[str, dict], cols=COLS, ratio: bool = False) -> str:
    """ratio=True: every value is a plain number (e.g. a grid of Sharpe ratios)."""
    def cell(c, v):
        if v is None or v != v:
            return "n/a"
        if c in ("sharpe",) or ratio:
            return f"{v:.2f}"
        if c == "trades":
            return str(int(v))
        return f"{v:.1%}" if isinstance(v, float) else str(v)
    head = "| | " + " | ".join(cols) + " |\n|---|" + "---|" * len(cols)
    return head + "\n" + "\n".join(f"| {k} | " + " | ".join(cell(c, r.get(c)) for c in cols) + " |"
                                   for k, r in rows.items())


def sub_metrics(eq: pd.Series, cash, a, b) -> dict:
    e = eq.loc[a:b]
    return summarize(e, rf_daily=daily_rf(cash, e.index))


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    cash = load_cash_rate(str(DATA / "SPY.csv"))

    # ---- 1. moving-average crossover ------------------------------------------
    emit("## 1. Moving-average crossover (50/200) vs alternatives, SPY 1994-2026\n")
    spy = load_csv(DATA / "SPY.csv").loc[:END]
    start = spy.index[260]
    rows = {}
    for name, params in (("buy_hold", {}), ("sma_crossover", {}), ("trend", {}), ("momentum", {})):
        rows[name] = run_backtest(spy, get_strategy(name, **params), start=start, cash_rate=cash).metrics
    emit(fmt(rows))

    emit("\n### Parameter sensitivity (Sharpe), SPY\n")
    grid_rows = {}
    for fast in (20, 50, 100):
        grid_rows[f"fast {fast}"] = {f"slow {slow}": run_backtest(
            spy, get_strategy("sma_crossover", fast=fast, slow=slow), start=start, cash_rate=cash).metrics["sharpe"]
            for slow in (150, 200, 250)}
    emit(fmt(grid_rows, ["slow 150", "slow 200", "slow 250"], ratio=True))

    emit("\n### Walk-forward (tune on 8 years, trade the next blind), SPY\n")
    wf = walk_forward(spy, "sma_crossover", {"fast": [20, 50, 100], "slow": [150, 200, 250]},
                      train_years=8, cash_rate=cash)
    bh = run_backtest(spy, get_strategy("buy_hold"), start=wf.equity.index[0], cash_rate=cash).metrics
    emit(fmt({"sma_crossover (out-of-sample)": wf.metrics, "buy_hold": bh}, COLS[:4]))

    emit("\n### Other markets\n")
    rows = {}
    for sym in ("QQQ", "IWM", "GLD", "TLT"):
        p = load_csv(DATA / f"{sym}.csv").loc[:END]
        s0 = p.index[260]
        for name in ("buy_hold", "sma_crossover"):
            m = run_backtest(p, get_strategy(name), start=s0, cash_rate=cash).metrics
            rows[f"{sym} {name}"] = m
    emit(fmt(rows))

    # ---- 2. duopoly pairs ----------------------------------------------------------
    emit("\n## 2. Duopoly pairs trading, 2010-2026\n")
    symbols = sorted({s for p in DUOPOLY_PAIRS for s in p})
    prices = load_many(symbols, "2010-01-01", END)
    p_start = prices["close"].index[260]
    kw = dict(cash_rate=cash, start=p_start)
    variants = {
        "pairs long/short (default)": PairsMethod(),
        "pairs long-only": PairsMethod(mode="long_only"),
    }
    results = {k: run_portfolio_backtest(m, prices, **kw) for k, m in variants.items()}
    bench = buy_and_hold(symbols, prices, **kw)
    spy_bh = run_backtest(spy, get_strategy("buy_hold"), start=p_start, cash_rate=cash)
    rows = {k: r.metrics for k, r in results.items()}
    rows["buy & hold, all 12 stocks"] = bench.metrics
    rows["SPY buy & hold"] = spy_bh.metrics
    emit(fmt(rows, COLS + ["avg_gross_exposure", "avg_net_exposure"]))

    emit("\n### Correlation with the S&P 500 (daily returns)\n")
    spy_r = spy_bh.equity.pct_change()
    for k, r in results.items():
        emit(f"- {k}: {r.equity.pct_change().corr(spy_r):.2f}")

    emit("\n### Each pair on its own (long/short)\n")
    rows = {}
    for a, b in DUOPOLY_PAIRS:
        r = run_portfolio_backtest(PairsMethod(pairs=[(a, b)]), prices, **kw)
        ratio = prices["close"][a] / prices["close"][b]
        drift = (ratio.iloc[-1] / ratio.loc[p_start:].iloc[0]) ** (1 / ((ratio.index[-1] - p_start).days / 365.25)) - 1
        rows[f"{a}/{b}"] = {**r.metrics, "ratio drift/yr": drift}
    emit(fmt(rows, COLS + ["ratio drift/yr"]))

    emit("\n### Parameter sensitivity (Sharpe, long/short)\n")
    grid = {}
    for lb in (20, 60, 120):
        grid[f"lookback {lb}"] = {f"entry z {z}": run_portfolio_backtest(
            PairsMethod(lookback=lb, entry_z=z), prices, **kw).metrics["sharpe"] for z in (1.5, 2.0, 2.5)}
    emit(fmt(grid, ["entry z 1.5", "entry z 2.0", "entry z 2.5"], ratio=True))

    emit("\n### Sub-periods and costs (long/short)\n")
    ls = results["pairs long/short (default)"]
    rows = {"2011-2018": sub_metrics(ls.equity, cash, "2011", "2018"),
            "2019-2026": sub_metrics(ls.equity, cash, "2019", END)}
    rows["costs x3 (9bps)"] = run_portfolio_backtest(variants["pairs long/short (default)"], prices,
                                                     costs=CostModel(3, 6), **kw).metrics
    emit(fmt(rows, COLS[:4]))

    (OUT / "methods.md").write_text("# Methods evaluation - generated tables\n\n" + "\n".join(lines) + "\n")
    print(f"\nwrote {OUT / 'methods.md'}")


if __name__ == "__main__":
    main()
