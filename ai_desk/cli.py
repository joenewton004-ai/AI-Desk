"""Command line interface.  Run `python -m ai_desk --help`."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

from ai_desk.backtest import CostModel, run_backtest
from ai_desk.data import load_prices
from ai_desk.metrics import format_table
from ai_desk.risk import RiskConfig
from ai_desk.strategies import STRATEGIES, get_strategy


def _num(v: str):
    for cast in (int, float):
        try:
            return cast(v)
        except ValueError:
            pass
    return v


def parse_params(items: list[str] | None) -> dict:
    """--param lookback=150 --param band=0.02  ->  {"lookback": 150, "band": 0.02}"""
    out = {}
    for item in items or []:
        k, _, v = item.partition("=")
        out[k.strip()] = _num(v.strip())
    return out


def parse_grid(items: list[str]) -> dict[str, list]:
    """--grid lookback=100,150,200  ->  {"lookback": [100, 150, 200]}"""
    out = {}
    for item in items:
        k, _, v = item.partition("=")
        out[k.strip()] = [_num(x.strip()) for x in v.split(",")]
    return out


def _common(p: argparse.ArgumentParser) -> None:
    p.add_argument("--symbol", default="SPY")
    p.add_argument("--start", default="2000-01-01", help="first date of data to load")
    p.add_argument("--end", default=None)
    p.add_argument("--source", default="yahoo", help="yahoo | synthetic | path/to/prices.csv")
    p.add_argument("--commission-bps", type=float, default=1.0)
    p.add_argument("--slippage-bps", type=float, default=2.0)
    p.add_argument("--target-vol", type=float, default=None, help="e.g. 0.15 for 15%% annual vol targeting")
    p.add_argument("--max-leverage", type=float, default=1.0)
    p.add_argument("--max-dd-halt", type=float, default=None, help="e.g. 0.25: stop trading after a 25%% drawdown")


def _risk(a) -> RiskConfig:
    return RiskConfig(target_vol=a.target_vol, max_leverage=a.max_leverage, max_drawdown_halt=a.max_dd_halt)


def _costs(a) -> CostModel:
    return CostModel(a.commission_bps, a.slippage_bps)


def _warmup_start(prices: pd.DataFrame, days: int = 250):
    """Skip the first ~year so long averages have data before trading begins."""
    return prices.index[min(days, len(prices) - 2)]


def cmd_backtest(a) -> None:
    prices = load_prices(a.symbol, a.start, a.end, a.source)
    start = _warmup_start(prices)
    names = list(STRATEGIES) if a.strategy == "all" else [a.strategy, "buy_hold"]
    params = parse_params(a.param)
    rows, results = {}, {}
    for name in dict.fromkeys(names):
        strat = get_strategy(name, **(params if name == a.strategy else {}))
        # the benchmark is always plain buy & hold, with no risk overlay
        risk = RiskConfig() if name == "buy_hold" else _risk(a)
        res = run_backtest(prices, strat, risk, _costs(a), start=start)
        rows[name] = res.metrics
        results[name] = res
        if res.halted_on is not None:
            print(f"[!] {name}: drawdown circuit breaker tripped on {res.halted_on.date()}")
    print(f"\n{a.symbol}  ({a.source})  costs={a.commission_bps + a.slippage_bps:.1f}bps/trade\n")
    print(format_table(rows))
    if a.source == "synthetic":
        print("\nNote: synthetic data is random - these numbers say nothing about real markets.")

    if a.out:
        out = Path(a.out)
        out.mkdir(parents=True, exist_ok=True)
        pd.DataFrame({n: r.equity for n, r in results.items()}).to_csv(out / "equity.csv")
        for n, r in results.items():
            r.trades.to_csv(out / f"trades_{n}.csv", index=False)
        print(f"\nSaved equity curves and trade lists to {out}/")
        if a.plot:
            _plot(results, out / "equity.png")


def _plot(results, path: Path) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not installed - run: pip install matplotlib")
        return
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 7), sharex=True, height_ratios=[3, 1])
    for name, r in results.items():
        ax1.plot(r.equity.index, r.equity, label=name, linewidth=1.2)
        ax2.plot(r.equity.index, r.equity / r.equity.cummax() - 1, linewidth=1)
    ax1.set_yscale("log")
    ax1.set_ylabel("equity (log scale)")
    ax1.legend()
    ax2.set_ylabel("drawdown")
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    print(f"Saved chart to {path}")


def cmd_validate(a) -> None:
    from ai_desk.validation import param_sensitivity, split_test

    prices = load_prices(a.symbol, a.start, a.end, a.source)
    start = _warmup_start(prices)
    params = parse_params(a.param)
    res = split_test(prices, a.strategy, params, a.split, _risk(a), _costs(a), start=start)
    print(f"\n{get_strategy(a.strategy, **params).describe()}  split at {a.split}\n")
    print(format_table({k: v.metrics for k, v in res.items()}))
    if a.grid:
        print("\nParameter sensitivity (IN-SAMPLE only). Look for a broad plateau, not one lucky peak:\n")
        table = param_sensitivity(prices, a.strategy, parse_grid(a.grid), _risk(a), _costs(a),
                                  start=start, end=pd.Timestamp(a.split) - pd.Timedelta(days=1))
        print(table.to_string(index=False, float_format=lambda x: f"{x:.3f}"))


def cmd_walkforward(a) -> None:
    from ai_desk.metrics import summarize
    from ai_desk.validation import walk_forward

    prices = load_prices(a.symbol, a.start, a.end, a.source)
    wf = walk_forward(prices, a.strategy, parse_grid(a.grid), a.train_years, a.test_years,
                      a.metric, _risk(a), _costs(a))
    bench = run_backtest(prices, get_strategy("buy_hold"), RiskConfig(), _costs(a),
                         start=wf.equity.index[0])
    print("\nParameters chosen in each window (each test year traded blind):\n")
    print(wf.windows.to_string(index=False, float_format=lambda x: f"{x:.3f}"))
    print("\nStitched out-of-sample performance vs buy & hold:\n")
    print(format_table({f"{a.strategy} (OOS)": wf.metrics, "buy_hold": summarize(bench.equity)}))


def cmd_paper(a) -> None:
    from ai_desk.live import run_paper

    demo = a.source == "synthetic"   # offline demo: old fake data, so skip the freshness check
    start = "2000-01-01" if demo else (pd.Timestamp.today() - pd.DateOffset(years=2)).date().isoformat()
    prices = load_prices(a.symbol, start, None, a.source)
    strat = get_strategy(a.strategy, **parse_params(a.param))
    plan = run_paper(prices, strat, _risk(a), a.symbol, execute=a.execute,
                     max_order_pct=a.max_order_pct, max_drawdown_halt=a.account_dd_halt,
                     max_data_age_days=None if demo else 5)
    print(f"\n{strat.describe()} on {a.symbol}, signal from close of {plan.signal_date}")
    print(f"  target weight : {plan.target_weight:.1%} of ${plan.equity:,.0f}")
    print(f"  holding now   : {plan.current_qty:g} shares   target: {plan.target_qty} shares")
    if plan.side:
        verb = "SUBMITTED" if a.execute else "WOULD PLACE (dry run, add --execute)"
        print(f"  {verb}: {plan.side} {plan.order_qty} {a.symbol} @ market (~${plan.notional:,.0f})")
    else:
        print(f"  no order: {plan.reason}")
    print("  logged to logs/journal.csv")


def cmd_options(a) -> None:
    from ai_desk.options import payoff
    from ai_desk.options.black_scholes import greeks

    t = a.days / 365
    if a.action == "price":
        for kind in ("call", "put"):
            g = greeks(kind, a.spot, a.strike, t, a.vol, a.rate, a.div)
            print(f"{kind:>4}: price ${g.price:.2f}  (${g.price * 100:,.0f}/contract)  delta {g.delta:+.3f}  "
                  f"gamma {g.gamma:.4f}  vega ${g.vega:.3f}  theta ${g.theta:.3f}/day")
        return

    # strategy demo: price each leg with Black-Scholes, then show payoff at expiry
    S, w = a.spot, a.width

    def prem(kind, k):
        return greeks(kind, S, k, t, a.vol, a.rate, a.div).price

    builders = {
        "covered_call": lambda: payoff.covered_call(S, S + w, prem("call", S + w)),
        "cash_secured_put": lambda: payoff.cash_secured_put(S - w, prem("put", S - w)),
        "bull_call_spread": lambda: payoff.bull_call_spread(S, prem("call", S), S + w, prem("call", S + w)),
        "bull_put_spread": lambda: payoff.bull_put_spread(S - w, prem("put", S - w), S - 2 * w, prem("put", S - 2 * w)),
        "iron_condor": lambda: payoff.iron_condor(S - 2 * w, prem("put", S - 2 * w), S - w, prem("put", S - w),
                                                  S + w, prem("call", S + w), S + 2 * w, prem("call", S + 2 * w)),
        "long_call": lambda: payoff.long_call(S, prem("call", S)),
        "long_put": lambda: payoff.long_put(S, prem("put", S)),
    }
    if a.action not in builders:
        sys.exit(f"unknown options action. Choose: price, {', '.join(builders)}")
    legs = builders[a.action]()
    print(f"\n{a.action} on underlying @ {S}, {a.days} days, IV {a.vol:.0%} (premiums from Black-Scholes)\n")
    for leg in legs:
        side = "long " if leg.qty > 0 else "short"
        if leg.kind == "stock":
            print(f"  {side} {abs(leg.qty):g} shares @ {leg.strike:.2f}")
        else:
            print(f"  {side} {abs(leg.qty):g} {leg.kind} K={leg.strike:.2f}  premium {leg.premium:.2f}")
    stats = payoff.analyze(legs)
    print()
    for k, v in stats.items():
        print(f"  {k:12}: {v if isinstance(v, (str, list)) else f'${v:,.2f}'}")
    grid = [S * (1 + x / 100) for x in range(-10, 11, 2)]
    print("\n  price at expiry -> P&L")
    for p, pnl in zip(grid, payoff.position_payoff(legs, pd.Series(grid).to_numpy())):
        print(f"  {p:>10.2f}  {pnl:>+12,.2f}")


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="ai_desk", description="Rules-based trading desk")
    sub = ap.add_subparsers(dest="cmd", required=True)
    strategies = list(STRATEGIES)

    b = sub.add_parser("backtest", help="backtest a strategy against buy & hold")
    _common(b)
    b.add_argument("--strategy", default="trend", choices=strategies + ["all"])
    b.add_argument("--param", action="append", help="strategy parameter, e.g. lookback=150")
    b.add_argument("--out", default=None, help="folder to save equity/trades CSVs")
    b.add_argument("--plot", action="store_true", help="also save a chart (needs matplotlib)")
    b.set_defaults(func=cmd_backtest)

    v = sub.add_parser("validate", help="in-sample vs out-of-sample check + parameter sensitivity")
    _common(v)
    v.add_argument("--strategy", default="trend", choices=strategies)
    v.add_argument("--param", action="append")
    v.add_argument("--split", default="2015-01-01", help="out-of-sample starts here")
    v.add_argument("--grid", action="append", help="e.g. lookback=100,150,200,250")
    v.set_defaults(func=cmd_validate)

    w = sub.add_parser("walkforward", help="rolling optimise-then-trade-blind test")
    _common(w)
    w.add_argument("--strategy", default="trend", choices=strategies)
    w.add_argument("--grid", action="append", required=True, help="e.g. lookback=100,150,200,250")
    w.add_argument("--train-years", type=int, default=5)
    w.add_argument("--test-years", type=int, default=1)
    w.add_argument("--metric", default="sharpe", choices=["sharpe", "cagr", "calmar", "sortino"])
    w.set_defaults(func=cmd_walkforward)

    p = sub.add_parser("paper", help="run today's signal against your Alpaca PAPER account")
    _common(p)
    p.add_argument("--strategy", default="trend", choices=strategies)
    p.add_argument("--param", action="append")
    p.add_argument("--execute", action="store_true", help="actually submit the order (paper account)")
    p.add_argument("--max-order-pct", type=float, default=1.05,
                   help="refuse any single order larger than this fraction of account equity")
    p.add_argument("--account-dd-halt", type=float, default=0.20, help="stop if account falls this far from peak")
    p.set_defaults(func=cmd_paper)

    o = sub.add_parser("options", help="price options / explore strategy payoffs")
    o.add_argument("action", help="price | covered_call | cash_secured_put | bull_call_spread | "
                                  "bull_put_spread | iron_condor | long_call | long_put")
    o.add_argument("--spot", type=float, default=500.0)
    o.add_argument("--strike", type=float, default=500.0, help="used by 'price'")
    o.add_argument("--width", type=float, default=10.0, help="distance between strikes for strategies")
    o.add_argument("--days", type=float, default=30)
    o.add_argument("--vol", type=float, default=0.18, help="implied volatility, 0.18 = 18%%")
    o.add_argument("--rate", type=float, default=0.04)
    o.add_argument("--div", type=float, default=0.013)
    o.set_defaults(func=cmd_options)
    return ap


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
