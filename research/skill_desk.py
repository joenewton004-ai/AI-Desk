"""The trader-skill desk backtested: day-trader-skill's opening-range rules on ten years of Alpaca 5-minute bars.

    python research/skill_desk.py      (needs the 5-minute caches from research/alpaca_bars.py --5min, as ict_long.py)

The live ledger's rules exactly (ai_desk/skill_desk.py: 15-minute range, buy the next open after the first 5-minute
close above it, stop at the range middle, target 2R, flat by 15:55, $50 max loss a trade, $4,000 an order, 3 trades a
day, -$150 daily limit, a $5,000 account) on the 100 largest US companies at each date (the latest quarter-end known
45 days earlier, as ict_long.py), 2016-2026. Fixed before running:
  - the account compounds from $5,000; cash earns T-bills overnight; Sharpe of daily returns above T-bills
  - costs 0.02% each way (large caps), and 0.05% as a stress
  - variants: target 1R (the README's worked example), and no daily limits (every breakout, 1 share-equivalent
    per trade - the rule's own average R, without the account's choices)
  - halves 2016-20 / 2021-26; SPY buy-and-hold over the same days for comparison
Survivors-only: a company Alpaca has no bars for (renamed or delisted) is skipped and counted.
Writes research/output/skill_desk.md.
"""

from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "research"))

import alpaca_bars  # noqa: E402
import ict  # noqa: E402
import ict_long  # noqa: E402
from ai_desk import skill_desk as sd  # noqa: E402

OUT = Path(__file__).resolve().parent / "output"
START, END = ict_long.START, ict_long.END
SPLIT = pd.Timestamp("2021-01-01")


def hits_by_day(cfgs: dict[str, dict]) -> tuple[dict[str, dict], list[str], int]:
    """{variant: {day: [breakouts of member stocks]}} for every cached stock; plus the missing names."""
    snaps = ict.snapshots()
    spy = alpaca_bars.bars("SPY", timeframe="5Min", extended=True)
    days = pd.DatetimeIndex(sorted(set(alpaca_bars.regular_session(spy).index.normalize())))
    days = days[(days >= pd.Timestamp(START)) & (days <= pd.Timestamp(END))]
    member = ict_long.members_by_day(snaps, days)
    out = {v: {} for v in cfgs}
    missing, used = [], 0
    for k, sym in enumerate(ict_long.universe(snaps)):
        path = ict.CACHE / f"alpaca_5m_{sym.replace('-', '.')}.pkl"
        b5 = pd.read_pickle(path) if path.exists() else None
        if b5 is None or b5.empty:
            missing.append(sym)
            continue
        used += 1
        b5 = alpaca_bars.regular_session(b5.loc[START:f"{END} 23:59"])
        for d, g in b5.groupby(b5.index.normalize()):
            m = member.get(d)
            if m is None or sym not in m[1]:
                continue
            for v, cfg in cfgs.items():
                x = sd.breakout(g, cfg)
                if x:
                    out[v].setdefault(d, []).append(dict(symbol=sym, **x))
        if k % 25 == 0:
            print(f"  {k} stocks", flush=True)
    return out, missing, used, days


def run(hits: dict, days: pd.DatetimeIndex, cfg: dict) -> tuple[pd.DataFrame, pd.Series]:
    """The account day by day: trades and the daily return (P&L / equity at the open)."""
    eq, rows, rets = cfg["budget"], [], {}
    for d in days:
        tr = sd.allocate(hits.get(d, []), eq, cfg)
        pnl = sum(x["pnl"] for x in tr)
        rets[d] = pnl / eq
        eq += pnl
        rows += [dict(date=d, **x) for x in tr]
    return pd.DataFrame(rows), pd.Series(rets)


def perf(r: pd.Series, rf: pd.Series) -> dict:
    total = r + rf.reindex(r.index).fillna(0.0)                 # cash earns T-bills while flat (all night)
    eq = (1 + total).cumprod()
    yrs = len(r) / 252
    sh = r.mean() / r.std() * np.sqrt(252) if r.std() > 0 else np.nan
    se = np.sqrt((1 + sh ** 2 / 2) / yrs) if np.isfinite(sh) else np.nan
    return {"cagr": eq.iloc[-1] ** (1 / yrs) - 1, "sharpe": sh, "lo": sh - 1.96 * se, "hi": sh + 1.96 * se,
            "worst": (eq / eq.cummax() - 1).min()}


