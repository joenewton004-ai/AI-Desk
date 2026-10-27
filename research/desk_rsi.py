"""The desk with an RSI dip-buying overlay (amendment 661549dd, testing).

    python research/desk_rsi.py

The rule (research/CANDLE_RSI.md): one of the 100 largest US companies (point-in-time) closes above its 200-day
average with RSI(14) below 30 -> buy at the next open, sell at the open after it first closes above its 5-day average
(at most 10 days). On its own it made ~+1.1% a trade but is invested only ~6% of the time, so how it is funded matters.
Fixed before running (in the amendment):
  PRIMARY   positions of 3% of the desk each, at most 5 (15%), funded from the overnight sleeve's 30% while open: the
            overnight sleeve buys that much less each night; quality 50% and momentum 20% unchanged
  S1        a fixed 10% sleeve (5 slots of 2% of the desk), T-bills when idle; the rest 45% quality, 18% momentum,
            27% overnight (pro-rata)
  S2        the same 10% sleeve taken from the quality screen (40/20/30)
Same-day signals beyond the free slots: the lowest RSI first. Costs 0.05% each way (stress 0.20%).
The other sleeves as they run live: quality screen top 25 (research/screen_backtest), momentum top 20 with the entry
filter and 100-day exit (research/desk_top10.py), overnight = 12-month return re-picked daily, ranked the evening
before, with the SPY 200-day and picks-day checks (research/overnight_v2.py), 0.02% each way.
Decision rule (fixed in the amendment): recommend accepting only if the desk's Sharpe is higher in BOTH 2014-19 and
2020-26, the worst drop is no more than 1 point deeper, and the desk still beats the current one with the overlay at
0.20% costs each way. Monthly, 2014-06 to 2026-09; survivors-only prices. Writes research/output/desk_rsi.md; findings
in research/DESK_RSI.md.
"""

from __future__ import annotations

import pickle
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "research"))

import candle_rsi as cr  # noqa: E402
import desk_overnight as do  # noqa: E402
import lookbacks as lb  # noqa: E402
import momentum_sleeve as ms  # noqa: E402
import overnight as ov  # noqa: E402
import overnight_picks_check as opc  # noqa: E402
import overnight_regime as orr  # noqa: E402
import swing  # noqa: E402
import weekly  # noqa: E402
from ai_desk.data import load_cash_rate  # noqa: E402
from ai_desk.fundamentals import screen_backtest as sb  # noqa: E402
from ai_desk.indicators import rsi  # noqa: E402

CACHE, OUT, MONTH_END = do.CACHE, do.OUT, do.MONTH_END
RULE = ("T1", "R2", "C0", "E1")                 # above SMA200, RSI(14) < 30, no candle, exit above SMA5
PERIOD = ("2014-05-15", "2026-10-20")


# --- pure pieces (unit-tested) --------------------------------------------------------

def book(trades: list[tuple], rsi_at: dict, days: pd.DatetimeIndex, slot: float, max_pos: int) -> pd.DataFrame:
    """Daily desk weights: each accepted trade holds `slot` from its entry day to the day before its exit (open to
    open). A trade is accepted if fewer than `max_pos` are open on its entry day; same-day entries lowest RSI first.
    trades: (symbol, entry date, exit date); rsi_at[(symbol, entry date)] = the signal day's RSI."""
    order = sorted(trades, key=lambda x: (x[1], rsi_at.get((x[0], x[1]), 0.0)))
    w = pd.DataFrame(0.0, index=days, columns=sorted({t[0] for t in trades}))
    open_until: list[pd.Timestamp] = []
    for s, e, x in order:
        open_until = [u for u in open_until if u > e]
        if len(open_until) >= max_pos:
            continue
        open_until.append(x)
        w.loc[e:x - pd.Timedelta(days=1), s] += slot
    return w


def entry_mask(w: pd.DataFrame) -> pd.DataFrame:
    """Pure: True on the first day of each position (where the weight turns on)."""
    return (w > 0) & ~(w.shift(1, fill_value=0) > 0)


