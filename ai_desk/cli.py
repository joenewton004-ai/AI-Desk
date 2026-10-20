"""Command line interface.  Run `python -m ai_desk --help`."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

from ai_desk.backtest import CostModel, run_backtest
from ai_desk.data import add_required_columns, load_cash_rate, load_prices
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
    p.add_argument("--cash-rate", default="auto",
                   help="interest on cash: auto (T-bill rate from ^IRX), none, or a fixed rate like 0.03")


def _risk(a) -> RiskConfig:
    return RiskConfig(target_vol=a.target_vol, max_leverage=a.max_leverage, max_drawdown_halt=a.max_dd_halt)


def _costs(a) -> CostModel:
    return CostModel(a.commission_bps, a.slippage_bps)


def _load(a, strategy_names) -> pd.DataFrame:
    """Price table plus any extra columns (e.g. VIX) the strategies need."""
    prices = load_prices(a.symbol, a.start, a.end, a.source)
    needed = {c for n in strategy_names for c in STRATEGIES[n].requires}
    return add_required_columns(prices, sorted(needed), a.source) if needed else prices


def _cash(a):
    if a.cash_rate == "none":
        return None
    if a.cash_rate == "auto":
        try:
            return load_cash_rate(a.source)
        except Exception as e:  # noqa: BLE001 - interest is a refinement, don't fail the run
            print(f"[!] couldn't load T-bill rates ({e}); cash earns 0%")
            return None
    return float(a.cash_rate)


def _warmup_start(prices: pd.DataFrame, days: int = 250):
    """Skip the first ~year so long averages have data before trading begins."""
    return prices.index[min(days, len(prices) - 2)]


def cmd_backtest(a) -> None:
    names = list(STRATEGIES) if a.strategy == "all" else [a.strategy, "buy_hold"]
    prices = _load(a, names)
    start = _warmup_start(prices)
    params = parse_params(a.param)
    rows, results = {}, {}
    cash = _cash(a)
    for name in dict.fromkeys(names):
        strat = get_strategy(name, **(params if name == a.strategy else {}))
        # the benchmark is always plain buy & hold, with no risk overlay
        risk = RiskConfig() if name == "buy_hold" else _risk(a)
        res = run_backtest(prices, strat, risk, _costs(a), start=start, cash_rate=cash)
        rows[name] = res.metrics
        results[name] = res
        if res.halted_on is not None:
            print(f"[!] {name}: drawdown circuit breaker tripped on {res.halted_on.date()}")
    print(f"\n{a.symbol}  ({a.source})  costs={a.commission_bps + a.slippage_bps:.1f}bps/trade  "
          f"cash earns {'T-bill rate' if isinstance(cash, pd.Series) else f'{cash or 0:.1%}'}  "
          f"(sharpe/sortino measured above that rate)\n")
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

    prices = _load(a, [a.strategy])
    start = _warmup_start(prices)
    params = parse_params(a.param)
    cash = _cash(a)
    res = split_test(prices, a.strategy, params, a.split, _risk(a), _costs(a), start=start, cash_rate=cash)
    print(f"\n{get_strategy(a.strategy, **params).describe()}  split at {a.split}\n")
    print(format_table({k: v.metrics for k, v in res.items()}))
    if a.grid:
        print("\nParameter sensitivity (IN-SAMPLE only). Look for a broad plateau, not one lucky peak:\n")
        table = param_sensitivity(prices, a.strategy, parse_grid(a.grid), _risk(a), _costs(a),
                                  start=start, end=pd.Timestamp(a.split) - pd.Timedelta(days=1), cash_rate=cash)
        print(table.to_string(index=False, float_format=lambda x: f"{x:.3f}"))


def cmd_walkforward(a) -> None:
    from ai_desk.validation import walk_forward

    prices = _load(a, [a.strategy])
    cash = _cash(a)
    wf = walk_forward(prices, a.strategy, parse_grid(a.grid), a.train_years, a.test_years,
                      a.metric, _risk(a), _costs(a), cash_rate=cash)
    bench = run_backtest(prices, get_strategy("buy_hold"), RiskConfig(), _costs(a),
                         start=wf.equity.index[0], cash_rate=cash)
    print("\nParameters chosen in each window (each test year traded blind):\n")
    print(wf.windows.to_string(index=False, float_format=lambda x: f"{x:.3f}"))
    print("\nStitched out-of-sample performance vs buy & hold:\n")
    print(format_table({f"{a.strategy} (OOS)": wf.metrics, "buy_hold": bench.metrics}))


def cmd_paper(a) -> None:
    from ai_desk.live import run_paper

    demo = a.source == "synthetic"   # offline demo: old fake data, so skip the freshness check
    start = "2000-01-01" if demo else (pd.Timestamp.today() - pd.DateOffset(years=2)).date().isoformat()
    prices = load_prices(a.symbol, start, None, a.source)
    strat = get_strategy(a.strategy, **parse_params(a.param))
    if strat.requires:
        prices = add_required_columns(prices, strat.requires, a.source)
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


def cmd_fetch(a) -> None:
    """Download daily bars to market_data/<SYMBOL>.csv so they can be committed
    and shared (e.g. with a cloud session that can't reach Yahoo)."""
    import yfinance as yf

    from ai_desk.data import _normalise

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for symbol in a.symbols:
        raw = yf.Ticker(symbol).history(start=a.start, end=a.end, auto_adjust=True)
        if raw.empty:
            print(f"  {symbol}: no data returned - skipped")
            continue
        df = _normalise(raw)
        path = out / f"{symbol.upper().lstrip('^')}.csv"
        df.to_csv(path, float_format="%.6f")
        print(f"  {symbol}: {len(df)} days {df.index[0].date()} -> {df.index[-1].date()}  saved {path}")


def cmd_screen(a) -> None:
    from datetime import date

    from ai_desk.fundamentals import filters
    from ai_desk.fundamentals.metrics import compute_all
    from ai_desk.fundamentals.scoring import score
    from ai_desk.fundamentals.universe import large_caps
    from ai_desk.fundamentals.yahoo import fetch_many, price_momentum

    if a.tickers:
        symbols = [t.upper() for t in a.tickers]
    else:
        print(f"Building universe: US-listed companies above ${a.min_cap / 1e9:.0f}B ...")
        symbols = large_caps(a.min_cap)["symbol"].tolist()
    print(f"Fetching fundamentals for {len(symbols)} companies (cached for a week) ...")
    companies = fetch_many(symbols, max_age_days=0 if a.refresh else 7, workers=a.workers)
    df = compute_all(companies)

    gates = None if a.no_gates else ({"min_roic_avg": a.min_roic} if a.min_roic is not None else {})
    df, notes = filters.apply(df, gates)
    if a.max_forward_pe is not None:
        df = df[df["forward_pe"] <= a.max_forward_pe]
        notes.append(f"kept only forward P/E <= {a.max_forward_pe:g}")
    if gates is not None:
        notes.append("gates: avg ROIC >= {min_roic_avg:.0%}, no negative-ROIC year, revenue up in most years, "
                     "positive FCF (--no-gates to rank everything)".format(**{**filters.DEFAULT_GATES, **gates}))

    if not a.no_history:
        df, history_notes = long_run_filter(df, a.allow_unverified)
        notes += history_notes

    print("Fetching 12-month price momentum ...")
    df["momentum_12_1"] = price_momentum(df.index.tolist()).reindex(df.index)
    ranked = score(df, parse_params(a.weight))

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    stem = out / f"screen_{date.today().isoformat()}"
    ranked.to_csv(f"{stem}.csv")
    md = screen_report(ranked.head(a.top), len(ranked), notes)
    Path(f"{stem}.md").write_text(md)
    print("\n" + md)
    print(f"Full results ({len(ranked)} companies, every metric): {stem}.csv")


def long_run_filter(df: pd.DataFrame, allow_unverified: bool = False) -> tuple[pd.DataFrame, list[str]]:
    from ai_desk.fundamentals import filters
    from ai_desk.fundamentals.edgar import annual_history, ticker_map

    print("10-year check: loading SEC filings (cached; the first run takes several minutes) ...")
    from concurrent.futures import ThreadPoolExecutor

    ciks = ticker_map()

    def load(sym):
        cik = ciks.get(sym.upper())
        try:
            return annual_history(cik) if cik else None
        except Exception as e:  # noqa: BLE001 - one bad filing shouldn't stop the screen
            print(f"  [!] {sym}: SEC history failed ({str(e)[:60]})")
            return None

    # parallel downloads; edgar's shared rate limiter keeps them under the SEC's cap
    with ThreadPoolExecutor(max_workers=6) as pool:
        histories = dict(zip(df.index, pool.map(load, df.index)))
    return filters.apply_long_run(df, histories, allow_unverified=allow_unverified)


def screen_report(top: pd.DataFrame, n_total: int, notes: list[str]) -> str:
    def pct(v):
        return f"{v:.0%}" if pd.notna(v) else "n/a"

    lines = [f"# Stock screen - {pd.Timestamp.today().date()}", "",
             f"Top {len(top)} of {n_total} companies. Scores are percentiles vs the universe (100 = best).", ""]
    lines += [f"- {n}" for n in notes] + [""]
    lines += ["| # | symbol | name | score | quality | growth | value | strength | momentum | "
              "avg ROIC | revenue growth | fwd P/E | FCF yield |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for i, (sym, r) in enumerate(top.iterrows(), 1):
        pe = f"{r['forward_pe']:.0f}" if pd.notna(r["forward_pe"]) else "n/a"
        lines.append(f"| {i} | {sym} | {str(r['name'])[:28]} | {r['score']:.0f} | {r['quality_score']:.0f} | "
                     f"{r['growth_score']:.0f} | {r['value_score']:.0f} | {r['strength_score']:.0f} | "
                     f"{r['momentum_score']:.0f} | {pct(r['roic_avg'])} | {pct(r['rev_cagr'])} | {pe} | "
                     f"{pct(r['fcf_yield'])} |")
    lines += ["", "## Why each company ranks where it does", ""]
    for i, (sym, r) in enumerate(top.iterrows(), 1):
        lines.append(f"**{i}. {sym} - {r['name']}** ({r['industry']})")
        lines.append(f"- strengths: {r['strengths'] or 'none in the top 20%'}")
        lines.append(f"- weaknesses: {r['weaknesses'] or 'none in the bottom 20%'}")
        if "long_run" in r and r["long_run"] != "pass":
            lines.append(f"- 10-year check: {r['long_run']} ({r['long_run_detail']})")
        elif "long_run" in r:
            lines.append(f"- 10-year check: passed ({r['long_run_detail']})")
        if r.get("data_flags"):
            lines.append(f"- ⚠ data check: {r['data_flags']}")
        if r["data_coverage"] < 0.8:
            lines.append(f"- note: only {r['data_coverage']:.0%} of metrics available")
        lines.append("")
    lines.append("_A research shortlist, not buy recommendations. Check each business yourself._")
    return "\n".join(lines)


def cmd_portfolio(a) -> None:
    from ai_desk.data import load_many
    from ai_desk.portfolio import executor
    from ai_desk.portfolio.backtest import buy_and_hold, run_portfolio_backtest
    from ai_desk.portfolio.methods import build

    params = parse_params(a.param)
    if getattr(a, "rebalance", False):
        params["quality_screen.rebalance"] = True
    method = build(a.method, params)
    print(f"\nmethod: {method.describe()}")

    if a.action == "backtest":
        prices = load_many(method.symbols(), a.start, a.end, a.source)
        start = prices["close"].index[min(260, len(prices["close"]) - 2)]   # let long averages warm up
        kw = dict(costs=_costs(a), cash_rate=_cash(a), start=start)
        res = run_portfolio_backtest(method, prices, **kw)
        bench = buy_and_hold(method.symbols(), prices, **kw)
        rows = {"method": res.metrics, "buy & hold (same symbols)": bench.metrics}
        if a.split:
            for label, sl in (("in-sample", slice(None, a.split)), ("out-of-sample", slice(a.split, None))):
                from ai_desk.metrics import daily_rf, summarize
                for name, r in (("method", res), ("buy & hold", bench)):
                    eq = r.equity.loc[sl]
                    rows[f"{name}, {label}"] = summarize(eq, rf_daily=daily_rf(_cash(a), eq.index))
        print(f"{len(method.symbols())} symbols, {a.source}, costs {a.commission_bps + a.slippage_bps:.1f}bps\n")
        print(format_table(rows))
        return

    limits = executor.Limits(max_position=a.max_position, max_gross=a.max_gross, max_order=a.max_order_pct,
                             allow_short=method.can_short and not a.no_short,
                             max_fund_position=a.max_fund_position, fractional=not a.whole_shares,
                             cash_buffer=a.cash_buffer)
    plan = executor.run(method, limits, execute=(a.action == "run" and a.execute), source=a.source)
    for note in plan.notes:
        print(f"  - {note}")
    if not plan.orders:
        print("  no orders needed - the account already matches the targets")
    for o in plan.orders:
        flag = f"  BLOCKED: {o.blocked}" if o.blocked else ""
        print(f"  {o.side:4} {o.qty:>10g} {o.symbol:6} ~${o.notional:>11,.0f}   {o.reason}{flag}")
    sent = a.action == "run" and a.execute
    print(f"\n{'SUBMITTED' if sent else 'DRY RUN - nothing sent'} ({len(plan.sendable)} orders). "
          f"Logged to {executor.JOURNAL}")
    if not sent:
        print("To send them to your Alpaca PAPER account: add  run --execute")


def cmd_broker(a) -> None:
    """Check the Alpaca PAPER connection and explain any failure in plain terms."""
    import requests

    from ai_desk.broker.alpaca import PAPER_URL, AlpacaPaper

    try:
        client = AlpacaPaper()
        s = client.status()
    except RuntimeError as e:                        # live keys
        sys.exit(f"Not connected: {e}")
    except requests.HTTPError as e:
        code = e.response.status_code if e.response is not None else "?"
        if code in (401, 403) and client.injected:
            hint = ("no keys reached Alpaca. Locally: set APCA_API_KEY_ID and APCA_API_SECRET_KEY in .env. "
                    "In a cloud session: add a network secret for paper-api.alpaca.markets with headers "
                    "APCA-API-KEY-ID and APCA-API-SECRET-KEY (no prefix), then start a new session")
        elif code in (401, 403):
            hint = ("the keys were rejected - check they are PAPER keys (start with 'PK') and were copied "
                    "whole; regenerating them in the Alpaca dashboard invalidates old ones")
        else:
            hint = "unexpected response from Alpaca"
        sys.exit(f"Not connected (HTTP {code}): {hint}")
    except requests.RequestException as e:
        sys.exit(f"Not connected: can't reach {PAPER_URL.split('/v2')[0]} ({type(e).__name__}). If this is a cloud "
                 "session, add paper-api.alpaca.markets to the environment's allowed network domains.")
    via = "keys added by the environment's network secret" if client.injected else "keys from .env / environment"
    print(f"\nConnected to Alpaca PAPER account {s['account']} (status: {s['status']}; {via})")
    print(f"  equity ${s['equity']:,.2f}   cash ${s['cash']:,.2f}   buying power ${s['buying_power']:,.2f}")
    print(f"  shorting enabled: {s['shorting_enabled']}   trading blocked: {s['trading_blocked']}")
    print(f"  market open now: {s['market_open']}   next open: {s['next_open']}")
    print(f"  positions: {len(s['positions'])}   open orders: {s['open_orders']}")
    for sym, qty in sorted(s["positions"].items()):
        print(f"    {sym:6} {qty:+g}")


def cmd_bottleneck(a) -> None:
    from ai_desk.bottleneck.scan import report, run_scan

    theme = None if a.theme == "none" else a.theme
    print(f"Bottleneck scan (theme: {theme or 'none - money flow only'}) ...")
    result = run_scan(theme=theme, top_industries=a.top_industries, min_cap=a.min_cap,
                      with_backlog=not a.no_backlog, theme_only=a.theme_only, ma_days=a.ma)
    path = report(result, top=a.top)
    print("\n" + path.read_text())
    print(f"Saved {path} and {path.with_suffix('.csv')}")


def cmd_journal(a) -> None:
    from ai_desk import register, tradebook

    if a.action == "sync":
        from ai_desk.broker.alpaca import AlpacaPaper
        n = tradebook.sync_fills(AlpacaPaper())
        print(f"Updated {n} orders from Alpaca. {sum(1 for t in tradebook.trades() if t.get('fill_price'))} "
              f"of {len(tradebook.trades())} trades have fills.")
    elif a.action == "review":
        from ai_desk.broker.alpaca import AlpacaPaper
        broker = AlpacaPaper()
        tradebook.sync_fills(broker)
        r = tradebook.review(broker.latest_prices(), float(broker.account()["equity"]))
        register.register()
        print(f"\nEquity ${r['equity']:,.2f} | {r['trades_logged']} trades logged | {r['notes']} notes")
        print(f"{'sleeve':16} {'open':>5} {'invested':>11} {'unrealized':>11} {'realized':>10} {'closed':>7} {'win rate':>9}")
        for s, v in r["by_sleeve"].items():
            wr = "n/a" if v["win_rate"] is None else f"{v['win_rate']:.0%}"
            print(f"{s:16} {v['open_positions']:>5} {v['invested']:>11,.0f} {v['unrealized_pnl']:>+11,.0f} "
                  f"{v['realized_pnl']:>+10,.0f} {v['closed_trades']:>7} {wr:>9}")
        print("\nSaved journal/review.json and journal/methods.json")
    elif a.action == "snapshot":
        from ai_desk import scorecard
        from ai_desk.broker.alpaca import AlpacaPaper
        broker = AlpacaPaper()
        n = tradebook.sync_fills(broker)
        row = scorecard.snapshot(broker)
        by = {}
        for h in row["holdings"].values():
            by[h["sleeve"] or "unassigned"] = by.get(h["sleeve"] or "unassigned", 0) + h["qty"] * (h["price"] or 0)
        print(f"Snapshot {row['date']}: equity ${row['equity']:,.2f}, cash ${row['cash']:,.2f} "
              f"({n} orders synced)")
        for k, v in sorted(by.items()):
            print(f"  {k:16} ${v:,.0f}")
    elif a.action == "scorecard":
        from ai_desk import scorecard
        from ai_desk.broker.alpaca import AlpacaPaper
        out = scorecard.build(AlpacaPaper())
        d = out["desk"]
        print(f"Since {out['launch']} ({d['days']} trading days): desk {d['total_return']:+.2%}, "
              f"SPY {out['spy']['total_return']:+.2%}, equal-weight S&P {out['rsp']['total_return']:+.2%}")
        for r in out["scorecard"]:
            v = r["value"]
            shown = "n/a" if v is None else (f"{v:+.2%}" if r["format"] == "pct" else
                                             f"{v:.1f}" if r["format"] in ("bps", "num") else f"{v:g}")
            print(f"  [{r['status']:9}] {r['tier']:11} {r['metric']:45} {shown:>9}  target {r['target']}")
        print("\nSaved journal/scorecard.json")
    elif a.action == "watchlist":
        from ai_desk import watchlist
        from ai_desk.portfolio.methods import build
        new = watchlist.sync(build(["desk"]))
        for c in new:
            print(f"Saved cohort {c['id']}: {len(c['rows'])} companies from {c['screen_file']}")
        out = watchlist.review()
        for s in out["summary"]:
            if not s.get("current"):
                continue
            f = lambda v: "n/a" if v is None else f"{v:+.2%}"  # noqa: E731
            print(f"\n{s['cohort']} (from the {s['ref_date']} close, {s['days']} trading days)")
            print(f"  picks ({s['picks']}) {f(s['picks_avg'])} | near misses {f(s['near_miss_avg'])} | "
                  f"failed a gate {f(s['failed_gate_avg'])} | SPY {f(s['spy'])}")
            print(f"  {s['watch_beating_picks']} of {s['watching']} watched stocks are beating the picks' average; "
                  f"best: {s['best_symbol']} {f(s['best_return'])}")
        print("\nSaved journal/watchlist.json and journal/watchlist_review.json")
    elif a.action == "export":
        from ai_desk import dashboard
        counts = dashboard.export()
        print("Saved journal/dashboard/: " + ", ".join(f"{k} ({v} rows)" for k, v in counts.items()))
    elif a.action == "note":
        row = tradebook.add_note(a.target, a.text, author=a.author)
        print(f"note {row['id']} added to {a.target}")
    elif a.action == "methods":
        reg = register.register()
        print(f"Live mix ({reg['live_preset']}): " + ", ".join(f"{k} {v:.0%}" for k, v in reg["live_allocation"].items()))
        for m in reg["methods"]:
            print(f"\n{m['name']} [{m['status']}]{' - LIVE ' + format(m['allocation'], '.0%') if m['in_live_mix'] else ''}")
            print(f"  {m['description']}")
            print(f"  parameters: {m['parameters']}")
            print(f"  evidence: {m['evidence_summary']}")
    elif a.action == "propose":
        row = register.propose(a.target, a.text, a.rationale or "", author=a.author)
        print(f"amendment {row['id']} proposed for {a.target}")
    elif a.action == "decide":
        row = register.decide(a.target, a.status, a.text or "")
        print(f"amendment {row['id']} -> {row['status']}")
    elif a.action == "amendments":
        for r in register.amendments():
            print(f"{r['id']} [{r['status']:8}] {r['method']}: {r['proposal']}  ({r['author']}, {r['created_utc'][:10]})")


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

    sc = sub.add_parser("screen", help="rank companies on quality, growth, value, strength, momentum")
    sc.add_argument("--min-cap", type=float, default=10e9, help="minimum market cap in $ (default 10e9)")
    sc.add_argument("--tickers", nargs="+", help="screen these symbols instead of the universe")
    sc.add_argument("--top", type=int, default=25)
    sc.add_argument("--weight", action="append",
                    help="category weight, e.g. quality=0.5 (categories: quality growth value strength momentum)")
    sc.add_argument("--min-roic", type=float, default=None, help="minimum average ROIC gate (default 0.12)")
    sc.add_argument("--no-gates", action="store_true",
                    help="rank every company, not just ones passing the great-business gates")
    sc.add_argument("--max-forward-pe", type=float, default=None, help="hard filter, e.g. 35")
    sc.add_argument("--no-history", action="store_true",
                    help="skip the 10-year SEC check (faster, but lets cyclical peaks through)")
    sc.add_argument("--allow-unverified", action="store_true",
                    help="keep companies with no SEC filings to check (mostly foreign filers)")
    sc.add_argument("--refresh", action="store_true", help="ignore the cache and re-download")
    sc.add_argument("--workers", type=int, default=2, help="parallel downloads (Yahoo throttles above ~4)")
    sc.add_argument("--out", default="output")
    sc.set_defaults(func=cmd_screen)

    pf = sub.add_parser("portfolio", help="multi-stock methods: backtest, plan or run on Alpaca paper")
    pf.add_argument("action", choices=["backtest", "plan", "run"],
                    help="backtest | plan (dry run vs your paper account) | run (add --execute to trade)")
    pf.add_argument("--method", action="append", required=True,
                    help="index_momentum | sma_crossover | pairs | quality_screen | thesis | aggressive; blend with "
                         "name:share, e.g. --method quality_screen:0.5 --method index_momentum:0.5")
    pf.add_argument("--param", action="append",
                    help="method settings, e.g. symbols=SPY,QQQ  pairs.entry_z=2.5  pairs=V/MA,KO/PEP")
    _common(pf)
    pf.set_defaults(source="yahoo", start="2005-01-01")
    pf.add_argument("--split", default=None, help="backtest: also report before/after this date")
    pf.add_argument("--max-position", type=float, default=0.10, help="largest single stock (fraction)")
    pf.add_argument("--max-fund-position", type=float, default=0.60,
                    help="largest holding in a broad index fund like SPY (fraction)")
    pf.add_argument("--max-gross", type=float, default=1.0, help="max sum of |weights| (1.0 = no leverage)")
    pf.add_argument("--max-order-pct", type=float, default=0.25, help="largest single order (fraction)")
    pf.add_argument("--no-short", action="store_true", help="never open short positions")
    pf.add_argument("--whole-shares", action="store_true", help="don't use fractional shares")
    pf.add_argument("--cash-buffer", type=float, default=0.01,
                    help="fraction of equity always left in cash (default 0.01 = 1%%)")
    pf.add_argument("--execute", action="store_true", help="with `run`: actually submit to Alpaca PAPER")
    pf.add_argument("--rebalance", action="store_true",
                    help="re-pick the screen's stocks now instead of waiting for the quarterly date")
    pf.set_defaults(func=cmd_portfolio)

    bn = sub.add_parser("bottleneck", help="find bottleneck stocks in themes money is flowing into")
    bn.add_argument("action", choices=["scan"])
    bn.add_argument("--theme", default="ai_datacenter", help="theme map in bottleneck/themes.py, or 'none'")
    bn.add_argument("--top-industries", type=int, default=8, help="how many top money-flow industries to scan")
    bn.add_argument("--min-cap", type=float, default=10e9)
    bn.add_argument("--top", type=int, default=15)
    bn.add_argument("--no-backlog", action="store_true", help="skip SEC backlog data (faster)")
    bn.add_argument("--ma", type=int, default=100,
                    help="moving average (days) a stock must be above to buy; the sleeve sells below it")
    bn.add_argument("--theme-only", action="store_true",
                    help="only pick companies in the theme map (money-flow industries are still reported)")
    bn.set_defaults(func=cmd_bottleneck)

    jn = sub.add_parser("journal", help="trade journal, notes, methodology register and amendments")
    jn.add_argument("action", choices=["sync", "review", "note", "methods", "propose", "decide", "amendments", "export",
                                       "snapshot", "scorecard", "watchlist"])
    jn.add_argument("target", nargs="?", help="note: trade id / symbol / method; propose: method; decide: amendment id")
    jn.add_argument("text", nargs="?", help="note text, proposal text, or decision evidence")
    jn.add_argument("--rationale", help="propose: why")
    jn.add_argument("--status", choices=["proposed", "testing", "accepted", "rejected"], help="decide: new status")
    jn.add_argument("--author", default="you")
    jn.set_defaults(func=cmd_journal)

    bk = sub.add_parser("broker", help="check the Alpaca paper connection")
    bk.add_argument("action", choices=["status"])
    bk.set_defaults(func=cmd_broker)

    f = sub.add_parser("fetch", help="download daily prices to CSV files you can commit")
    f.add_argument("symbols", nargs="+", help="e.g. SPY QQQ TLT GLD ^VIX")
    f.add_argument("--start", default="1993-01-01")
    f.add_argument("--end", default=None)
    f.add_argument("--out", default="market_data")
    f.set_defaults(func=cmd_fetch)
    return ap


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
