"""ICT day trading, as fixed rules - and does mixing in the company's financials help?

    python research/ict.py            (first run downloads intraday bars from Yahoo; a few minutes)

ICT ("Inner Circle Trader", Michael Huddleston) teaches intraday entries around "liquidity": stops
resting above an obvious high or below an obvious low. Price runs those stops (a "sweep"), then
reverses with force, often leaving a fair value gap (FVG: a 3-bar gap where bar 3 doesn't overlap
bar 1). The rules below are community descriptions of two of his models (sources in research/ICT.md),
fixed before running anything:

Model 1 - Silver Bullet (5-minute bars, the 10:00-11:00 New York window)
  sweep    after 9:30, price trades below the prior day's low or the 9:30-10:00 range low (long
           setup) / above the prior day's high or opening-range high (short setup)
  FVG      between 10:00 and 11:00, after the sweep, a 3-bar gap in the reversal direction
  entry    a limit order at the gap's near edge, filled if price comes back to it by 11:30
  stop     beyond the most extreme price since 9:30 (the sweep); target 2x the risk (2R)
  exit     stop, target, or the 15:55 bar's close. If a bar touches both, assume the stop.
Model 2 - Judas swing (hourly bars, about 3 years)
  setup    the first hour (9:30-10:30) trades beyond the prior day's high (or low) and closes back
           inside the prior day's range: a fake move that ran the stops
  entry    the 10:30 open, against the fake move
  stop     beyond the first hour's extreme; target 2R; else out at the last bar's close

Financials and trend, layered on top (point-in-time SEC snapshots, data/backtest/snapshots_m*.pkl):
  financial bias   longs only in the top third by the desk's quality score, shorts only in the
                   bottom third (the chart picks the moment, the financials pick the side)
  trend bias       longs only above the 50-day average, shorts only below (ICT's "higher-timeframe bias")
Controls: the same entries with a coin-flip direction (does the direction call add anything?).

Universe: the 100 largest US companies at the latest quarter-end. Costs 0.03% each way (large-cap
spread and slippage), stress 0.10%. Results are per trade in R (multiples of the risk) and in %;
the portfolio view puts 10% of the account in each trade, at most 10 a day.
Writes research/output/ict.md; findings in research/ICT.md.
"""

from __future__ import annotations

import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ai_desk.fundamentals.scoring import score  # noqa: E402
from ai_desk.fundamentals.yahoo import with_retry  # noqa: E402

CACHE = ROOT / "data" / "backtest"
OUT = Path(__file__).resolve().parent / "output"
END = "2026-10-20"          # last full trading day
COST = 0.0003
N_UNIVERSE = 100


# --- data -----------------------------------------------------------------------------

def snapshots() -> dict[pd.Timestamp, pd.DataFrame]:
    s = {}
    for m in (3, 6, 9, 12):
        s.update(pickle.loads((CACHE / f"snapshots_m{m}.pkl").read_bytes()))
    return dict(sorted(s.items()))


def universe(snaps, since: str) -> list[str]:
    names = set()
    keys = [k for k in snaps if k >= pd.Timestamp(since) - pd.DateOffset(months=3)]
    for k in keys:
        names |= set(snaps[k]["market_cap"].nlargest(N_UNIVERSE).index)
    return sorted(names)


def fetch_intraday(tickers: list[str], interval: str, period: str) -> dict[str, pd.DataFrame]:
    path = CACHE / f"intraday_{interval}.pkl"
    if path.exists():
        return pickle.loads(path.read_bytes())
    import yfinance as yf

    parts = {k: [] for k in ("Open", "High", "Low", "Close", "Volume")}
    for i in range(0, len(tickers), 50):
        chunk = tickers[i:i + 50]
        d = with_retry(lambda chunk=chunk: yf.download(chunk, period=period, interval=interval, auto_adjust=False,
                                                       progress=False, threads=4, prepost=False))
        for k in parts:
            parts[k].append(d[k])
        print(f"  {interval} bars {min(i + 50, len(tickers))}/{len(tickers)}", flush=True)
    out = {}
    for k, v in parts.items():
        df = pd.concat(v, axis=1, sort=True)
        df = df.loc[:, ~df.columns.duplicated()]
        idx = pd.to_datetime(df.index)
        df.index = idx.tz_convert("America/New_York").tz_localize(None) if idx.tz is not None else idx
        out[k.lower()] = df.loc[:f"{END} 23:59"].astype("float32")
    path.write_bytes(pickle.dumps(out))
    return out


# --- pure pieces (unit-tested) --------------------------------------------------------

