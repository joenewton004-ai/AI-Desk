"""Edge research: put every strategy through the same robustness gauntlet.

    python research/edges.py            # uses market_data/*.csv (run `ai_desk fetch` first)

Writes tables to research/output/report.md and charts to research/output/.
Every test uses the engine's rules: signal at the close, fill at the next
open, 3bps costs, cash earns the T-bill rate.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ai_desk.backtest import CostModel, run_backtest  # noqa: E402
from ai_desk.data import add_required_columns, load_cash_rate, load_csv  # noqa: E402
from ai_desk.metrics import TRADING_DAYS, daily_rf, summarize  # noqa: E402
from ai_desk.strategies import STRATEGIES, get_strategy  # noqa: E402
from ai_desk.validation import param_sensitivity, walk_forward  # noqa: E402

DATA = ROOT / "market_data"
OUT = Path(__file__).resolve().parent / "output"
END = "2026-10-16"   # last complete trading day when this was run

GRIDS = {
    "buy_hold": {},
    "trend": {"lookback": [100, 150, 200, 250], "band": [0.0, 0.01, 0.02]},
    "rsi_reversion": {"entry_rsi": [5, 10, 15], "exit_sma": [3, 5, 10]},
    "momentum": {"lookback": [126, 189, 252, 315], "skip": [0, 21]},
    "vix_filter": {"exit_above": [30, 35, 40], "enter_below": [18, 22, 26]},
    "turn_of_month": {"days_before": [1, 2, 3], "days_after": [2, 3, 4]},
}
PERIODS = [("1994-01-25", "2006-12-31"), ("2007-01-01", "2016-12-31"), ("2017-01-01", END)]
COLS = ["cagr", "volatility", "sharpe", "max_drawdown", "time_in_market", "trades"]

lines: list[str] = []


def emit(text: str = "") -> None:
    print(text)
    lines.append(text)


def fmt(df: pd.DataFrame) -> str:
    def cell(col, v):
        if isinstance(v, str):
            return v
        if pd.isna(v):
            return "n/a"
        if col in ("cagr", "volatility", "max_drawdown", "time_in_market", "total_return",
                   "test_return", "overnight", "intraday", "close_to_close") or col.endswith("%"):
            return f"{v:.1%}"
        if col == "trades":
            return f"{int(v)}"
        return f"{v:.2f}" if isinstance(v, float) else str(v)

    head = "| " + " | ".join([df.index.name or ""] + list(df.columns)) + " |"
    sep = "|" + "---|" * (len(df.columns) + 1)
    rows = ["| " + " | ".join([str(i)] + [cell(c, df.at[i, c]) for c in df.columns]) + " |" for i in df.index]
    return "\n".join([head, sep, *rows])


def load(symbol: str) -> pd.DataFrame:
    p = load_csv(DATA / f"{symbol}.csv").loc[:END]
    return add_required_columns(p, ["vix"], str(DATA / f"{symbol}.csv"))


def sharpe_se(sr: float, years: float) -> float:
    """Approximate standard error of an annualised Sharpe ratio (Lo, 2002)."""
    return float(np.sqrt((1 + 0.5 * sr ** 2) / years))


def main() -> None:
    needed = ["SPY", "QQQ", "IWM", "GLD", "TLT", "IEF", "VIX", "IRX"]
    missing = [s for s in needed if not (DATA / f"{s}.csv").exists()]
    if missing:
        sys.exit(f"missing market_data for {missing}. Run:\n"
                 "  python -m ai_desk fetch SPY QQQ IWM GLD TLT IEF ^VIX ^IRX")
    OUT.mkdir(parents=True, exist_ok=True)
    cash = load_cash_rate(str(DATA / "SPY.csv"))
    spy = load("SPY")
    start = spy.index[260]
    names = list(STRATEGIES)

    # 1. full period ----------------------------------------------------------
    emit("## 1. Full period, SPY\n")
    res = {n: run_backtest(spy, get_strategy(n), start=start, cash_rate=cash) for n in names}
    full = pd.DataFrame({n: r.metrics for n, r in res.items()}).T[COLS]
    years = len(res["buy_hold"].equity) / TRADING_DAYS
    full["sharpe_±1se"] = [f"±{sharpe_se(s, years):.2f}" for s in full["sharpe"]]
    full.index.name = "strategy"
    emit(fmt(full))
    pd.DataFrame({n: r.equity for n, r in res.items()}).to_csv(OUT / "equity_spy.csv")

    # 2. sub-periods ----------------------------------------------------------
    emit("\n## 2. Sub-periods (Sharpe above T-bills / CAGR / max drawdown)\n")
    rows = {}
    for n in names:
        row = {}
        for a, b in PERIODS:
            r = run_backtest(spy.loc[:b], get_strategy(n), start=a, cash_rate=cash)
            label = f"{a[:4]}-{b[:4]}"
            row[label] = f"{r.metrics['sharpe']:.2f} / {r.metrics['cagr']:.1%} / {r.metrics['max_drawdown']:.0%}"
        rows[n] = row
    t = pd.DataFrame(rows).T
    t.index.name = "strategy"
    emit(fmt(t))

    # 3. cost stress ----------------------------------------------------------
    emit("\n## 3. Cost stress: CAGR at 3 / 8 / 18 bps per trade\n")
    rows = {}
    for n in names:
        rows[n] = {f"{c}bps": run_backtest(spy, get_strategy(n), costs=CostModel(1, c - 1), start=start,
                                           cash_rate=cash).metrics["cagr"] for c in (3, 8, 18)}
    t = pd.DataFrame(rows).T
    t.columns = [c + " cagr%" for c in t.columns]
    t.index.name = "strategy"
    emit(fmt(t))

    # 4. other markets --------------------------------------------------------
    emit("\n## 4. Same rules on other markets (Sharpe / CAGR / max drawdown)\n")
    rows = {}
    for sym in ("QQQ", "IWM"):
        p = load(sym)
        s0 = p.index[260]
        for n in names:
            m = run_backtest(p, get_strategy(n), start=s0, cash_rate=cash).metrics
            rows.setdefault(n, {})[f"{sym} {m['start'][:4]}+"] = \
                f"{m['sharpe']:.2f} / {m['cagr']:.1%} / {m['max_drawdown']:.0%}"
    t = pd.DataFrame(rows).T
    t.index.name = "strategy"
    emit(fmt(t))

    # 5. parameter sensitivity -----------------------------------------------
    emit("\n## 5. Parameter sensitivity, full period SPY (Sharpe)\n")
    emit("A real edge shows a broad plateau; a lone peak is luck.\n")
    for n, grid in GRIDS.items():
        if not grid:
            continue
        table = param_sensitivity(spy, n, grid, start=start, cash_rate=cash)
        keys = list(grid)
        if len(keys) == 2:
            pivot = table.pivot(index=keys[0], columns=keys[1], values="sharpe")
            pivot.columns = [f"{keys[1]}={c}" for c in pivot.columns]
            pivot.index = [f"{keys[0]}={i}" for i in pivot.index]
            pivot.index.name = n
            emit(fmt(pivot))
        emit(f"\nrange: {table['sharpe'].min():.2f} to {table['sharpe'].max():.2f}\n")

    # 6. walk-forward ---------------------------------------------------------
    emit("\n## 6. Walk-forward: tune on 8 years, trade the next year blind, repeat\n")
    rows, wf_equity = {}, {}
    for n, grid in GRIDS.items():
        wf = walk_forward(spy, n, grid, train_years=8, test_years=1, cash_rate=cash)
        rows[n] = {k: wf.metrics[k] for k in ("start", "cagr", "volatility", "sharpe", "max_drawdown")}
        wf_equity[n] = wf.equity
        picks = wf.windows[list(grid)].astype(str).agg(",".join, axis=1) if grid else pd.Series(["-"])
        rows[n]["param_changes"] = int((picks != picks.shift()).sum() - 1)
    t = pd.DataFrame(rows).T
    t.index.name = "strategy (out-of-sample)"
    emit(fmt(t))
    pd.DataFrame(wf_equity).to_csv(OUT / "walkforward_equity.csv")

    # 7. overnight vs intraday -----------------------------------------------
    emit("\n## 7. Where do SPY's returns come from? Overnight vs intraday\n")
    o, c = spy["open"], spy["close"]
    rows = {}
    for label, sl in (("1994-2026", slice("1994", END)), ("2017-2026", slice("2017", END))):
        p = spy.loc[sl]
        yrs = len(p) / TRADING_DAYS
        on = (o / c.shift(1)).loc[sl].dropna().prod()
        intra = (c / o).loc[sl].prod()
        cc = p["close"].iloc[-1] / p["close"].iloc[0]
        rows[label] = {"overnight": on ** (1 / yrs) - 1, "intraday": intra ** (1 / yrs) - 1,
                       "close_to_close": cc ** (1 / yrs) - 1}
    t = pd.DataFrame(rows).T
    t.index.name = "CAGR"
    emit(fmt(t))
    emit("\nAlmost all of SPY's gain has come overnight. But an overnight-only strategy (buy every "
         "close, sell every open) still trails buy & hold before costs, and it trades ~500 times a "
         "year: ~15%/yr of friction at 3bps per trade, ~5%/yr even at a very tight 1bp.")

    # 8. multi-asset momentum rotation ---------------------------------------
    emit("\n## 8. Multi-asset momentum rotation (SPY, QQQ, IWM, GLD, TLT; IEF as the safe asset)\n")
    rot = rotation_study(cash)
    emit(fmt(rot))

    (OUT / "report.md").write_text("# Edge research - generated tables\n\n" + "\n".join(lines) + "\n")
    charts(res, wf_equity)
    print(f"\nwrote {OUT / 'report.md'}")


def rotation_study(cash) -> pd.DataFrame:
    """Once a month, hold the top-N assets by trailing return, but only those beating
    T-bills; the rest goes to IEF. Signal at the first close of the month, fill next open."""
    universe = ["SPY", "QQQ", "IWM", "GLD", "TLT"]
    safe = "IEF"
    frames = {s: load_csv(DATA / f"{s}.csv").loc[:END] for s in universe + [safe]}
    idx = frames["GLD"].index
    for f in frames.values():
        idx = idx.intersection(f.index)
    opens = pd.DataFrame({s: f["open"] for s, f in frames.items()}).loc[idx]
    closes = pd.DataFrame({s: f["close"] for s, f in frames.items()}).loc[idx]
    rf = cash.reindex(idx).ffill().fillna(0)
    rate = 3 / 10_000

    def run(lookbacks, top_n):
        mom = sum(closes / closes.shift(lb) - 1 for lb in lookbacks) / len(lookbacks)
        hurdle = rf * np.mean(lookbacks) / TRADING_DAYS     # T-bill return over the lookback
        new_month = pd.Series(idx.month, index=idx).diff().fillna(1) != 0
        targets = pd.DataFrame(0.0, index=idx, columns=closes.columns)
        for d in idx[new_month.to_numpy()]:
            m = mom.loc[d, universe]
            if m.isna().any():
                continue
            picks = [s for s in m.sort_values(ascending=False).index[:top_n] if m[s] > hurdle.loc[d]]
            w = pd.Series(0.0, index=closes.columns)
            w[picks] = 1 / top_n
            w[safe] += 1 - w.sum()
            targets.loc[d] = w
        targets = targets.where(new_month, np.nan).ffill().fillna(0.0)
        first = targets.index[(targets.sum(axis=1) > 0).to_numpy()][0]
        return simulate(opens, closes, targets, rate, first)

    def simulate(opens, closes, targets, rate, first):
        o, c, t = opens.to_numpy(), closes.to_numpy(), targets.to_numpy()
        i0 = idx.get_loc(first)
        eq, w, pend, out = 1.0, np.zeros(o.shape[1]), t[i0], [1.0]
        for i in range(i0 + 1, len(idx)):
            eq *= 1 + w @ (o[i] / c[i - 1] - 1)
            if not np.allclose(pend, w):
                eq -= np.abs(pend - w).sum() * eq * rate
                w = pend
            eq *= 1 + w @ (c[i] / o[i] - 1)
            out.append(eq)
            pend = t[i]
        return pd.Series(out, index=idx[i0:])

    variants = {"12m, top 1": ([252], 1), "12m, top 2": ([252], 2),
                "3/6/12m blend, top 1": ([63, 126, 252], 1), "3/6/12m blend, top 2": ([63, 126, 252], 2),
                "6m, top 2": ([126], 2)}
    curves = {k: run(*v) for k, v in variants.items()}
    start = max(cv.index[0] for cv in curves.values())
    spy_bh = closes["SPY"].loc[start:] / closes["SPY"].loc[start]
    sixty40 = (0.6 * closes["SPY"].pct_change() + 0.4 * closes["IEF"].pct_change()).loc[start:]
    curves["SPY buy & hold"] = spy_bh
    curves["60/40 SPY/IEF (daily rebal.)"] = (1 + sixty40.fillna(0)).cumprod()
    rows = {}
    for k, cv in curves.items():
        cv = cv.loc[start:]
        m = summarize(cv / cv.iloc[0], rf_daily=daily_rf(cash, cv.index))
        rows[k] = {"start": m["start"], "cagr": m["cagr"], "volatility": m["volatility"],
                   "sharpe": m["sharpe"], "max_drawdown": m["max_drawdown"]}
    pd.DataFrame(curves).loc[start:].to_csv(OUT / "rotation_equity.csv")
    t = pd.DataFrame(rows).T
    t.index.name = "variant"
    return t


def charts(res, wf_equity) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return
    for title, curves, fname in (("SPY strategies, full period", {n: r.equity for n, r in res.items()}, "spy_strategies.png"),
                                 ("Walk-forward (out-of-sample only)", wf_equity, "walkforward.png")):
        fig, (a1, a2) = plt.subplots(2, 1, figsize=(11, 7), sharex=True, height_ratios=[3, 1.3])
        for n, eq in curves.items():
            eq = eq / eq.iloc[0]
            a1.plot(eq.index, eq, label=n, linewidth=1.6 if n == "buy_hold" else 1.1,
                    color="black" if n == "buy_hold" else None)
            a2.plot(eq.index, eq / eq.cummax() - 1, linewidth=0.9, color="black" if n == "buy_hold" else None)
        a1.set_yscale("log")
        a1.set_title(title)
        a1.set_ylabel("growth of $1 (log)")
        a1.legend(ncol=3, fontsize=8)
        a2.set_ylabel("drawdown")
        fig.tight_layout()
        fig.savefig(OUT / fname, dpi=110)
        plt.close(fig)


if __name__ == "__main__":
    main()
