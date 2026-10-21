"""Swing trading, tested: a rules-only version of the VCP breakout screen.

    python research/swing.py            (first run downloads daily prices; about 15 minutes)

The idea comes from the `vcp-screener` skill in tradermonty/claude-trading-skills, which follows
Mark Minervini's "volatility contraction pattern". In plain words: a stock in a strong uptrend
pauses, each pullback in the pause is smaller and quieter than the last, and then it breaks out
above the top of the pause on heavy volume. Here every part of it is a fixed rule:

  trend      close above its 50-, 150- and 200-day averages, 50 > 150 > 200, the 200-day average
             higher than a month ago, within 25% of its 52-week high, at least 30% above its low
  tight      the last 10 days' range is under half the range of the 50 days before it (the
             contraction), and recent volume is quieter than its 50-day average
  breakout   today's close is above the highest close of the previous 20 days, on volume at least
             1.5x the 50-day average
  entry      the next day's open (decided at today's close: no lookahead)
  exits      a stop 8% below the entry price, or a close below the 50-day average, or a profit
             target of +25%, or 40 trading days, whichever comes first. A close-based exit sells
             at the next open, so a gap can lose more than the stop
  book       up to 10 positions, 10% each, the rest in T-bills; if more breakouts than free slots,
             the ones with the biggest volume surge go first

Universe each day = the 750 largest US companies at the latest quarter-end (point-in-time,
data/backtest/snapshots_m*.pkl). Daily prices from Yahoo, adjusted, cached in
data/backtest/daily_ohlcv.pkl. Costs 0.10% per trade (stress 0.20% and 0.30%).

Things that flatter this (say so when quoting it):
  * survivors-only prices: breakouts that later collapsed and delisted are missing;
  * the volume and price data are Yahoo's, adjusted after the fact.

Writes research/output/swing.md; findings in research/SWING.md.
"""

from __future__ import annotations

import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ai_desk.data import load_cash_rate  # noqa: E402
from ai_desk.fundamentals.yahoo import with_retry  # noqa: E402

CACHE = ROOT / "data" / "backtest"
OUT = Path(__file__).resolve().parent / "output"
START, END = "2014-04-01", "2026-10-20"      # first point-in-time universe; last full trading day
MID = "2020-01-01"
COST = 0.001


def fetch_daily(tickers: list[str]) -> dict[str, pd.DataFrame]:
    """Daily adjusted open/high/low/close/volume, cached. Chunks of 100, a few threads (Yahoo throttles)."""
    path = CACHE / "daily_ohlcv.pkl"
    if path.exists():
        return pickle.loads(path.read_bytes())
    import yfinance as yf

    parts = {k: [] for k in ("open", "high", "low", "close", "volume")}
    for i in range(0, len(tickers), 100):
        chunk = tickers[i:i + 100]
        d = with_retry(lambda chunk=chunk: yf.download(chunk, start="2012-06-01", end="2026-10-21", interval="1d",
                                                       auto_adjust=True, progress=False, threads=4))
        for k in parts:
            parts[k].append(d[k.capitalize()])
        print(f"  daily prices {min(i + 100, len(tickers))}/{len(tickers)}", flush=True)
    out = {}
    for k, v in parts.items():
        df = pd.concat(v, axis=1, sort=True)
        df = df.loc[:, ~df.columns.duplicated()]
        df.index = pd.to_datetime(df.index).tz_localize(None)
        out[k] = df.astype("float32")
    path.write_bytes(pickle.dumps(out))
    return out


def universe_tickers() -> list[str]:
    u = pickle.loads((CACHE / "universe.pkl").read_bytes())
    return sorted(set(u.tickers.values()))


# --- pure pieces (unit-tested) --------------------------------------------------------