def fvg(h: np.ndarray, lo: np.ndarray, k: int) -> int:
    """+1 if bars k-2, k-1, k leave a bullish gap (low[k] > high[k-2]), -1 bearish, 0 none."""
    if k < 2:
        return 0
    if lo[k] > h[k - 2]:
        return 1
    if h[k] < lo[k - 2]:
        return -1
    return 0


def run_trade(o, h, lo, c, start: int, side: int, entry: float, stop: float, target: float,
              limit: bool, fill_by: int | None = None) -> dict | None:
    """Walk forward from bar `start`. limit=True: wait for price to reach `entry` (by `fill_by`).
    Returns the trade in R and %, or None if never filled. A bar touching stop and target = stop."""
    n = len(c)
    i = start
    if limit:
        while i < n and (fill_by is None or i <= fill_by):
            if (side > 0 and lo[i] <= entry) or (side < 0 and h[i] >= entry):
                if (side > 0 and o[i] < entry) or (side < 0 and o[i] > entry):
                    entry = o[i]               # gapped through the limit: filled at the open (better)
                break
            i += 1
        else:
            return None
        if i >= n or (fill_by is not None and i > fill_by):
            return None
    risk = abs(entry - stop)
    if risk <= 0:
        return None
    for j in range(i, n):
        hit_stop = lo[j] <= stop if side > 0 else h[j] >= stop
        hit_tgt = h[j] >= target if side > 0 else lo[j] <= target
        if hit_stop:
            px = o[j] if (side > 0 and o[j] < stop) or (side < 0 and o[j] > stop) else stop
            return _trade(side, entry, px, risk, "stop", i, j)
        if hit_tgt:
            px = target if j > i or not limit else target
            return _trade(side, entry, px, risk, "target", i, j)
    return _trade(side, entry, c[n - 1], risk, "close", i, n - 1)


def _trade(side, entry, exit_, risk, why, i, j) -> dict:
    return {"side": side, "entry": float(entry), "exit": float(exit_), "R": float(side * (exit_ - entry) / risk),
            "ret": float(side * (exit_ / entry - 1)), "why": why, "bar_in": int(i), "bar_out": int(j)}


def silver_bullet(day: pd.DataFrame, pdh: float, pdl: float, rr: float = 2.0) -> dict | None:
    """One stock-day of 5-minute bars (index = times). Returns the first Silver Bullet trade or None."""
    t = day.index
    o, h, lo, c = (day[k].to_numpy(dtype=float) for k in ("open", "high", "low", "close"))
    if len(c) < 30 or not np.isfinite(c).all():
        return None
    mins = t.hour * 60 + t.minute
    or_mask = (mins >= 570) & (mins < 600)                       # 9:30-10:00 opening range
    if not or_mask.any():
        return None
    orh, orl = h[or_mask].max(), lo[or_mask].min()
    lows, highs = np.minimum.accumulate(lo), np.maximum.accumulate(h)
    for k in range(2, len(c)):
        if not (600 <= mins[k] < 660):                           # FVG completes 10:00-10:55
            continue
        g = fvg(h, lo, k)
        if g == 0:
            continue
        # the sweep must come before the gap: by bar k-2, price has run a level on the other side
        if g > 0:
            swept = lows[k - 2] < pdl or lows[k - 2] < orl and k - 2 > np.flatnonzero(or_mask)[-1]
            if not swept:
                continue
            entry, stop = lo[k], lows[k]
        else:
            swept = highs[k - 2] > pdh or highs[k - 2] > orh and k - 2 > np.flatnonzero(or_mask)[-1]
            if not swept:
                continue
            entry, stop = h[k], highs[k]
        if (entry - stop) * g <= 0:
            continue
        target = entry + g * rr * abs(entry - stop)
        fill_by = int(np.searchsorted(mins, 690, side="right") - 1)   # by 11:30
        tr = run_trade(o, h, lo, c, k + 1, g, entry, stop, target, limit=True, fill_by=fill_by)
        if tr:
            tr["time"] = t[tr["bar_in"]]
            return tr
        return None
    return None


def judas(day: pd.DataFrame, pdh: float, pdl: float, rr: float = 2.0) -> dict | None:
    """Hourly bars for one stock-day. First bar sweeps the prior day's high/low and closes back inside."""
    o, h, lo, c = (day[k].to_numpy(dtype=float) for k in ("open", "high", "low", "close"))
    if len(c) < 3 or not np.isfinite(c).all():
        return None
    if h[0] > pdh and pdl < c[0] < pdh:
        side, stop = -1, h[0]
    elif lo[0] < pdl and pdl < c[0] < pdh:
        side, stop = 1, lo[0]
    else:
        return None
    entry = o[1]
    if (entry - stop) * side <= 0:
        return None
    tr = run_trade(o, h, lo, c, 1, side, entry, stop, entry + side * rr * abs(entry - stop), limit=False)
    if tr:
        tr["time"] = day.index[1]
    return tr


