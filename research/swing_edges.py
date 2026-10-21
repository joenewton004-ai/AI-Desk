"""Four documented swing-trading effects, tested with realistic fills.

    python research/swing_edges.py        (first run reads the cached SEC filings for earnings; ~5 minutes)

1. Weekly pullback / reversal, done properly: decide at Friday's close, buy at MONDAY'S OPEN, sell
   at the next Monday's open (research/WEEKLY.md bought at the decision close, which flatters it).
2. Post-earnings drift (Bernard & Thomas 1989): after a quarterly report, stocks with a big
   earnings surprise keep drifting the same way. Surprise (SUE) = net income vs the same quarter a
   year earlier, divided by how much that change usually varies (last 8 quarters). Traded only
   after the 10-Q is FILED (data/sec, point-in-time), so the drift before filing is not counted.
   Q1-Q3 only (Q4 comes inside the annual report). Buy the top fifth of surprises, hold 60 days.
3. 52-week high (George & Hwang 2004): stocks close to their 52-week high keep outperforming.
   Monthly: hold the 50 stocks closest to their high. Swing: buy new 52-week-high closes, hold 20 days.
4. Overnight vs daytime: buy at the close and sell at the next open (overnight), or the reverse.

Universe = the 750 largest US companies at each quarter-end (point-in-time); daily Yahoo prices
(data/backtest/daily_ohlcv.pkl, survivors-only - flatters every row; compare with the
equal-weight universe first). Every trade fills at an open after the decision close. Costs per
trade each way: 0.02% (large-cap spread), 0.05% and 0.10%. Idle cash earns T-bills; Sharpe
above T-bills. Writes research/output/swing_edges.md; findings in research/SWING_EDGES.md.
"""

from __future__ import annotations

import gzip
import warnings
import json
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "research"))

import swing  # noqa: E402
from ai_desk.data import load_cash_rate  # noqa: E402
from ai_desk.fundamentals import edgar  # noqa: E402

CACHE = ROOT / "data" / "backtest"
SEC = ROOT / "data" / "sec"
OUT = Path(__file__).resolve().parent / "output"
START, END, MID = "2014-04-01", "2026-10-20", "2020-01-01"
COSTS = (0.0002, 0.0005, 0.001)


# --- pure pieces (unit-tested) --------------------------------------------------------

def week_ends(dates: pd.DatetimeIndex) -> np.ndarray:
    """True on the last trading day of each calendar week."""
    wk = dates.to_period("W-FRI")
    return np.r_[wk[1:] != wk[:-1], True]


def sue(quarters: pd.DataFrame) -> pd.DataFrame:
    """quarters: one row per fiscal quarter (index = quarter end) with net_income and filed date.
    Adds the year-on-year change and its standardised surprise, using only earlier quarters' changes."""
    q = quarters.sort_index().copy()
    q["yoy"] = q["net_income"] - q["net_income"].shift(4)
    spread = q["yoy"].shift(1).rolling(8, min_periods=4).std()
    q["sue"] = q["yoy"] / spread.replace(0, np.nan)
    return q


def overnight_split(o: pd.Series, c: pd.Series) -> tuple[pd.Series, pd.Series]:
    """(close-to-open, open-to-close) returns, dated by the day they end."""
    return o / c.shift(1) - 1, c / o - 1


# --- earnings events from the cached SEC filings --------------------------------------

def quarterly_events(u) -> pd.DataFrame:
    path = CACHE / "earnings_events.pkl"
    if path.exists():
        return pickle.loads(path.read_bytes())
    rows = []
    for n, (cik, ticker) in enumerate(u.tickers.items()):
        f = SEC / f"CIK{cik:010d}.json.gz"
        if not f.exists():
            continue
        facts = json.loads(gzip.decompress(f.read_bytes()))
        recs = []
        for prio, tag in enumerate(edgar.FLOW["net_income"]):
            for e in edgar._entries(facts, tag):
                if e.get("form") not in ("10-Q", "10-Q/A") or "start" not in e:
                    continue
                days = (pd.Timestamp(e["end"]) - pd.Timestamp(e["start"])).days
                if not 80 <= days <= 100:          # three-month figures only
                    continue
                recs.append((prio, pd.Timestamp(e["end"]), pd.Timestamp(e["filed"]), float(e["val"])))
        if not recs:
            continue
        df = pd.DataFrame(recs, columns=["prio", "end", "filed", "net_income"])
        # first filing of each quarter = when it became public; value as first reported (no restatements)
        df = df.sort_values(["prio", "filed"]).groupby("end").first()
        # comparatives: last year's quarter as reported in this year's 10-Q is fine too, but we use first reports
        q = sue(df[["net_income", "filed"]])
        q = q.dropna(subset=["sue"])
        for end, r in q.iterrows():
            rows.append({"symbol": ticker, "quarter_end": end, "filed": r["filed"], "sue": r["sue"]})
        if (n + 1) % 300 == 0:
            print(f"  earnings: {n + 1}/{len(u.tickers)} companies", flush=True)
    ev = pd.DataFrame(rows)
    path.write_bytes(pickle.dumps(ev))
    return ev