def signals(o: pd.DataFrame, h: pd.DataFrame, lo: pd.DataFrame, c: pd.DataFrame, v: pd.DataFrame,
            breakout_days: int = 20, vol_mult: float = 1.5, tight_ratio: float = 0.5) -> dict[str, pd.DataFrame]:
    """Everything decided at each day's close, from data up to that close only."""
    ma50, ma150, ma200 = (c.rolling(n, min_periods=n).mean() for n in (50, 150, 200))
    hi52 = h.rolling(252, min_periods=200).max()
    lo52 = lo.rolling(252, min_periods=200).min()
    trend = ((c > ma50) & (ma50 > ma150) & (ma150 > ma200) & (ma200 > ma200.shift(21))
             & (c >= 0.75 * hi52) & (c >= 1.30 * lo52))
    # the base before today: the last 10 days' range vs the 50 days before those
    rng10 = (h.rolling(10).max() - lo.rolling(10).min()).shift(1) / c.shift(1)
    rng_prior = (h.shift(11).rolling(50).max() - lo.shift(11).rolling(50).min()) / c.shift(11)
    vol50 = v.rolling(50, min_periods=40).mean().shift(1)
    quiet = v.rolling(10).mean().shift(1) < vol50
    tight = (rng10 < tight_ratio * rng_prior) & quiet
    breakout = (c > c.shift(1).rolling(breakout_days).max()) & (v >= vol_mult * vol50)
    liquid = (c > 10) & ((c * v).rolling(50, min_periods=40).mean() > 20e6)
    return {"trend": trend & liquid, "setup": trend & tight & breakout & liquid, "surge": v / vol50, "ma50": ma50}


def simulate(o: np.ndarray, c: np.ndarray, setup: np.ndarray, rank: np.ndarray, ma50: np.ndarray,
             rf: np.ndarray, dates, symbols, slots: int = 10, stop: float = 0.08, target: float | None = 0.25,
             max_days: int = 40, cost: float = COST, start: int = 0) -> tuple[pd.Series, pd.DataFrame]:
    """Event-driven daily book. Decisions at close t (setups, exits) fill at open t+1.
    Each new position gets 1/slots of current equity; the rest earns T-bills."""
    cash, pos = 1.0, {}          # pos[j] = dict(shares, entry, entry_i, entry_date)
    exits_due: dict[int, str] = {}
    entries_due: list[int] = []
    eq_out, trades = [], []
    for i in range(start, len(dates)):
        # 1) the open: fill yesterday's decisions
        for j, why in list(exits_due.items()):
            px = o[i, j] if np.isfinite(o[i, j]) else c[i - 1, j]
            p = pos.pop(j)
            cash += p["shares"] * px * (1 - cost)
            trades.append({"symbol": symbols[j], "entry_date": p["entry_date"], "exit_date": dates[i], "entry": p["entry"],
                           "exit": px, "return": px / p["entry"] * (1 - cost) ** 2 - 1, "days": i - p["entry_i"], "why": why})
        exits_due = {}
        if entries_due:
            equity = cash + sum(p["shares"] * c[i - 1, j] for j, p in pos.items())
            for j in entries_due:
                if len(pos) >= slots or not np.isfinite(o[i, j]) or o[i, j] <= 0:
                    continue
                spend = min(equity / slots, cash)
                if spend <= equity / slots * 0.2:      # less than a fifth of a slot left: stop buying
                    break
                pos[j] = {"shares": spend * (1 - cost) / o[i, j], "entry": o[i, j], "entry_i": i, "entry_date": dates[i]}
                cash -= spend
        entries_due = []
        # 2) the close: mark to market, earn cash interest, decide for tomorrow
        cash *= 1 + rf[i]
        equity = cash + sum(p["shares"] * (c[i, j] if np.isfinite(c[i, j]) else p["entry"]) for j, p in pos.items())
        eq_out.append(equity)
        for j, p in pos.items():
            px = c[i, j]
            if not np.isfinite(px):
                continue
            if px <= p["entry"] * (1 - stop):
                exits_due[j] = "stop"
            elif target is not None and px >= p["entry"] * (1 + target):
                exits_due[j] = "target"
            elif np.isfinite(ma50[i, j]) and px < ma50[i, j]:
                exits_due[j] = "below 50-day"
            elif i - p["entry_i"] + 1 >= max_days:
                exits_due[j] = "time"
        free = slots - len(pos) + len(exits_due)
        if free > 0:
            cand = np.flatnonzero(setup[i])
            cand = [j for j in cand if j not in pos]
            cand.sort(key=lambda j: -rank[i, j])
            entries_due = cand[:free]
    return pd.Series(eq_out, index=dates[start:]), pd.DataFrame(trades)


def trade_stats(t: pd.DataFrame) -> dict:
    if t.empty:
        return {"trades": 0}
    win, loss = t[t["return"] > 0]["return"], t[t["return"] <= 0]["return"]
    return {"trades": len(t), "win rate": len(win) / len(t), "avg win": win.mean() if len(win) else 0.0,
            "avg loss": loss.mean() if len(loss) else 0.0, "expectancy": t["return"].mean(),
            "profit factor": win.sum() / -loss.sum() if loss.sum() < 0 else np.inf, "avg days": t["days"].mean()}


