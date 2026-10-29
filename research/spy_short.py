"""What if the desk shorted SPY? Short-side swing rules, a trend short, and an SPY hedge on the overnight sleeve.

    python research/spy_short.py      (market_data/SPY QQQ IWM DIA IRX .csv; the hedge part rebuilds the overnight
                                       sleeve from research/desk_rsi.py's data, ~5 minutes)

Shorting starts behind: SPY rose ~10%/yr since 1993, a short pays its dividends (the adjusted prices include them)
and a borrow fee (0.5%/yr assumed; SPY is easy to borrow). Costs 0.01% each way. Fixed before running:
1. Short swing rules (signal at a close, short at the next open, covered at the open after the exit close, at most
   5 days), the mirror images of the dip rules that work long (research/SWING_ETF.md):
     rally_below_200   RSI(2) > 90 while below the 200-day average; cover after a close below the 5-day average
     rally_any         RSI(2) > 90, no trend filter; same cover
     ten_day_high_down the highest close of 10 days while below the 200-day; 5 days
     three_up_down     three higher closes while below the 200-day; 5 days
     tweezer_top       the one candle pattern that passed in research/CANDLES_DAILY_SPY.md (found on this data -
                       not an independent test); 5 days
   PASS: the short makes money after costs in BOTH 1993-2009 and 2010-2026 with t >= 2, AND on QQQ, IWM and DIA
   pooled in both halves. (Unlike the long rules, the yardstick is zero, not holding: a short has to make money.)
2. Whole strategies on SPY, daily, T-bills on idle cash (and on the cash behind a short), Sharpe above T-bills:
   dips long only; dips long + the best short rule; long above the 200-day / cash below; long above / SHORT below;
   buy and hold.
3. The overnight sleeve (as live, research/desk_rsi.overnight_live) with and without an SPY short against it each
   night it's invested, sized by its beta to SPY's overnight move (estimated on 2014-2019, applied 2020-2026, so the
   test years don't set their own hedge). Costs of the hedge: 0.01% each way a night, plus the borrow fee.
Writes research/output/spy_short.md.
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

import swing_etf as se  # noqa: E402
from ai_desk.indicators import rsi  # noqa: E402

OUT = Path(__file__).resolve().parent / "output"
COST, BORROW = 0.0001, 0.005
SPLIT = "2010-01-01"
SHORTS = ["rally_below_200", "rally_any", "ten_day_high_down", "three_up_down", "tweezer_top"]


def short_signals(d: pd.DataFrame, rule: str) -> tuple[np.ndarray, np.ndarray | None]:
    """Pure: the signal at each close and the cover condition (or None for a fixed 5 days)."""
    o, h, c = d["open"], d["high"], d["close"]
    down = c < c.rolling(200).mean()
    cover = (c < c.rolling(5).mean()).to_numpy()
    if rule == "rally_below_200":
        return ((rsi(c, 2) > 90) & down).to_numpy(), cover
    if rule == "rally_any":
        return (rsi(c, 2) > 90).to_numpy(), cover
    if rule == "ten_day_high_down":
        return ((c >= c.rolling(10).max()) & down).to_numpy(), None
    if rule == "three_up_down":
        return ((c > c.shift(1)) & (c.shift(1) > c.shift(2)) & (c.shift(2) > c.shift(3)) & down).to_numpy(), None
    if rule == "tweezer_top":
        tw = (c > c.shift(5)) & (c.shift(1) > o.shift(1)) & (c < o) & ((h - h.shift(1)).abs() <= 0.001 * c)
        return tw.to_numpy(), None
    raise ValueError(rule)


def trades(d: pd.DataFrame, sig: np.ndarray, exit_: np.ndarray | None, side: int, hold: int = 5) -> pd.DataFrame:
    """Pure: one position at a time; `side` +1 long, -1 short. Short P&L pays costs and the borrow fee."""
    o = d["open"].to_numpy()
    rows, i, n = [], 0, len(d)
    while i < n - 1:
        if not sig[i]:
            i += 1
            continue
        e = i + 1
        x = min(e + hold, n - 1)
        if exit_ is not None:
            hit = np.nonzero(exit_[e:min(e + hold, n - 1)])[0]
            if len(hit):
                x = e + hit[0] + 1
        if x >= n or x <= e:
            break
        r = side * (o[x] / o[e] - 1) - 2 * COST - (BORROW * (x - e) / 252 if side < 0 else 0.0)
        rows.append((d.index[e], d.index[x], x - e, side, r))
        i = x
    return pd.DataFrame(rows, columns=["entry", "exit", "days", "side", "net"])


def positions(d: pd.DataFrame, tr: pd.DataFrame) -> pd.Series:
    """Daily position (open to next open): +1 / -1 while in a trade, 0 otherwise."""
    p = pd.Series(0.0, index=d.index)
    for r in tr.itertuples():
        p.loc[r.entry:r.exit] = r.side
        p.loc[r.exit] = 0.0
    return p


def perf(pos: pd.Series, d: pd.DataFrame, rf: pd.Series, start=None, end=None) -> dict:
    """Daily strategy: position x open-to-open return, T-bills on the cash (all of it when flat, and the collateral
    behind a short), less trading costs on each change and the borrow fee on short days."""
    oo = (d["open"].shift(-1) / d["open"] - 1).fillna(0.0)
    rfd = rf.reindex(d.index).ffill().fillna(0.0)
    turn = pos.diff().abs().fillna(pos.abs())
    r = pos * oo + rfd * (pos <= 0) + rfd * 0 - turn * COST - (pos < 0) * BORROW / 252
    r = r.loc[start:end]
    x = r - rfd.loc[r.index]
    eq = (1 + r).cumprod()
    yrs = len(r) / 252
    return {"cagr": eq.iloc[-1] ** (1 / yrs) - 1, "sharpe": x.mean() / x.std() * np.sqrt(252),
            "worst": (eq / eq.cummax() - 1).min(), "long": (pos.loc[r.index] > 0).mean(),
            "short": (pos.loc[r.index] < 0).mean()}


def t_of(x: pd.Series) -> float:
    return x.mean() / x.std() * np.sqrt(len(x)) if len(x) > 2 and x.std() > 0 else np.nan


def main() -> None:
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    lines: list[str] = []

    def emit(s=""):
        print(s, flush=True)
        lines.append(s)

    data = {s: se.load(s) for s in ("SPY", "QQQ", "IWM", "DIA")}
    irx = pd.read_csv(ROOT / "market_data" / "IRX.csv", index_col=0, parse_dates=True)["close"] / 100 / 252
    spy = data["SPY"]
    emit("# What if the desk shorted SPY? - generated tables\n")
    emit(f"Daily bars to {se.END} (adjusted, so a short pays the dividends). Costs 0.01% each way, borrow 0.5%/yr.\n")

    emit("## 1. Short-side swing rules (a short has to make money: the yardstick is zero)\n")
    emit("| rule | SPY shorts/yr | days held | win rate | avg per short | t | 1993-2009 | 2010-2026 | QQQ+IWM+DIA 1st / 2nd half | passes |")
    emit("|---|---|---|---|---|---|---|---|---|---|")
    yrs = (spy.index[-1] - spy.index[200]).days / 365.25
    best, best_t = None, -99
    for rule in SHORTS:
        sig, ex = short_signals(spy, rule)
        t = trades(spy, sig, ex, -1)
        oth = pd.concat([trades(data[s], *short_signals(data[s], rule), -1) for s in ("QQQ", "IWM", "DIA")])
        early, late = t["entry"] < pd.Timestamp(SPLIT), t["entry"] >= pd.Timestamp(SPLIT)
        oe_, ol_ = oth["entry"] < pd.Timestamp(SPLIT), oth["entry"] >= pd.Timestamp(SPLIT)
        tt = t_of(t["net"])
        ok = (t.loc[early, "net"].mean() > 0 and t.loc[late, "net"].mean() > 0 and tt >= 2
              and oth.loc[oe_, "net"].mean() > 0 and oth.loc[ol_, "net"].mean() > 0)
        if tt > best_t:
            best, best_t = rule, tt
        emit(f"| {rule} | {len(t) / yrs:.1f} | {t['days'].mean():.1f} | {(t['net'] > 0).mean():.0%} | {t['net'].mean():+.2%} | "
             f"{tt:.1f} | {t.loc[early, 'net'].mean():+.2%} | {t.loc[late, 'net'].mean():+.2%} | "
             f"{oth.loc[oe_, 'net'].mean():+.2%} / {oth.loc[ol_, 'net'].mean():+.2%} | {'**yes**' if ok else 'no'} |")

    emit(f"\n## 2. Whole strategies on SPY (the best short rule by t: {best})\n")
    c = spy["close"]
    dips = trades(spy, ((rsi(c, 2) < 10) & (c > c.rolling(200).mean())).to_numpy(), (c > c.rolling(5).mean()).to_numpy(), 1)
    shorts = trades(spy, *short_signals(spy, best), -1)
    long_short = pd.concat([dips, shorts]).sort_values("entry")
    above = (c > c.rolling(200).mean()).astype(float)
    trend_cash = above.shift(1).fillna(0.0)                       # decided at the close, held from the next open
    trend_short = (2 * above - 1).where(c.rolling(200).mean().notna(), 0.0).shift(1).fillna(0.0)
    strategies = {
        "buy and hold": pd.Series(1.0, index=spy.index),
        "dips long only (RSI(2) < 10 above the 200-day)": positions(spy, dips),
        f"dips long + {best} short": positions(spy, long_short),
        "above the 200-day: long; below: cash": trend_cash,
        "above the 200-day: long; below: SHORT": trend_short,
    }
    emit("| strategy | period | return/yr | Sharpe (above T-bills) | worst drop | long / short of the time |")
    emit("|---|---|---|---|---|---|")
    first = spy.index[200]
    for name, pos in strategies.items():
        for lbl, a, b in (("1993-2026", first, None), ("1993-2009", first, "2009-12-31"), ("2010-2026", SPLIT, None)):
            p = perf(pos, spy, irx, a, b)
            emit(f"| {name} | {lbl} | {p['cagr']:+.1%} | {p['sharpe']:.2f} | {p['worst']:.0%} | "
                 f"{p['long']:.0%} / {p['short']:.0%} |")

    emit("\n## 3. Hedging the overnight sleeve with an SPY short each night\n")
    import desk_rsi
    on, rf_on, inv = desk_rsi.overnight_live()
    spy_on = (spy["open"] / spy["close"].shift(1) - 1).reindex(on.index)   # SPY's own night, dated by the morning
    x = pd.DataFrame({"on": on - rf_on, "spy": spy_on, "inv": inv.reindex(on.index).fillna(False)}).dropna()
    fit = x[(x.index < pd.Timestamp("2020-01-01")) & x["inv"]]
    beta = np.polyfit(fit["spy"], fit["on"], 1)[0]
    hedge = (-beta * x["spy"] - beta * (2 * COST + BORROW / 252)).where(x["inv"], 0.0)
    emit(f"Beta of the sleeve's nights to SPY's night (2014-2019): {beta:.2f}. Hedge = short {beta:.2f}x SPY on each "
         "invested night, applied unchanged in 2020-2026.\n")
    emit("| version | period | return/yr | Sharpe (above T-bills) | worst drop |")
    emit("|---|---|---|---|---|")
    for name, r in (("overnight sleeve (as live)", on.reindex(x.index)),
                    ("overnight sleeve + SPY hedge", on.reindex(x.index) + hedge)):
        for lbl, a, b in (("2014-2026", None, None), ("2014-2019", None, "2019-12-31"), ("2020-2026", "2020-01-01", None)):
            rr = r.loc[a:b]
            ex = rr - rf_on.reindex(rr.index).fillna(0.0)
            eq = (1 + rr).cumprod()
            emit(f"| {name} | {lbl} | {eq.iloc[-1] ** (252 / len(rr)) - 1:+.1%} | {ex.mean() / ex.std() * np.sqrt(252):.2f} | "
                 f"{(eq / eq.cummax() - 1).min():.0%} |")
    OUT.mkdir(exist_ok=True)
    (OUT / "spy_short.md").write_text("\n".join(lines) + "\n")
    print(f"\nwrote {OUT / 'spy_short.md'}")


if __name__ == "__main__":
    main()