# --- the experiment ------------------------------------------------------------------

def main() -> None:
    warnings.filterwarnings("ignore", category=RuntimeWarning)   # empty days in the averages
    lines: list[str] = []

    def emit(t=""):
        print(t, flush=True)
        lines.append(t)

    d = swing.fetch_daily([])
    o, h, lo, c, v = (d[k].astype(float).loc[:END] for k in ("open", "high", "low", "close", "volume"))
    snaps = {}
    for m in (3, 6, 9, 12):
        snaps.update({k: list(s.index) for k, s in pickle.loads((CACHE / f"snapshots_m{m}.pkl").read_bytes()).items()})
    dates, symbols = c.index, list(c.columns)
    member = swing.membership(dict(sorted(snaps.items())), dates, symbols)
    rf_rate = load_cash_rate(str(ROOT / "market_data" / "SPY.csv"))
    rf = (rf_rate.reindex(dates, method="ffill") / 252).shift(1).fillna(0)
    start = int(dates.searchsorted(pd.Timestamp(START)))
    O, C = o.to_numpy(float), c.to_numpy(float)
    nan_ma = np.full(C.shape, np.nan)
    liquid = ((c > 10) & ((c * v).rolling(50, min_periods=40).mean() > 20e6)).to_numpy() & member

    def book(setup, rank, hold, slots, cost):
        return swing.simulate(O, C, setup, np.nan_to_num(rank, nan=-1e9), nan_ma, rf.to_numpy(), dates, symbols,
                              slots=slots, stop=1.0, target=None, max_days=hold, cost=cost, start=start)

    # benchmarks: equal-weight universe (close to close) and SPY
    uni_r = pd.Series(np.nanmean(np.where(member[start + 1:], C[start + 1:] / C[start:-1] - 1, np.nan), axis=1),
                      index=dates[start + 1:]).clip(-0.5, 0.5)
    uni = pd.concat([pd.Series([1.0], index=[dates[start]]), (1 + uni_r).cumprod()])
    spy_df = pd.read_csv(ROOT / "market_data" / "SPY.csv", index_col=0, parse_dates=True)
    spy = spy_df["close"].reindex(dates[start:]).ffill()

    def row(name, eq, trades=None, extra=""):
        s = swing.stats(eq, rf)
        a, b = swing.stats(eq.loc[:MID], rf), swing.stats(eq.loc[MID:], rf)
        n = f"{len(trades)}" if trades is not None else ""
        emit(f"| {name} | {s['CAGR']:.1%} | {s['volatility']:.0%} | {s['Sharpe']:.2f} | {s['max drawdown']:.0%} | "
             f"{a['Sharpe']:.2f} | {b['Sharpe']:.2f} | {n} | {extra} |")

    head = "| | return/yr | volatility | Sharpe | worst drop | 2014-19 Sharpe | 2020-26 Sharpe | trades | |\n|---|---|---|---|---|---|---|---|---|"

    emit("# Four swing-trading effects with realistic fills - generated tables\n")
    emit(f"Daily, {dates[start].date()} to {dates[-1].date()}; universe = the 750 largest US companies at each quarter-end "
         "(point-in-time); survivors-only Yahoo prices. Decide at a close, fill at the next open. Costs per trade each "
         "way as shown. Idle cash earns T-bills; Sharpe above T-bills.\n")
    emit("## Benchmarks\n")
    emit(head)
    row("Equal-weight universe (always invested)", uni)
    row("SPY (always invested)", spy)

    # --- 1. weekly pullback / reversal, Monday-open fills
    we = week_ends(dates)
    wret = (c / c.shift(5) - 1).to_numpy()
    above200 = (c > c.rolling(200, min_periods=200).mean()).to_numpy()
    strength = (c / c.shift(130) - 1)
    strong = (strength.rank(axis=1, pct=True) >= 0.5).to_numpy()
    base = liquid & we[:, None] & np.isfinite(wret)
    pull = base & above200 & strong
    emit("\n## 1. Weekly pullback and reversal, bought at Monday's open\n")
    emit("20 positions of 5%, chosen at Friday's close, sold at the next Monday's open (5 trading days).\n")
    emit(head)
    for cost in COSTS:
        eq, t = book(pull, -wret, 5, 20, cost)
        row(f"Pullback: 20 weakest weeks among strong uptrends, costs {cost:.2%}", eq, t)
    for cost in COSTS[:2]:
        eq, t = book(base, -wret, 5, 20, cost)
        row(f"Reversal: 20 weakest weeks, any stock, costs {cost:.2%}", eq, t)
    eq, t = book(pull, -wret, 5, 20, 0.0)
    row("Pullback at zero cost (for reference)", eq, t)

    # --- 2. post-earnings drift
    u = pickle.loads((CACHE / "universe.pkl").read_bytes())
    ev = quarterly_events(u)
    ev = ev[(ev["filed"] >= pd.Timestamp(START) - pd.Timedelta(days=200)) & (ev["filed"] <= pd.Timestamp(END))]
    col = {s: j for j, s in enumerate(symbols)}
    sue_m = np.full(C.shape, np.nan)
    for r in ev.itertuples():
        j = col.get(r.symbol)
        if j is None:
            continue
        i = int(dates.searchsorted(r.filed))            # the filing day (or the next trading day)
        if i < len(dates):
            sue_m[i, j] = r.sue
    sue_df = pd.DataFrame(sue_m, index=dates, columns=symbols)
    # top fifth = SUE above the 80th percentile of all surprises filed in the previous 365 days (known by then)
    flat = sue_df.stack().dropna()
    thr = flat.groupby(level=0).apply(lambda s: s.to_list())
    hist_vals, cut_hi, cut_lo = [], {}, {}
    window = []
    for dt in dates:
        if dt in thr.index:
            window += [(dt, x) for x in thr[dt]]
        window = [(a, x) for a, x in window if (dt - a).days <= 365]
        vals = [x for a, x in window if a < dt]
        if len(vals) >= 100:
            cut_hi[dt], cut_lo[dt] = np.percentile(vals, 80), np.percentile(vals, 20)
    hi = pd.Series(cut_hi).reindex(dates).to_numpy()[:, None]
    lo_ = pd.Series(cut_lo).reindex(dates).to_numpy()[:, None]
    pos_surprise = liquid & (sue_m >= hi)
    neg_surprise = liquid & (sue_m <= lo_)
    emit("\n## 2. Post-earnings drift (after the 10-Q is filed)\n")
    emit(f"{int(np.isfinite(sue_m).sum())} quarterly reports with a surprise measure. Buy the top fifth of surprises "
         "at the open after the filing day, hold 60 trading days; up to 30 positions.\n")
    emit(head)
    for cost in COSTS:
        eq, t = book(pos_surprise, sue_m, 60, 30, cost)
        row(f"Top-fifth surprises, costs {cost:.2%}", eq, t)
    eq, t = book(neg_surprise, -sue_m, 60, 30, COSTS[0])
    row("(Bottom-fifth surprises, bought - should lag)", eq, t)
    # event study: 60-day open-to-open return minus the equal-weight universe, by surprise fifth
    emit("\nEvent study, each report's next 60 trading days (open to open) minus the average stock:\n")
    emit("| surprise fifth | reports | excess return | t-stat |\n|---|---|---|---|")
    uni_oo = pd.Series(np.nanmean(np.where(member, np.r_[O[1:] / O[:-1] - 1, np.full((1, O.shape[1]), np.nan)], np.nan),
                                  axis=1), index=dates).fillna(0)
    uni_cum = (1 + uni_oo).cumprod()
    evr = []
    for i, j in zip(*np.where(np.isfinite(sue_m) & liquid)):
        if i + 61 >= len(dates) or i < start:
            continue
        r = O[i + 61, j] / O[i + 1, j] - 1
        if not np.isfinite(r) or abs(r) > 3:
            continue
        evr.append((sue_m[i, j], r - (uni_cum.iloc[i + 60] / uni_cum.iloc[i] - 1), dates[i]))
    evr = pd.DataFrame(evr, columns=["sue", "ex", "date"])
    evr["fifth"] = pd.qcut(evr["sue"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5])
    for k, g in evr.groupby("fifth", observed=True):
        emit(f"| {k} {'(worst)' if k == 1 else '(best)' if k == 5 else ''} | {len(g)} | {g['ex'].mean():+.2%} | "
             f"{g['ex'].mean() / (g['ex'].std() / np.sqrt(len(g))):.1f} |")
    top, bot = evr[evr["fifth"] == 5], evr[evr["fifth"] == 1]
    for lbl, part in (("2014-19", evr[evr["date"] < MID]), ("2020-26", evr[evr["date"] >= MID])):
        t5, t1 = part[part["fifth"] == 5]["ex"].mean(), part[part["fifth"] == 1]["ex"].mean()
        emit(f"\n{lbl}: best fifth {t5:+.2%}, worst fifth {t1:+.2%} (spread {t5 - t1:+.2%}).")
    _ = top, bot

    # --- 3. 52-week high
    hi52 = np.fmax(c.rolling(252, min_periods=240).max(), c)     # today's close always counts toward the high
    ratio = (c / hi52).to_numpy()
    month_end = np.r_[dates.month[1:] != dates.month[:-1], True]
    near_high = liquid & month_end[:, None] & np.isfinite(ratio)
    new_high = liquid & (c >= hi52).to_numpy() & (c.shift(1) < hi52.shift(1)).to_numpy()
    emit("\n## 3. 52-week high\n")
    emit(head)
    for cost in COSTS[:2]:
        eq, t = book(near_high, ratio, 21, 50, cost)
        row(f"Monthly: 50 stocks closest to their 52-week high, costs {cost:.2%}", eq, t)
    eq, t = book(near_high, -ratio, 21, 50, COSTS[0])
    row("(Monthly: 50 furthest from their high - should lag)", eq, t)
    surge = (v / v.rolling(50, min_periods=40).mean().shift(1)).to_numpy()
    for cost in COSTS[:2]:
        eq, t = book(new_high, surge, 20, 20, cost)
        row(f"Swing: new 52-week-high closes, hold 20 days, 20 slots, costs {cost:.2%}", eq, t)

    # --- 4. overnight vs daytime
    emit("\n## 4. Overnight vs daytime returns\n")
    emit("Overnight = buy at the close, sell at the next open; daytime = buy at the open, sell at the close. "
         "Both trade every day, so costs are paid twice a day.\n")
    emit("| | gross return/yr | at 0.02% each way | at 0.05% each way | share of days positive |\n|---|---|---|---|---|")
    so, sc = spy_df["open"].loc[START:END], spy_df["close"].loc[START:END]
    on, day = overnight_split(so, sc)
    stock_on = np.nanmean(np.where(member[1:], O[1:] / C[:-1] - 1, np.nan), axis=1)
    stock_day = np.nanmean(np.where(member, C / O - 1, np.nan), axis=1)
    series = {"SPY overnight": on.dropna(), "SPY daytime": day.dropna(),
              "Average stock overnight": pd.Series(stock_on, index=dates[1:]).loc[START:].clip(-0.5, 0.5),
              "Average stock daytime": pd.Series(stock_day, index=dates).loc[START:].clip(-0.5, 0.5)}
    for k, r in series.items():
        yrs = len(r) / 252
        g = (1 + r).prod() ** (1 / yrs) - 1
        n2 = (1 + r - 2 * 0.0002).prod() ** (1 / yrs) - 1
        n5 = (1 + r - 2 * 0.0005).prod() ** (1 / yrs) - 1
        emit(f"| {k} | {g:+.1%} | {n2:+.1%} | {n5:+.1%} | {(r > 0).mean():.0%} |")

    OUT.mkdir(exist_ok=True)
    (OUT / "swing_edges.md").write_text("\n".join(lines) + "\n")
    print(f"\nwrote {OUT / 'swing_edges.md'}")


if __name__ == "__main__":
    main()