def stats(eq: pd.Series, rf: pd.Series) -> dict:
    r = eq.pct_change().dropna()
    ex = r - rf.reindex(r.index).fillna(0)
    return {"CAGR": (eq.iloc[-1] / eq.iloc[0]) ** (252 / len(r)) - 1, "volatility": r.std() * np.sqrt(252),
            "Sharpe": ex.mean() / ex.std() * np.sqrt(252) if ex.std() > 0 else np.nan,
            "max drawdown": (eq / eq.cummax() - 1).min()}


def membership(snaps: dict[pd.Timestamp, list[str]], dates: pd.DatetimeIndex, symbols: list[str]) -> np.ndarray:
    """mask[i, j]: symbol j was in the latest quarter-end universe on or before dates[i]."""
    col = {s: k for k, s in enumerate(symbols)}
    mask = np.zeros((len(dates), len(symbols)), dtype=bool)
    keys = sorted(snaps)
    for a, b in zip(keys, keys[1:] + [pd.Timestamp.max]):
        rows = (dates >= a) & (dates < b)
        idx = [col[s] for s in snaps[a] if s in col]
        mask[np.ix_(rows, idx)] = True
    return mask


# --- the experiment ------------------------------------------------------------------

def main() -> None:
    lines: list[str] = []

    def emit(t=""):
        print(t, flush=True)
        lines.append(t)

    d = fetch_daily(universe_tickers())
    o, h, lo, c, v = (d[k].astype(float).loc[:END] for k in ("open", "high", "low", "close", "volume"))
    snaps = {}
    for m in (3, 6, 9, 12):
        snaps.update({k: list(s.index) for k, s in pickle.loads((CACHE / f"snapshots_m{m}.pkl").read_bytes()).items()})
    dates, symbols = c.index, list(c.columns)
    member = membership(dict(sorted(snaps.items())), dates, symbols)
    rf_rate = load_cash_rate(str(ROOT / "market_data" / "SPY.csv"))
    rf = (rf_rate.reindex(dates, method="ffill") / 252).shift(1).fillna(0)
    start = int(dates.searchsorted(pd.Timestamp(START)))
    arr = lambda df: df.to_numpy(dtype=float)  # noqa: E731
    O, C = arr(o), arr(c)

    cache_sig = {}

    def run(breakout_days=20, vol_mult=1.5, tight_ratio=0.5, control=False, **kw):
        key = (breakout_days, vol_mult, tight_ratio)
        if key not in cache_sig:
            s = signals(o, h, lo, c, v, breakout_days, vol_mult, tight_ratio)
            cache_sig[key] = (s["setup"].to_numpy() & member, s["trend"].to_numpy() & member,
                              s["surge"].to_numpy(dtype=float), arr(s["ma50"]))
        setup, trend, surge, ma50 = cache_sig[key]
        if control:          # same exits, but random trend-template stocks instead of breakouts
            rng = np.random.default_rng(7)
            n_set = setup.sum(axis=1)
            pick = np.zeros_like(trend)
            for i in range(len(dates)):
                cand = np.flatnonzero(trend[i])
                if n_set[i] and len(cand):
                    pick[i, rng.choice(cand, size=min(n_set[i], len(cand)), replace=False)] = True
            setup, surge = pick, rng.random(surge.shape)
        return simulate(O, C, setup, np.nan_to_num(surge), ma50, rf.to_numpy(), dates, symbols, start=start, **kw)

    base_eq, base_t = run()
    spy = pd.read_csv(ROOT / "market_data" / "SPY.csv", index_col=0, parse_dates=True)["close"].reindex(dates[start:]).ffill()
    uni_r = pd.Series(np.nanmean(np.where(member[start + 1:], C[start + 1:] / C[start:-1] - 1, np.nan), axis=1),
                      index=dates[start + 1:]).clip(-0.5, 0.5)
    uni = pd.concat([pd.Series([1.0], index=[dates[start]]), (1 + uni_r).cumprod()])

    emit("# Swing trading (VCP breakouts) - generated tables\n")
    emit(f"Daily, {dates[start].date()} to {dates[-1].date()}; universe = the 750 largest US companies at each "
         "quarter-end (point-in-time); survivors-only Yahoo prices. Decide at the close, fill at the next open. "
         "Up to 10 positions of 10%; idle cash earns T-bills; 0.10% per trade each way. Sharpe above T-bills.\n")
    emit("## 1. The strategy against its benchmarks\n")
    emit("| | return/yr | volatility | Sharpe | worst drop | 2014-19 Sharpe | 2020-26 Sharpe | avg invested |")
    emit("|---|---|---|---|---|---|---|---|")

    def row(name, eq, invested=""):
        s = stats(eq, rf)
        a, b = stats(eq.loc[:MID], rf), stats(eq.loc[MID:], rf)
        emit(f"| {name} | {s['CAGR']:.1%} | {s['volatility']:.0%} | {s['Sharpe']:.2f} | {s['max drawdown']:.0%} | "
             f"{a['Sharpe']:.2f} | {b['Sharpe']:.2f} | {invested} |")

    def invested(t: pd.DataFrame) -> str:
        if t.empty:
            return "0%"
        days = t["days"].sum()
        return f"{days / (10 * (len(dates) - start)):.0%}"

    row("VCP breakouts (base rules)", base_eq, invested(base_t))
    c_eq, c_t = run(control=True)
    row("Control: random strong-trend stocks, same exits", c_eq, invested(c_t))
    row("Equal-weight universe (always invested)", uni, "100%")
    row("SPY (always invested)", spy, "100%")

    emit("\n## 2. The trades\n")
    emit("| | trades | win rate | avg win | avg loss | per trade | profit factor | avg days held |\n|---|---|---|---|---|---|---|---|")
    for name, t in (("VCP breakouts", base_t), ("Control", c_t)):
        s = trade_stats(t)
        emit(f"| {name} | {s['trades']} | {s['win rate']:.0%} | {s['avg win']:+.1%} | {s['avg loss']:+.1%} | "
             f"{s['expectancy']:+.2%} | {s['profit factor']:.2f} | {s['avg days']:.0f} |")
    emit("\nHow the VCP trades ended:\n")
    emit("| exit | trades | avg return |\n|---|---|---|")
    for why, g in base_t.groupby("why"):
        emit(f"| {why} | {len(g)} | {g['return'].mean():+.1%} |")

    emit("\n## 3. Stress tests (the backtest-expert checklist)\n")
    emit("Costs, then one setting at a time around the base rules. A real edge should hold up across them.\n")
    emit("| change | return/yr | Sharpe | worst drop | trades | per trade |\n|---|---|---|---|---|---|")
    tests = {
        "Base rules": {},
        "Costs 0.20% each way": dict(cost=0.002),
        "Costs 0.30% each way": dict(cost=0.003),
        "Stop 6%": dict(stop=0.06), "Stop 10%": dict(stop=0.10),
        "Target 15%": dict(target=0.15), "Target 35%": dict(target=0.35), "No target": dict(target=None),
        "Max hold 20 days": dict(max_days=20), "Max hold 60 days": dict(max_days=60),
        "Breakout above 50-day high": dict(breakout_days=50),
        "Volume 2x average": dict(vol_mult=2.0), "Volume 1.2x average": dict(vol_mult=1.2),
        "Looser base (range under 70%)": dict(tight_ratio=0.7),
        "5 positions of 20%": dict(slots=5), "20 positions of 5%": dict(slots=20),
    }
    for name, kw in tests.items():
        eq, t = (base_eq, base_t) if not kw else run(**kw)
        s, ts = stats(eq, rf), trade_stats(t)
        emit(f"| {name} | {s['CAGR']:.1%} | {s['Sharpe']:.2f} | {s['max drawdown']:.0%} | {ts['trades']} | "
             f"{ts.get('expectancy', 0):+.2%} |")

    emit("\n## 4. Year by year\n")
    emit("| year | VCP breakouts | control | equal-weight universe | SPY |\n|---|---|---|---|---|")
    yr = lambda eq: eq.resample("YE").last().pct_change().fillna(eq.resample("YE").last().iloc[0] / eq.iloc[0] - 1)  # noqa: E731
    yv, yc, yu, ys = yr(base_eq), yr(c_eq), yr(uni), yr(spy)
    for y in yv.index:
        emit(f"| {y.year} | {yv[y]:+.1%} | {yc[y]:+.1%} | {yu[y]:+.1%} | {ys[y]:+.1%} |")
    emit(f"\nVCP beat the equal-weight universe in {int((yv > yu).sum())} of {len(yv)} years and SPY in "
         f"{int((yv > ys).sum())}.")

    OUT.mkdir(exist_ok=True)
    (OUT / "swing.md").write_text("\n".join(lines) + "\n")
    print(f"\nwrote {OUT / 'swing.md'}")


if __name__ == "__main__":
    if sys.argv[1:] == ["--fetch"]:
        fetch_daily(universe_tickers())
    else:
        main()