def summarize(t: pd.DataFrame, cost: float = COST) -> dict:
    if t.empty:
        return {"trades": 0}
    net = t["ret"] - 2 * cost
    win = net > 0
    return {"trades": len(t), "days": t["date"].nunique(), "win rate": win.mean(), "avg R": t["R"].mean(),
            "per trade": net.mean(), "t": net.mean() / (net.std() / np.sqrt(len(net))) if net.std() > 0 else np.nan,
            "profit factor": net[win].sum() / -net[~win].sum() if (~win).any() else np.inf}


def portfolio(t: pd.DataFrame, all_days, cost: float = COST, slot: float = 0.10, max_per_day: int = 10) -> pd.Series:
    """Daily return: 10% of the account in each trade, the first `max_per_day` trades by entry time."""
    if t.empty:
        return pd.Series(0.0, index=all_days)
    t = t.sort_values("time").groupby("date").head(max_per_day)
    daily = t.assign(net=(t["ret"] - 2 * cost) * slot).groupby("date")["net"].sum()
    return daily.reindex(all_days, fill_value=0.0)


# --- the experiment ------------------------------------------------------------------

def bias_tables(snaps, daily_close: pd.DataFrame):
    """Per (quarter-end, symbol): quality-score third; per (day, symbol): above the 50-day average."""
    thirds = {}
    for k, snap in snaps.items():
        top = snap["market_cap"].nlargest(N_UNIVERSE * 3)              # score against a wider peer set
        sc = score(snap.loc[top.index].drop(columns=["passes_gates"], errors="ignore"))["score"]
        thirds[k] = pd.cut(sc.rank(pct=True), [0, 1 / 3, 2 / 3, 1.0], labels=[-1, 0, 1]).astype(int)
    above = daily_close > daily_close.rolling(50, min_periods=50).mean()
    return thirds, above


def collect(bars: dict[str, pd.DataFrame], model, snaps, thirds, above) -> pd.DataFrame:
    rows = []
    c = bars["close"]
    days = sorted(set(c.index.normalize()))
    keys = sorted(thirds)
    # prior day's high/low from the same (unadjusted) intraday bars, so a dividend adjustment can't fake a sweep
    dh = bars["high"].groupby(bars["high"].index.normalize()).max()
    dl = bars["low"].groupby(bars["low"].index.normalize()).min()
    for d in days:
        known = [k for k in keys if k + pd.Timedelta(days=45) <= d]    # filings lag the quarter-end
        if not known:
            continue
        q = known[-1]
        members = list(snaps[q]["market_cap"].nlargest(N_UNIVERSE).index)
        prev = dh.index[dh.index < d]
        if not len(prev):
            continue
        p = prev[-1]
        sl = slice(d, d + pd.Timedelta(hours=23))
        for s in members:
            if s not in c.columns or s not in dh.columns:
                continue
            day = pd.DataFrame({k: bars[k][s].loc[sl] for k in ("open", "high", "low", "close")}).dropna()
            if day.empty:
                continue
            pdh, pdl = dh.at[p, s], dl.at[p, s]
            if not (np.isfinite(pdh) and np.isfinite(pdl)):
                continue
            tr = model(day, float(pdh), float(pdl))
            if tr:
                ap = above.index[above.index < d]
                tr.update({"date": d, "symbol": s, "fin": int(thirds[q].get(s, 0)),
                           "trend_up": bool(above.at[ap[-1], s]) if s in above.columns and len(ap) else None})
                rows.append(tr)
    return pd.DataFrame(rows)