def main() -> None:
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    lines: list[str] = []

    def emit(s=""):
        print(s, flush=True)
        lines.append(s)

    cfgs = {"2R (live)": dict(sd.CONFIG), "1R": dict(sd.CONFIG, target_r=1.0)}
    hits, missing, used, days = hits_by_day(cfgs)
    from ai_desk.data import load_cash_rate
    rf = (load_cash_rate(str(ROOT / "market_data" / "SPY.csv")).reindex(days).ffill().bfill() / 252)
    spy = pd.read_csv(ROOT / "market_data" / "SPY.csv", index_col=0, parse_dates=True)["close"].reindex(days)
    spy_r = spy.pct_change().fillna(0.0)

    emit("# The trader-skill desk, backtested - generated tables\n")
    emit(f"Top 100 US companies at each date, Alpaca 5-minute bars {START} to {END}; {used} stocks with bars, "
         f"{len(missing)} without (skipped: {', '.join(missing[:12])}{' ...' if len(missing) > 12 else ''}). "
         "$5,000 account compounding, T-bills on cash overnight, Sharpe above T-bills (95% range). "
         "**Survivors-only.**\n")
    emit("| rules | costs | period | trades | trades/yr | win rate | avg R (before costs) | avg P&L | return/yr | Sharpe (range) | "
         "worst drop |")
    emit("|---|---|---|---|---|---|---|---|---|---|---|")
    for v, cfg0 in cfgs.items():
        for cost in (0.0002, 0.0005):
            cfg = dict(cfg0, cost=cost)
            tr, r = run(hits[v], days, cfg)
            for label, a, b in (("2016-2026", days[0], days[-1]), ("2016-20", days[0], SPLIT),
                                ("2021-26", SPLIT, days[-1])):
                rr = r.loc[a:b]
                t = tr[(tr["date"] >= a) & (tr["date"] < b + pd.Timedelta(days=1))] if len(tr) else tr
                p = perf(rr, rf)
                emit(f"| {v} | {cost:.2%} | {label} | {len(t):,} | {len(t) / (len(rr) / 252):.0f} | "
                     f"{(t['pnl'] > 0).mean():.0%} | {t['R'].mean():+.3f} | ${t['pnl'].mean():+.2f} | "
                     f"{p['cagr']:+.1%} | {p['sharpe']:.2f} ({p['lo']:.2f} to {p['hi']:.2f}) | {p['worst']:.0%} |")
    p = perf(spy_r - rf, rf)
    emit(f"| SPY buy and hold | - | 2016-2026 | - | - | - | - | - | {p['cagr']:+.1%} | {p['sharpe']:.2f} | "
         f"{p['worst']:.0%} |")

    emit("\n## Every breakout, before the account's limits (the rule's own edge)\n")
    emit("| rules | period | breakouts | avg return after 0.02% each way | t | avg R (before costs) | stop / target / flat_by |")
    emit("|---|---|---|---|---|---|---|")
    for v in cfgs:
        allx = pd.DataFrame([dict(date=d, **x) for d, xs in hits[v].items() for x in xs])
        allx["ret"] = allx["exit"] / allx["entry"] - 1 - 2 * 0.0002
        allx["R"] = (allx["exit"] - allx["entry"]) / allx["risk"]
        for label, m in (("2016-2026", allx["date"] >= days[0]), ("2016-20", allx["date"] < SPLIT),
                         ("2021-26", allx["date"] >= SPLIT)):
            x = allx[m]
            daily = x.groupby("date")["ret"].mean()
            t = daily.mean() / daily.std() * np.sqrt(len(daily))
            why = x["exit_why"].value_counts(normalize=True)
            emit(f"| {v} | {label} | {len(x):,} | {x['ret'].mean():+.3%} | {t:.1f} | {x['R'].mean():+.3f} | "
                 f"{why.get('stop', 0):.0%} / {why.get('target', 0):.0%} / {why.get('flat_by', 0):.0%} |")

    OUT.mkdir(exist_ok=True)
    (OUT / "skill_desk.md").write_text("\n".join(lines) + "\n")
    print(f"\nwrote {OUT / 'skill_desk.md'}")


if __name__ == "__main__":
    main()