def overlay_daily(w: pd.DataFrame, oo: pd.DataFrame, cost: float) -> pd.Series:
    """The overlay's contribution to the desk each day (open-to-open moves of what it holds, costs on entry)."""
    oo = oo.reindex(index=w.index, columns=w.columns).fillna(0.0)
    return (w * oo).sum(axis=1) - (w * entry_mask(w)).sum(axis=1) * 2 * cost


# --- the sleeves ----------------------------------------------------------------------

def overnight_live() -> tuple[pd.Series, pd.Series]:
    """The overnight sleeve as it runs live (research/overnight_v2.py 'as live' + checks): daily, dated by the
    morning each night ends; T-bills on cash nights. Also the daily T-bill rate."""
    d = swing.fetch_daily([])
    o, c, v = (d[k].astype(float).loc[:ov.END] for k in ("open", "close", "volume"))
    snaps = {}
    for m in (3, 6, 9, 12):
        snaps.update({k: list(s.index) for k, s in pickle.loads((CACHE / f"snapshots_m{m}.pkl").read_bytes()).items()})
    dates, symbols = c.index, list(c.columns)
    member = pd.DataFrame(swing.membership(dict(sorted(snaps.items())), dates, symbols), index=dates, columns=symbols)
    eligible = member & (c > 10) & ((c * v).rolling(50, min_periods=40).mean() > 20e6)
    on, day = ov.split_returns(o, c)
    rf = (load_cash_rate(str(ROOT / "market_data" / "SPY.csv")).reindex(dates, method="ffill") / 252).fillna(0)
    mkt = pd.read_csv(ROOT / "market_data" / "SPY.csv", index_col=0, parse_dates=True)["close"].reindex(dates).ffill()
    spy_flag = (mkt < mkt.rolling(200).mean()).shift(1).fillna(False).astype(bool)
    h = lb.daily_top(c / c.shift(252) - 1, eligible).shift(2, fill_value=False)
    base = orr.nightly(on, h, orr.COST).loc[ov.START:ov.END]
    idx = base.index
    pday = day.shift(1).where(h).mean(axis=1).reindex(idx)
    flag = spy_flag.reindex(idx).fillna(False) | opc.bad_day(pday, 0.10)
    return orr.switch(base, rf.reindex(idx).fillna(0), flag), rf