def report(name: str, t: pd.DataFrame, days, emit, rf_daily: float) -> None:
    rng = np.random.default_rng(11)
    variants = {
        "Pure ICT (both sides, all stocks)": t,
        "+ financial bias (long top third, short bottom third)":
            t[((t["side"] > 0) & (t["fin"] == 1)) | ((t["side"] < 0) & (t["fin"] == -1))],
        "+ financials, long only (top third)": t[(t["side"] > 0) & (t["fin"] == 1)],
        "+ trend bias (long above 50-day, short below)":
            t[((t["side"] > 0) & (t["trend_up"] == True)) | ((t["side"] < 0) & (t["trend_up"] == False))],  # noqa: E712
        "+ financial and trend bias":
            t[(((t["side"] > 0) & (t["fin"] == 1)) | ((t["side"] < 0) & (t["fin"] == -1)))
              & (((t["side"] > 0) & (t["trend_up"] == True)) | ((t["side"] < 0) & (t["trend_up"] == False)))],  # noqa: E712
        "Longs only (all stocks)": t[t["side"] > 0],
        "Shorts only (all stocks)": t[t["side"] < 0],
    }
    emit(f"\n## {name}\n")
    emit(f"{t['date'].nunique() if len(t) else 0} trading days with a setup, {days[0].date()} to {days[-1].date()}.\n")
    emit("| rules | trades | win rate | avg R (before costs) | per trade after costs | t-stat | at 0.10% costs | "
         "portfolio return/yr | Sharpe |")
    emit("|---|---|---|---|---|---|---|---|---|")
    for k, v in variants.items():
        s, s3 = summarize(v), summarize(v, 0.001)
        if not s["trades"]:
            emit(f"| {k} | 0 | | | | | | | |")
            continue
        p = portfolio(v, days)
        ann = (1 + p).prod() ** (252 / len(p)) - 1
        ex = p - rf_daily
        sh = ex.mean() / ex.std() * np.sqrt(252) if ex.std() > 0 else np.nan
        emit(f"| {k} | {s['trades']} | {s['win rate']:.0%} | {s['avg R']:+.2f} | {s['per trade']:+.3%} | {s['t']:.1f} | "
             f"{s3['per trade']:+.3%} | {ann:+.1%} | {sh:.2f} |")
    # control: the same entries and exit times with a coin-flip direction (the flipped trade's result is the
    # negative of the same move; it ignores that a flipped trade would have had its own stop and target)
    flip = rng.choice([-1, 1], size=len(t))
    ctrl = t.assign(ret=t["ret"] * flip, R=t["R"] * flip)
    s = summarize(ctrl)
    emit(f"| Control: same trades, coin-flip direction | {s['trades']} | {s['win rate']:.0%} | {s['avg R']:+.2f} | "
         f"{s['per trade']:+.3%} | {s['t']:.1f} | | | |")
    if len(t):
        emit("\nHow trades ended (pure ICT): " + ", ".join(f"{w} {n}" for w, n in t["why"].value_counts().items()) + ".")
        m = t.assign(month=pd.to_datetime(t["date"]).dt.to_period("Q"))
        g = m.groupby("month").apply(lambda x: (x["ret"] - 2 * COST).mean(), include_groups=False)
        emit("By quarter, per trade after costs: " + ", ".join(f"{k} {v:+.2%}" for k, v in g.items()) + ".")


def main() -> None:
    lines: list[str] = []

    def emit(x=""):
        print(x, flush=True)
        lines.append(x)

    snaps = snapshots()
    daily = pickle.loads((CACHE / "daily_ohlcv.pkl").read_bytes())
    daily = {k: v.astype(float) for k, v in daily.items()}
    thirds, above = bias_tables(snaps, daily["close"])
    from ai_desk.data import load_cash_rate
    rf = float(load_cash_rate(str(ROOT / "market_data" / "SPY.csv")).iloc[-500:].mean()) / 252

    emit("# ICT day trading - generated tables\n")
    emit("Rules fixed in research/ict.py before running. Universe = the 100 largest US companies at the latest "
         "quarter-end known at the time (filings assumed public 45 days after it). Costs 0.03% each way "
         "(stress 0.10%). Portfolio: 10% of the account per trade, at most 10 trades a day, cash otherwise "
         "(Sharpe above T-bills). Yahoo intraday bars, regular hours only.\n")

    tick5 = universe(snaps, "2026-06-01")
    b5 = fetch_intraday(tick5, "5m", "60d")
    t5 = collect(b5, silver_bullet, snaps, thirds, above)
    days5 = pd.DatetimeIndex(sorted(set(b5["close"].index.normalize())))
    report("Model 1: Silver Bullet, 5-minute bars (last ~60 days only - a short sample)", t5, days5, emit, rf)

    tick1 = universe(snaps, "2023-10-01")
    b1 = fetch_intraday(tick1, "1h", "730d")
    t1 = collect(b1, judas, snaps, thirds, above)
    days1 = pd.DatetimeIndex(sorted(set(b1["close"].index.normalize())))
    report("Model 2: Judas swing, hourly bars (~3 years)", t1, days1, emit, rf)

    spy = daily["close"]["SPY"] if "SPY" in daily["close"] else None
    if spy is None:
        spy = pd.read_csv(ROOT / "market_data" / "SPY.csv", index_col=0, parse_dates=True)["close"]
    for name, days in (("Model 1 window", days5), ("Model 2 window", days1)):
        s = spy.loc[days[0]:days[-1]]
        emit(f"\nSPY over the {name}: {s.iloc[-1] / s.iloc[0] - 1:+.1%} ({len(s)} days).")

    OUT.mkdir(exist_ok=True)
    (OUT / "ict.md").write_text("\n".join(lines) + "\n")
    print(f"\nwrote {OUT / 'ict.md'}")


if __name__ == "__main__":
    main()