def main() -> None:
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    lines: list[str] = []

    def emit(t=""):
        print(t, flush=True)
        lines.append(t)

    print("quality and momentum...", flush=True)
    px, snaps = weekly.load()
    f = weekly.build(px, snaps)
    ma20 = px.rolling(20, min_periods=20).mean()
    f_both = {**f, "above": f["above"] & (px > ma20)}
    mom = ms.monthly(weekly.simulate(weekly.momentum_book(px, snaps, f_both, lookback=26, n=20, every=4, exit_ma=20),
                                     f["ret"], weekly.COST))
    prices = pickle.loads((CACHE / "prices.pkl").read_bytes())
    for k in prices:
        prices[k] = prices[k].groupby(level=0).last() if k != "splits" else prices[k].groupby(level=0).max()
    s_snaps = {}
    for m in (3, 6, 9, 12):
        s_snaps.update(pickle.loads((CACHE / f"snapshots_m{m}.pkl").read_bytes()))
    screen = sb.simulate({"t": sb.books(dict(sorted(s_snaps.items())), 25)["screen_top"]}, prices, MONTH_END)["t"]
    rf_m = (load_cash_rate(str(ROOT / "market_data" / "SPY.csv")).resample("ME").last() / 12).shift(1)

    print("overnight (as live)...", flush=True)
    on_r, rf_d = overnight_live()

    print("RSI dip trades...", flush=True)
    frames, member = cr.stock_data()
    feats = {s: cr.features(d) for s, d in frames.items()}
    _, _, trades = cr.run_rule(frames, feats, RULE, 0.0, PERIOD, member)
    rsi_at = {}
    for s, e, x in trades:
        r14 = rsi(frames[s]["close"], 14)
        prev = r14.index[r14.index < e]
        rsi_at[(s, e)] = float(r14.loc[prev[-1]]) if len(prev) else 0.0
    days = on_r.index
    oo = pd.DataFrame({s: d["open"].shift(-1) / d["open"] - 1 for s, d in frames.items()})

    idx = screen.index.intersection(mom.index)
    idx = idx[(idx >= pd.Timestamp("2014-06-30")) & (idx <= pd.Timestamp(MONTH_END))]
    rfm = rf_m.reindex(idx).fillna(0)
    q, mo = screen.reindex(idx), mom.reindex(idx)
    to_m = lambda daily: ((1 + daily).resample("ME").prod() - 1).reindex(idx)  # noqa: E731

    def desk(kind: str, cost: float) -> tuple[pd.Series, pd.Series, float]:
        """Monthly desk return, the overlay's own monthly contribution, and its average weight."""
        if kind == "current":
            return 0.5 * q + 0.2 * mo + to_m(0.3 * on_r), pd.Series(0.0, index=idx), 0.0
        slot, mx = (0.03, 5) if kind == "primary" else (0.02, 5)
        w = book(trades, rsi_at, days, slot, mx)
        held = w.sum(axis=1)
        ovl = overlay_daily(w, oo, cost)
        if kind == "primary":
            night = held.shift(1, fill_value=0.0)                       # held through the night ending today
            daily = (0.3 - night) * on_r + ovl
            return 0.5 * q + 0.2 * mo + to_m(daily), to_m(ovl), held.mean()
        weights = (0.45, 0.18, 0.27) if kind == "S1" else (0.40, 0.20, 0.30)
        daily = weights[2] * on_r + ovl + (0.10 - held) * rf_d.reindex(days).fillna(0)
        return weights[0] * q + weights[1] * mo + to_m(daily), to_m(ovl), held.mean()

    names = {"current": "Current desk (50% quality, 20% momentum, 30% overnight)",
             "primary": "PRIMARY: RSI dips, 3% each (max 5), funded from the overnight sleeve",
             "S1": "S1: fixed 10% RSI sleeve, pro-rata (45/18/27)",
             "S2": "S2: fixed 10% RSI sleeve, from quality (40/20/30)"}
    res = {(k, c): desk(k, c) for k in names for c in (0.0005, 0.002)}

    emit("# The desk with an RSI dip-buying overlay - generated tables\n")
    emit(f"Monthly, {idx[0]:%Y-%m} to {idx[-1]:%Y-%m}. **Survivors-only prices.** Overlay trades: {len(trades):,} signals "
         "(above SMA200, RSI(14)<30, sell above SMA5), point-in-time top 100. Sharpe above T-bills.\n")
    emit("| desk | overlay costs | return/yr | volatility | Sharpe | worst drop | 2014-19 Sharpe | 2020-26 Sharpe | "
         "overlay's average weight | overlay's return/yr (desk %) |")
    emit("|---|---|---|---|---|---|---|---|---|---|")
    for (k, c), (d, ovl, wbar) in res.items():
        if k == "current" and c != 0.0005:
            continue
        s, a, b = ms.mstats(d, rfm), ms.mstats(d.loc[:"2019"], rfm), ms.mstats(d.loc["2020":], rfm)
        emit(f"| {names[k]} | {'' if k == 'current' else f'{c:.2%}'} | {s['CAGR']:.1%} | {s['volatility']:.1%} | "
             f"{s['Sharpe']:.3f} | {s['max drawdown']:.1%} | {a['Sharpe']:.3f} | {b['Sharpe']:.3f} | {wbar:.1%} | "
             f"{(1 + ovl).prod() ** (12 / len(ovl)) - 1:+.2%} |")
    # the fixed sleeves hold ~9% of the desk in T-bills: the same mixes with plain cash and no trades separate the
    # cash effect from the RSI trades
    for name, wts in (("(S1 without trades: 45/18/27 + 10% T-bills)", (0.45, 0.18, 0.27)),
                      ("(S2 without trades: 40/20/30 + 10% T-bills)", (0.40, 0.20, 0.30))):
        d = wts[0] * q + wts[1] * mo + to_m(wts[2] * on_r + 0.10 * rf_d.reindex(days).fillna(0))
        st, a, b = ms.mstats(d, rfm), ms.mstats(d.loc[:"2019"], rfm), ms.mstats(d.loc["2020":], rfm)
        emit(f"| {name} | | {st['CAGR']:.1%} | {st['volatility']:.1%} | {st['Sharpe']:.3f} | {st['max drawdown']:.1%} | "
             f"{a['Sharpe']:.3f} | {b['Sharpe']:.3f} | | |")
    spy = prices["adj"]["SPY"].loc[:MONTH_END].pct_change().reindex(idx)
    emit(ms.fmt_row("SPY (for reference)", ms.mstats(spy, rfm)).replace("| SPY (for reference) |", "| SPY | |"))

    cur = res[("current", 0.0005)][0]
    emit("\n## Against the decision rule (fixed before running)\n")
    emit("| desk | overlay costs | Sharpe 2014-19: new vs current | 2020-26 | worst drop: new vs current | "
         "Sharpe gap, 90% range (block bootstrap) | better years | passes |")
    emit("|---|---|---|---|---|---|---|---|")
    rng = np.random.default_rng(0)
    sc, sca, scb = ms.mstats(cur, rfm), ms.mstats(cur.loc[:"2019"], rfm), ms.mstats(cur.loc["2020":], rfm)
    verdict = {}
    for (k, c), (d, _, _) in res.items():
        if k == "current":
            continue
        s, a, b = ms.mstats(d, rfm), ms.mstats(d.loc[:"2019"], rfm), ms.mstats(d.loc["2020":], rfm)
        boot = []
        for _ in range(2000):
            starts = rng.integers(0, len(idx) - 12, size=len(idx) // 12 + 1)
            pick = np.concatenate([np.arange(st, st + 12) for st in starts])[:len(idx)]
            dd, cc, rr = (x.iloc[pick].reset_index(drop=True) for x in (d, cur, rfm))
            boot.append(ms.mstats(dd, rr)["Sharpe"] - ms.mstats(cc, rr)["Sharpe"])
        lo, hi = np.percentile(boot, [5, 95])
        yd, yc = (1 + d).groupby(idx.year).prod() - 1, (1 + cur).groupby(idx.year).prod() - 1
        ok = a["Sharpe"] > sca["Sharpe"] and b["Sharpe"] > scb["Sharpe"] and s["max drawdown"] >= sc["max drawdown"] - 0.01
        verdict[(k, c)] = ok
        emit(f"| {names[k]} | {c:.2%} | {a['Sharpe']:.3f} vs {sca['Sharpe']:.3f} | {b['Sharpe']:.3f} vs {scb['Sharpe']:.3f} | "
             f"{s['max drawdown']:.1%} vs {sc['max drawdown']:.1%} | {s['Sharpe'] - sc['Sharpe']:+.3f} ({lo:+.3f} to "
             f"{hi:+.3f}) | {int((yd > yc).sum())} of {len(yd)} | {'yes' if ok else 'no'} |")
    emit(f"\nPrimary passes the full rule (both halves + drop + still better at 0.20%): "
         f"{'yes' if verdict[('primary', 0.0005)] and verdict[('primary', 0.002)] else 'no'}.")

    d, ovl, _ = res[("primary", 0.0005)]
    emit("\n## Year by year (primary, 0.05%)\n")
    emit("| year | current | with the overlay | difference | overlay's own contribution |\n|---|---|---|---|---|")
    yd, yc = (1 + d).groupby(idx.year).prod() - 1, (1 + cur).groupby(idx.year).prod() - 1
    yo = (1 + ovl).groupby(idx.year).prod() - 1
    for y in yd.index:
        emit(f"| {y} | {yc[y]:+.1%} | {yd[y]:+.1%} | {yd[y] - yc[y]:+.2%} | {yo[y]:+.2%} |")
    emit(f"\nMonthly correlation of the overlay's contribution with the current desk: {ovl.corr(cur):.2f}. "
         f"The market's 10 worst months: overlay {ovl[spy.nsmallest(10).index].mean():+.2%} on average, "
         f"current desk {cur[spy.nsmallest(10).index].mean():+.1%}.")

    OUT.mkdir(exist_ok=True)
    (OUT / "desk_rsi.md").write_text("\n".join(lines) + "\n")
    print(f"\nwrote {OUT / 'desk_rsi.md'}")


if __name__ == "__main__":
    main()
